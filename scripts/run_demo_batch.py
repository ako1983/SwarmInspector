"""
scripts/run_demo_batch.py
Runs 3 demo scenarios in sequence to populate W&B Weave with rich trace data.

Scenarios:
  1. Clean run — NVDA, no failures
  2. Loop-healed run — NVDA, risk agent enters loop, inspector heals it
  3. Multi-ticker clean — AAPL + TSLA + MSFT clean runs

Set MOCK_LLM=true to run without API credits.

Usage:
  MOCK_LLM=true python scripts/run_demo_batch.py
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

load_dotenv()

from core.weave_setup import init_weave, get_weave_url
from core.redis_state import init_state
from agents.swarm_graph import run_swarm_parallel
from inspector.inspector_graph import run_inspector_loop

console = Console()


async def run_scenario(
    label: str,
    ticker: str,
    inject: bool = False,
    inject_agent: str = "risk_agent",
    inject_type: str = "loop",
    inject_delay: float = 6.0,
) -> dict:
    console.print()
    console.print(Rule(f"[bold cyan]{label}[/bold cyan]", style="dim"))
    console.print(f"  Ticker: [yellow]{ticker}[/yellow]  |  "
                  f"Failure: [{'red' if inject else 'dim'}]"
                  f"{'AUTO → ' + inject_type + ' on ' + inject_agent if inject else 'None'}[/]")
    console.print()

    redis = await init_state()
    stop_event = asyncio.Event()
    start = time.time()

    tasks = [
        asyncio.create_task(run_swarm_parallel(ticker)),
        asyncio.create_task(run_inspector_loop(ticker, poll_interval=2.0,
                                               stop_event=stop_event, max_cycles=20)),
    ]

    if inject:
        async def _inject():
            await asyncio.sleep(inject_delay)
            await redis.inject_failure(ticker, inject_agent, inject_type)
            console.print(f"  [bold red]>>> INJECTED[/bold red] {inject_type} into {inject_agent}")
        tasks.append(asyncio.create_task(_inject()))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    stop_event.set()

    elapsed = time.time() - start
    swarm_state = results[0] if not isinstance(results[0], Exception) else {}

    synthesis = swarm_state.get("synthesis_result", "") if swarm_state else ""
    errors = swarm_state.get("errors", []) if swarm_state else []

    status = "[green]✓ COMPLETE[/green]" if synthesis else "[red]✗ INCOMPLETE[/red]"
    console.print(f"  {status}  ({elapsed:.1f}s)  errors={len(errors)}")
    if synthesis:
        # Print first 200 chars
        preview = synthesis[:200].replace("\n", " ")
        console.print(f"  [dim]{preview}...[/dim]")

    return {
        "label": label,
        "ticker": ticker,
        "elapsed": elapsed,
        "synthesis_preview": synthesis[:300] if synthesis else "",
        "errors": errors,
        "ok": bool(synthesis),
    }


async def main():
    mock = os.getenv("MOCK_LLM", "false").lower() in ("1", "true", "yes")

    console.print(Panel(
        f"[bold cyan]SwarmInspector Demo Batch[/bold cyan]\n\n"
        f"  Mode:  [yellow]{'MOCK — no API calls' if mock else 'LIVE — real LLM'}[/yellow]\n"
        f"  Goal:  Populate W&B Weave with 3 demo scenarios\n"
        f"  Weave: [dim]{get_weave_url() or '(initializing)'}[/dim]",
        border_style="cyan",
    ))

    init_weave()

    outcomes = []

    # Scenario 1: Clean run — best-case baseline
    r1 = await run_scenario(
        label="Scenario 1/3 — Clean Run (NVDA)",
        ticker="NVDA",
        inject=False,
    )
    outcomes.append(r1)
    await asyncio.sleep(1)

    # Scenario 2: Loop failure + inspector healing — the money shot
    r2 = await run_scenario(
        label="Scenario 2/3 — Loop Failure + Self-Healing (NVDA)",
        ticker="NVDA",
        inject=True,
        inject_agent="risk_agent",
        inject_type="loop",
        inject_delay=5.0,
    )
    outcomes.append(r2)
    await asyncio.sleep(1)

    # Scenario 3: Multi-ticker breadth demo
    for ticker in ["AAPL", "TSLA", "MSFT"]:
        r = await run_scenario(
            label=f"Scenario 3/3 — Multi-ticker Clean ({ticker})",
            ticker=ticker,
            inject=False,
        )
        outcomes.append(r)
        await asyncio.sleep(0.5)

    # Summary
    console.print()
    console.print(Rule("[bold green]Batch Complete[/bold green]", style="green"))
    passed = sum(1 for o in outcomes if o["ok"])
    console.print(f"\n  {passed}/{len(outcomes)} scenarios produced synthesis output\n")

    weave_url = get_weave_url()
    if weave_url:
        console.print(f"[bold]W&B Weave dashboard:[/bold] {weave_url}")
        console.print("[dim]You should see 5 separate trace groups in the Traces tab.[/dim]")
        console.print("[dim]The Scenario 2 trace will show the inspector.monitor → diagnostician → healer chain.[/dim]")
    else:
        console.print("[yellow]Set WANDB_API_KEY in .env to see traces in W&B Weave.[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())
