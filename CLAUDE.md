# CLAUDE.md — SwarmInspector Hackathon Handoff
# WeaveHacks 4: Multi-Agent Orchestration | June 6–7, 2026

## WHO YOU ARE & WHAT THIS IS

You are Claude Code, finishing a project started before the hackathon.
This is **SwarmInspector**: a meta-agent system that monitors a financial analysis
swarm in real time, detects failures (loops, silent drops, context drift),
and self-heals — all traced in W&B Weave.

Demo target: 3 minutes, Sunday demo session.
Builder: solo, limited time on-site.

---

## PROJECT STRUCTURE

```
swarm-inspector/
├── CLAUDE.md                  ← you are here
├── README.md
├── requirements.txt
├── .env.example
├── main.py                    ← entry point, run this for demo
├── demo_runner.py             ← scripted demo with injected failures
│
├── core/
│   ├── state.py               ← shared TypedDict state schemas
│   ├── weave_setup.py         ← W&B Weave init + decorators
│   └── redis_state.py         ← Redis shared state (with in-memory fallback)
│
├── agents/                    ← the "subject" swarm (financial analysis)
│   ├── earnings_agent.py      ← analyzes earnings data
│   ├── risk_agent.py          ← assesses risk factors
│   ├── sentiment_agent.py     ← sentiment from news/filings
│   ├── synthesis_agent.py     ← final report synthesis
│   └── swarm_graph.py         ← LangGraph graph wiring all 4 agents
│
├── inspector/                 ← the "meta" swarm (watches the subject swarm)
│   ├── monitor_agent.py       ← polls Weave traces + Redis heartbeats
│   ├── diagnostician_agent.py ← classifies failure type
│   ├── healer_agent.py        ← executes recovery action
│   └── inspector_graph.py     ← LangGraph graph for inspector loop
│
├── api/
│   └── server.py              ← FastAPI server (CopilotKit-compatible)
│
├── ui/                        ← CopilotKit React dashboard (finish at hackathon)
│   └── README.md
│
└── scripts/
    └── inject_failure.py      ← CLI tool to manually trigger failures for demo
```

---

## DEMO STORY (3 MINUTES — MEMORIZE THIS)

**Minute 1 — Setup**
> "I built a financial analysis swarm: 4 agents working in parallel on a stock.
> Earnings agent, Risk agent, Sentiment agent, Synthesis agent.
> Each writes heartbeats to Redis. All traces go to W&B Weave."

Show: swarm running normally in terminal OR the dashboard

**Minute 2 — Failure injection**
> "Now watch what happens when the Risk agent enters a silent loop —
> it keeps calling the same tool without making progress."

Run: `python scripts/inject_failure.py --agent risk --type loop`

Show: Inspector swarm wakes up → Monitor detects missed heartbeat →
Diagnostician classifies "infinite_loop" → Healer restarts the agent with a
modified prompt + loop-break instruction. All of this is visible in Weave traces.

**Minute 3 — Resolution + insight**
> "The swarm heals itself. The Synthesis agent gets the result.
> And in Weave, you can see the full trace: what failed, when, why, and what fixed it.
> This is what multi-agent observability looks like in production."

Show: Weave dashboard with the anomaly trace highlighted. Final synthesis output.

---

## WHAT'S ALREADY BUILT (pre-hackathon)

- [x] Core state schemas (`core/state.py`)
- [x] Weave setup + `@weave.op()` decorators (`core/weave_setup.py`)
- [x] Redis state with in-memory fallback (`core/redis_state.py`)
- [x] All 4 financial agents (working, realistic mock data)
- [x] Subject swarm LangGraph graph (`agents/swarm_graph.py`)
- [x] All 3 inspector agents (monitor, diagnostician, healer)
- [x] Inspector LangGraph graph (`inspector/inspector_graph.py`)
- [x] Failure injection script (`scripts/inject_failure.py`)
- [x] FastAPI server skeleton (`api/server.py`)

## WHAT CLAUDE CODE NEEDS TO FINISH

