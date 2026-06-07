const BASE = "/api";

export interface AgentHeartbeat {
  agent_id: string;
  last_seen: number;
  call_count: number;
  last_tool: string;
  status: "running" | "stalled" | "failed" | "done" | "unknown";
}

export interface SwarmStatus {
  ticker: string;
  agents: Record<string, AgentHeartbeat>;
  timestamp: number;
  weave_url: string | null;
}

export async function getStatus(ticker: string): Promise<SwarmStatus> {
  const res = await fetch(`${BASE}/status/${ticker}`);
  if (!res.ok) throw new Error(`Status fetch failed: ${res.status}`);
  return res.json();
}

export async function injectFailure(
  ticker: string,
  agentId: string,
  failureType: string
): Promise<void> {
  const res = await fetch(`${BASE}/inject-failure`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, agent_id: agentId, failure_type: failureType }),
  });
  if (!res.ok) throw new Error(`Inject failed: ${res.status}`);
}

export async function startSwarm(
  ticker: string,
  injectFailure: boolean,
  failureAgent: string,
  failureType: string,
  failureDelay: number
): Promise<void> {
  const res = await fetch(`${BASE}/run-swarm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ticker,
      inject_failure: injectFailure,
      failure_agent: failureAgent,
      failure_type: failureType,
      failure_delay: failureDelay,
    }),
  });
  if (!res.ok) throw new Error(`Start swarm failed: ${res.status}`);
}
