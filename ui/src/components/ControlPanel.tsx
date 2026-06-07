import React, { useState } from "react";
import { injectFailure, startSwarm } from "../api/client";

interface Props {
  ticker: string;
  onTickerChange: (t: string) => void;
}

export const ControlPanel: React.FC<Props> = ({ ticker, onTickerChange }) => {
  const [loading, setLoading] = useState(false);
  const [lastAction, setLastAction] = useState<string | null>(null);

  const doInject = async (agent: string, type: string) => {
    setLoading(true);
    try {
      await injectFailure(ticker, agent, type);
      setLastAction(`Injected ${type} → ${agent}`);
    } catch (e) {
      setLastAction(`Error: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const doStart = async (withInject: boolean) => {
    setLoading(true);
    try {
      await startSwarm(ticker, withInject, "risk_agent", "loop", 10);
      setLastAction(
        withInject
          ? `Started swarm with loop injection in 10s`
          : "Started swarm (no failure)"
      );
    } catch (e) {
      setLastAction(`Error: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const TICKERS = ["NVDA", "AAPL", "TSLA", "MSFT"];

  return (
    <div
      style={{
        background: "rgba(15, 23, 42, 0.8)",
        border: "1px solid rgba(100,116,139,0.2)",
        borderRadius: 12,
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div
        style={{
          fontWeight: 700,
          fontSize: 14,
          color: "#94a3b8",
          textTransform: "uppercase",
          letterSpacing: 1,
        }}
      >
        Controls
      </div>

      {/* Ticker selector */}
      <div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>
          TICKER
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => onTickerChange(t)}
              style={{
                padding: "6px 14px",
                borderRadius: 6,
                border: `1px solid ${ticker === t ? "#6366f1" : "rgba(100,116,139,0.3)"}`,
                background: ticker === t ? "rgba(99,102,241,0.2)" : "transparent",
                color: ticker === t ? "#a5b4fc" : "#64748b",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: ticker === t ? 700 : 400,
                transition: "all 0.2s",
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Start buttons */}
      <div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>
          RUN SWARM
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => doStart(false)}
            disabled={loading}
            style={{
              flex: 1,
              padding: "10px",
              borderRadius: 8,
              border: "1px solid rgba(34,197,94,0.4)",
              background: "rgba(34,197,94,0.1)",
              color: "#4ade80",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            ▶ Clean Run
          </button>
          <button
            onClick={() => doStart(true)}
            disabled={loading}
            style={{
              flex: 1,
              padding: "10px",
              borderRadius: 8,
              border: "1px solid rgba(239,68,68,0.4)",
              background: "rgba(239,68,68,0.1)",
              color: "#f87171",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            💥 Inject Loop
          </button>
        </div>
      </div>

      {/* Manual injection */}
      <div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>
          INJECT FAILURE MANUALLY
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
          {[
            { agent: "risk_agent", type: "loop", label: "Risk: Loop" },
            { agent: "risk_agent", type: "silent_drop", label: "Risk: Silent Drop" },
            { agent: "sentiment_agent", type: "loop", label: "Sentiment: Loop" },
            { agent: "earnings_agent", type: "silent_drop", label: "Earnings: Drop" },
          ].map(({ agent, type, label }) => (
            <button
              key={`${agent}-${type}`}
              onClick={() => doInject(agent, type)}
              disabled={loading}
              style={{
                padding: "8px 6px",
                borderRadius: 6,
                border: "1px solid rgba(239,68,68,0.25)",
                background: "rgba(239,68,68,0.05)",
                color: "#fca5a5",
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: 11,
                textAlign: "center",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {lastAction && (
        <div
          style={{
            fontSize: 11,
            color: "#64748b",
            fontFamily: "monospace",
            padding: "6px 10px",
            background: "rgba(0,0,0,0.3)",
            borderRadius: 6,
          }}
        >
          {lastAction}
        </div>
      )}
    </div>
  );
};
