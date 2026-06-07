"""
api/server.py
FastAPI server — CopilotKit-compatible backend + REST status endpoints.

Run: uvicorn api.server:app --reload --port 8000
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from core.redis_state import init_state, get_state
from core.weave_setup import init_weave, get_weave_url

# ── Lifespan: connect to Redis and init Weave on startup ─────────────────────

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
    allow_origins=["*"],   # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class InjectFailureRequest(BaseModel):
    ticker: str
    agent_id: str
    failure_type: str   # "loop" | "silent_drop" | "context_drift"


class RunSwarmRequest(BaseModel):
    ticker: str = "NVDA"
    inject_failure: bool = False
    failure_agent: str = "risk_agent"
    failure_type: str = "loop"
    failure_delay: float = 10.0


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/status/{ticker}")
async def get_status(ticker: str):
    """Get real-time agent status for a ticker."""
    redis = get_state()
    summary = await redis.get_swarm_summary(ticker)
    return {
        **summary,
        "weave_url": get_weave_url(),
    }


@app.post("/inject-failure")
async def inject_failure(req: InjectFailureRequest):
    """Manually inject a failure into an agent (for demo use)."""
    redis = get_state()
    await redis.inject_failure(req.ticker, req.agent_id, req.failure_type)
    return {
        "ok": True,
        "message": f"Injected {req.failure_type} into {req.agent_id} for {req.ticker}",
    }


@app.post("/run-swarm")
async def run_swarm_endpoint(req: RunSwarmRequest):
    """
    Start a swarm analysis run as a background task.
    Returns immediately — poll /status/{ticker} for progress.
    """
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
    url = get_weave_url()
    return {"url": url}


# ── CopilotKit integration ────────────────────────────────────────────────────
# CopilotKit expects a POST /copilotkit endpoint that streams responses.
# We implement a minimal version that exposes swarm status as context.

@app.post("/copilotkit")
async def copilotkit_endpoint(request: dict):
    """
    Minimal CopilotKit-compatible endpoint.
    Provides swarm status context and handles natural language queries.
    """
    try:
        from copilotkit.integrations.fastapi import add_fastapi_endpoint
        from copilotkit import CopilotKitSDK, Action, LangGraphAgent
        # If copilotkit is installed, use it properly
        pass
    except ImportError:
        pass

    # Fallback: respond with current swarm status
    ticker = request.get("context", {}).get("ticker", "NVDA")
    redis = get_state()
    summary = await redis.get_swarm_summary(ticker)

    return {
        "message": f"SwarmInspector monitoring {ticker}. "
                   f"Agents: {list(summary.get('agents', {}).keys())}. "
                   f"Weave URL: {get_weave_url() or 'not configured'}",
        "status": summary,
    }


# ── Server-Sent Events: live status stream ────────────────────────────────────

@app.get("/stream/{ticker}")
async def stream_status(ticker: str):
    """SSE endpoint — the React dashboard subscribes to this for live updates."""

    async def event_generator():
        redis = get_state()
        while True:
            summary = await redis.get_swarm_summary(ticker)
            yield f"data: {summary}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
