"""
agents/sentiment_agent.py
Analyzes market sentiment from news headlines and SEC filing tone.
"""

import asyncio
import time
from anthropic import AsyncAnthropic
from core.state import FinancialSwarmState
from core.redis_state import get_state
from core.weave_setup import agent_op

client = AsyncAnthropic()
AGENT_ID = "sentiment_agent"


# ── Mock tools ────────────────────────────────────────────────────────────────

async def fetch_news_headlines(ticker: str) -> list[dict]:
    await asyncio.sleep(0.25)
    data = {
        "AAPL": [
            {"headline": "Apple Vision Pro sales disappoint analysts", "sentiment": "negative", "source": "WSJ"},
            {"headline": "iPhone 17 pre-orders shatter records in China", "sentiment": "positive", "source": "Bloomberg"},
            {"headline": "Apple Services revenue hits all-time high", "sentiment": "positive", "source": "Reuters"},
            {"headline": "Tim Cook signals caution on AI chip supply constraints", "sentiment": "neutral", "source": "FT"},
        ],
        "NVDA": [
            {"headline": "Nvidia Blackwell demand surges beyond all supply", "sentiment": "positive", "source": "Bloomberg"},
            {"headline": "Jensen Huang: AI inference wave 'just beginning'", "sentiment": "positive", "source": "CNBC"},
            {"headline": "Export controls tighten on China AI chip sales", "sentiment": "negative", "source": "WSJ"},
            {"headline": "Nvidia data center revenue up 409% year over year", "sentiment": "positive", "source": "Reuters"},
        ],
        "TSLA": [
            {"headline": "Tesla Q1 deliveries miss estimates by 6%", "sentiment": "negative", "source": "Bloomberg"},
            {"headline": "Robotaxi launch delayed again, says Elon Musk", "sentiment": "negative", "source": "Reuters"},
            {"headline": "Tesla Model Y remains best-selling EV globally", "sentiment": "positive", "source": "WSJ"},
            {"headline": "Cybertruck production ramp accelerating in Q2", "sentiment": "positive", "source": "CNBC"},
        ],
    }
    return data.get(ticker, [
        {"headline": f"{ticker} reports solid quarterly results", "sentiment": "positive", "source": "Reuters"},
        {"headline": f"{ticker} faces sector headwinds", "sentiment": "neutral", "source": "Bloomberg"},
    ])


async def fetch_social_sentiment(ticker: str) -> dict:
    await asyncio.sleep(0.2)
    data = {
        "AAPL": {"reddit_score": 0.62, "twitter_score": 0.58, "mention_volume": "high", "trend": "stable"},
        "NVDA": {"reddit_score": 0.89, "twitter_score": 0.87, "mention_volume": "very_high", "trend": "bullish"},
        "TSLA": {"reddit_score": 0.44, "twitter_score": 0.41, "mention_volume": "very_high", "trend": "bearish"},
    }
    return data.get(ticker, {
        "reddit_score": 0.55, "twitter_score": 0.55, "mention_volume": "moderate", "trend": "stable"
    })


async def fetch_analyst_ratings(ticker: str) -> dict:
    await asyncio.sleep(0.15)
    data = {
        "AAPL": {"buy": 32, "hold": 8, "sell": 3, "avg_price_target": 215.0, "consensus": "buy"},
        "NVDA": {"buy": 47, "hold": 5, "sell": 1, "avg_price_target": 165.0, "consensus": "strong_buy"},
        "TSLA": {"buy": 18, "hold": 14, "sell": 10, "avg_price_target": 185.0, "consensus": "hold"},
    }
    return data.get(ticker, {
        "buy": 15, "hold": 10, "sell": 5, "avg_price_target": 100.0, "consensus": "hold"
    })


# ── Main agent node ───────────────────────────────────────────────────────────

@agent_op("sentiment_agent")
async def run_sentiment_agent(state: FinancialSwarmState) -> dict:
    ticker = state["ticker"]
    redis = get_state()
    call_count = 0

    async def heartbeat(tool: str = "") -> None:
        nonlocal call_count
        call_count += 1
        await redis.write_heartbeat(ticker, AGENT_ID, tool, call_count)

    await heartbeat("start")

    # Check for injected failures
    failure = await redis.check_failure_injection(ticker, AGENT_ID)
    if failure == "silent_drop":
        await asyncio.sleep(30)
        return {"errors": [f"{AGENT_ID}: silent_drop"]}

    # Step 1: News headlines
    await heartbeat("fetch_news_headlines")
    headlines = await fetch_news_headlines(ticker)

    # Step 2: Social sentiment
    await heartbeat("fetch_social_sentiment")
    social = await fetch_social_sentiment(ticker)

    # Step 3: Analyst ratings
    await heartbeat("fetch_analyst_ratings")
    ratings = await fetch_analyst_ratings(ticker)

    # Step 4: LLM sentiment synthesis
    await heartbeat("llm_sentiment_analysis")

    headlines_str = "\n".join(
        f"[{h['sentiment'].upper()}] {h['headline']} — {h['source']}"
        for h in headlines
    )

    prompt = f"""You are a sentiment analyst. Assess market sentiment for {ticker}:

Recent News:
{headlines_str}

Social Media Sentiment:
- Reddit score: {social['reddit_score']:.2f}/1.0
- Twitter score: {social['twitter_score']:.2f}/1.0
- Mention volume: {social['mention_volume']}
- Trend: {social['trend']}

Analyst Consensus:
- Buy/Hold/Sell: {ratings['buy']}/{ratings['hold']}/{ratings['sell']}
- Avg price target: ${ratings['avg_price_target']}
- Consensus: {ratings['consensus']}

Provide a concise sentiment assessment (3-4 sentences) covering:
1. Overall market sentiment (bullish/neutral/bearish and strength)
2. Key sentiment driver (what's dominating the narrative)
3. Divergence between retail and institutional sentiment (if any)
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
        "headlines": headlines,
        "social": social,
        "analyst_ratings": ratings,
        "analysis": analysis_text,
        "agent_id": AGENT_ID,
        "completed_at": time.time(),
    }

    return {
        "sentiment_result": result,
        "tool_call_log": [{
            "agent": AGENT_ID,
            "tools_called": call_count,
            "ticker": ticker,
            "timestamp": time.time(),
        }]
    }
