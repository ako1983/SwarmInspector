import React, { useEffect, useRef, useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { useCopilotReadable } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

import { getStatus, type SwarmStatus } from "./api/client";
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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Expose swarm status to CopilotKit so the AI can answer questions about it
  useCopilotReadable({
    description: "Current SwarmInspector status — agent heartbeats, anomalies, and recovery",
    value: {
      ticker,
      agents: status?.agents ?? {},
      anomalyDetected,
      diagnosis,
      recoveryLog,
      inspectorCycles,
      weaveUrl: status?.weave_url,
    },
  });

  useEffect(() => {
    const poll = async () => {
      try {
        const s = await getStatus(ticker);
        setStatus(s);

        // Detect anomalies from heartbeat data
        const now = Date.now() / 1000;
        for (const [agentId, hb] of Object.entries(s.agents)) {
          const timeSince = now - hb.last_seen;
          const callsPerSec = hb.call_count / Math.max(timeSince, 1);

          if (hb.status !== "done" && hb.status !== "failed") {
            if (timeSince > 8) {
              setAnomalyDetected(true);
              setFailedAgent(agentId);
              setDiagnosis(`${agentId} has not sent a heartbeat for ${timeSince.toFixed(1)}s — possible silent drop or stall.`);
            } else if (callsPerSec > 0.8 && hb.call_count > 6 && timeSince > 3) {
              setAnomalyDetected(true);
              setFailedAgent(agentId);
              setDiagnosis(`${agentId} is making ${callsPerSec.toFixed(1)} tool calls/sec — infinite loop detected. Inspector dispatching recovery signal.`);
            }
          }
        }
      } catch {
        // API not running yet — silent fail
      }
    };

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [ticker]);

  const weaveUrl = status?.weave_url;

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
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
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
                background: anomalyDetected
                  ? "rgba(239,68,68,0.1)"
                  : "rgba(34,197,94,0.1)",
                border: `1px solid ${anomalyDetected ? "rgba(239,68,68,0.4)" : "rgba(34,197,94,0.3)"}`,
                color: anomalyDetected ? "#f87171" : "#4ade80",
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {anomalyDetected ? "🔴 ANOMALY DETECTED" : "🟢 NOMINAL"}
            </div>
          </div>
        </div>

        {/* Subject swarm agent cards */}
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

        {/* Inspector + Controls side-by-side */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 320px",
            gap: 16,
          }}
        >
          <InspectorPanel
            recoveryLog={recoveryLog}
            anomalyDetected={anomalyDetected}
            diagnosis={diagnosis}
            cycles={inspectorCycles}
          />
          <ControlPanel ticker={ticker} onTickerChange={setTicker} />
        </div>

        {/* Synthesis output */}
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
              All agents finished. Check the terminal for the full synthesis
              report, or view the Weave trace for complete execution details.
            </div>
          </div>
        )}
      </div>

      {/* ── CopilotKit sidebar ────────────────────────────────────────────── */}
      <CopilotSidebar
        defaultOpen={false}
        labels={{
          title: "SwarmInspector AI",
          initial:
            "Ask me about the swarm! Try: 'Which agents are running?', 'Was there a failure?', 'What did the inspector find?'",
        }}
        instructions={`You are SwarmInspector's AI assistant. You have real-time access to the swarm status.
Answer questions about agent health, failures, recovery actions, and what the inspector found.
Be concise and technical. Reference specific agent names and metrics when answering.`}
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
