"""
agents/risk_agent.py
Assesses risk factors for a given ticker.
THIS IS THE AGENT THAT FAILS DURING THE DEMO.
Supports: loop injection (same tool called repeatedly), silent_drop.
"""

import asyncio
import time
from openai import AsyncOpenAI
from core.state import FinancialSwarmState
from core.redis_state import get_state, LOOP_THRESHOLD
from core.weave_setup import agent_op

client = AsyncOpenAI()
AGENT_ID = "risk_agent"


# ── Mock tools ────────────────────────────────────────────────────────────────

async def fetch_volatility(ticker: str) -> dict:
    await asyncio.sleep(0.3)
    data = {
        "AAPL": {"beta": 1.19, "52w_high": 237.49, "52w_low": 164.08, "vix_corr": 0.62},
        "NVDA": {"beta": 1.98, "52w_high": 153.13, "52w_low": 66.25, "vix_corr": 0.71},
        "TSLA": {"beta": 2.34, "52w_high": 488.54, "52w_low": 138.80, "vix_corr": 0.58},
    }
    return data.get(ticker, {"beta": 1.2, "52w_high": 100.0, "52w_low": 70.0, "vix_corr": 0.55})

async def fetch_debt_metrics(ticker: str) -> dict:
    await asyncio.sleep(0.2)
    data = {
        "AAPL": {"debt_to_equity": 1.87, "current_ratio": 0.87, "interest_coverage": 28.5},
        "NVDA": {"debt_to_equity": 0.41, "current_ratio": 4.17, "interest_coverage": 89.3},
        "TSLA": {"debt_to_equity": 0.09, "current_ratio": 1.84, "interest_coverage": 14.2},
    }
    return data.get(ticker, {"debt_to_equity": 0.8, "current_ratio": 1.5, "interest_coverage": 10.0})

async def fetch_macro_factors() -> list[str]:
    await asyncio.sleep(0.15)
    return [
        "Fed funds rate at 4.25-4.50%",
        "10Y Treasury yield: 4.38%",
        "CPI YoY: 2.9%",
        "USD Index: 104.2",
    ]


# ── Main agent node ───────────────────────────────────────────────────────────

@agent_op("risk_agent")
async def run_risk_agent(state: FinancialSwarmState) -> dict:
    """
    LangGraph node: Risk assessment agent.
    This agent is the demo failure target — it can enter a loop.
    """
    ticker = state["ticker"]
    redis = get_state()
    call_count = 0
    loop_count = 0  # tracks repeated tool calls (the bug we inject)

    async def heartbeat(tool: str = "") -> None:
        nonlocal call_count
        call_count += 1
        await redis.write_heartbeat(ticker, AGENT_ID, tool, call_count)

    await heartbeat("start")

    # Check for failure injection
    failure = await redis.check_failure_injection(ticker, AGENT_ID)

    if failure == "silent_drop":
        # Agent goes dark
        await asyncio.sleep(20)
        return {"errors": [f"{AGENT_ID}: silent_drop"]}

    if failure == "loop":
        # Agent enters an infinite loop — calls the same tool repeatedly.
        # Inspector detects this via heartbeat tool_call_count exceeding threshold
        # AND via repeated last_tool value.
        while True:
            loop_count += 1
            await heartbeat("fetch_volatility")   # same tool, over and over
            _ = await fetch_volatility(ticker)    # real call, but going nowhere

            # Check if inspector sent a recovery signal
            recovery = await redis.check_recovery_signal(ticker, AGENT_ID)
            if recovery:
                # Inspector healed us — break the loop and continue normally
                await heartbeat("recovery_received")
                break

            await asyncio.sleep(1.0)

            if loop_count > 50:  # hard safety limit
                return {"errors": [f"{AGENT_ID}: loop exceeded safety limit"]}

    # Normal execution path ──────────────────────────────────────────────────

    # Step 1: Fetch volatility
    await heartbeat("fetch_volatility")
    vol = await fetch_volatility(ticker)

    # Step 2: Fetch debt metrics
    await heartbeat("fetch_debt_metrics")
    debt = await fetch_debt_metrics(ticker)

    # Step 3: Fetch macro factors
    await heartbeat("fetch_macro_factors")
    macro = await fetch_macro_factors()

    # Step 4: LLM risk assessment
    await heartbeat("llm_risk_analysis")

    prompt = f"""You are a risk analyst. Assess the risk profile for {ticker}:

Volatility Metrics:
- Beta: {vol['beta']}
- 52W Range: ${vol['52w_low']} - ${vol['52w_high']}
- VIX Correlation: {vol['vix_corr']}

Debt Metrics:
- Debt/Equity: {debt['debt_to_equity']}
- Current Ratio: {debt['current_ratio']}
- Interest Coverage: {debt['interest_coverage']}x

Macro Environment:
{chr(10).join(f'- {f}' for f in macro)}

Provide a concise risk assessment (3-4 sentences) covering:
1. Overall risk level (low/medium/high)
2. Biggest risk factor
3. One mitigating factor
"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    analysis_text = response.choices[0].message.content

    await heartbeat("done")
    await redis.mark_agent_done(ticker, AGENT_ID)

    result = {
        "volatility": vol,
        "debt_metrics": debt,
        "macro_factors": macro,
        "analysis": analysis_text,
        "agent_id": AGENT_ID,
        "completed_at": time.time(),
        "recovered_from_loop": loop_count > 0,
    }

    return {
        "risk_result": result,
        "tool_call_log": [{
            "agent": AGENT_ID,
            "tools_called": call_count,
            "loop_count": loop_count,
            "ticker": ticker,
            "timestamp": time.time(),
        }]
    }
