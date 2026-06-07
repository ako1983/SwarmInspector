"""
scripts/inject_failure.py
CLI tool to manually inject failures into swarm agents.

Usage:
  python scripts/inject_failure.py --agent risk_agent --type loop
  python scripts/inject_failure.py --agent sentiment_agent --type silent_drop
  python scripts/inject_failure.py --agent earnings_agent --type context_drift
"""

import asyncio
import sys
import os

# Ensure root package is importable when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()

app = typer.Typer()
console = Console()

VALID_AGENTS = ["earnings_agent", "risk_agent", "sentiment_agent", "synthesis_agent"]
VALID_TYPES = ["loop", "silent_drop", "context_drift"]


@app.command()
def inject(
    agent: str = typer.Option("risk_agent", "--agent", "-a",
                               help=f"Agent to target: {VALID_AGENTS}"),
    failure_type: str = typer.Option("loop", "--type", "-t",
                                      help=f"Failure type: {VALID_TYPES}"),
    ticker: str = typer.Option("NVDA", "--ticker",
                                help="Stock ticker the swarm is analyzing"),
):
    """Inject a failure into a running swarm agent."""
    if agent not in VALID_AGENTS:
        console.print(f"[red]Unknown agent '{agent}'. Choose from: {VALID_AGENTS}[/red]")
        raise typer.Exit(1)
    if failure_type not in VALID_TYPES:
        console.print(f"[red]Unknown failure type '{failure_type}'. Choose from: {VALID_TYPES}[/red]")
        raise typer.Exit(1)

    asyncio.run(_inject(ticker, agent, failure_type))


async def _inject(ticker: str, agent: str, failure_type: str):
    from core.redis_state import init_state

    redis = await init_state()
    await redis.inject_failure(ticker, agent, failure_type)

    descriptions = {
        "loop": f"[red]LOOP[/red] — {agent} will call the same tool repeatedly until healed",
        "silent_drop": f"[red]SILENT DROP[/red] — {agent} will stop sending heartbeats (goes dark)",
        "context_drift": f"[red]CONTEXT DRIFT[/red] — {agent} will start analyzing the wrong ticker",
    }

    console.print(Panel(
        f"Failure injected into [bold cyan]{agent}[/bold cyan] for ticker [yellow]{ticker}[/yellow]\n\n"
        f"Type: {descriptions[failure_type]}\n\n"
        f"[dim]Inspector swarm will detect and heal this within ~{_expected_detection_time(failure_type)}s[/dim]",
        title="[bold red]Failure Injected[/bold red]",
        border_style="red",
    ))


def _expected_detection_time(failure_type: str) -> str:
    return {"loop": "5-10", "silent_drop": "8-12", "context_drift": "10-15"}.get(failure_type, "10")


if __name__ == "__main__":
    app()
