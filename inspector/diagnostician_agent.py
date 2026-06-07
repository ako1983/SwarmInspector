"""
inspector/diagnostician_agent.py
Classifies failure type and produces a human-readable diagnosis via LLM.
"""

from anthropic import AsyncAnthropic
from core.state import InspectorState
from core.weave_setup import inspector_op
from core.mock_llm import is_mock

client = AsyncAnthropic()


@inspector_op("diagnostician")
async def run_diagnostician_agent(state: InspectorState) -> dict:
    """
    Takes the anomaly report from the monitor and produces:
    1. A classification (confirmed failure type)
    2. A human-readable diagnosis
    3. A recommended recovery action type
    """
    report = state.get("anomaly_report")
    if not report:
        return {"diagnosis": None, "failure_classification": None}

    evidence_str = "\n".join(f"- {e}" for e in report["evidence"])

    prompt = f"""You are an AI system diagnostician analyzing a multi-agent financial analysis swarm.

An anomaly has been detected in agent: {report['agent_id']}
Initial classification: {report['failure_type']}
Confidence: {report['confidence']*100:.0f}%

Evidence:
{evidence_str}

Based on this evidence, provide:
1. CONFIRMED FAILURE TYPE: (infinite_loop | silent_drop | context_drift | unknown)
2. ROOT CAUSE: One sentence explaining what likely went wrong
3. RECOMMENDED ACTION: (restart | modify_prompt | skip_agent | escalate)
4. URGENCY: (low | medium | high)
5. DIAGNOSIS: 2-3 sentence narrative for the dashboard

Format your response exactly as:
FAILURE_TYPE: <type>
ROOT_CAUSE: <sentence>
ACTION: <action>
URGENCY: <level>
DIAGNOSIS: <narrative>
"""

    if is_mock():
        # Return a deterministic structured response based on initial classification
        ft = report.get("failure_type", "unknown")
        type_map = {"loop": "infinite_loop", "silent_drop": "silent_drop", "context_drift": "context_drift"}
        action_map = {"loop": "modify_prompt", "silent_drop": "skip_agent", "context_drift": "restart"}
        confirmed = type_map.get(ft, "unknown")
        action = action_map.get(ft, "escalate")
        text = (
            f"FAILURE_TYPE: {confirmed}\n"
            f"ROOT_CAUSE: Agent entered a deterministic failure state detected via heartbeat analysis.\n"
            f"ACTION: {action}\n"
            f"URGENCY: high\n"
            f"DIAGNOSIS: The {report['agent_id']} has been flagged with a {confirmed} failure. "
            f"Evidence shows {report['evidence'][0] if report['evidence'] else 'anomalous behavior'}. "
            f"Inspector is dispatching recovery signal to restore normal operation."
        )
    else:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text

    # Parse structured response
    lines = {
        line.split(": ")[0]: ": ".join(line.split(": ")[1:])
        for line in text.strip().split("\n") if ": " in line
    }

    confirmed_type = lines.get("FAILURE_TYPE", report["failure_type"])
    diagnosis = lines.get("DIAGNOSIS", "Agent failure detected. Recovery in progress.")

    return {
        "failure_classification": confirmed_type,
        "diagnosis": diagnosis,
    }
