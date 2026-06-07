"""
main.py — SwarmInspector entry point

Run this for the demo:
  python main.py                    # analyze NVDA, no failure
  python main.py --ticker AAPL      # analyze AAPL
  python main.py --inject           # auto-inject loop failure after 8s

Then from a second terminal:
  python scripts/inject_failure.py --agent risk --type loop
"""

import asyncio
import os
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
import time

load_dotenv()

from core.weave_setup import init_weave, get_weave_url
from core.redis_state import get_state
from agents.swarm_graph import run_swarm_parallel
from inspector.inspector_graph import run_inspector_loop

app = typer.Typer()
console = Console()


def make_status_table(ticker: str, agents: dict, anomaly_info: dict | None = None) -> Table:
    """Build a Rich table showing real-time agent status."""
    table = Table(title=f"🔬 SwarmInspector — {ticker}", show_header=True, header_style="bold cyan")
    table.add_column("Agent", style="cyan", width=20)
    table.add_column("Status", width=12)
    table.add_column("Tool Calls", width=10)
    table.add_column("Last Tool", width=20)
    table.add_column("Last Seen", width=10)

    status_colors = {
        "running": "green",
        "done": "dim green",
        "failed": "red",
        "stalled": "yellow",
        "unknown": "dim",
    }

    for agent_id, info in agents.items():
        status = info.get("status", "unknown")
        color = status_colors.get(status, "white")
        table.add_row(
            agent_id.replace("_agent", ""),
            Text(status.upper(), style=color),
            str(info.get("call_count", 0)),
            info.get("last_tool", "—"),
            f"{info.get('last_seen_ago', 0):.1f}s ago",
        )

    return table


async def poll_and_display(ticker: str, duration: float = 60.0):
    """Displays live agent status table while the swarm runs."""
    redis = get_state()
    agent_ids = ["earnings_agent", "risk_agent", "sentiment_agent", "synthesis_agent"]
    end_time = time.time() + duration

    with Live(console=console, refresh_per_second=2) as live:
        while time.time() < end_time:
            agents = {}
            for agent_id in agent_ids:
                hb = await redis.read_heartbeat(ticker, agent_id)
                if hb:
                    agents[agent_id] = {
                        "status": hb.get("status", "unknown"),
                        "call_count": hb.get("call_count", 0),
                        "last_tool": hb.get("last_tool", "—"),
                        "last_seen_ago": round(time.time() - hb.get("last_seen", time.time()), 1),
                    }

            table = make_status_table(ticker, agents)
            live.update(table)
            await asyncio.sleep(0.5)


@app.command()
def run(
    ticker: str = typer.Option("NVDA", "--ticker", "-t", help="Stock ticker to analyze"),
    inject: bool = typer.Option(False, "--inject", "-i", help="Auto-inject loop failure after 8s"),
    failure_agent: str = typer.Option("risk_agent", "--agent", help="Agent to inject failure into"),
    failure_type: str = typer.Option("loop", "--failure", help="Failure type: loop|silent_drop|context_drift"),
    no_display: bool = typer.Option(False, "--no-display", help="Skip live table (cleaner output)"),
):
    """Run the SwarmInspector demo."""
    asyncio.run(_run(ticker, inject, failure_agent, failure_type, no_display))


async def _run(ticker: str, inject: bool, failure_agent: str,
               failure_type: str, no_display: bool):
    # ── Startup banner ────────────────────────────────────────────────────────
    console.print(Panel(
        f"[bold cyan]SwarmInspector[/bold cyan] — WeaveHacks 4\n\n"
        f"  Ticker:  [yellow]{ticker}[/yellow]\n"
        f"  Failure: [{'red' if inject else 'dim'}]{'AUTO-INJECT ' + failure_type + ' on ' + failure_agent if inject else 'None (manual via inject_failure.py)'}[/]\n"
        f"  Weave:   [dim]{get_weave_url() or 'initializing...'}[/dim]",
        border_style="cyan",
        title="[bold]Starting[/bold]",
    ))

    # ── Init Weave ────────────────────────────────────────────────────────────
    init_weave()

    redis = get_state()
    stop_event = asyncio.Event()

    # ── Optional auto-inject ──────────────────────────────────────────────────
    async def delayed_inject():
        if inject:
            console.print(f"[yellow]⏳ Failure injection scheduled in 8s...[/yellow]")
            await asyncio.sleep(8)
            await redis.inject_failure(ticker, failure_agent, failure_type)
            console.print(f"[bold red]💉 {failure_type} injected into {failure_agent}![/bold red]")

    # ── Run everything concurrently ───────────────────────────────────────────
    tasks = [
        asyncio.create_task(run_swarm_parallel(ticker)),
        asyncio.create_task(run_inspector_loop(ticker, poll_interval=2.0, stop_event=stop_event)),
        asyncio.create_task(delayed_inject()),
    ]

    if not no_display:
        tasks.append(asyncio.create_task(poll_and_display(ticker, duration=120.0)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    stop_event.set()

    # ── Final output ──────────────────────────────────────────────────────────
    swarm_state = results[0] if not isinstance(results[0], Exception) else None

    if swarm_state and swarm_state.get("synthesis_result"):
        console.print(Panel(
            swarm_state["synthesis_result"],
            title=f"[bold green]📊 Final Analysis: {ticker}[/bold green]",
            border_style="green",
        ))

    weave_url = get_weave_url()
    if weave_url:
        console.print(f"\n[bold]View traces in W&B Weave:[/bold] [link={weave_url}]{weave_url}[/link]")

    console.print("[bold green]✓ Demo complete[/bold green]")


if __name__ == "__main__":
    app()
