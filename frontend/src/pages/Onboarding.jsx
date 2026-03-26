import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { submitOnboarding } from "../api/profile";

const TOTAL_STEPS = 4;

const ACTIVITY_OPTIONS = [
  { value: "sedentary",         label: "Sedentary",         desc: "Little or no exercise" },
  { value: "lightly_active",    label: "Lightly Active",    desc: "1–3 days / week" },
  { value: "moderately_active", label: "Moderately Active", desc: "3–5 days / week" },
  { value: "very_active",       label: "Very Active",       desc: "6–7 days / week" },
  { value: "extra_active",      label: "Extra Active",      desc: "Athlete / physical job" },
];

const EXPERIENCE_OPTIONS = [
  { value: "beginner",     label: "Beginner",     desc: "< 1 year" },
  { value: "intermediate", label: "Intermediate", desc: "1–3 years" },
  { value: "advanced",     label: "Advanced",     desc: "3+ years" },
];

const GOAL_CHIPS = [
  "Build muscle and strength",
  "Lose weight and burn fat",
  "Improve endurance and cardio",
  "Increase flexibility and mobility",
  "Maintain current fitness",
  "Train for a specific sport",
];

// ── Shared style tokens ──────────────────────────────────────────────────────
const T = {
  bg:        "#0f1117",
  card:      "#161a24",
  border:    "#1e2130",
  accent:    "#c8f135",
  accentBg:  "rgba(200,241,53,0.06)",
  accentBd:  "rgba(200,241,53,0.2)",
  textPri:   "#f0f4f8",
  textMuted: "#4a5568",
  textDim:   "#2d3748",
  danger:    "#ef4444",
  dangerBg:  "rgba(239,68,68,0.06)",
  dangerBd:  "rgba(239,68,68,0.25)",
};

// ── Inject one-time hover styles ─────────────────────────────────────────────
const STYLE_ID = "ob-styles";
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = `
    .ob-input:focus  { border-color: rgba(200,241,53,0.4) !important; outline: none; }
    .ob-ta:focus     { border-color: rgba(200,241,53,0.4) !important; outline: none; }
    .ob-chip:hover   { border-color: rgba(200,241,53,0.35) !important; color: ${T.textPri} !important; }
    .ob-pill:hover   { border-color: rgba(200,241,53,0.35) !important; color: ${T.textPri} !important; }
    .ob-opt:hover    { border-color: rgba(200,241,53,0.35) !important; background: rgba(200,241,53,0.04) !important; }
    .ob-btn-pri:hover:not(:disabled) { background: #d4f53c !important; }
    .ob-btn-sec:hover { border-color: rgba(200,241,53,0.25) !important; color: ${T.textPri} !important; }
    @keyframes ob-in { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
    @keyframes ob-pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  `;
  document.head.appendChild(s);
}

// ── Sub-components at MODULE level (NOT inside Onboarding) ───────────────────
// Defining these inside the component causes React to remount inputs on every
// keystroke (focus lost), because the component reference changes each render.
const Label = ({ children }) => (
  <p style={{ fontSize: "11px", fontWeight: "700", color: T.textMuted,
              letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "8px" }}>
    {children}
  </p>
);

const Input = ({ id, type = "text", placeholder, value, onChange, min, max }) => (
  <input
    id={id}
    type={type}
    min={min} max={max}
    placeholder={placeholder}
    value={value}
    onChange={e => onChange(e.target.value)}
    className="ob-input"
    style={{
      width: "100%", boxSizing: "border-box",
      background: "#0f1117",
      border: `1px solid ${T.border}`,
      borderRadius: "8px",
      padding: "9px 12px",
      color: T.textPri,
      fontSize: "13px",
      fontWeight: "600",
      transition: "border-color 0.15s",
    }}
  />
);

const Textarea = ({ id, placeholder, value, onChange, rows = 3 }) => (
  <textarea
    id={id}
    rows={rows}
    placeholder={placeholder}
    value={value}
    onChange={e => onChange(e.target.value)}
    className="ob-ta"
    style={{
      width: "100%", boxSizing: "border-box",
      background: "#0f1117",
      border: `1px solid ${T.border}`,
      borderRadius: "8px",
      padding: "9px 12px",
      color: T.textPri,
      fontSize: "13px",
      resize: "vertical",
      fontFamily: "inherit",
      transition: "border-color 0.15s",
    }}
  />
);

