"""
eval_runner.py — Weave Evaluation for SwarmInspector

Demonstrates systematic quality measurement of the financial analysis swarm.
Runs evals across multiple tickers and failure scenarios, scores outputs,
and saves everything to W&B Weave.

Usage:
  MOCK_LLM=true python eval_runner.py
  MOCK_LLM=true python eval_runner.py --tickers NVDA AAPL TSLA MSFT
"""

import asyncio
import os
import re
import time
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()

from core.weave_setup import init_weave, get_weave_url
from core.redis_state import init_state
from agents.swarm_graph import run_swarm_parallel

app = typer.Typer()
console = Console()


# ── Weave Dataset ─────────────────────────────────────────────────────────────

EVAL_SCENARIOS = [
    {
        "ticker": "NVDA",
        "sector": "semiconductors",
        "expected_themes": ["AI", "data center", "GPU", "Blackwell"],
        "expected_stance_words": ["bullish", "buy"],
        "description": "High-growth AI infrastructure play",
    },
    {
        "ticker": "AAPL",
        "sector": "consumer_tech",
        "expected_themes": ["Services", "iPhone", "China", "margin"],
        "expected_stance_words": ["neutral", "bullish"],
        "description": "Mature quality compounder with Services tailwind",
    },
    {
        "ticker": "TSLA",
        "sector": "ev_auto",
        "expected_themes": ["delivery", "margin", "autonomous", "robotaxi"],
        "expected_stance_words": ["neutral", "bearish", "speculative"],
        "description": "High-risk/reward EV transition play",
    },
    {
        "ticker": "MSFT",
        "sector": "enterprise_tech",
        "expected_themes": ["Azure", "Copilot", "cloud", "AI"],
        "expected_stance_words": ["bullish", "buy"],
        "description": "Best-in-class enterprise AI monetization",
    },
]


# ── Model under evaluation ────────────────────────────────────────────────────

async def run_analysis_model(ticker: str, sector: str, description: str,
                              expected_themes: list, expected_stance_words: list) -> dict:
    """Runs the full swarm pipeline and returns structured output for scoring."""
    start = time.time()
    state = await run_swarm_parallel(ticker)
    elapsed = time.time() - start

    synthesis = state.get("synthesis_result") or ""
    errors = state.get("errors") or []

    return {
        "ticker": ticker,
        "synthesis": synthesis,
        "earnings_analysis": (state.get("earnings_result") or {}).get("analysis", ""),
        "risk_analysis": (state.get("risk_result") or {}).get("analysis", ""),
        "sentiment_analysis": (state.get("sentiment_result") or {}).get("analysis", ""),
        "errors": errors,
        "runtime_seconds": round(elapsed, 2),
        "all_agents_completed": len(errors) == 0,
    }


# ── Scorers ───────────────────────────────────────────────────────────────────

def score_theme_coverage(output: dict, expected_themes: list) -> dict:
    """Checks how many expected themes appear in the synthesis."""
    text = (output.get("synthesis") or "").lower()
    hits = [t for t in expected_themes if t.lower() in text]
    coverage = len(hits) / len(expected_themes) if expected_themes else 0
    return {
        "theme_coverage": round(coverage, 2),
        "themes_found": hits,
        "themes_missing": [t for t in expected_themes if t.lower() not in text],
        "score": coverage,
    }


def score_investment_stance(output: dict, expected_stance_words: list) -> dict:
    """Checks whether the synthesis includes a clear investment stance."""
    text = (output.get("synthesis") or "").lower()
    has_stance = any(w in text for w in ["bullish", "bearish", "neutral", "buy", "sell", "hold"])
    matches_expected = any(w in text for w in expected_stance_words)
    return {
        "has_clear_stance": has_stance,
        "matches_expected_stance": matches_expected,
        "score": 1.0 if (has_stance and matches_expected) else (0.5 if has_stance else 0.0),
    }


def score_synthesis_quality(output: dict) -> dict:
    """Heuristic quality checks on the synthesis output."""
    text = output.get("synthesis") or ""
    words = text.split()
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 20]

    checks = {
        "min_length": len(words) >= 80,
        "multi_sentence": len(sentences) >= 3,
        "mentions_earnings": any(w in text.lower() for w in ["earnings", "eps", "revenue", "margin"]),
        "mentions_risk": any(w in text.lower() for w in ["risk", "beta", "volatile", "downside"]),
        "mentions_sentiment": any(w in text.lower() for w in ["sentiment", "bullish", "bearish", "analyst"]),
        "has_timeframe": bool(re.search(r'\d+[-–]\d+\s*(month|year)', text, re.IGNORECASE)),
        "no_errors": not output.get("errors"),
    }

    score = sum(checks.values()) / len(checks)
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "checks": checks,
        "score": round(score, 2),
    }


def score_completeness(output: dict) -> dict:
    """Checks that all three specialist analyses fed into the synthesis."""
    has_earnings = bool(output.get("earnings_analysis"))
    has_risk = bool(output.get("risk_analysis"))
    has_sentiment = bool(output.get("sentiment_analysis"))
    has_synthesis = bool(output.get("synthesis"))
    all_complete = output.get("all_agents_completed", False)

    checks = {
        "earnings_completed": has_earnings,
        "risk_completed": has_risk,
        "sentiment_completed": has_sentiment,
        "synthesis_completed": has_synthesis,
        "no_errors": all_complete,
    }
    score = sum(checks.values()) / len(checks)
    return {"checks": checks, "score": round(score, 2)}


