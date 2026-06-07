"""
core/mock_llm.py
Realistic mock LLM responses for all agents.

Set MOCK_LLM=true in .env (or shell) to skip real API calls while still
generating full W&B Weave traces. Ideal for populating the dashboard without
burning API credits.

Each response is realistic, ticker-specific, and different enough that
evals produce meaningful variance.
"""

import os

def is_mock() -> bool:
    return os.getenv("MOCK_LLM", "").lower() in ("1", "true", "yes")


# ── Earnings analysis mocks ───────────────────────────────────────────────────

EARNINGS_MOCK: dict[str, str] = {
    "NVDA": (
        "NVIDIA delivered a landmark quarter, reporting EPS of $6.12 against consensus of $5.59 — "
        "a 9.5% beat driven entirely by unprecedented data center GPU demand. Revenue of $35.1B grew "
        "122% year-over-year, with gross margins expanding 340bps to 74.8%, reflecting Blackwell's "
        "premium pricing power. Management raised next-quarter guidance to $37.5B, citing demand for "
        "AI inference infrastructure that continues to outstrip supply. The quality of this earnings "
        "beat is exceptionally high: it is broad-based, margin-accretive, and backed by a lengthening "
        "order backlog that gives multi-quarter revenue visibility."
    ),
    "AAPL": (
        "Apple reported a solid but nuanced quarter with EPS of $2.18, beating estimates by 3.8% on "
        "the back of Services revenue reaching an all-time high of $23.9B. Hardware revenue growth "
        "remained muted, with iPhone revenue flat year-over-year as the China market continued to "
        "compress volumes. Gross margin of 46.2% was the highest in company history, a structural "
        "shift reflecting the growing Services mix. Management guided conservatively for Q2 at $89B, "
        "below street expectations, citing ongoing uncertainty in the Greater China region. The "
        "earnings are solid but the lack of a hardware growth catalyst remains the central debate."
    ),
    "TSLA": (
        "Tesla's Q1 results missed meaningfully on both revenue ($25.7B vs $26.3B expected) and EPS "
        "($0.71 vs $0.68 consensus). Deliveries fell 6% year-over-year — the sharpest decline since "
        "2020 — as the legacy Model 3/Y cycle matures and the Cybertruck ramp remains below initial "
        "targets. Gross margin compressed to 17.4%, a multi-year low, driven by ongoing price cuts. "
        "Management offered no formal guidance, instead pointing to the robotaxi launch as the "
        "inflection catalyst. The earnings reveal a company in transition: core EV economics are "
        "deteriorating while the optionality narrative requires execution on unproven product lines."
    ),
    "MSFT": (
        "Microsoft posted strong Q3 results with EPS of $3.46, beating estimates by 6.1%, driven by "
        "Azure cloud revenue growing 31% year-over-year — an acceleration from the prior quarter. "
        "Copilot AI integrations are driving ARPU expansion across M365, with commercial seat "
        "additions ahead of plan. Operating margins expanded 190bps to 44.6%, reflecting operating "
        "leverage in the cloud segment. Management guided Q4 Azure growth of 34-35%, implying "
        "continued AI workload tailwinds. This is a clean, high-quality beat across all three "
        "revenue segments with improving unit economics."
    ),
}

# ── Risk analysis mocks ───────────────────────────────────────────────────────

RISK_MOCK: dict[str, str] = {
    "NVDA": (
        "NVIDIA presents a medium-high risk profile despite dominant fundamentals. The stock's beta "
        "of 1.98 means it amplifies broad market moves, and at 40x forward earnings, valuations leave "
        "little room for execution misses. The primary risk is a cyclical air-pocket in AI capex: "
        "if hyperscaler spending decelerates — even temporarily — NVDA revenue could undershoot "
        "dramatically given the concentration of revenue in a handful of large customers. Export "
        "controls on China (historically ~25% of data center revenue) represent a durable structural "
        "headwind. Mitigating factor: the Blackwell supply constraint creates a multi-quarter revenue "
        "floor, and no credible competitor can challenge CUDA ecosystem lock-in within 24 months."
    ),
    "AAPL": (
        "Apple carries a moderate risk profile underpinned by exceptional balance sheet strength "
        "and $165B of annual free cash flow. Key risks center on China exposure (~18% of revenue) "
        "where Huawei is regaining premium market share, and a potential EU regulatory action on "
        "App Store fees that could erode the highest-margin Services segment. The beta of 1.19 "
        "is lower than the Nasdaq, providing relative defensiveness in risk-off environments. "
        "Mitigating factor: the installed base of 2.2B active devices creates a recurring monetization "
        "engine that is structurally insulated from hardware unit cycle volatility."
    ),
    "TSLA": (
        "Tesla presents the highest risk profile in the large-cap EV space. Beta of 2.34 combined "
        "with a $185 average analyst price target (below current levels) signals elevated downside "
        "risk. The core auto business faces margin compression from price cuts, while BYD and legacy "
        "OEMs are scaling competitive products. Debt/equity of 0.09 provides financial flexibility, "
        "but the current ratio of 1.84 needs monitoring as capex for Gigafactory expansion intensifies. "
        "The largest risk is binary: Tesla's premium valuation is almost entirely predicated on "
        "autonomous driving optionality materializing by 2026. Regulatory approval delays would "
        "compress the multiple substantially."
    ),
    "MSFT": (
        "Microsoft is among the lowest-risk mega-cap tech investments. Beta of 0.92 provides "
        "near-market volatility with above-market fundamentals. Debt/equity of 0.35 is conservative "
        "for its cash generation, and interest coverage of 42x offers exceptional financial resilience. "
        "The primary risk is competitive pressure in cloud from AWS and GCP in AI infrastructure, "
        "where Microsoft's OpenAI partnership gives early advantage but not a permanent moat. "
        "Regulatory scrutiny of the Activision acquisition integration is an ongoing overhang. "
        "Mitigating factor: 99% commercial cloud revenue renewal rates create exceptional revenue "
        "predictability and limit downside scenarios."
    ),
}

