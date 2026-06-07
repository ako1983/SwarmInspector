# SwarmInspector
**WeaveHacks 4: Multi-Agent Orchestration | June 6–7, 2026**

> A multi-agent system that uses agents to debug agents — with every failure, diagnosis, and recovery traced in W&B Weave.

---

## What it is

SwarmInspector runs two swarms in parallel:

1. **Subject swarm** — 4 financial analysis agents (earnings, risk, sentiment, synthesis) that analyze a stock ticker in parallel
2. **Inspector swarm** — 3 meta-agents (monitor, diagnostician, healer) that watch the subject swarm, detect failures, and self-heal

All agent calls are traced in [W&B Weave](https://wandb.ai) under `swarm-inspector-weavehacks4`.

---

## Demo story (3 minutes)

| Minute | What happens |
|--------|-------------|
| 1 | Subject swarm starts analyzing NVDA — 4 agents visible in terminal |
| 2 | Risk agent enters an infinite loop (injected) → Inspector detects → Diagnostician classifies → Healer sends recovery signal |
| 3 | Risk agent breaks loop, Synthesis produces full report, Weave trace shows the whole chain |

---

## Quick start

```bash
pip install -r requirements.txt

cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, WANDB_API_KEY

# Scripted 3-min demo (auto-injects loop failure at 15s)
python demo_runner.py

# Or run manually and inject from a second terminal
python main.py
python scripts/inject_failure.py --agent risk_agent --type loop
```

---

## Project structure

```
├── main.py                    ← entry point
├── demo_runner.py             ← scripted demo with auto-injection
├── core/
│   ├── state.py               ← shared TypedDict schemas
│   ├── weave_setup.py         ← W&B Weave init + @agent_op / @inspector_op
│   └── redis_state.py         ← Redis state (in-memory fallback included)
├── agents/                    ← subject swarm
│   ├── earnings_agent.py
│   ├── risk_agent.py          ← demo failure target
│   ├── sentiment_agent.py
│   ├── synthesis_agent.py
│   └── swarm_graph.py         ← asyncio parallel fan-out
├── inspector/                 ← meta swarm
│   ├── monitor_agent.py       ← heartbeat polling + anomaly detection
│   ├── diagnostician_agent.py ← LLM failure classification
│   ├── healer_agent.py        ← recovery via Redis signal
│   └── inspector_graph.py     ← inspector control loop
├── api/server.py              ← FastAPI (REST + CopilotKit endpoint)
├── scripts/inject_failure.py  ← CLI failure injector
└── ui/                        ← CopilotKit React dashboard
```

---

## Failure types

| Type | How it's detected | How it's healed |
|------|--------------------|-----------------|
| `loop` | call_count rate > 0.8/sec | Redis signal → agent breaks loop |
| `silent_drop` | no heartbeat for >8s | agent marked failed, synthesis skips it |
| `context_drift` | LLM judge (future) | restart signal with corrected ticker |

---

## Dashboard UI

```bash
uvicorn api.server:app --reload --port 8000

cd ui
npm install
npm run dev   # → http://localhost:3000
```

Live agent status cards, inspector pipeline visualization (monitor→diagnostician→healer),
failure injection controls, and a CopilotKit AI sidebar you can ask "what went wrong?".

---

## Environment variables

```bash
ANTHROPIC_API_KEY=   # required
WANDB_API_KEY=       # required — project: swarm-inspector-weavehacks4
REDIS_URL=           # optional, falls back to in-memory
```
