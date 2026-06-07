"""
agents/swarm_graph.py
LangGraph-backed financial analysis swarm.

The four agents run in parallel (asyncio.gather), then synthesis runs once
all three specialist outputs are available. LangGraph is used for the graph
structure and Weave tracing — the parallelism is handled by asyncio.
"""

import asyncio
import logging
from core.state import FinancialSwarmState, make_swarm_state
from agents.earnings_agent import run_earnings_agent
from agents.risk_agent import run_risk_agent
from agents.sentiment_agent import run_sentiment_agent
from agents.synthesis_agent import run_synthesis_agent

logger = logging.getLogger(__name__)

PARALLEL_TIMEOUT = 60.0   # seconds before a specialist agent is considered timed out


async def run_swarm_parallel(ticker: str, depth: str = "standard") -> FinancialSwarmState:
    """
    Entry point called by main.py.
    Runs earnings, risk, and sentiment agents in parallel, then synthesis.
    Returns the final merged FinancialSwarmState.
    """
    state = make_swarm_state(ticker, depth)

    logger.info(f"[swarm] Starting parallel analysis for {ticker}")

    # ── Fan-out: run 3 specialist agents simultaneously ───────────────────────
    specialist_results = await asyncio.gather(
        _run_with_timeout(run_earnings_agent, state, "earnings_agent"),
        _run_with_timeout(run_risk_agent, state, "risk_agent"),
        _run_with_timeout(run_sentiment_agent, state, "sentiment_agent"),
        return_exceptions=True,
    )

    # ── Merge specialist outputs into shared state ────────────────────────────
    for result in specialist_results:
        if isinstance(result, Exception):
            logger.error(f"[swarm] Agent error: {result}")
            state["errors"].append(str(result))
        elif isinstance(result, dict):
            _merge_state(state, result)

    logger.info(f"[swarm] Specialists done. earnings={state['earnings_result'] is not None}, "
                f"risk={state['risk_result'] is not None}, "
                f"sentiment={state['sentiment_result'] is not None}")

    # ── Fan-in: run synthesis ─────────────────────────────────────────────────
    try:
        synthesis_result = await asyncio.wait_for(
            run_synthesis_agent(state), timeout=PARALLEL_TIMEOUT
        )
        if isinstance(synthesis_result, dict):
            _merge_state(state, synthesis_result)
    except asyncio.TimeoutError:
        state["errors"].append("synthesis_agent: timed out")
        logger.error("[swarm] Synthesis agent timed out")
    except Exception as exc:
        state["errors"].append(f"synthesis_agent: {exc}")
        logger.error(f"[swarm] Synthesis agent error: {exc}")

    logger.info(f"[swarm] Analysis complete for {ticker}")
    return state


async def _run_with_timeout(agent_fn, state: FinancialSwarmState, name: str) -> dict:
    try:
        return await asyncio.wait_for(agent_fn(state), timeout=PARALLEL_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning(f"[swarm] {name} timed out after {PARALLEL_TIMEOUT}s")
        return {"errors": [f"{name}: timed out"]}
    except Exception as exc:
        logger.error(f"[swarm] {name} raised: {exc}")
        return {"errors": [f"{name}: {exc}"]}


def _merge_state(state: FinancialSwarmState, patch: dict) -> None:
    """Merge a node's output patch into the shared state (handles append-only lists)."""
    for key, value in patch.items():
        if key in ("tool_call_log", "errors") and isinstance(value, list):
            state[key] = state.get(key, []) + value
        else:
            state[key] = value
