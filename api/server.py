"""
api/server.py
FastAPI server — CopilotKit runtime + REST status endpoints.

Run: uvicorn api.server:app --reload --port 8000
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from core.redis_state import init_state, get_state
from core.weave_setup import init_weave, get_weave_url

# ── CopilotKit setup ──────────────────────────────────────────────────────────

from copilotkit import CopilotKitSDK, Action
from copilotkit.parameter import SimpleParameter, StringParameter
from copilotkit.integrations.fastapi import add_fastapi_endpoint


async def _inject_failure_action(ticker: str, agent: str, failure_type: str) -> str:
    """Server-side action: inject a failure into an agent."""
    redis = get_state()
    await redis.inject_failure(ticker, agent, failure_type)
    return f"Injected {failure_type} into {agent} for {ticker}. Inspector will detect this within ~5 seconds."


async def _start_analysis_action(ticker: str, inject: bool = False) -> str:
    """Server-side action: start a swarm analysis run."""
    from agents.swarm_graph import run_swarm_parallel
    from inspector.inspector_graph import run_inspector_loop

    redis = get_state()
    stop_event = asyncio.Event()

    async def _run():
        tasks = [
            asyncio.create_task(run_swarm_parallel(ticker)),
            asyncio.create_task(run_inspector_loop(ticker, stop_event=stop_event)),
        ]
        if inject:
            async def _delayed():
                await asyncio.sleep(8.0)
                await redis.inject_failure(ticker, "risk_agent", "loop")
            tasks.append(asyncio.create_task(_delayed()))
        await asyncio.gather(*tasks, return_exceptions=True)
        stop_event.set()

    asyncio.create_task(_run())
    mode = "with loop failure injection in 8s" if inject else "clean (no failure)"
    return f"Swarm analysis started for {ticker} ({mode}). Poll /status/{ticker} for updates."


async def _get_status_action(ticker: str) -> dict:
    """Server-side action: get current swarm status."""
    redis = get_state()
    summary = await redis.get_swarm_summary(ticker)
    return {
        **summary,
        "weave_url": get_weave_url(),
    }


sdk = CopilotKitSDK(
    actions=[
        Action(
            name="inject_failure",
            description=(
                "Inject a failure into a specific agent in the financial analysis swarm. "
                "Use this to demonstrate self-healing. "
                "Failure types: 'loop' (infinite tool loop) or 'silent_drop' (agent goes silent)."
            ),
            parameters=[
                SimpleParameter(name="ticker", type="string",
                               description="Stock ticker (NVDA, AAPL, TSLA, MSFT)"),
                SimpleParameter(name="agent", type="string",
                               description="Agent to target: earnings_agent, risk_agent, sentiment_agent"),
                SimpleParameter(name="failure_type", type="string",
                               description="Type of failure: 'loop' or 'silent_drop'"),
            ],
            handler=_inject_failure_action,
        ),
        Action(
            name="start_analysis",
            description=(
                "Start a fresh swarm analysis run for a stock ticker. "
                "Optionally inject a loop failure after 8s to demo self-healing."
            ),
            parameters=[
                SimpleParameter(name="ticker", type="string",
                               description="Stock ticker to analyze (NVDA, AAPL, TSLA, MSFT)"),
                SimpleParameter(name="inject", type="boolean",
                               description="If true, inject a loop failure after 8s"),
            ],
            handler=_start_analysis_action,
        ),
        Action(
            name="get_status",
            description="Get the current status of all agents in the swarm for a ticker.",
            parameters=[
                SimpleParameter(name="ticker", type="string",
                               description="Stock ticker (NVDA, AAPL, TSLA, MSFT)"),
            ],
            handler=_get_status_action,
        ),
    ]
)


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

# Wire up CopilotKit at /copilotkit
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
    return {"status": "ok", "timestamp": time.time(), "weave_url": get_weave_url()}


@app.get("/status/{ticker}")
async def get_status(ticker: str):
    redis = get_state()
    summary = await redis.get_swarm_summary(ticker)
    return {**summary, "weave_url": get_weave_url()}


@app.post("/inject-failure")
async def inject_failure(req: InjectFailureRequest):
    redis = get_state()
    await redis.inject_failure(req.ticker, req.agent_id, req.failure_type)
    return {
        "ok": True,
        "message": f"Injected {req.failure_type} into {req.agent_id} for {req.ticker}",
    }


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
    return {
        "ok": True,
        "ticker": req.ticker,
        "message": f"Swarm started for {req.ticker}. Poll /status/{req.ticker} for updates.",
    }


async def _delayed_inject(redis, ticker, agent, failure_type, delay):
    await asyncio.sleep(delay)
    await redis.inject_failure(ticker, agent, failure_type)


@app.get("/weave-url")
async def weave_url_endpoint():
    return {"url": get_weave_url()}


@app.get("/stream/{ticker}")
async def stream_status(ticker: str):
    """SSE endpoint for live status updates."""
    import json

    async def event_generator():
        redis = get_state()
        while True:
            summary = await redis.get_swarm_summary(ticker)
            yield f"data: {json.dumps(summary)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
