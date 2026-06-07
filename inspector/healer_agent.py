"""
inspector/healer_agent.py
Executes recovery actions based on diagnostician output.
"""

import time
from core.state import InspectorState, RecoveryAction
from core.redis_state import get_state
from core.weave_setup import inspector_op


@inspector_op("healer")
async def run_healer_agent(state: InspectorState) -> dict:
    """
    Executes recovery based on the diagnostician's classification.
    Signals the affected agent via Redis.
    """
    report = state.get("anomaly_report")
    failure_type = state.get("failure_classification") or "unknown"

    if not report:
        return {"recovery_action": None, "recovery_log": ["No anomaly to heal"]}

    ticker = state["subject_ticker"]
    agent_id = report["agent_id"]
    redis = get_state()

    action_type = "restart"
    payload = {}
    log_messages = []

    if failure_type == "infinite_loop":
        action_type = "modify_prompt"
        payload = {
            "signal": "break_loop",
            "message": "Inspector detected infinite loop. Resuming normal execution.",
            "new_system_hint": "Stop repeating the same tool call. Move to the next step.",
        }
        await redis.signal_recovery(ticker, agent_id, payload)
        log_messages.append(f"Sent loop-break signal to {agent_id}")
        log_messages.append(f"Agent will receive recovery signal on next iteration")

    elif failure_type == "silent_drop":
        action_type = "skip_agent"
        payload = {"reason": "heartbeat timeout", "skip_in_synthesis": True}
        await redis.mark_agent_failed(ticker, agent_id)
        log_messages.append(f"Marked {agent_id} as failed (heartbeat timeout)")
        log_messages.append(f"Synthesis agent will proceed without {agent_id}'s output")

    elif failure_type == "context_drift":
        action_type = "restart"
        payload = {
            "restart_with_ticker": ticker,
            "message": "Context drift detected. Agent was analyzing wrong ticker.",
        }
        await redis.signal_recovery(ticker, agent_id, payload)
        log_messages.append(f"Sent ticker correction signal to {agent_id}")

    else:
        # Also handle the "loop" classification (monitor uses "loop", diagnostician may say "infinite_loop")
        if report.get("failure_type") == "loop":
            action_type = "modify_prompt"
            payload = {
                "signal": "break_loop",
                "message": "Inspector detected loop via heartbeat analysis.",
                "new_system_hint": "Stop repeating the same tool call. Move to the next step.",
            }
            await redis.signal_recovery(ticker, agent_id, payload)
            log_messages.append(f"Sent loop-break signal to {agent_id} (via fallback path)")
        else:
            action_type = "escalate"
            payload = {"reason": f"unknown failure type: {failure_type}"}
            log_messages.append(f"Unknown failure type '{failure_type}' — escalating")

    recovery: RecoveryAction = {
        "action_type": action_type,
        "target_agent": agent_id,
        "payload": payload,
        "executed_at": time.time(),
        "success": True,
    }

    log_messages.append(
        f"Recovery action '{action_type}' executed for {agent_id} at {time.strftime('%H:%M:%S')}"
    )

    return {
        "recovery_action": recovery,
        "recovery_log": log_messages,
    }