- [ ] `main.py` — wire everything together, clean startup
- [ ] `demo_runner.py` — scripted demo that auto-injects failure after 15s
- [ ] `ui/` — CopilotKit React dashboard (see ui/README.md)
- [ ] Redis connection using actual Redis sponsor credentials (if available)
  - Fallback: `core/redis_state.py` already has in-memory mode, just works
- [ ] Daily.co integration (OPTIONAL — voice narration of agent events)
  - If Daily is sponsoring: add a voice agent that reads aloud what the inspector finds
- [ ] Cursor integration (OPTIONAL — show agents editing their own prompts)
- [ ] Final W&B Weave project name: `swarm-inspector-weavehacks4`

---

## ENVIRONMENT VARIABLES NEEDED

```bash
# Required
ANTHROPIC_API_KEY=          # your key
WANDB_API_KEY=              # from wandb.ai — project: swarm-inspector-weavehacks4

# Optional (use in-memory fallback if not available)
REDIS_URL=redis://localhost:6379

# Optional sponsors
DAILY_API_KEY=              # if Daily is available at hackathon
```

---

## KEY TECHNICAL DECISIONS

**Why LangGraph over pure asyncio?**
LangGraph gives us state persistence + easy graph visualization for the demo.
The inspector graph runs as a separate compiled graph that shares state
via Redis (or in-memory dict). Two graphs, one shared state layer.

**Failure types implemented:**
1. `loop` — agent calls same tool repeatedly (detected by: tool_call_count > threshold)
2. `silent_drop` — agent stops sending heartbeats (detected by: heartbeat timeout)
3. `context_drift` — agent output stops referencing the input ticker (detected by: LLM judge)

**W&B Weave integration strategy:**
- Every agent node is wrapped with `@weave.op()`
- Inspector reads Weave call metadata via `weave.Api()` to detect anomalies
- Final demo shows the Weave UI with the anomaly highlighted

**In-memory fallback:**
If Redis is down or not available, `RedisState` class transparently uses a dict.
Nothing else needs to change. Just works.

---

## COMMANDS

```bash
# Install
pip install -r requirements.txt

# Set env
cp .env.example .env
# fill in ANTHROPIC_API_KEY and WANDB_API_KEY

# Run full system
python main.py

# Run scripted demo (auto-injects failure after 15s)
python demo_runner.py

# Manually inject a failure
python scripts/inject_failure.py --agent risk --type loop
python scripts/inject_failure.py --agent sentiment --type silent_drop

# Run API server (for CopilotKit dashboard)
uvicorn api.server:app --reload --port 8000
```

---

## JUDGING CRITERIA — HOW WE WIN SHORTLIST

From WeaveHacks rubric:
1. **Theme** — multi-agent orchestration ✅ (inspector IS the orchestrator)
2. **Weave usage** — deeply integrated, not bolted on ✅
3. **Sponsor tools** — Redis (state), CopilotKit (UI), Daily (optional narration) ✅
4. **Demo clarity** — 3-minute arc with clear before/after ✅
5. **Creativity** — agents watching agents is the meta-joke judges will love ✅

**The one-liner for judges:**
> "SwarmInspector: a multi-agent system that uses agents to debug agents,
> with every failure, diagnosis, and recovery traced in W&B Weave."

---

## IF THINGS BREAK (contingency)

**If LangGraph is slow:** switch to pure asyncio orchestration in `core/fallback_runner.py`
(not yet written — Claude Code can write this in ~10 min if needed)

**If Weave traces aren't showing:** double-check `wandb.init()` is called before any `@weave.op()`.
Project name must match exactly: `swarm-inspector-weavehacks4`

**If Redis isn't available:** `RedisState(use_memory=True)` — already handled in `core/redis_state.py`

**If demo_runner.py fails:** run `main.py` manually and use `inject_failure.py` from a second terminal.
Same effect, slightly less polished.

**Nuclear option (still shortlist-worthy):**
Just run `main.py`, show the Weave dashboard, explain the architecture verbally.
The code quality and Weave traces alone are enough to shortlist.