# ── Evaluation runner ─────────────────────────────────────────────────────────

async def run_evaluation(tickers: list[str] | None = None):
    """Runs the full evaluation suite and saves results to Weave."""
    init_weave()
    await init_state()

    mock = os.getenv("MOCK_LLM", "false")
    console.print(Panel(
        f"[bold cyan]SwarmInspector Evaluation[/bold cyan]\n\n"
        f"  Mode:     [yellow]{'MOCK (no API calls)' if mock in ('1', 'true', 'yes') else 'LIVE (real LLM calls)'}[/yellow]\n"
        f"  Weave:    [dim]{get_weave_url() or 'not configured'}[/dim]\n"
        f"  Tickers:  {tickers or [s['ticker'] for s in EVAL_SCENARIOS]}",
        border_style="cyan",
        title="[bold]Weave Evaluation[/bold]",
    ))

    # Filter scenarios to requested tickers
    scenarios = EVAL_SCENARIOS if not tickers else [
        s for s in EVAL_SCENARIOS if s["ticker"] in tickers
    ]

    results = []

    try:
        import weave

        # Register the dataset in Weave
        dataset = weave.Dataset(
            name="financial-analysis-scenarios",
            rows=scenarios,
        )

        # Wrap model and scorers with @weave.op() for tracing
        traced_model = weave.op()(run_analysis_model)
        traced_model.__name__ = "swarm.analysis_pipeline"

        traced_theme = weave.op()(score_theme_coverage)
        traced_theme.__name__ = "scorer.theme_coverage"

        traced_stance = weave.op()(score_investment_stance)
        traced_stance.__name__ = "scorer.investment_stance"

        traced_quality = weave.op()(score_synthesis_quality)
        traced_quality.__name__ = "scorer.synthesis_quality"

        traced_complete = weave.op()(score_completeness)
        traced_complete.__name__ = "scorer.completeness"

        # Run evaluation
        evaluation = weave.Evaluation(
            name="swarm-inspector-eval-v1",
            dataset=dataset,
            scorers=[traced_theme, traced_stance, traced_quality, traced_complete],
        )

        console.print("\n[bold]Running Weave Evaluation...[/bold]")
        eval_results = await evaluation.evaluate(traced_model)
        results = eval_results

    except (ImportError, Exception) as exc:
        console.print(f"[yellow]Weave Evaluation API not available ({exc}), running manually...[/yellow]")
        # Fallback: run manually and display results
        results = await _run_manual_eval(scenarios)

    _display_results(results, scenarios)
    return results


async def _run_manual_eval(scenarios: list) -> list:
    """Manual evaluation when Weave Evaluation API isn't available."""
    all_results = []
    for scenario in scenarios:
        ticker = scenario["ticker"]
        console.print(f"  [cyan]Analyzing {ticker}...[/cyan]", end="")
        output = await run_analysis_model(**{k: scenario[k] for k in scenario})
        scores = {
            "theme_coverage": score_theme_coverage(output, scenario["expected_themes"]),
            "investment_stance": score_investment_stance(output, scenario["expected_stance_words"]),
            "synthesis_quality": score_synthesis_quality(output),
            "completeness": score_completeness(output),
        }
        all_results.append({"scenario": scenario, "output": output, "scores": scores})
        overall = sum(s.get("score", 0) for s in scores.values()) / len(scores)
        console.print(f" [green]✓[/green] (score: {overall:.2f})")
    return all_results


def _display_results(results, scenarios):
    """Pretty-prints evaluation results."""
    console.print()
    table = Table(
        title="[bold cyan]Evaluation Results[/bold cyan]",
        show_header=True, header_style="bold",
    )
    table.add_column("Ticker", style="cyan", width=8)
    table.add_column("Themes", width=10)
    table.add_column("Stance", width=10)
    table.add_column("Quality", width=10)
    table.add_column("Complete", width=10)
    table.add_column("Runtime", width=10)

    if isinstance(results, list) and results and isinstance(results[0], dict) and "scores" in results[0]:
        for r in results:
            t = r["scenario"]["ticker"]
            s = r["scores"]
            rt = r["output"].get("runtime_seconds", "—")
            table.add_row(
                t,
                f"{s['theme_coverage']['score']:.0%}",
                f"{s['investment_stance']['score']:.0%}",
                f"{s['synthesis_quality']['score']:.0%}",
                f"{s['completeness']['score']:.0%}",
                f"{rt}s",
            )

    console.print(table)

    weave_url = get_weave_url()
    if weave_url:
        console.print(f"\n[bold]Full eval results in Weave:[/bold] {weave_url}")
        console.print("[dim]Navigate to Evaluations tab to see per-row scores and traces[/dim]")


@app.command()
def run(
    tickers: list[str] = typer.Argument(None, help="Tickers to eval (default: all 4)"),
):
    """Run Weave Evaluation across tickers. Set MOCK_LLM=true to skip API calls."""
    asyncio.run(run_evaluation(tickers or None))


if __name__ == "__main__":
    app()
