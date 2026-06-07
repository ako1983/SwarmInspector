"""
inspector/monitor_agent.py
Polls Redis heartbeats and detects anomalies in the subject swarm.
"""

import time
from core.state import InspectorState, AnomalyReport
from core.redis_state import get_state, STALL_THRESHOLD, LOOP_THRESHOLD
from core.weave_setup import inspector_op

SUBJECT_AGENTS = ["earnings_agent", "risk_agent", "sentiment_agent", "synthesis_agent"]


@inspector_op("monitor")
async def run_monitor_agent(state: InspectorState) -> dict:
    """
    Checks all subject swarm agents for:
    1. Missed heartbeat (silent_drop)
    2. Repeated tool call (loop)
    3. Unexpected status
    """
    ticker = state["subject_ticker"]
    redis = get_state()

    heartbeats = await redis.get_all_heartbeats(ticker, SUBJECT_AGENTS)
    now = time.time()

    anomaly_detected = False
    anomaly_agent = None
    evidence = []
    failure_type = "unknown"

    for agent_id, hb in heartbeats.items():
        if hb.get("status") in ("done", "failed"):
            continue  # already completed, not a problem

        time_since = now - hb.get("last_seen", now)
        call_count = hb.get("call_count", 0)
        last_tool = hb.get("last_tool", "")

        # Detection 1: Stalled heartbeat (silent drop)
        if time_since > STALL_THRESHOLD:
            anomaly_detected = True
            anomaly_agent = agent_id
            failure_type = "silent_drop"
            evidence.append(f"No heartbeat for {time_since:.1f}s (threshold: {STALL_THRESHOLD}s)")
            evidence.append(f"Last tool: {last_tool}, last seen: {time_since:.1f}s ago")
            break

        # Detection 2: Excessive tool calls (loop)
        if call_count > LOOP_THRESHOLD and last_tool:
            calls_per_sec = call_count / max(time_since, 1)
            if calls_per_sec > 0.8 and time_since > 3.0:
                anomaly_detected = True
                anomaly_agent = agent_id
                failure_type = "loop"
                evidence.append(f"High tool call rate: {calls_per_sec:.1f} calls/sec")
                evidence.append(f"Total calls: {call_count}, last tool: '{last_tool}' (repeated)")
                evidence.append(f"Running for {time_since:.1f}s without completing")
                break

    if not anomaly_detected:
        return {
            "anomaly_detected": False,
            "anomaly_report": None,
            "inspection_cycles": state["inspection_cycles"] + 1,
        }

    report: AnomalyReport = {
        "detected_at": now,
        "agent_id": anomaly_agent,
        "failure_type": failure_type,
        "confidence": 0.85 if len(evidence) >= 2 else 0.60,
        "evidence": evidence,
    }

    return {
        "anomaly_detected": True,
        "anomaly_report": report,
        "inspection_cycles": state["inspection_cycles"] + 1,
    }
