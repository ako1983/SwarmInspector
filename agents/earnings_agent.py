"""
agents/earnings_agent.py
Analyzes earnings data for a given ticker.
"""

import asyncio
import time
from anthropic import AsyncAnthropic
from core.state import FinancialSwarmState
from core.redis_state import get_state
from core.weave_setup import agent_op

client = AsyncAnthropic()
AGENT_ID = "earnings_agent"


# ── Mock tools ────────────────────────────────────────────────────────────────

async def fetch_eps_data(ticker: str) -> dict:
    await asyncio.sleep(0.3)
    data = {
        "AAPL": {
            "eps_actual": 2.18, "eps_estimate": 2.10, "beat_pct": 3.8,
            "yoy_growth": 7.5, "quarters": [1.89, 1.96, 2.05, 2.18],
        },
        "NVDA": {
            "eps_actual": 6.12, "eps_estimate": 5.59, "beat_pct": 9.5,
            "yoy_growth": 85.0, "quarters": [2.48, 3.71, 4.93, 6.12],
        },
        "TSLA": {
            "eps_actual": 0.71, "eps_estimate": 0.68, "beat_pct": 4.4,
            "yoy_growth": -9.0, "quarters": [0.85, 0.78, 0.66, 0.71],
        },
    }
    return data.get(ticker, {
        "eps_actual": 1.50, "eps_estimate": 1.45, "beat_pct": 3.4,
        "yoy_growth": 5.0, "quarters": [1.20, 1.30, 1.40, 1.50],
    })


async def fetch_revenue_data(ticker: str) -> dict:
    await asyncio.sleep(0.25)
    data = {
        "AAPL": {"revenue_b": 94.9, "qoq_growth": 5.2, "gross_margin": 46.2},
        "NVDA": {"revenue_b": 35.1, "qoq_growth": 12.0, "gross_margin": 74.8},
        "TSLA": {"revenue_b": 25.7, "qoq_growth": -1.1, "gross_margin": 17.4},
    }
    return data.get(ticker, {"revenue_b": 10.0, "qoq_growth": 3.0, "gross_margin": 40.0})


async def fetch_guidance(ticker: str) -> dict:
    await asyncio.sleep(0.15)
    data = {
        "AAPL": {"next_q_rev_guidance_b": 89.0, "raised": False, "commentary": "Cautious on China"},
        "NVDA": {"next_q_rev_guidance_b": 37.5, "raised": True, "commentary": "Blackwell demand exceeds supply"},
        "TSLA": {"next_q_rev_guidance_b": 26.0, "raised": False, "commentary": "Affordable model key to growth"},
    }
    return data.get(ticker, {
        "next_q_rev_guidance_b": 10.5, "raised": False, "commentary": "In-line with expectations"
    })


# ── Main agent node ───────────────────────────────────────────────────────────

@agent_op("earnings_agent")
async def run_earnings_agent(state: FinancialSwarmState) -> dict:
    ticker = state["ticker"]
    redis = get_state()
    call_count = 0

    async def heartbeat(tool: str = "") -> None:
        nonlocal call_count
        call_count += 1
        await redis.write_heartbeat(ticker, AGENT_ID, tool, call_count)

    await heartbeat("start")

    # Check for injected failures (earnings agent can also be targeted)
    failure = await redis.check_failure_injection(ticker, AGENT_ID)
    if failure == "silent_drop":
        await asyncio.sleep(30)
        return {"errors": [f"{AGENT_ID}: silent_drop"]}

    # Step 1: EPS data
    await heartbeat("fetch_eps_data")
    eps = await fetch_eps_data(ticker)

    # Step 2: Revenue data
    await heartbeat("fetch_revenue_data")
    rev = await fetch_revenue_data(ticker)

    # Step 3: Guidance
    await heartbeat("fetch_guidance")
    guidance = await fetch_guidance(ticker)

    # Step 4: LLM analysis
    await heartbeat("llm_earnings_analysis")

    prompt = f"""You are a financial analyst specializing in earnings analysis.
Analyze the earnings data for {ticker}:

EPS Performance:
- Actual: ${eps['eps_actual']} vs Estimate: ${eps['eps_estimate']} ({eps['beat_pct']:+.1f}% beat)
- YoY EPS Growth: {eps['yoy_growth']:+.1f}%
- Recent quarters: {eps['quarters']}

Revenue Performance:
- Revenue: ${rev['revenue_b']}B (QoQ: {rev['qoq_growth']:+.1f}%)
- Gross Margin: {rev['gross_margin']}%

Forward Guidance:
- Next Q Revenue Guidance: ${guidance['next_q_rev_guidance_b']}B (Raised: {guidance['raised']})
- Management Commentary: "{guidance['commentary']}"

Provide a concise earnings assessment (3-4 sentences) covering:
1. Overall earnings quality (beat/miss significance)
2. Revenue trend and margin health
3. Guidance outlook and investor implications
"""

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    analysis_text = response.content[0].text

    await heartbeat("done")
    await redis.mark_agent_done(ticker, AGENT_ID)

    result = {
        "eps": eps,
        "revenue": rev,
        "guidance": guidance,
        "analysis": analysis_text,
        "agent_id": AGENT_ID,
        "completed_at": time.time(),
    }

    return {
        "earnings_result": result,
        "tool_call_log": [{
            "agent": AGENT_ID,
            "tools_called": call_count,
            "ticker": ticker,
            "timestamp": time.time(),
        }]
    }