# ── Sentiment analysis mocks ──────────────────────────────────────────────────

SENTIMENT_MOCK: dict[str, str] = {
    "NVDA": (
        "Market sentiment on NVIDIA is overwhelmingly bullish, with social scores of 0.89 (Reddit) "
        "and 0.87 (Twitter/X) representing near-peak retail enthusiasm. Institutional positioning "
        "is similarly constructive: 47 buy ratings, 5 holds, 1 sell, with an average price target "
        "of $165 implying 12% upside. The dominant narrative is 'AI supercycle with no end in sight,' "
        "amplified by CEO Jensen Huang's high-profile appearances at major conferences. The primary "
        "risk of this sentiment picture is crowdedness: NVDA is the most widely-held stock in "
        "hedge fund portfolios, meaning sentiment is vulnerable to mean-reversion on any negative "
        "data point. Retail and institutional sentiment are unusually aligned — historically a "
        "late-cycle signal."
    ),
    "AAPL": (
        "Apple sentiment is cautiously constructive at 0.62 (Reddit) and 0.58 (Twitter/X) — positive "
        "but notably below peak enthusiasm levels seen during the iPhone supercycle. Analyst "
        "consensus is a buy with 32 buy / 8 hold / 3 sell ratings and a $215 price target. The "
        "dominant retail narrative is 'steady compounder with AI upside,' while institutional "
        "focus centers on the pace of India market penetration as the China offset strategy. "
        "There is a meaningful divergence between retail optimism (driven by brand loyalty) and "
        "institutional caution (driven by valuation at 30x earnings with low-single-digit growth). "
        "This divergence typically resolves in the direction of institutional positioning."
    ),
    "TSLA": (
        "Tesla sentiment is deeply bifurcated, with Reddit scores of 0.44 and Twitter/X of 0.41 "
        "reflecting the highest retail-to-institutional divergence in the S&P 500. Retail 'Tesla bulls' "
        "remain fiercely loyal to the Elon Musk optionality narrative, while institutional sentiment "
        "has turned sharply negative following the delivery miss. Analyst consensus has deteriorated "
        "to 18 buy / 14 hold / 10 sell — the most contested rating distribution of any Mag-7 name. "
        "The dominant negative narrative is the gap between Tesla's $550B market cap and its current "
        "auto business fundamentals. The dominant positive counter-narrative is that any autonomous "
        "driving progress warrants a rerating. High mention volume (very_high) on a bearish trend "
        "suggests the stock is a battleground with elevated volatility risk in both directions."
    ),
    "MSFT": (
        "Microsoft commands quietly strong institutional sentiment, with analyst ratings of 45 buy / "
        "6 hold / 1 sell and a $500 average price target. Social sentiment scores of 0.71 (Reddit) "
        "and 0.68 (Twitter/X) are solid without being frothy — indicating a 'quality compounder' "
        "perception rather than speculative excitement. The dominant narrative is 'best-positioned "
        "enterprise AI play with execution credibility,' reinforced by Copilot adoption data and "
        "Azure reacceleration. Unlike NVDA, institutional and retail sentiment are aligned without "
        "being overcrowded, a constructive setup. The primary sentiment risk is that AI monetization "
        "timelines disappoint — expectations are high but not irrational at current price levels."
    ),
}

# ── Synthesis mocks ───────────────────────────────────────────────────────────

