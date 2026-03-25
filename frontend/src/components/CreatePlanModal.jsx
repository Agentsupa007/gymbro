// src/components/CreatePlanModal.jsx
import { useState, useEffect, useRef, useCallback } from "react";
import { getExerciseCatalog, createWorkoutPlan } from "../api/client";

// Inject styles once
const STYLE_ID = "create-plan-modal-styles";
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = `
    .cpm-input:focus { border-color: rgba(200,241,53,0.4) !important; outline: none; }
    .cpm-catalog-row:hover:not(:disabled) { background: rgba(200,241,53,0.05) !important; border-color: rgba(200,241,53,0.2) !important; }
    .cpm-remove-btn:hover { color: #ef4444 !important; }
    .cpm-submit-btn:hover:not(:disabled) { background: #d4f53c !important; }
    .cpm-close-btn:hover { color: #f0f4f8 !important; }
    @keyframes cpm-slide-up {
      from { transform: translateY(100%); opacity: 0; }
      to   { transform: translateY(0);   opacity: 1; }
    }
  `;
  document.head.appendChild(s);
}

const toNum = (v) => {
  const n = parseFloat(v);
  return isNaN(n) ? "" : n;
};

export default function CreatePlanModal({ onClose, onCreated }) {
  // ── Plan meta ────────────────────────────────────────────────────────────────
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  // ── Selected exercises ───────────────────────────────────────────────────────
  // Each item: { catalogId, exercise_name, sets, reps, weight_kg, notes }
  const [selected, setSelected] = useState([]);

  // ── Catalog ──────────────────────────────────────────────────────────────────
  const [catalog, setCatalog] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState(null);
  const [search, setSearch] = useState("");

  // ── Submit state ─────────────────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // ── Tab: "search" | "configure" ──────────────────────────────────────────────
  const [tab, setTab] = useState("search");

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Load catalog on mount
  useEffect(() => {
    getExerciseCatalog()
      .then((res) => {
        if (!mountedRef.current) return;
        setCatalog(res.data ?? []);
      })
      .catch((err) => {
        if (!mountedRef.current) return;
        setCatalogError(err?.message ?? "Failed to load catalog.");
      })
      .finally(() => {
        if (mountedRef.current) setCatalogLoading(false);
      });
  }, []);

  // ── Helpers ──────────────────────────────────────────────────────────────────
  const selectedNames = new Set(selected.map((s) => s.exercise_name.toLowerCase()));

  const addExercise = useCallback((item) => {
    if (selectedNames.has(item.name.toLowerCase())) return;
    setSelected((prev) => [
      ...prev,
      {
        catalogId: item.id,
        exercise_name: item.name,
        sets: "",
        reps: "",
        weight_kg: "",
      },
    ]);
  }, [selectedNames]);

  const removeExercise = (name) => {
    setSelected((prev) => prev.filter((e) => e.exercise_name !== name));
  };

  const updateField = (exercise_name, field, value) => {
    setSelected((prev) =>
      prev.map((e) =>
        e.exercise_name === exercise_name ? { ...e, [field]: value } : e
      )
    );
  };

  // ── Submit ───────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!name.trim()) { setSubmitError("Plan name is required."); return; }
    if (selected.length === 0) { setSubmitError("Add at least one exercise."); return; }

    setSubmitting(true);
    setSubmitError(null);

    const payload = {
      name: name.trim(),
      description: description.trim() || null,
      exercises: selected.map((ex, idx) => ({
        exercise_name: ex.exercise_name,
        sets: toNum(ex.sets) || null,
        reps: toNum(ex.reps) || null,
        weight_kg: toNum(ex.weight_kg) || null,
        order_index: idx + 1,
      })),
    };

    try {
      const res = await createWorkoutPlan(payload);
      if (!mountedRef.current) return;
      onCreated?.(res.data);
      onClose?.();
    } catch (err) {
      if (!mountedRef.current) return;
      setSubmitError(err?.message ?? "Failed to create plan.");
    } finally {
      if (mountedRef.current) setSubmitting(false);
    }
  };

  const filteredCatalog = catalog.filter(
    (item) =>
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.muscle_group?.toLowerCase().includes(search.toLowerCase()) ||
      item.category?.toLowerCase().includes(search.toLowerCase())
  );

  // ── Shared input style ───────────────────────────────────────────────────────
  const inputStyle = {
    width: "100%",
    padding: "9px 12px",
    borderRadius: "8px",
    border: "1px solid #1e2130",
    background: "#0f1117",
    color: "#f0f4f8",
    fontSize: "13px",
    boxSizing: "border-box",
    transition: "border-color 0.15s ease",
  };

  const smallInputStyle = {
    padding: "7px 10px",
    borderRadius: "6px",
    border: "1px solid #1e2130",
    background: "#0f1117",
    color: "#f0f4f8",
    fontSize: "12px",
    width: "80px",
    boxSizing: "border-box",
    textAlign: "center",
    transition: "border-color 0.15s ease",
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.65)",
          zIndex: 50,
        }}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-label="Create Workout Plan"
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          maxHeight: "92vh",
          background: "#161a24",
          borderTop: "1px solid #1e2130",
          borderRadius: "20px 20px 0 0",
          zIndex: 60,
          display: "flex",
          flexDirection: "column",
          animation: "cpm-slide-up 0.25s ease",
        }}
      >
        {/* ── Header ── */}
        <div
          style={{
            padding: "20px 24px 16px",
            borderBottom: "1px solid #1e2130",
            flexShrink: 0,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <p style={{ fontSize: "11px", color: "#4a5568", letterSpacing: "0.1em", marginBottom: "4px" }}>
              TRAINING
            </p>
            <h2 style={{ fontSize: "18px", fontWeight: "700", color: "#f0f4f8", letterSpacing: "-0.02em" }}>
              New Workout Plan
            </h2>
          </div>
          <button
            className="cpm-close-btn"
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#4a5568",
              fontSize: "22px",
              cursor: "pointer",
              lineHeight: 1,
              transition: "color 0.15s ease",
            }}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div style={{ overflowY: "auto", flex: 1, padding: "20px 24px" }}>

          {/* Plan name */}
          <div style={{ marginBottom: "14px" }}>
            <label style={{ fontSize: "11px", color: "#4a5568", letterSpacing: "0.06em", display: "block", marginBottom: "6px" }}>
              PLAN NAME *
            </label>
            <input
              className="cpm-input"
              type="text"
              placeholder="e.g. Push Day A"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={255}
              style={inputStyle}
              aria-label="Plan name"
            />
          </div>

          {/* Description */}
          <div style={{ marginBottom: "20px" }}>
            <label style={{ fontSize: "11px", color: "#4a5568", letterSpacing: "0.06em", display: "block", marginBottom: "6px" }}>
              DESCRIPTION
            </label>
            <textarea
              className="cpm-input"
              placeholder="Optional description…"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              style={{ ...inputStyle, resize: "vertical", lineHeight: "1.5" }}
              aria-label="Plan description"
            />
          </div>

          {/* ── Tabs ── */}
          <div
            style={{
              display: "flex",
              gap: "4px",
              marginBottom: "16px",
              background: "#0f1117",
              borderRadius: "8px",
              padding: "4px",
            }}
          >
            {["search", "configure"].map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  flex: 1,
                  padding: "8px",
                  borderRadius: "6px",
                  border: "none",
                  background: tab === t ? "#1e2130" : "transparent",
                  color: tab === t ? "#f0f4f8" : "#4a5568",
                  fontSize: "12px",
                  fontWeight: "600",
                  cursor: "pointer",
                  letterSpacing: "0.04em",
                  transition: "all 0.15s ease",
                }}
              >
                {t === "search"
                  ? `Add Exercises${selected.length > 0 ? ` (${selected.length})` : ""}`
                  : `Configure Sets${selected.length > 0 ? ` (${selected.length})` : ""}`}
              </button>
            ))}
          </div>

          {/* ── Tab: Search catalog ── */}
          {tab === "search" && (
            <div>
              <input
                className="cpm-input"
                type="text"
                placeholder="Search exercises…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ ...inputStyle, marginBottom: "12px" }}
                autoFocus
                aria-label="Search exercise catalog"
              />

              {catalogLoading && (
                <p style={{ fontSize: "13px", color: "#4a5568", textAlign: "center", padding: "24px 0" }}>
                  Loading catalog…
                </p>
              )}

              {catalogError && (
                <p style={{ fontSize: "13px", color: "#ef4444", padding: "8px 0" }}>
                  {catalogError}
                </p>
              )}

              {!catalogLoading && filteredCatalog.length === 0 && (
                <p style={{ fontSize: "13px", color: "#4a5568", textAlign: "center", padding: "20px 0" }}>
                  No exercises match "{search}".
                </p>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                {filteredCatalog.map((item) => {
                  const added = selectedNames.has(item.name.toLowerCase());
                  return (
                    <button
                      key={item.id}
                      className="cpm-catalog-row"
                      onClick={() => addExercise(item)}
                      disabled={added}
                      style={{
                        width: "100%",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "10px 12px",
                        borderRadius: "8px",
                        border: added ? "1px solid rgba(200,241,53,0.2)" : "1px solid transparent",
                        background: added ? "rgba(200,241,53,0.04)" : "transparent",
                        cursor: added ? "default" : "pointer",
                        opacity: added ? 0.7 : 1,
                        textAlign: "left",
                        transition: "all 0.15s ease",
                      }}
                      aria-label={`Add ${item.name}`}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                        <span style={{ fontSize: "13px", color: "#f0f4f8", fontWeight: "600" }}>
                          {item.name}
                        </span>
                        <span style={{ fontSize: "11px", color: "#4a5568" }}>
                          {[item.category, item.muscle_group].filter(Boolean).join(" · ")}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: "700",
                          color: added ? "#c8f135" : "#4a5568",
                          flexShrink: 0,
                          marginLeft: "12px",
                        }}
                      >
                        {added ? "✓" : "+"}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Tab: Configure sets/reps/weight ── */}
          {tab === "configure" && (
            <div>
              {selected.length === 0 && (
                <div
                  style={{
                    padding: "40px",
                    borderRadius: "12px",
                    border: "1px dashed #1e2130",
                    textAlign: "center",
                  }}
                >
                  <p style={{ color: "#4a5568", fontSize: "13px", marginBottom: "6px" }}>
                    No exercises added yet.
                  </p>
                  <p style={{ color: "#2d3748", fontSize: "12px" }}>
                    Go to "Add Exercises" tab to pick from the catalog.
                  </p>
                </div>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {selected.map((ex) => (
                  <div
                    key={ex.exercise_name}
                    style={{
                      background: "#0f1117",
                      borderRadius: "10px",
                      border: "1px solid #1e2130",
                      padding: "14px 16px",
                    }}
                  >
                    {/* Exercise name + remove */}
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "10px",
                      }}
                    >
                      <span style={{ fontSize: "13px", fontWeight: "700", color: "#f0f4f8" }}>
                        {ex.exercise_name}
                      </span>
                      <button
                        className="cpm-remove-btn"
                        onClick={() => removeExercise(ex.exercise_name)}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#4a5568",
                          fontSize: "18px",
                          cursor: "pointer",
                          lineHeight: 1,
                          transition: "color 0.15s ease",
                        }}
                        aria-label={`Remove ${ex.exercise_name}`}
                      >
                        ×
                      </button>
                    </div>

                    {/* Sets / Reps / Weight row */}
                    <div style={{ display: "flex", gap: "10px", marginBottom: "6px" }}>
                      {[
                        { field: "sets", label: "Sets" },
                        { field: "reps", label: "Reps" },
                        { field: "weight_kg", label: "kg" },
                      ].map(({ field, label }) => (
                        <div key={field} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <label style={{ fontSize: "10px", color: "#4a5568", letterSpacing: "0.06em", textAlign: "center" }}>
                            {label.toUpperCase()}
                          </label>
                          <input
                            className="cpm-input"
                            type="number"
                            min="0"
                            placeholder="—"
                            value={ex[field]}
                            onChange={(e) => updateField(ex.exercise_name, field, e.target.value)}
                            style={smallInputStyle}
                            aria-label={`${ex.exercise_name} ${label}`}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid #1e2130",
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          {submitError && (
            <p style={{ fontSize: "12px", color: "#ef4444", margin: 0 }}>
              {submitError}
            </p>
          )}

          <button
            className="cpm-submit-btn"
            onClick={handleSubmit}
            disabled={submitting || !name.trim() || selected.length === 0}
            style={{
              width: "100%",
              padding: "13px",
              borderRadius: "10px",
              border: "none",
              background: "#c8f135",
              color: "#0f1117",
              fontSize: "14px",
              fontWeight: "700",
              cursor: submitting || !name.trim() || selected.length === 0 ? "not-allowed" : "pointer",
              opacity: submitting || !name.trim() || selected.length === 0 ? 0.5 : 1,
              letterSpacing: "0.04em",
              transition: "background 0.15s ease",
            }}
            aria-label="Create workout plan"
          >
            {submitting ? "Creating…" : `CREATE PLAN${selected.length > 0 ? ` · ${selected.length} EXERCISE${selected.length !== 1 ? "S" : ""}` : ""}`}
          </button>
        </div>
      </div>
    </>
  );
}
