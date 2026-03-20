import Layout from "../components/Layout";

export default function Profile() {
  return (
    <Layout>
      <div style={{ padding: "36px 40px" }}>
        <p style={{ fontSize: "11px", color: "#4a5568", letterSpacing: "0.1em", marginBottom: "6px" }}>
          ACCOUNT
        </p>
        <h1 style={{ fontSize: "26px", fontWeight: "700", color: "#f0f4f8", letterSpacing: "-0.02em", marginBottom: "32px" }}>
          Profile
        </h1>
        <div style={{ padding: "48px", borderRadius: "12px", border: "1px dashed #1e2130", textAlign: "center" }}>
          <p style={{ color: "#4a5568", fontSize: "13px" }}>Profile settings coming soon.</p>
        </div>
      </div>
    </Layout>
  );
}