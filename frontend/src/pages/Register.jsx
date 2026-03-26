import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";

// ── Style tokens (same as rest of app) ───────────────────────────────────────
const T = {
  bg:        "#0f1117",
  card:      "#161a24",
  border:    "#1e2130",
  accent:    "#c8f135",
  accentBg:  "rgba(200,241,53,0.06)",
  accentBd:  "rgba(200,241,53,0.2)",
  textPri:   "#f0f4f8",
  textMuted: "#4a5568",
  danger:    "#ef4444",
  dangerBg:  "rgba(239,68,68,0.06)",
  dangerBd:  "rgba(239,68,68,0.25)",
};

// ── Reuse the auth-styles injected by Login (same STYLE_ID) ──────────────────
const STYLE_ID = "auth-styles";
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = `
    .auth-input:focus { border-color: rgba(200,241,53,0.4) !important; outline: none; }
    .auth-submit:hover:not(:disabled) { background: #d4f53c !important; }
    .auth-link:hover { color: #c8f135 !important; }
  `;
  document.head.appendChild(s);
}

export default function Register() {
  const { register, login } = useAuth();
  const navigate            = useNavigate();

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [confirm,  setConfirm]  = useState("");
  const [error,    setError]    = useState(null);
  const [loading,  setLoading]  = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (password !== confirm)  { setError("Passwords do not match."); return; }

    setLoading(true);
    try {
      await register(email.trim(), password);
      await login(email.trim(), password);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.detail || "Registration failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: "100%", boxSizing: "border-box",
    background: T.bg,
    border: `1px solid ${T.border}`,
    borderRadius: "8px",
    padding: "10px 14px",
    color: T.textPri,
    fontSize: "13px",
    fontWeight: "600",
    transition: "border-color 0.15s",
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: T.bg,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "40px 16px",
      fontFamily: "system-ui, -apple-system, sans-serif",
    }}>
      <div style={{
        width: "100%",
        maxWidth: "400px",
        background: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: "16px",
        overflow: "hidden",
      }}>

        {/* Header */}
        <div style={{ padding: "28px 32px 24px", borderBottom: `1px solid ${T.border}` }}>
          <p style={{ fontSize: "11px", color: T.textMuted, letterSpacing: "0.1em", marginBottom: "6px" }}>
            GYMBRO
          </p>
          <h1 style={{ fontSize: "22px", fontWeight: "700", color: T.textPri, letterSpacing: "-0.02em", margin: 0 }}>
            Create an account
          </h1>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: "28px 32px" }}>

          {error && (
            <div style={{
              marginBottom: "20px", padding: "10px 14px", borderRadius: "8px",
              background: T.dangerBg, border: `1px solid ${T.dangerBd}`,
              color: T.danger, fontSize: "12px",
            }}>
              {error}
            </div>
          )}

          <div style={{ marginBottom: "16px" }}>
            <p style={{ fontSize: "11px", fontWeight: "700", color: T.textMuted,
                        letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "8px" }}>
              Email
            </p>
            <input
              type="email"
              required
              autoFocus
              disabled={loading}
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="auth-input"
              style={{ ...inputStyle, opacity: loading ? 0.6 : 1 }}
            />
          </div>

          <div style={{ marginBottom: "16px" }}>
            <p style={{ fontSize: "11px", fontWeight: "700", color: T.textMuted,
                        letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "8px" }}>
              Password
            </p>
            <input
              type="password"
              required
              disabled={loading}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Min 8 characters"
              className="auth-input"
              style={{ ...inputStyle, opacity: loading ? 0.6 : 1 }}
            />
          </div>

          <div style={{ marginBottom: "24px" }}>
            <p style={{ fontSize: "11px", fontWeight: "700", color: T.textMuted,
                        letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "8px" }}>
              Confirm Password
            </p>
            <input
              type="password"
              required
              disabled={loading}
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              placeholder="••••••••"
              className="auth-input"
              style={{ ...inputStyle, opacity: loading ? 0.6 : 1 }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="auth-submit"
            style={{
              width: "100%",
              padding: "10px",
              borderRadius: "8px",
              border: "none",
              background: loading ? T.border : T.accent,
              color: loading ? T.textMuted : "#0f1117",
              fontSize: "12px",
              fontWeight: "700",
              letterSpacing: "0.04em",
              cursor: loading ? "not-allowed" : "pointer",
              transition: "background 0.15s",
            }}
          >
            {loading ? "Creating account…" : "CREATE ACCOUNT →"}
          </button>

          <p style={{ fontSize: "12px", color: T.textMuted, marginTop: "20px", textAlign: "center" }}>
            Already have an account?{" "}
            <Link to="/login" className="auth-link"
              style={{ color: T.accent, textDecoration: "none", fontWeight: "600", transition: "color 0.15s" }}>
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}