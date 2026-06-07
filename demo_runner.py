"""
demo_runner.py — Scripted 3-minute demo for WeaveHacks 4

Runs the full swarm, auto-injects a loop failure after 15s,
and narrates every step to the terminal.

Usage:
  python demo_runner.py                    # NVDA, loop failure in 15s
  python demo_runner.py --ticker AAPL      # AAPL
  python demo_runner.py --no-inject        # no failure (clean run)
  python demo_runner.py --dry-run          # smoke test, forces MOCK_LLM=true
"""

import asyncio
import time

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.rule import Rule

load_dotenv()

from core.weave_setup import init_weave, get_weave_url
from core.redis_state import init_state

app = typer.Typer()
console = Console()

INJECT_DELAY = 15.0
FAILURE_AGENT = "risk_agent"
FAILURE_TYPE = "loop"


def _step_banner(step: str, title: str) -> None:
    console.print()
    console.print(Rule(f"[bold white]{step}[/bold white]", style="dim"))
    console.print(f"[bold yellow]{title}[/bold yellow]")
    console.print()


def make_status_table(ticker: str, heartbeats: dict) -> Table:
    table = Table(
        title=f"[bold cyan]SwarmInspector[/bold cyan] — {ticker}",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Agent", style="cyan", width=22)
    table.add_column("Status", width=14)
    table.add_column("Tool Calls", width=12)
    table.add_column("Last Tool", width=22)
    table.add_column("Last Seen", width=14)

    colors = {
        "running": "green",
        "done": "dim green",
        "failed": "red",
        "stalled": "yellow",
        "unknown": "dim",
    }

    now = time.time()
    for agent_id in ["earnings_agent", "risk_agent", "sentiment_agent", "synthesis_agent"]:
        hb = heartbeats.get(agent_id)
        if not hb:
            table.add_row(
                agent_id.replace("_agent", ""), Text("WAITING", style="dim"),
                "—", "—", "—"
            )
            continue

        status = hb.get("status", "unknown")
        color = colors.get(status, "white")
        last_seen_ago = now - hb.get("last_seen", now)
        table.add_row(
            agent_id.replace("_agent", ""),
            Text(status.upper(), style=color),
            str(hb.get("call_count", 0)),
            hb.get("last_tool", "—"),
            Text(f"{last_seen_ago:.1f}s ago",
                 style="red" if last_seen_ago > 8 and status == "running" else "default"),
        )

    return table


@app.command()
def run(
    ticker: str = typer.Option("NVDA", "--ticker", "-t"),
    no_inject: bool = typer.Option(False, "--no-inject", help="Skip failure injection"),
    inject_delay: float = typer.Option(INJECT_DELAY, "--delay", help="Seconds before failure injection"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Smoke test: forces MOCK_LLM=true, no API keys needed"),
):
    if dry_run:
        import os
        os.environ["MOCK_LLM"] = "true"
        console.print("[bold yellow]DRY RUN MODE[/bold yellow] — MOCK_LLM=true, no API keys needed")
    asyncio.run(_demo(ticker, not no_inject, inject_delay))


async def _demo(ticker: str, inject: bool, inject_delay: float):
    # Lazy imports to avoid circular issues at module level
    from agents.swarm_graph import run_swarm_parallel
    from inspector.inspector_graph import run_inspector_loop

    # ══════════════════════════════════════════════════════════════════════════
    # MINUTE 1 — SETUP
    # ══════════════════════════════════════════════════════════════════════════
    _step_banner("MINUTE 1", "Setting up the swarm")

    console.print(Panel(
        "[bold]SwarmInspector[/bold] — WeaveHacks 4\n\n"
        "A multi-agent financial analysis system with self-healing.\n\n"
        f"  Ticker:        [yellow]{ticker}[/yellow]\n"
        f"  Swarm agents:  earnings → risk → sentiment → synthesis\n"
        f"  Inspector:     monitor → diagnostician → healer\n"
        f"  State store:   Redis (in-memory fallback)\n"
        f"  Observability: W&B Weave [swarm-inspector-weavehacks4]",
        border_style="cyan",
        title="[bold cyan]SwarmInspector[/bold cyan]",
    ))

    init_weave()
    redis = await init_state()

    weave_url = get_weave_url()
    if weave_url:
        console.print(f"[dim]Weave dashboard: {weave_url}[/dim]")
    else:
        console.print("[dim]Weave: traces will appear once WANDB_API_KEY is set[/dim]")

    if inject:
        console.print(
            f"\n[yellow]Failure injection scheduled: "
            f"[red]{FAILURE_TYPE}[/red] → [cyan]{FAILURE_AGENT}[/cyan] "
            f"in [bold]{inject_delay:.0f}s[/bold][/yellow]"
        )

    console.print("\n[dim]Starting swarm and inspector...[/dim]\n")
    await asyncio.sleep(1.0)

    # ══════════════════════════════════════════════════════════════════════════
    # Launch tasks
    # ══════════════════════════════════════════════════════════════════════════
    stop_event = asyncio.Event()
    inject_state = {"done": False}   # mutable dict so the display task can mutate it

    swarm_task = asyncio.create_task(run_swarm_parallel(ticker))
    inspector_task = asyncio.create_task(
        run_inspector_loop(ticker, poll_interval=2.0, stop_event=stop_event)
    )

    # ── Live display + injection ──────────────────────────────────────────────
    agents_list = ["earnings_agent", "risk_agent", "sentiment_agent", "synthesis_agent"]
    start_time = time.time()

    with Live(console=console, refresh_per_second=2, transient=False) as live:
        while not swarm_task.done():
            elapsed = time.time() - start_time

            # Trigger failure injection
            if inject and not inject_state["done"] and elapsed >= inject_delay:
                inject_state["done"] = True
                await redis.inject_failure(ticker, FAILURE_AGENT, FAILURE_TYPE)

                live.stop()
                _step_banner("MINUTE 2", "Failure injected — inspector responding")
                console.print(
                    f"[bold red]>>> FAILURE INJECTED:[/bold red] "
                    f"[cyan]{FAILURE_AGENT}[/cyan] → [red]{FAILURE_TYPE}[/red]\n"
                    f"[dim]Inspector will detect this within ~5-10 seconds[/dim]"
                )
                live.start()

            heartbeats = await redis.get_all_heartbeats(ticker, agents_list)
            live.update(make_status_table(ticker, heartbeats))
            await asyncio.sleep(0.5)

        # Do one final refresh
        heartbeats = await redis.get_all_heartbeats(ticker, agents_list)
        live.update(make_status_table(ticker, heartbeats))

    stop_event.set()

    # Collect results
    swarm_state = None
    try:
        swarm_state = await asyncio.wait_for(
            asyncio.shield(swarm_task), timeout=2.0
        )
    except (asyncio.TimeoutError, Exception):
        pass

    inspector_result = None
    try:
        inspector_result = await asyncio.wait_for(inspector_task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        inspector_task.cancel()

    # ══════════════════════════════════════════════════════════════════════════
    # MINUTE 3 — RESOLUTION
    # ══════════════════════════════════════════════════════════════════════════
    _step_banner("MINUTE 3", "Swarm healed — final synthesis")

    if swarm_state and swarm_state.get("synthesis_result"):
        console.print(Panel(
            swarm_state["synthesis_result"],
            title=f"[bold green]📊 Final Analysis: {ticker}[/bold green]",
            border_style="green",
        ))

    if inspector_result and inspector_result.get("recovery_log"):
        console.print("\n[bold cyan]Inspector Recovery Log:[/bold cyan]")
        for line in inspector_result["recovery_log"]:
            console.print(f"  [dim]•[/dim] {line}")

    if weave_url:
        console.print(f"\n[bold]Full trace in W&B Weave:[/bold]")
        console.print(f"  {weave_url}")
        console.print(
            "[dim]Look for inspector.monitor → inspector.diagnostician → inspector.healer[/dim]"
        )

    console.print(Panel(
        "[bold green]Demo complete![/bold green]\n\n"
        "What you just saw:\n"
        "  1.  4 financial agents ran in parallel, all traced in Weave\n"
        "  2.  Risk agent entered an infinite loop (injected failure)\n"
        "  3.  Inspector detected it via heartbeat call-rate analysis\n"
        "  4.  Diagnostician classified it as [red]infinite_loop[/red]\n"
        "  5.  Healer sent a Redis recovery signal to the agent\n"
        "  6.  Risk agent broke the loop and finished normally\n"
        "  7.  Synthesis produced a complete report\n\n"
        "[italic]This is what multi-agent observability looks like in production.[/italic]",
        border_style="green",
        title="[bold]SwarmInspector — WeaveHacks 4[/bold]",
    ))


if __name__ == "__main__":
    app()
