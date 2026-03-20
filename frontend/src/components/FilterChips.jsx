export default function FilterChips({ options, active, onChange }) {
  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
      {options.map((option) => {
        const isActive = option === active;
        return (
          <button
            key={option}
            onClick={() => onChange(option)}
            style={{
              padding: "6px 14px",
              borderRadius: "20px",
              border: `1px solid ${isActive ? "rgba(200,241,53,0.4)" : "#1e2130"}`,
              background: isActive ? "rgba(200,241,53,0.1)" : "transparent",
              color: isActive ? "#c8f135" : "#4a5568",
              fontSize: "11px",
              fontWeight: isActive ? "600" : "400",
              cursor: "pointer",
              fontFamily: "'DM Mono', monospace",
              letterSpacing: "0.05em",
              transition: "all 0.15s ease",
              textTransform: "uppercase",
            }}
            onMouseEnter={(e) => {
              if (!isActive) {
                e.currentTarget.style.borderColor = "#4a5568";
                e.currentTarget.style.color = "#8892a4";
              }
            }}
            onMouseLeave={(e) => {
              if (!isActive) {
                e.currentTarget.style.borderColor = "#1e2130";
                e.currentTarget.style.color = "#4a5568";
              }
            }}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}