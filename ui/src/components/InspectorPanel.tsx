import React from "react";

interface Props {
  recoveryLog: string[];
  anomalyDetected: boolean;
  diagnosis: string | null;
  cycles: number;
}

export const InspectorPanel: React.FC<Props> = ({
  recoveryLog,
  anomalyDetected,
  diagnosis,
  cycles,
}) => {
  const phases = [
    { id: "monitor", label: "Monitor", icon: "👁️", desc: "Polls heartbeats" },
    { id: "diagnostician", label: "Diagnostician", icon: "🔬", desc: "Classifies failure" },
    { id: "healer", label: "Healer", icon: "💊", desc: "Executes recovery" },
  ];

  const activePhase = anomalyDetected
    ? recoveryLog.length === 0
      ? "diagnostician"
      : "healer"
    : "monitor";

  return (
    <div
      style={{
        background: "rgba(15, 23, 42, 0.8)",
        border: "1px solid rgba(99, 102, 241, 0.3)",
        borderRadius: 12,
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderBottom: "1px solid rgba(99,102,241,0.2)",
          paddingBottom: 12,
        }}
      >
        <span style={{ fontSize: 20 }}>🔍</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: "#a5b4fc" }}>
            Inspector Swarm
          </div>
          <div style={{ fontSize: 11, color: "#64748b" }}>
            Cycle {cycles} — meta-agent monitoring
          </div>
        </div>
      </div>

      {/* Phase indicators */}
      <div style={{ display: "flex", gap: 8 }}>
        {phases.map((phase, i) => {
          const isActive = phase.id === activePhase;
          const isDone =
            recoveryLog.length > 0 &&
            (phase.id === "monitor" || phase.id === "diagnostician");

          return (
            <React.Fragment key={phase.id}>
              <div
                style={{
                  flex: 1,
                  background: isActive
                    ? "rgba(99,102,241,0.2)"
                    : isDone
                    ? "rgba(34,197,94,0.1)"
                    : "rgba(30,41,59,0.5)",
                  border: `1px solid ${
                    isActive
                      ? "rgba(99,102,241,0.6)"
                      : isDone
                      ? "rgba(34,197,94,0.3)"
                      : "rgba(100,116,139,0.2)"
                  }`,
                  borderRadius: 8,
                  padding: "10px 12px",
                  textAlign: "center",
                  transition: "all 0.3s ease",
                }}
              >
                <div style={{ fontSize: 18, marginBottom: 4 }}>
                  {isDone ? "✓" : phase.icon}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: isActive ? "#a5b4fc" : isDone ? "#4ade80" : "#64748b",
                  }}
                >
                  {phase.label}
                </div>
                <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>
                  {phase.desc}
                </div>
              </div>
              {i < phases.length - 1 && (
                <div
                  style={{
                    alignSelf: "center",
                    color: "#334155",
                    fontSize: 16,
                    flexShrink: 0,
                  }}
                >
                  →
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Diagnosis */}
      {diagnosis && (
        <div
          style={{
            background: "rgba(234,179,8,0.1)",
            border: "1px solid rgba(234,179,8,0.3)",
            borderRadius: 8,
            padding: "10px 14px",
            fontSize: 12,
            color: "#fde68a",
            lineHeight: 1.5,
          }}
        >
          <div
            style={{
              fontSize: 11,
              color: "#92400e",
              fontWeight: 600,
              marginBottom: 4,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            Diagnosis
          </div>
          {diagnosis}
        </div>
      )}

      {/* Recovery log */}
      {recoveryLog.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 11,
              color: "#64748b",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            Recovery Log
          </div>
          <div
            style={{
              background: "rgba(0,0,0,0.3)",
              borderRadius: 6,
              padding: "10px 12px",
              fontFamily: "monospace",
              fontSize: 11,
              color: "#4ade80",
              display: "flex",
              flexDirection: "column",
              gap: 4,
              maxHeight: 140,
              overflowY: "auto",
            }}
          >
            {recoveryLog.map((line, i) => (
              <div key={i}>
                <span style={{ color: "#334155" }}>$ </span>
                {line}
              </div>
            ))}
          </div>
        </div>
      )}

      {!anomalyDetected && recoveryLog.length === 0 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 12,
            color: "#64748b",
          }}
        >
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#22c55e",
              animation: "pulse 2s infinite",
            }}
          />
          All agents nominal — monitoring active
        </div>
      )}
    </div>
  );
};
