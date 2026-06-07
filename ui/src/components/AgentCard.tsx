import React from "react";
import type { AgentHeartbeat } from "../api/client";

interface Props {
  agentId: string;
  heartbeat: AgentHeartbeat | undefined;
  isTarget?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  running: "#22c55e",
  done: "#4ade80",
  failed: "#ef4444",
  stalled: "#eab308",
  unknown: "#64748b",
};

const AGENT_ICONS: Record<string, string> = {
  earnings_agent: "📈",
  risk_agent: "⚠️",
  sentiment_agent: "💬",
  synthesis_agent: "🧠",
};

const AGENT_LABELS: Record<string, string> = {
  earnings_agent: "Earnings",
  risk_agent: "Risk",
  sentiment_agent: "Sentiment",
  synthesis_agent: "Synthesis",
};

export const AgentCard: React.FC<Props> = ({ agentId, heartbeat, isTarget }) => {
  const status = heartbeat?.status ?? "unknown";
  const color = STATUS_COLORS[status] ?? "#64748b";
  const now = Date.now() / 1000;
  const lastSeenAgo = heartbeat ? Math.max(0, now - heartbeat.last_seen) : null;

  return (
    <div
      style={{
        background: isTarget ? "rgba(239,68,68,0.08)" : "rgba(30,41,59,0.8)",
        border: `1px solid ${isTarget ? "#ef4444" : "rgba(100,116,139,0.3)"}`,
        borderRadius: 12,
        padding: "16px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        transition: "all 0.3s ease",
        boxShadow: isTarget ? "0 0 20px rgba(239,68,68,0.2)" : "none",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Pulse animation for running */}
      {status === "running" && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 2,
            background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
            animation: "pulse-bar 2s ease-in-out infinite",
          }}
        />
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 24 }}>{AGENT_ICONS[agentId] ?? "🤖"}</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: "#f1f5f9" }}>
            {AGENT_LABELS[agentId] ?? agentId}
          </div>
          <div style={{ fontSize: 11, color: "#64748b", fontFamily: "monospace" }}>
            {agentId}
          </div>
        </div>
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: color,
              boxShadow: status === "running" ? `0 0 8px ${color}` : "none",
            }}
          />
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              color,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            {status}
          </span>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
          fontSize: 12,
          color: "#94a3b8",
        }}
      >
        <div>
          <span style={{ color: "#64748b" }}>Tool calls: </span>
          <span style={{ color: "#e2e8f0", fontWeight: 600 }}>
            {heartbeat?.call_count ?? "—"}
          </span>
        </div>
        <div>
          <span style={{ color: "#64748b" }}>Last seen: </span>
          <span
            style={{
              color: lastSeenAgo && lastSeenAgo > 8 ? "#ef4444" : "#e2e8f0",
              fontWeight: 600,
            }}
          >
            {lastSeenAgo !== null ? `${lastSeenAgo.toFixed(1)}s ago` : "—"}
          </span>
        </div>
        <div style={{ gridColumn: "1 / -1" }}>
          <span style={{ color: "#64748b" }}>Last tool: </span>
          <span style={{ color: "#7dd3fc", fontFamily: "monospace", fontSize: 11 }}>
            {heartbeat?.last_tool || "—"}
          </span>
        </div>
      </div>

      {isTarget && (
        <div
          style={{
            background: "rgba(239,68,68,0.15)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 6,
            padding: "6px 10px",
            fontSize: 11,
            color: "#fca5a5",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span>🔴</span>
          <span>FAILURE INJECTED — Inspector responding...</span>
        </div>
      )}
    </div>
  );
};