SYNTHESIS_MOCK: dict[str, str] = {
    "NVDA": (
        "NVIDIA stands out as the singular AI infrastructure beneficiary of this market cycle, with "
        "Q4 results and forward guidance that leave no ambiguity about demand trajectory. The 9.5% "
        "EPS beat, 74.8% gross margin, and raised guidance to $37.5B reflect a company operating "
        "at the nexus of the most significant capital expenditure wave in enterprise technology history. "
        "Risk metrics are elevated — beta of 1.98, concentrated customer exposure, and export "
        "control headwinds — but these are known, priced risks rather than hidden vulnerabilities. "
        "Sentiment is near-unanimously bullish across retail and institutional investors, a "
        "crowdedness dynamic that warrants position sizing discipline but does not undermine the "
        "fundamental thesis. The synthesis across earnings quality, risk profile, and sentiment "
        "alignment produces a [BULLISH — 12-18 month] investment stance, with the primary variant "
        "to monitor being hyperscaler capex commentary in upcoming earnings calls."
    ),
    "AAPL": (
        "Apple presents a compelling quality-versus-growth tension that defines the investment debate. "
        "The earnings showed structural margin improvement (46.2% gross margin, all-time high) but "
        "hardware unit stagnation, while the risk profile is genuinely defensive — sub-1.2 beta, "
        "fortress balance sheet, and recurring revenue mix expanding to 35% of total revenue. "
        "Sentiment is cautiously optimistic but below prior cycle peaks, reflecting institutional "
        "concern about the China market compression that retail investors are underweighting. "
        "The fundamental tension: Apple is becoming more profitable per unit while selling fewer "
        "incremental units. That is not a bad business — it is a mature one. The synthesis supports "
        "a [NEUTRAL-TO-BULLISH — 6-12 month] stance: the stock is not expensive enough to avoid "
        "but not cheap enough to aggressively add into current valuation without a hardware catalyst."
    ),
    "TSLA": (
        "Tesla's investment case has entered its most contested phase, with Q1 earnings revealing "
        "structural deterioration in the core auto business while the optionality narrative remains "
        "speculative but potentially transformative. The 6% delivery decline, 17.4% gross margin "
        "(multi-year low), and management's refusal to provide quantitative guidance are fundamental "
        "negatives that cannot be dismissed. Risk metrics are among the highest in mega-cap tech: "
        "beta of 2.34, no credible earnings floor estimate, and a valuation that embeds outcomes "
        "that have not yet materialized. Sentiment bifurcation — retail bullish, institutional "
        "cautious — historically resolves toward institutional consensus over a 12-month horizon. "
        "The synthesis produces a [NEUTRAL — risk-adjusted] stance: the risk/reward is asymmetric "
        "but in both directions. Position sizing should reflect that this is a speculation on "
        "autonomous driving timelines, not a bet on the current auto business."
    ),
    "MSFT": (
        "Microsoft represents the highest-quality AI monetization story in the large-cap universe, "
        "with Q3 results confirming that Copilot and Azure AI workloads are translating into "
        "measurable revenue acceleration — not future optionality. The 31% Azure growth "
        "reacceleration, 44.6% operating margins, and conservative financial leverage create an "
        "exceptionally resilient fundamental floor. Risk is genuinely low: beta under 1.0, 42x "
        "interest coverage, and 99% commercial renewal rates provide multi-year revenue visibility "
        "that few companies at this scale can match. Sentiment is constructive without being "
        "overcrowded — the most sustainable positioning for a long investment. The synthesis across "
        "all three dimensions produces a [BULLISH — 18-24 month] stance, with Microsoft as the "
        "preferred risk-adjusted AI exposure relative to pure-play infrastructure names."
    ),
}


def get_earnings_mock(ticker: str) -> str:
    return EARNINGS_MOCK.get(ticker, (
        f"{ticker} reported in-line results with EPS matching consensus estimates. "
        f"Revenue grew modestly year-over-year with stable gross margins. "
        f"Management provided cautious guidance citing macro uncertainty."
    ))

def get_risk_mock(ticker: str) -> str:
    return RISK_MOCK.get(ticker, (
        f"{ticker} carries a moderate risk profile with beta near market average. "
        f"Key risks include sector headwinds and valuation compression in a higher-rate environment. "
        f"Balance sheet strength provides a mitigating cushion against near-term volatility."
    ))

def get_sentiment_mock(ticker: str) -> str:
    return SENTIMENT_MOCK.get(ticker, (
        f"{ticker} sentiment is neutral-to-positive across retail and institutional channels. "
        f"Analyst consensus is a hold with modest upside to price targets. "
        f"No significant divergence between retail and institutional positioning."
    ))

def get_synthesis_mock(ticker: str) -> str:
    return SYNTHESIS_MOCK.get(ticker, (
        f"{ticker} presents a balanced investment case with earnings in line, moderate risk, "
        f"and neutral sentiment. The synthesis across dimensions supports a [NEUTRAL — 6-12 month] "
        f"stance pending clearer catalysts on either the bull or bear case."
    ))
