
import { useState } from "react";
import ProcedureReview from "./ProcedureReview";
import { extractProcedure } from "./api";

export default function AdminPage() {
  const [url, setUrl] = useState("");
  const [review, setReview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function extract() {
    if (!url.trim()) {
      setError("Please enter a government URL.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await extractProcedure(url.trim());
      setReview(data);
    } catch {
      setError("Extraction failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (review?.procedure) {
    return (
      <ProcedureReview
        procedure={review.procedure}
        source_text={review.source_text}
        onDiscard={() => setReview(null)}
      />
    );
  }

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <div style={styles.logo}>PA</div>

        <h1 style={styles.title}>ProcedureAssist AI</h1>
        <p style={styles.subtitle}>
          Extract and review government procedures using AI
        </p>

        <div style={styles.card}>
          <h2 style={styles.heading}>Admin Procedure Review</h2>

          <p style={styles.description}>
            Enter an official government webpage to extract its procedure
            details.
          </p>

          <label style={styles.label}>Government URL</label>

          <input
            style={styles.input}
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter") extract();
            }}
            placeholder="https://example.gov.in/..."
          />

          <button
            style={{
              ...styles.primaryButton,
              opacity: loading ? 0.7 : 1,
            }}
            onClick={extract}
            disabled={loading}
          >
            {loading ? "Extracting..." : "Extract Procedure"}
          </button>

          {error && <p style={styles.error}>{error}</p>}
        </div>

        <p style={styles.footer}>
          ProcedureAssist AI • Admin Review
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "#f5f7fa",
    display: "flex",
    justifyContent: "center",
    padding: "60px 20px",
    fontFamily: "Arial, sans-serif",
    color: "#1f2937",
  },

  container: {
    width: "100%",
    maxWidth: "650px",
    textAlign: "center",
  },

  logo: {
    width: "52px",
    height: "52px",
    margin: "0 auto 18px",
    borderRadius: "12px",
    background: "#2563eb",
    color: "white",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "bold",
    fontSize: "18px",
  },

  title: {
    margin: 0,
    fontSize: "30px",
    fontWeight: 700,
  },

  subtitle: {
    margin: "8px 0 30px",
    color: "#6b7280",
    fontSize: "15px",
  },

  card: {
    background: "white",
    border: "1px solid #e5e7eb",
    borderRadius: "12px",
    padding: "30px",
    textAlign: "left",
    boxShadow: "0 4px 16px rgba(0,0,0,0.05)",
  },

  heading: {
    margin: "0 0 8px",
    fontSize: "21px",
  },

  description: {
    margin: "0 0 24px",
    color: "#6b7280",
    fontSize: "14px",
    lineHeight: 1.5,
  },

  label: {
    display: "block",
    marginBottom: "8px",
    fontSize: "14px",
    fontWeight: 600,
  },

  input: {
    width: "100%",
    padding: "12px",
    border: "1px solid #d1d5db",
    borderRadius: "7px",
    fontSize: "14px",
    boxSizing: "border-box",
    outline: "none",
  },

  primaryButton: {
    width: "100%",
    marginTop: "18px",
    padding: "12px",
    border: "none",
    borderRadius: "7px",
    background: "#2563eb",
    color: "white",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "14px",
  },

  error: {
    marginTop: "14px",
    color: "#dc2626",
    fontSize: "14px",
  },

  footer: {
    marginTop: "24px",
    color: "#9ca3af",
    fontSize: "12px",
  },
};

