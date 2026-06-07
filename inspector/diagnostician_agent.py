"""
inspector/diagnostician_agent.py
Classifies failure type and produces a human-readable diagnosis via LLM.
"""

from anthropic import AsyncAnthropic
from core.state import InspectorState
from core.weave_setup import inspector_op

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
