# SwarmInspector
WeaveHacks 4: Multi-Agent Orchestration | June 6–7, 2026

# SwarmInspector UI

CopilotKit React dashboard for the SwarmInspector demo.

## Quick start

```bash
cd ui
npm install
npm run dev
# → http://localhost:3000
```

Requires the API server running at http://localhost:8000:
```bash
uvicorn api.server:app --reload --port 8000
```

## What it shows

- **4 agent cards** — real-time heartbeat status for earnings/risk/sentiment/synthesis
- **Inspector panel** — monitor → diagnostician → healer pipeline visualization
- **Control panel** — start swarm, inject failures, switch tickers
- **CopilotKit sidebar** — ask the AI about swarm status in natural language

## CopilotKit integration

The sidebar connects to `/api/copilotkit` (proxied to `http://localhost:8000/copilotkit`).
The AI has read access to live swarm state via `useCopilotReadable`.
