
import { useState } from "react";
import { approveProcedure, reExtract } from "./api";

type Procedure = {
  name: string;
  department: string | null;
  jurisdiction: string | null;
  summary: string;
  eligibility: string | null;
  steps: string[];
  source_url: string;
};

type Props = {
  procedure: Procedure;
  source_text: string;
  onDiscard: () => void;
};

export default function ProcedureReview({
  procedure: initial,
  source_text,
  onDiscard,
}: Props) {
  const [procedure, setProcedure] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  function update(field: keyof Procedure, value: any) {
    setProcedure({ ...procedure, [field]: value });
  }

  async function extractAgain() {
    setLoading(true);
    setMessage("");

    try {
      const data = await reExtract(
        procedure.source_url,
        source_text
      );

      setProcedure(data.procedure);
      setMessage("Procedure re-extracted successfully.");
    } catch {
      setMessage("Re-extraction failed.");
    } finally {
      setLoading(false);
    }
  }

  async function approve() {
    const clean = {
      ...procedure,
      name: procedure.name.trim(),
      summary: procedure.summary.trim(),
      department: procedure.department?.trim() || null,
      jurisdiction: procedure.jurisdiction?.trim() || null,
      eligibility: procedure.eligibility?.trim() || null,
      steps: procedure.steps.map(s => s.trim()).filter(Boolean),
    };

    if (!clean.name || !clean.summary || !clean.steps.length) {
      setMessage("Name, summary and at least one step are required.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      await approveProcedure(clean, source_text);
      setMessage("Procedure approved successfully.");
    } catch {
      setMessage("Approval failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.container}>

        <div style={styles.topbar}>
          <div>
            <div style={styles.brand}>ProcedureAssist AI</div>
            <div style={styles.small}>Admin Review</div>
          </div>

          <button
            style={styles.backButton}
            onClick={onDiscard}
            disabled={loading}
          >
            ← New Procedure
          </button>
        </div>

        <div style={styles.card}>
          <h1 style={styles.title}>Review Procedure</h1>

          <p style={styles.subtitle}>
            Verify the information extracted by the AI before approval.
          </p>

          <Section title="Procedure Details">

            <div style={styles.grid}>
              <Field
                label="Procedure Name"
                value={procedure.name}
                onChange={value => update("name", value)}
              />

              <Field
                label="Department"
                value={procedure.department || ""}
                onChange={value => update("department", value)}
              />

              <Field
                label="Jurisdiction"
                value={procedure.jurisdiction || ""}
                onChange={value => update("jurisdiction", value)}
              />
            </div>

            <TextField
              label="Summary"
              value={procedure.summary}
              onChange={value => update("summary", value)}
            />

            <TextField
              label="Eligibility"
              value={procedure.eligibility || ""}
              onChange={value => update("eligibility", value)}
            />

          </Section>

          <Section title="Procedure Steps">

            <div style={styles.steps}>
              {procedure.steps.map((step, index) => (
                <div style={styles.step} key={index}>
                  <div style={styles.number}>{index + 1}</div>

                  <input
                    style={styles.stepInput}
                    value={step}
                    onChange={e => {
                      const steps = [...procedure.steps];
                      steps[index] = e.target.value;
                      update("steps", steps);
                    }}
                  />

                  <button
                    style={styles.remove}
                    onClick={() =>
                      update(
                        "steps",
                        procedure.steps.filter(
                          (_, i) => i !== index
                        )
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>

            <button
              style={styles.addButton}
              onClick={() =>
                update("steps", [...procedure.steps, ""])
              }
            >
              + Add Step
            </button>

          </Section>

          <Section title="Source Information">

            <label style={styles.label}>Source URL</label>

            <input
              style={styles.input}
              value={procedure.source_url}
              readOnly
            />

            <label style={styles.label}>Source Text</label>

            <textarea
              style={styles.sourceText}
              value={source_text}
              readOnly
            />

          </Section>

          <div style={styles.actions}>

            <button
              style={styles.secondary}
              onClick={extractAgain}
              disabled={loading}
            >
              {loading ? "Working..." : "Re-extract"}
            </button>

            <button
              style={styles.discard}
              onClick={onDiscard}
              disabled={loading}
            >
              Discard
            </button>

            <button
              style={styles.approve}
              onClick={approve}
              disabled={loading}
            >
              {loading ? "Saving..." : "Approve"}
            </button>

          </div>

          {message && (
            <p
              style={{
                ...styles.message,
                color: message.includes("failed")
                  ? "#dc2626"
                  : "#15803d",
              }}
            >
              {message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section style={styles.section}>
      <h2 style={styles.sectionTitle}>{title}</h2>
      {children}
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label style={styles.label}>{label}</label>
      <input
        style={styles.input}
        value={value}
        onChange={e => onChange(e.target.value)}
      />
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label style={styles.label}>{label}</label>
      <textarea
        style={styles.textarea}
        value={value}
        onChange={e => onChange(e.target.value)}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "#f5f7fa",
    padding: "30px 20px",
    fontFamily: "Arial, sans-serif",
    color: "#1f2937",
  },

  container: {
    maxWidth: "950px",
    margin: "auto",
  },

  topbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "24px",
  },

  brand: {
    fontSize: "20px",
    fontWeight: 700,
  },

  small: {
    color: "#6b7280",
    fontSize: "13px",
    marginTop: "3px",
  },

  backButton: {
    background: "white",
    border: "1px solid #d1d5db",
    borderRadius: "7px",
    padding: "9px 14px",
    cursor: "pointer",
  },

  card: {
    background: "white",
    border: "1px solid #e5e7eb",
    borderRadius: "12px",
    padding: "32px",
    boxShadow: "0 3px 15px rgba(0,0,0,0.05)",
  },

  title: {
    margin: 0,
    fontSize: "26px",
  },

  subtitle: {
    color: "#6b7280",
    fontSize: "14px",
    marginTop: "7px",
    marginBottom: "30px",
  },

  section: {
    borderTop: "1px solid #e5e7eb",
    paddingTop: "24px",
    marginTop: "24px",
  },

  sectionTitle: {
    fontSize: "17px",
    margin: "0 0 18px",
  },

  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "18px",
  },

  label: {
    display: "block",
    fontSize: "13px",
    fontWeight: 600,
    marginBottom: "7px",
  },

  input: {
    width: "100%",
    padding: "10px 11px",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    boxSizing: "border-box",
    fontSize: "14px",
  },

  textarea: {
    width: "100%",
    minHeight: "90px",
    padding: "10px 11px",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    boxSizing: "border-box",
    fontSize: "14px",
    resize: "vertical",
  },

  steps: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },

  step: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },

  number: {
    minWidth: "28px",
    height: "28px",
    borderRadius: "50%",
    background: "#eff6ff",
    color: "#2563eb",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: "13px",
  },

  stepInput: {
    flex: 1,
    padding: "10px",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
  },

  remove: {
    background: "#fff1f2",
    color: "#be123c",
    border: "none",
    borderRadius: "6px",
    padding: "9px 11px",
    cursor: "pointer",
  },

  addButton: {
    marginTop: "14px",
    background: "#f3f4f6",
    border: "none",
    borderRadius: "6px",
    padding: "9px 13px",
    cursor: "pointer",
    fontWeight: 600,
  },

  sourceText: {
    width: "100%",
    height: "180px",
    padding: "10px 11px",
    background: "#f9fafb",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    boxSizing: "border-box",
    resize: "vertical",
    fontSize: "13px",
    lineHeight: 1.5,
  },

  actions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "10px",
    marginTop: "30px",
    paddingTop: "22px",
    borderTop: "1px solid #e5e7eb",
  },

  secondary: {
    background: "#f3f4f6",
    border: "none",
    borderRadius: "6px",
    padding: "10px 16px",
    cursor: "pointer",
    fontWeight: 600,
  },

  discard: {
    background: "#fff1f2",
    color: "#be123c",
    border: "none",
    borderRadius: "6px",
    padding: "10px 16px",
    cursor: "pointer",
    fontWeight: 600,
  },

  approve: {
    background: "#2563eb",
    color: "white",
    border: "none",
    borderRadius: "6px",
    padding: "10px 20px",
    cursor: "pointer",
    fontWeight: 600,
  },

  message: {
    textAlign: "right",
    fontSize: "14px",
    marginBottom: 0,
  },
};

