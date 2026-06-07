"""
core/state.py
Shared state schemas for the subject swarm and the inspector swarm.
Both graphs operate on typed state — LangGraph enforces this.
"""

from typing import TypedDict, Annotated, Literal
from operator import add
import time


# ── Subject Swarm State ──────────────────────────────────────────────────────

class AgentHeartbeat(TypedDict):
    agent_id: str
    last_seen: float          # unix timestamp
    call_count: int           # total tool calls made
    last_tool: str            # last tool name called
    status: Literal["running", "stalled", "failed", "done"]


class FinancialSwarmState(TypedDict):
    # Input
    ticker: str
    analysis_depth: Literal["quick", "standard", "deep"]

    # Agent outputs (populated as agents complete)
    earnings_result: dict | None
    risk_result: dict | None
    sentiment_result: dict | None
    synthesis_result: str | None

    # Observability
    heartbeats: dict[str, AgentHeartbeat]   # agent_id -> heartbeat
    tool_call_log: Annotated[list[dict], add]  # append-only log
    errors: Annotated[list[str], add]

    # Inspector signals
    failure_injected: bool
    failure_type: str | None     # "loop" | "silent_drop" | "context_drift"
    failed_agent: str | None


# ── Inspector Swarm State ────────────────────────────────────────────────────

class AnomalyReport(TypedDict):
    detected_at: float
    agent_id: str
    failure_type: Literal["loop", "silent_drop", "context_drift", "unknown"]
    confidence: float           # 0.0 – 1.0
    evidence: list[str]         # human-readable evidence strings


class RecoveryAction(TypedDict):
    action_type: Literal["restart", "modify_prompt", "skip_agent", "escalate"]
    target_agent: str
    payload: dict               # action-specific data (e.g. new prompt, timeout)
    executed_at: float
    success: bool


class InspectorState(TypedDict):
    # Shared reference to the subject swarm's state
    subject_ticker: str

    # Monitor outputs
    anomaly_detected: bool
    anomaly_report: AnomalyReport | None

    # Diagnostician outputs
    diagnosis: str | None        # natural language diagnosis
    failure_classification: str | None

    # Healer outputs
    recovery_action: RecoveryAction | None
    recovery_log: Annotated[list[str], add]

    # Inspector loop control
    inspection_cycles: int
    max_cycles: int


# ── Shared Redis Key Conventions ─────────────────────────────────────────────

def heartbeat_key(ticker: str, agent_id: str) -> str:
    return f"swarm:{ticker}:heartbeat:{agent_id}"

def swarm_status_key(ticker: str) -> str:
    return f"swarm:{ticker}:status"

def tool_call_count_key(ticker: str, agent_id: str) -> str:
    return f"swarm:{ticker}:tool_calls:{agent_id}"


# ── Initial State Factories ───────────────────────────────────────────────────

def make_swarm_state(ticker: str, depth: str = "standard") -> FinancialSwarmState:
    return FinancialSwarmState(
        ticker=ticker,
        analysis_depth=depth,
        earnings_result=None,
        risk_result=None,
        sentiment_result=None,
        synthesis_result=None,
        heartbeats={},
        tool_call_log=[],
        errors=[],
        failure_injected=False,
        failure_type=None,
        failed_agent=None,
    )

def make_inspector_state(ticker: str, max_cycles: int = 30) -> InspectorState:
    return InspectorState(
        subject_ticker=ticker,
        anomaly_detected=False,
        anomaly_report=None,
        diagnosis=None,
        failure_classification=None,
        recovery_action=None,
        recovery_log=[],
        inspection_cycles=0,
        max_cycles=max_cycles,
    )
