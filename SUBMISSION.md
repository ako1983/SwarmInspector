# SUBMISSION.md


## Team name
ClaAko

## Team members
- Ako Heidari (solo) | GitHub: github.com/ako1983 | W&B: wandb.ai/profile/ako-oka

---

## 2–3 sentence summary

SwarmInspector is a meta-agent system that deploys an inspector swarm to monitor,
diagnose, and self-heal a financial analysis swarm in real time. When an agent
enters an infinite loop, drops silent, or drifts context, the inspector swarm
detects it within seconds, classifies the failure using LLM reasoning, and sends
a targeted recovery signal — all with full trace visibility in W&B Weave.
It's agents watching agents: multi-agent observability as a first-class system.

---

## What it does / what it's useful for

Production multi-agent systems fail silently. A single agent stuck in a loop
can block an entire pipeline for minutes while the orchestrator has no idea.
SwarmInspector solves this by adding a second layer of agents whose only job
is to watch the first layer.

The financial analysis swarm (earnings, risk, sentiment, synthesis agents)
analyzes a stock ticker in parallel. The inspector swarm (monitor, diagnostician,
healer) polls Redis heartbeats and W&B Weave traces every 2 seconds.

When an anomaly is detected:
1. **Monitor** flags it (missed heartbeat, repeated tool call, context drift)
2. **Diagnostician** classifies it using LLM reasoning and names the root cause
3. **Healer** sends a targeted recovery signal via Redis

The swarm heals itself without human intervention. The full trace — what failed,
when, why, and what fixed it — is visible in W&B Weave.

---

## How it's built

**Orchestration:** LangGraph (two compiled graphs: subject swarm + inspector swarm)
**Agent communication:** asyncio + Redis pub/sub (shared heartbeat + signal layer)
**Agent protocols:** MCP (W&B MCP server for trace querying), A2A-style coordination
between inspector agents via shared InspectorState
**LLM:** Anthropic Claude (agents) + W&B Weave Inference (diagnostician)
**Observability:** W&B Weave — every agent node wrapped with @weave.op()
**Frontend:** CopilotKit (AG-UI protocol) for live dashboard with useCopilotAction
**API:** FastAPI serving agent state to CopilotKit

**Failure types implemented:**
- `infinite_loop` — detected via tool call rate heuristic
- `silent_drop` — detected via heartbeat timeout (>6s)
- `context_drift` — detected via LLM judge (agent analyzing wrong ticker)

---

## Sponsor tools used

| Tool | How used | Depth |
|------|----------|-------|
| **W&B Weave** | Every agent node traced with @weave.op(). Inspector reads Weave call metadata to detect anomalies. Final demo shows Weave UI with anomaly highlighted. | Deep |
| **Redis** | Shared state layer between both swarms. Heartbeats, failure injection signals, and recovery signals all route through Redis. Inspector can't function without it. | Deep |
| **CopilotKit** | AG-UI dashboard with useCopilotAction — judges can ask "what failed?" and get a live answer from inspector state. Real-time agent status grid. | Medium |
| **W&B MCP Server** | Used during development with Claude Code to inspect live Weave traces while building | Light |
| **Cursor** | Primary IDE with $100 sponsor credits | Light |
| **OpenAI** | [If used: gpt-4o-mini for one agent variant] | [Light] |

---

## W&B Weave project link
https://wandb.ai/ako-oka/swarm-inspector-weavehacks4

## GitHub repo
[ADD PUBLIC REPO LINK — make sure it's public before submitting]

## Demo video
[ADD LOOM/YOUTUBE LINK — record a 90-second screen recording before 1pm]

---

## One-liner for judges
"We used agents to debug agents — and traced every failure, diagnosis, and recovery in W&B Weave."
