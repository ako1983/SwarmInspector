"""
agents/synthesis_agent.py
Synthesizes outputs from the three specialist agents into a final report.
Runs after the other agents complete (or time out).
"""

import asyncio
import time
from anthropic import AsyncAnthropic
from core.state import FinancialSwarmState
from core.redis_state import get_state
from core.weave_setup import agent_op

client = AsyncAnthropic()
AGENT_ID = "synthesis_agent"


@agent_op("synthesis_agent")
async def run_synthesis_agent(state: FinancialSwarmState) -> dict:
    ticker = state["ticker"]
    redis = get_state()
    call_count = 0

    async def heartbeat(tool: str = "") -> None:
        nonlocal call_count
        call_count += 1
        await redis.write_heartbeat(ticker, AGENT_ID, tool, call_count)

    await heartbeat("start")

    earnings = state.get("earnings_result")
    risk = state.get("risk_result")
    sentiment = state.get("sentiment_result")

    # Build context from available results (gracefully handles missing agents)
    sections = [f"# SwarmInspector Financial Analysis: {ticker}\n"]

    earnings_text = earnings.get("analysis", "Earnings data unavailable.") if earnings else "Earnings agent did not complete."
    risk_text = risk.get("analysis", "Risk data unavailable.") if risk else "Risk agent did not complete (recovered from failure)."
    sentiment_text = sentiment.get("analysis", "Sentiment data unavailable.") if sentiment else "Sentiment agent did not complete."

    recovered = risk and risk.get("recovered_from_loop", False)

    await heartbeat("llm_synthesis")

    prompt = f"""You are a senior equity analyst writing a final investment brief for {ticker}.
Synthesize the following specialist reports into a coherent 5-6 sentence summary.

EARNINGS ANALYSIS:
{earnings_text}

RISK ASSESSMENT:
{risk_text}{"" if not recovered else " [NOTE: Risk agent recovered from an infinite loop — data is valid]"}

MARKET SENTIMENT:
{sentiment_text}

Write a balanced, professional synthesis that:
1. Opens with the single most important takeaway
2. Integrates insights across all three dimensions (earnings, risk, sentiment)
3. Notes any important divergences between the analyses
4. Closes with an actionable investment stance (bullish/neutral/bearish + timeframe)

Use professional financial language. No bullet points — flowing prose only.
"""

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    synthesis_text = response.content[0].text

    # Add recovery note if applicable
    if recovered:
        synthesis_text += (
            "\n\n[SwarmInspector Note: The Risk agent entered an infinite loop during analysis. "
            "The Inspector swarm detected the anomaly, diagnosed it as an infinite_loop, and "
            "dispatched a recovery signal. The agent resumed normal execution and its analysis "
            "is included above. Full trace available in W&B Weave.]"
        )

    await heartbeat("done")
    await redis.mark_agent_done(ticker, AGENT_ID)

    return {
        "synthesis_result": synthesis_text,
        "tool_call_log": [{
            "agent": AGENT_ID,
            "tools_called": call_count,
            "ticker": ticker,
            "timestamp": time.time(),
        }]
    }
