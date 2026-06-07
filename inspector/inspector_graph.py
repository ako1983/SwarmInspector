"""
inspector/inspector_graph.py
The inspector swarm control loop.

Loop: Monitor → (if anomaly) Diagnostician → Healer → back to Monitor
Runs as a background task alongside the subject swarm.
"""

import asyncio
import logging
from core.state import InspectorState, make_inspector_state
from inspector.monitor_agent import run_monitor_agent
from inspector.diagnostician_agent import run_diagnostician_agent
from inspector.healer_agent import run_healer_agent

logger = logging.getLogger(__name__)


def _merge(state: InspectorState, patch: dict) -> None:
    for key, value in patch.items():
        if key == "recovery_log" and isinstance(value, list):
            state[key] = state.get(key, []) + value
        else:
            state[key] = value


async def run_inspector_loop(
    ticker: str,
    poll_interval: float = 2.0,
    stop_event: asyncio.Event | None = None,
    max_cycles: int = 30,
) -> InspectorState:
    """
    Entry point called by main.py.
    Continuously monitors the subject swarm and heals failures.
    Returns when stop_event is set or max_cycles is reached.
    """
    state = make_inspector_state(ticker, max_cycles=max_cycles)
    healed_agents: set[str] = set()

    logger.info(f"[inspector] Starting inspector loop for {ticker}")

    while True:
        # Respect stop signal
        if stop_event and stop_event.is_set():
            logger.info("[inspector] Stop event received, exiting")
            break

        # Respect cycle limit
        if state["inspection_cycles"] >= state["max_cycles"]:
            logger.info(f"[inspector] Reached max cycles ({max_cycles}), exiting")
            break

        try:
            # ── Monitor ───────────────────────────────────────────────────────
            monitor_patch = await run_monitor_agent(state)
            _merge(state, monitor_patch)

            if state["anomaly_detected"]:
                agent_id = state["anomaly_report"]["agent_id"]

                if agent_id in healed_agents:
                    # Already healed this agent — don't spam recovery signals
                    logger.debug(f"[inspector] {agent_id} already healed, skipping")
                    state["anomaly_detected"] = False
                    state["anomaly_report"] = None
                    await asyncio.sleep(poll_interval)
                    continue

                logger.warning(
                    f"[inspector] Anomaly detected: {agent_id} "
                    f"({state['anomaly_report']['failure_type']}, "
                    f"confidence={state['anomaly_report']['confidence']:.0%})"
                )

                # ── Diagnostician ─────────────────────────────────────────────
                diag_patch = await run_diagnostician_agent(state)
                _merge(state, diag_patch)
                logger.info(f"[inspector] Diagnosis: {state.get('failure_classification')} — {state.get('diagnosis', '')[:80]}")

                # ── Healer ────────────────────────────────────────────────────
                heal_patch = await run_healer_agent(state)
                _merge(state, heal_patch)

                for msg in heal_patch.get("recovery_log", []):
                    logger.info(f"[inspector] {msg}")

                healed_agents.add(agent_id)

                # Reset for next cycle
                state["anomaly_detected"] = False
                state["anomaly_report"] = None

        except Exception as exc:
            logger.error(f"[inspector] Error in inspection cycle: {exc}")

        await asyncio.sleep(poll_interval)

    logger.info(f"[inspector] Inspector loop finished after {state['inspection_cycles']} cycles")
    return state
