import React, { useEffect, useRef, useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { useCopilotReadable, useCopilotAction } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

import { getStatus, injectFailure, startSwarm, type SwarmStatus } from "./api/client";
import { AgentCard } from "./components/AgentCard";
import { InspectorPanel } from "./components/InspectorPanel";
import { ControlPanel } from "./components/ControlPanel";

const SUBJECT_AGENTS = [
  "earnings_agent",
  "risk_agent",
  "sentiment_agent",
  "synthesis_agent",
] as const;

const POLL_INTERVAL_MS = 1500;

export default function App() {
  const [ticker, setTicker] = useState("NVDA");
  const [status, setStatus] = useState<SwarmStatus | null>(null);
  const [recoveryLog, setRecoveryLog] = useState<string[]>([]);
  const [diagnosis, setDiagnosis] = useState<string | null>(null);
  const [anomalyDetected, setAnomalyDetected] = useState(false);
  const [inspectorCycles, setInspectorCycles] = useState(0);
  const [failedAgent, setFailedAgent] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Expose live swarm state to the CopilotKit AI ─────────────────────────
  useCopilotReadable({
    description: "Live SwarmInspector status — agent heartbeats, anomalies, recovery log, and Weave traces",
    value: {
      ticker,
      agents: status?.agents ?? {},
      anomalyDetected,
      failedAgent,
      diagnosis,
      recoveryLog,
      inspectorCycles,
      weaveUrl: status?.weave_url ?? null,
    },
  });

  // ── CopilotKit actions — AI can trigger these from the chat sidebar ───────

  useCopilotAction({
    name: "switch_ticker",
    description: "Switch the swarm to analyze a different stock ticker",
    parameters: [
      {
        name: "ticker",
        type: "string",
        description: "Stock ticker symbol: NVDA, AAPL, TSLA, or MSFT",
        required: true,
      },
    ],
    handler: async ({ ticker: t }: { ticker: string }) => {
      const upper = t.toUpperCase();
      setTicker(upper);
      setAnomalyDetected(false);
      setFailedAgent(null);
      setDiagnosis(null);
      setRecoveryLog([]);
      setActionFeedback(`Switched to ${upper}`);
      return `Switched dashboard to ${upper}. Status panel will update momentarily.`;
    },
  });

  useCopilotAction({
    name: "inject_failure",
    description:
      "Inject a failure into an agent to demonstrate SwarmInspector's self-healing. " +
      "Use this during the demo to show the inspector catching and recovering from agent failures.",
    parameters: [
      {
        name: "agent",
        type: "string",
        description: "Agent to target: risk_agent, earnings_agent, or sentiment_agent",
        required: true,
      },
      {
        name: "failure_type",
        type: "string",
        description: "Type of failure: 'loop' (infinite tool loop) or 'silent_drop' (agent goes silent)",
        required: true,
      },
    ],
    handler: async ({ agent, failure_type }: { agent: string; failure_type: string }) => {
      await injectFailure(ticker, agent, failure_type);
      setAnomalyDetected(true);
      setFailedAgent(agent);
      setDiagnosis(`${agent} entered a ${failure_type} — inspector dispatching recovery signal.`);
      setActionFeedback(`Injected ${failure_type} → ${agent}`);
      return `Injected ${failure_type} into ${agent} for ${ticker}. Watch the dashboard — the inspector will detect this within ~5 seconds and dispatch a recovery signal.`;
    },
  });

  useCopilotAction({
    name: "start_swarm",
    description: "Start a fresh swarm analysis run for the current ticker",
    parameters: [
      {
        name: "with_failure",
        type: "boolean",
        description: "If true, auto-inject a loop failure after 10s to demo self-healing",
        required: false,
      },
    ],
    handler: async ({ with_failure }: { with_failure?: boolean }) => {
      await startSwarm(ticker, with_failure ?? false, "risk_agent", "loop", 10);
      setAnomalyDetected(false);
      setFailedAgent(null);
      setDiagnosis(null);
      setRecoveryLog([]);
      const mode = with_failure ? "with loop failure injection in 10s" : "clean run";
      setActionFeedback(`Swarm started (${mode})`);
      return `Swarm analysis started for ${ticker} (${mode}). Watch the agent cards for real-time status.`;
    },
  });

  useCopilotAction({
    name: "explain_architecture",
    description: "Explain how SwarmInspector works for a judge or audience member",
    parameters: [],
    handler: async () => {
      return `SwarmInspector is a meta-agent system built for WeaveHacks 4.

SUBJECT SWARM (what gets monitored):
• 4 agents analyze a stock in parallel: Earnings, Risk, Sentiment → Synthesis
• Each agent writes heartbeats to Redis every time it calls a tool
• All operations are traced with @weave.op() to W&B Weave

INSPECTOR SWARM (what does the monitoring):
• Monitor agent: polls Redis heartbeats every 2s, detects anomalies
  - Infinite loop: call rate > 0.8/sec AND call count > 6
  - Silent drop: no heartbeat for > 8 seconds
• Diagnostician agent: classifies the failure via LLM analysis
• Healer agent: sends a Redis recovery signal to the stuck agent

SELF-HEALING DEMO:
1. Risk agent enters an infinite loop (injected failure)
2. Monitor detects it: "3.2 calls/sec — this is a loop"
3. Diagnostician: "FAILURE_TYPE: infinite_loop, ACTION: modify_prompt"
4. Healer: writes recovery signal to Redis
5. Risk agent reads signal, breaks loop, completes normally
6. Synthesis agent gets the result and writes the final report

Everything — the failure, diagnosis, and recovery — is visible in W&B Weave traces.`;
    },
  });

  // ── Polling for live status ───────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const s = await getStatus(ticker);
        setStatus(s);

        const now = Date.now() / 1000;
        let detected = false;
        for (const [agentId, hb] of Object.entries(s.agents)) {
          const timeSince = now - hb.last_seen;
          const callsPerSec = hb.call_count / Math.max(timeSince, 1);

          if (hb.status !== "done" && hb.status !== "failed") {
            if (timeSince > 8 && hb.call_count > 0) {
              detected = true;
              setFailedAgent(agentId);
              setDiagnosis(
                `${agentId} has not sent a heartbeat for ${timeSince.toFixed(1)}s — ` +
                `possible silent drop. Inspector monitoring...`
              );
            } else if (callsPerSec > 0.8 && hb.call_count > 6 && timeSince > 3) {
              detected = true;
              setFailedAgent(agentId);
              setDiagnosis(
                `${agentId} is making ${callsPerSec.toFixed(1)} tool calls/sec — ` +
                `infinite loop detected. Inspector dispatching recovery signal.`
              );
              setInspectorCycles((c) => c + 1);
            }
          }
        }
        setAnomalyDetected(detected);
      } catch {
        // API not running — silent fail, keep showing last known state
      }
    };

    setStatus(null);
    setAnomalyDetected(false);
    setFailedAgent(null);
    setDiagnosis(null);
    setRecoveryLog([]);
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [ticker]);

  const weaveUrl = status?.weave_url ?? null;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* ── Main dashboard ───────────────────────────────────────────────── */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "auto",
          padding: 24,
          gap: 20,
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1
              style={{
                fontSize: 24,
                fontWeight: 800,
                background: "linear-gradient(90deg, #6366f1, #22d3ee)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                letterSpacing: -0.5,
              }}
            >
              SwarmInspector
            </h1>
            <div style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>
              Multi-agent observability · WeaveHacks 4
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {weaveUrl && (
              <a
                href={weaveUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: "8px 16px",
                  borderRadius: 8,
                  background: "rgba(251,191,36,0.1)",
                  border: "1px solid rgba(251,191,36,0.3)",
                  color: "#fbbf24",
                  fontSize: 12,
                  fontWeight: 600,
                  textDecoration: "none",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span>🔗</span> View in W&B Weave
              </a>
            )}
            <div
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                background: anomalyDetected ? "rgba(239,68,68,0.1)" : "rgba(34,197,94,0.1)",
                border: `1px solid ${anomalyDetected ? "rgba(239,68,68,0.4)" : "rgba(34,197,94,0.3)"}`,
                color: anomalyDetected ? "#f87171" : "#4ade80",
                fontSize: 12,
                fontWeight: 600,
                animation: anomalyDetected ? "pulse 1.5s infinite" : "none",
              }}
            >
              {anomalyDetected ? "🔴 ANOMALY DETECTED" : "🟢 NOMINAL"}
            </div>
          </div>
        </div>

        {/* Action feedback toast */}
        {actionFeedback && (
          <div
            style={{
              background: "rgba(99,102,241,0.15)",
              border: "1px solid rgba(99,102,241,0.4)",
              borderRadius: 8,
              padding: "10px 16px",
              fontSize: 12,
              color: "#a5b4fc",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <span>⚡</span>
            <span>AI action: {actionFeedback}</span>
            <button
              onClick={() => setActionFeedback(null)}
              style={{ marginLeft: "auto", background: "none", border: "none", color: "#6366f1", cursor: "pointer", fontSize: 14 }}
            >
              ×
            </button>
          </div>
        )}

        {/* Agent cards */}
        <div>
          <div
            style={{
              fontSize: 11,
              color: "#64748b",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: 1,
              marginBottom: 12,
            }}
          >
            Financial Analysis Swarm — {ticker}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            {SUBJECT_AGENTS.map((agentId) => (
              <AgentCard
                key={agentId}
                agentId={agentId}
                heartbeat={status?.agents[agentId]}
                isTarget={failedAgent === agentId && anomalyDetected}
              />
            ))}
          </div>
        </div>

        {/* Inspector + Controls */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16 }}>
          <InspectorPanel
            recoveryLog={recoveryLog}
            anomalyDetected={anomalyDetected}
            diagnosis={diagnosis}
            cycles={inspectorCycles}
          />
          <ControlPanel
            ticker={ticker}
            onTickerChange={(t) => {
              setTicker(t);
              setAnomalyDetected(false);
              setFailedAgent(null);
              setDiagnosis(null);
              setRecoveryLog([]);
            }}
          />
        </div>

        {/* Synthesis complete banner */}
        {status?.agents?.synthesis_agent?.status === "done" && (
          <div
            style={{
              background: "rgba(34,197,94,0.05)",
              border: "1px solid rgba(34,197,94,0.2)",
              borderRadius: 12,
              padding: 20,
            }}
          >
            <div
              style={{
                fontSize: 11,
                color: "#4ade80",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 10,
              }}
            >
              ✓ Final Synthesis Complete
            </div>
            <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6 }}>
              All agents finished. Full execution trace available in W&B Weave.
              {weaveUrl && (
                <> {" "}
                  <a href={weaveUrl} target="_blank" rel="noopener noreferrer"
                    style={{ color: "#fbbf24", textDecoration: "none" }}>
                    View trace →
                  </a>
                </>
              )}
            </div>
          </div>
        )}

        {/* API offline notice */}
        {!status && (
          <div
            style={{
              background: "rgba(239,68,68,0.05)",
              border: "1px solid rgba(239,68,68,0.2)",
              borderRadius: 12,
              padding: 20,
              fontSize: 13,
              color: "#94a3b8",
            }}
          >
            <span style={{ color: "#f87171", fontWeight: 600 }}>API offline</span>
            {" — "}start the backend:{" "}
            <code style={{ fontFamily: "monospace", color: "#7dd3fc", fontSize: 12 }}>
              uvicorn api.server:app --reload --port 8000
            </code>
          </div>
        )}
      </div>

      {/* ── CopilotKit AI sidebar ─────────────────────────────────────────── */}
      <CopilotSidebar
        defaultOpen={false}
        labels={{
          title: "SwarmInspector AI",
          initial:
            "Ask me about the swarm or give me commands!\n\nTry:\n" +
            "• \"Which agents are running?\"\n" +
            "• \"Inject a loop failure into the risk agent\"\n" +
            "• \"Start a clean analysis of AAPL\"\n" +
            "• \"Explain the architecture to a judge\"\n" +
            "• \"What did the inspector find?\"",
        }}
        instructions={`You are SwarmInspector's AI assistant with real-time access to swarm status.

You can:
- Answer questions about agent health, failures, and recovery
- Inject failures (inject_failure action)
- Start new analysis runs (start_swarm action)
- Switch tickers (switch_ticker action)
- Explain the architecture (explain_architecture action)

Be concise and technical. Reference specific agent names, call counts, and timings.
When injecting failures, confirm what you did and tell the user to watch the dashboard.`}
      />

      <style>{`
        @keyframes pulse-bar {
          0%, 100% { opacity: 0.3; transform: translateX(-100%); }
          50% { opacity: 1; transform: translateX(100%); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
      `}</style>
    </div>
  );
}
