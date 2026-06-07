"""
api/server.py
FastAPI server — CopilotKit runtime (Anthropic-powered) + REST status endpoints.

Run: uvicorn api.server:app --reload --port 8000
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from core.redis_state import init_state, get_state
from core.weave_setup import init_weave, get_weave_url

# ── CopilotKit + LangGraph (Anthropic) ───────────────────────────────────────

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from copilotkit import CopilotKitSDK, LangGraphAGUIAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint


@tool
async def inject_swarm_failure(ticker: str, agent: str, failure_type: str) -> str:
    """
    Inject a failure into an agent in the financial analysis swarm.
    failure_type must be 'loop' (infinite tool loop) or 'silent_drop' (agent stops heartbeating).
    agent must be one of: earnings_agent, risk_agent, sentiment_agent.
    """
    redis = get_state()
    await redis.inject_failure(ticker, agent, failure_type)
    return (
        f"Injected {failure_type} into {agent} for {ticker}. "
        f"The inspector will detect this within ~5 seconds."
    )


@tool
async def start_swarm_analysis(ticker: str, inject_loop: bool = False) -> str:
    """
    Start a fresh financial analysis swarm for a stock ticker.
    Set inject_loop=True to auto-inject a loop failure after 8s (demo mode).
    """
    from agents.swarm_graph import run_swarm_parallel
    from inspector.inspector_graph import run_inspector_loop

    redis = get_state()
    stop_event = asyncio.Event()

    async def _run():
        tasks = [
            asyncio.create_task(run_swarm_parallel(ticker)),
            asyncio.create_task(run_inspector_loop(ticker, stop_event=stop_event)),
        ]
        if inject_loop:
            async def _inject():
                await asyncio.sleep(8.0)
                await redis.inject_failure(ticker, "risk_agent", "loop")
            tasks.append(asyncio.create_task(_inject()))
        await asyncio.gather(*tasks, return_exceptions=True)
        stop_event.set()

    asyncio.create_task(_run())
    mode = "with loop injection in 8s" if inject_loop else "clean run"
    return f"Swarm started for {ticker} ({mode}). Watch the dashboard for live updates."


@tool
async def get_swarm_status(ticker: str) -> str:
    """Get the current status of all agents in the swarm for a stock ticker."""
    redis = get_state()
    summary = await redis.get_swarm_summary(ticker)
    agents = summary.get("agents", {})
    lines = [f"Swarm status for {ticker}:"]
    for agent_id, hb in agents.items():
        lines.append(
            f"  {agent_id}: {hb.get('status', 'unknown')} "
            f"({hb.get('call_count', 0)} tool calls, "
            f"last seen {time.time() - hb.get('last_seen', time.time()):.1f}s ago)"
        )
    return "\n".join(lines) if len(lines) > 1 else f"No agents active for {ticker} yet."


def _build_copilot_graph():
    """Build a LangGraph ReAct agent using Anthropic Claude as the LLM."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return None

    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        anthropic_api_key=anthropic_key,
        max_tokens=1024,
    )

    tools = [inject_swarm_failure, start_swarm_analysis, get_swarm_status]
    llm_with_tools = llm.bind_tools(tools)

    system_msg = SystemMessage(content=(
        "You are SwarmInspector's AI assistant. You monitor a financial analysis swarm "
        "of 4 agents (earnings, risk, sentiment, synthesis) and an inspector swarm "
        "(monitor → diagnostician → healer). "
        "You can inject failures, start analyses, and get status. "
        "Be concise and technical. Reference specific agent names and metrics."
    ))

    def call_model(state: MessagesState):
        response = llm_with_tools.invoke([system_msg] + state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


# Build the graph at import time (None if no API key — sidebar will warn)
_copilot_graph = _build_copilot_graph()

if _copilot_graph:
    sdk = CopilotKitSDK(
        agents=[
            LangGraphAGUIAgent(
                name="swarm_assistant",
                description="SwarmInspector AI — monitors and controls the financial analysis swarm",
                graph=_copilot_graph,
            )
        ]
    )
else:
    sdk = CopilotKitSDK(agents=[])


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_state()
    init_weave()
    yield


app = FastAPI(
    title="SwarmInspector API",
    description="Backend for the SwarmInspector demo dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_fastapi_endpoint(app, sdk, "/copilotkit")


# ── Pydantic models ───────────────────────────────────────────────────────────

class InjectFailureRequest(BaseModel):
    ticker: str
    agent_id: str
    failure_type: str


class RunSwarmRequest(BaseModel):
    ticker: str = "NVDA"
    inject_failure: bool = False
    failure_agent: str = "risk_agent"
    failure_type: str = "loop"
    failure_delay: float = 10.0


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "weave_url": get_weave_url(),
        "copilot_ready": _copilot_graph is not None,
    }


@app.get("/status/{ticker}")
async def get_status(ticker: str):
    redis = get_state()
    summary = await redis.get_swarm_summary(ticker)
    return {**summary, "weave_url": get_weave_url()}


@app.post("/inject-failure")
async def inject_failure(req: InjectFailureRequest):
    redis = get_state()
    await redis.inject_failure(req.ticker, req.agent_id, req.failure_type)
    return {"ok": True, "message": f"Injected {req.failure_type} into {req.agent_id} for {req.ticker}"}


@app.post("/run-swarm")
async def run_swarm_endpoint(req: RunSwarmRequest):
    from agents.swarm_graph import run_swarm_parallel
    from inspector.inspector_graph import run_inspector_loop

    stop_event = asyncio.Event()
    redis = get_state()

    async def _run():
        tasks = [
            asyncio.create_task(run_swarm_parallel(req.ticker)),
            asyncio.create_task(run_inspector_loop(req.ticker, stop_event=stop_event)),
        ]
        if req.inject_failure:
            tasks.append(asyncio.create_task(
                _delayed_inject(redis, req.ticker, req.failure_agent,
                                req.failure_type, req.failure_delay)
            ))
        await asyncio.gather(*tasks, return_exceptions=True)
        stop_event.set()

    asyncio.create_task(_run())
    return {"ok": True, "ticker": req.ticker,
            "message": f"Swarm started for {req.ticker}. Poll /status/{req.ticker} for updates."}


async def _delayed_inject(redis, ticker, agent, failure_type, delay):
    await asyncio.sleep(delay)
    await redis.inject_failure(ticker, agent, failure_type)


@app.get("/weave-url")
async def weave_url_endpoint():
    return {"url": get_weave_url()}


@app.get("/stream/{ticker}")
async def stream_status(ticker: str):
    """SSE endpoint for live agent status."""
    import json

    async def event_generator():
        redis = get_state()
        while True:
            summary = await redis.get_swarm_summary(ticker)
            yield f"data: {json.dumps(summary)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
