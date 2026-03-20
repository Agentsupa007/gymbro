import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import { Link } from "react-router-dom";

const StatCard = ({ label, value, unit, sub, accent = false }) => (

  <div
    style={{
      background: accent ? "rgba(200,241,53,0.06)" : "#161a24",
      border: `1px solid ${accent ? "rgba(200,241,53,0.2)" : "#1e2130"}`,
      borderRadius: "12px",
      padding: "20px 24px",
      display: "flex",
      flexDirection: "column",
      gap: "6px",
    }}
  >
    <p style={{ fontSize: "11px", color: "#4a5568", letterSpacing: "0.1em" }}>
      {label}
    </p>
    <div style={{ display: "flex", alignItems: "baseline", gap: "4px" }}>
      <span
        style={{
          fontSize: "28px",
          fontWeight: "700",
          color: accent ? "#c8f135" : "#f0f4f8",
          lineHeight: 1,
        }}
      >
        {value ?? "—"}
      </span>
      {unit && (
        <span style={{ fontSize: "13px", color: "#4a5568" }}>{unit}</span>
      )}
    </div>
    {sub && (
      <p style={{ fontSize: "11px", color: "#4a5568" }}>{sub}</p>
    )}
  </div>
);

const SectionHeader = ({ title, action }) => (

  <div
    style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: "16px",
    }}
  >
    <h2
      style={{
        fontSize: "12px",
        fontWeight: "600",
        color: "#4a5568",
        letterSpacing: "0.1em",
      }}
    >
      {title}
    </h2>
    {action && (
      <button
        style={{
          fontSize: "11px",
          color: "#c8f135",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontFamily: "'DM Mono', monospace",
        }}
      >
        {action}
      </button>
    )}
  </div>
);

const EmptyState = ({ message }) => (

  <div
    style={{
      padding: "32px",
      borderRadius: "12px",
      border: "1px dashed #1e2130",
      textAlign: "center",
      color: "#4a5568",
      fontSize: "13px",
    }}
  >
    {message}
  </div>
);

export default function Dashboard() {
const { user } = useAuth();

const greeting = () => {
const hour = new Date().getHours();
if (hour < 12) return "Good morning";
if (hour < 17) return "Good afternoon";
return "Good evening";
};

const username = user?.email
? user.email.split("@")[0]
: "Athlete";

return ( <Layout>
<div style={{ padding: "36px 40px", maxWidth: "1100px", width: "100%" }}>

```
    {/* Header */}
    <div style={{ marginBottom: "36px" }}>
      <p style={{ fontSize: "12px", color: "#4a5568", marginBottom: "6px" }}>
        {new Date().toLocaleDateString("en-US", {
          weekday: "long",
          month: "long",
          day: "numeric",
        })}
      </p>
      <h1
        style={{
          fontSize: "26px",
          fontWeight: "700",
          color: "#f0f4f8",
          letterSpacing: "-0.02em",
        }}
      >
        {greeting()},{" "}
        <span style={{ color: "#c8f135" }}>
          {username}
        </span>
      </h1>
    </div>

    {/* Stats row */}
    <div style={{ marginBottom: "36px" }}>
      <SectionHeader title="TODAY'S SNAPSHOT" />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "12px",
        }}
      >
        <StatCard label="STEPS" value={null} sub="Goal: 10,000" accent />
        <StatCard label="CALORIES BURNED" value={null} unit="kcal" />
        <StatCard label="SLEEP" value={null} unit="hrs" />
        <StatCard label="WATER" value={null} unit="ml" />
      </div>
    </div>

    {/* Middle row */}
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
        gap: "24px",
        marginBottom: "36px",
      }}
    >
      {/* Progress */}
      <div>
        <SectionHeader title="PROGRESS" />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "12px",
          }}
        >
          <StatCard label="CURRENT STREAK" value={null} unit="days" />
          <StatCard label="WORKOUTS THIS MONTH" value={null} />
          <StatCard label="WEIGHT" value={null} unit="kg" />
          <StatCard label="WEIGHT CHANGE" value={null} unit="kg" />
        </div>
      </div>

      {/* Recent workouts */}
      <div>
        <SectionHeader title="RECENT WORKOUTS" action="View all →" />
        <EmptyState message="No workouts logged yet. Start your first session." />
      </div>
    </div>

    {/* Bottom row */}
    <div>
      <SectionHeader title="QUICK ACTIONS" />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "12px",
        }}
      >
        {[
          { label: "Log Today's Metrics", sub: "Steps, sleep, calories", path: "/metrics" },
          { label: "Start a Workout", sub: "Begin a new session", path: "/workouts" },
          { label: "Ask AI Coach", sub: "Get personalized advice", path: "/chat" },
        ].map((action) => (
          <Link
            key={action.path}
            to={action.path}
            style={{
              display: "block",
              padding: "18px 20px",
              borderRadius: "12px",
              border: "1px solid #1e2130",
              background: "#161a24",
              textDecoration: "none",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(200,241,53,0.3)";
              e.currentTarget.style.background = "rgba(200,241,53,0.04)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#1e2130";
              e.currentTarget.style.background = "#161a24";
            }}
          >
            <p style={{ fontSize: "13px", fontWeight: "600", color: "#f0f4f8", marginBottom: "4px" }}>
              {action.label}
            </p>
            <p style={{ fontSize: "11px", color: "#4a5568" }}>{action.sub}</p>
          </Link>
        ))}
      </div>
    </div>

  </div>
</Layout>
);
}