const Field = ({ children, style }) => (
  <div style={{ marginBottom: "20px", ...style }}>{children}</div>
);

export default function Onboarding() {
  const navigate = useNavigate();
  const { setOnboardingComplete } = useAuth();

  const [step, setStep]           = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]         = useState("");

  const [form, setForm] = useState({
    full_name: "", age: "", gender: "",
    height_cm: "", weight_kg: "",
    fitness_goal: "", activity_level: "", experience_level: "",
    injuries: "", preferences: "",
  });

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }));

  const canProceed = () => {
    if (step === 1) return form.full_name.trim() && form.age && form.gender;
    if (step === 2) return form.height_cm && form.weight_kg;
    if (step === 3) return form.fitness_goal.trim() && form.activity_level && form.experience_level;
    return true;
  };

  const next = () => {
    if (!canProceed()) { setError("Please fill in all required fields."); return; }
    setError("");
    setStep(s => s + 1);
  };

  const back = () => { setError(""); setStep(s => s - 1); };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError("");
    try {
      await submitOnboarding({
        full_name:        form.full_name.trim(),
        age:              parseInt(form.age),
        gender:           form.gender,
        height_cm:        parseFloat(form.height_cm),
        weight_kg:        parseFloat(form.weight_kg),
        fitness_goal:     form.fitness_goal.trim(),
        activity_level:   form.activity_level,
        experience_level: form.experience_level,
        injuries:         form.injuries.trim()    || null,
        preferences:      form.preferences.trim() || null,
      });
      setOnboardingComplete(true);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────
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
        maxWidth: "560px",
        background: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: "16px",
        overflow: "hidden",
      }}>

        {/* ── Header ─────────────────────────────────────────── */}
        <div style={{
          padding: "28px 32px 24px",
          borderBottom: `1px solid ${T.border}`,
        }}>
          <p style={{ fontSize: "11px", color: T.textMuted, letterSpacing: "0.1em", marginBottom: "6px" }}>
            SETUP
          </p>
          <h1 style={{ fontSize: "22px", fontWeight: "700", color: T.textPri,
                       letterSpacing: "-0.02em", marginBottom: "4px" }}>
            Set up your profile
          </h1>
          <p style={{ fontSize: "12px", color: T.textMuted }}>
            Help your AI coach personalise advice from day one
          </p>

          {/* Progress bar */}
          <div style={{ display: "flex", gap: "6px", marginTop: "20px" }}>
            {Array.from({ length: TOTAL_STEPS }, (_, i) => (
              <div key={i} style={{
                flex: 1,
                height: "3px",
                borderRadius: "99px",
                background: i + 1 <= step
                  ? T.accent
                  : T.border,
                transition: "background 0.3s",
              }} />
            ))}
          </div>
          <p style={{ fontSize: "11px", color: T.textMuted, marginTop: "6px", textAlign: "right" }}>
            Step {step} of {TOTAL_STEPS}
          </p>
        </div>

        {/* ── Body ───────────────────────────────────────────── */}
        <div style={{ padding: "28px 32px", animation: "ob-in 0.2s ease" }} key={step}>

          {/* STEP 1 — About You */}
          {step === 1 && (<>
            <p style={{ fontSize: "13px", fontWeight: "600", color: T.textPri, marginBottom: "20px" }}>
              About You
            </p>

            <Field>
              <Label>Full Name *</Label>
              <Input id="ob-name" placeholder="e.g. Alex Johnson"
                value={form.full_name} onChange={v => set("full_name", v)} />
            </Field>

            <Field>
              <Label>Age *</Label>
              <Input id="ob-age" type="number" min="10" max="120" placeholder="e.g. 25"
                value={form.age} onChange={v => set("age", v)} />
            </Field>

            <Field style={{ marginBottom: 0 }}>
              <Label>Gender *</Label>
              <div style={{ display: "flex", gap: "8px" }}>
                {["male", "female", "other"].map(g => (
                  <button key={g} id={`ob-gender-${g}`} className="ob-pill"
                    onClick={() => set("gender", g)}
                    style={{
                      flex: 1, padding: "8px 12px",
                      borderRadius: "8px",
                      border: `1px solid ${form.gender === g ? T.accent : T.border}`,
                      background: form.gender === g ? T.accentBg : "transparent",
                      color: form.gender === g ? T.accent : T.textMuted,
                      fontSize: "12px", fontWeight: "600", cursor: "pointer",
                      transition: "all 0.15s",
                    }}>
                    {g.charAt(0).toUpperCase() + g.slice(1)}
                  </button>
                ))}
              </div>
            </Field>
          </>)}

          {/* STEP 2 — Body */}
          {step === 2 && (<>
            <p style={{ fontSize: "13px", fontWeight: "600", color: T.textPri, marginBottom: "20px" }}>
              Your Body
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Field>
                <Label>Height (cm) *</Label>
                <Input id="ob-height" type="number" min="50" max="300" placeholder="e.g. 175"
                  value={form.height_cm} onChange={v => set("height_cm", v)} />
              </Field>
              <Field>
                <Label>Weight (kg) *</Label>
                <Input id="ob-weight" type="number" min="20" max="500" placeholder="e.g. 72"
                  value={form.weight_kg} onChange={v => set("weight_kg", v)} />
              </Field>
            </div>

            {form.height_cm && form.weight_kg && (() => {
              const bmi = (parseFloat(form.weight_kg) / Math.pow(parseFloat(form.height_cm) / 100, 2)).toFixed(1);
              const cat = bmi < 18.5 ? "Underweight" : bmi < 25 ? "Healthy" : bmi < 30 ? "Overweight" : "Obese";
              return (
                <div style={{
                  padding: "10px 14px", borderRadius: "8px",
                  background: T.accentBg, border: `1px solid ${T.accentBd}`,
                  fontSize: "12px", color: T.textMuted,
                }}>
                  BMI <span style={{ color: T.accent, fontWeight: "700" }}>{bmi}</span> — {cat}
                </div>
              );
            })()}
          </>)}

          {/* STEP 3 — Goals */}
          {step === 3 && (<>
            <p style={{ fontSize: "13px", fontWeight: "600", color: T.textPri, marginBottom: "20px" }}>
              Your Goals
            </p>

            <Field>
              <Label>Primary Fitness Goal *</Label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "8px" }}>
                {GOAL_CHIPS.map(g => (
                  <button key={g} className="ob-chip"
                    onClick={() => set("fitness_goal", g)}
                    style={{
                      padding: "5px 10px", borderRadius: "6px",
                      border: `1px solid ${form.fitness_goal === g ? T.accent : T.border}`,
                      background: form.fitness_goal === g ? T.accentBg : "transparent",
                      color: form.fitness_goal === g ? T.accent : T.textMuted,
                      fontSize: "11px", fontWeight: "600", cursor: "pointer",
                      transition: "all 0.15s",
                    }}>
                    {g}
                  </button>
                ))}
              </div>
              <Input id="ob-goal" placeholder="Or type your own goal…"
                value={form.fitness_goal} onChange={v => set("fitness_goal", v)} />
            </Field>

            <Field>
              <Label>Activity Level *</Label>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {ACTIVITY_OPTIONS.map(o => (
                  <button key={o.value} id={`ob-activity-${o.value}`} className="ob-opt"
                    onClick={() => set("activity_level", o.value)}
                    style={{
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      padding: "10px 14px", borderRadius: "8px",
                      border: `1px solid ${form.activity_level === o.value ? T.accent : T.border}`,
                      background: form.activity_level === o.value ? T.accentBg : "transparent",
                      cursor: "pointer", transition: "all 0.15s", textAlign: "left",
                    }}>
                    <span style={{ fontSize: "12px", fontWeight: "600",
                                   color: form.activity_level === o.value ? T.accent : T.textPri }}>
                      {o.label}
                    </span>
                    <span style={{ fontSize: "11px", color: T.textMuted }}>{o.desc}</span>
                  </button>
                ))}
              </div>
            </Field>

            <Field style={{ marginBottom: 0 }}>
              <Label>Experience Level *</Label>
              <div style={{ display: "flex", gap: "8px" }}>
                {EXPERIENCE_OPTIONS.map(o => (
                  <button key={o.value} id={`ob-exp-${o.value}`} className="ob-pill"
                    onClick={() => set("experience_level", o.value)}
                    style={{
                      flex: 1, padding: "10px 8px", borderRadius: "8px", cursor: "pointer",
                      border: `1px solid ${form.experience_level === o.value ? T.accent : T.border}`,
                      background: form.experience_level === o.value ? T.accentBg : "transparent",
                      transition: "all 0.15s", textAlign: "center",
                    }}>
                    <p style={{ fontSize: "12px", fontWeight: "600", margin: 0,
                                color: form.experience_level === o.value ? T.accent : T.textPri }}>
                      {o.label}
                    </p>
                    <p style={{ fontSize: "10px", color: T.textMuted, margin: "2px 0 0" }}>
                      {o.desc}
                    </p>
                  </button>
                ))}
              </div>
            </Field>
          </>)}

          {/* STEP 4 — Extras */}
          {step === 4 && (<>
            <p style={{ fontSize: "13px", fontWeight: "600", color: T.textPri, marginBottom: "4px" }}>
              A Bit More <span style={{ color: T.textMuted, fontWeight: "400" }}>(Optional)</span>
            </p>
            <p style={{ fontSize: "11px", color: T.textMuted, marginBottom: "20px" }}>
              Helps your coach avoid exercises that could hurt you.
            </p>

            <Field>
              <Label>Injuries or Physical Limitations</Label>
              <Textarea id="ob-injuries"
                placeholder="e.g. bad left knee, lower back pain, shoulder impingement…"
                value={form.injuries} onChange={v => set("injuries", v)} />
            </Field>

            <Field style={{ marginBottom: 0 }}>
              <Label>Workout Preferences</Label>
              <Textarea id="ob-preferences"
                placeholder="e.g. no equipment, prefer mornings, love HIIT…"
                value={form.preferences} onChange={v => set("preferences", v)} />
            </Field>
          </>)}

          {/* Error */}
          {error && (
            <div style={{
              marginTop: "16px", padding: "10px 14px", borderRadius: "8px",
              background: T.dangerBg, border: `1px solid ${T.dangerBd}`,
              color: T.danger, fontSize: "12px",
            }}>
              {error}
            </div>
          )}
        </div>

        {/* ── Footer ─────────────────────────────────────────── */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "20px 32px",
          borderTop: `1px solid ${T.border}`,
        }}>
          {step > 1 ? (
            <button className="ob-btn-sec"
              onClick={back}
              disabled={submitting}
              style={{
                padding: "9px 18px", borderRadius: "8px",
                border: `1px solid ${T.border}`,
                background: "transparent",
                color: T.textMuted,
                fontSize: "12px", fontWeight: "600", cursor: "pointer",
                transition: "all 0.15s",
              }}>
              ← Back
            </button>
          ) : <div />}

          {step < TOTAL_STEPS ? (
            <button id="ob-next" className="ob-btn-pri"
              onClick={next}
              disabled={!canProceed()}
              style={{
                padding: "9px 22px", borderRadius: "8px",
                border: "none",
                background: canProceed() ? T.accent : T.border,
                color: canProceed() ? "#0f1117" : T.textMuted,
                fontSize: "12px", fontWeight: "700",
                letterSpacing: "0.04em",
                cursor: canProceed() ? "pointer" : "not-allowed",
                transition: "all 0.15s",
              }}>
              NEXT →
            </button>
          ) : (
            <button id="ob-submit" className="ob-btn-pri"
              onClick={handleSubmit}
              disabled={submitting}
              style={{
                padding: "9px 22px", borderRadius: "8px",
                border: "none",
                background: submitting ? T.border : T.accent,
                color: submitting ? T.textMuted : "#0f1117",
                fontSize: "12px", fontWeight: "700",
                letterSpacing: "0.04em",
                cursor: submitting ? "not-allowed" : "pointer",
                transition: "all 0.15s",
              }}>
              {submitting ? "Setting up…" : "START TRAINING →"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
