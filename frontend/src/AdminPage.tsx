import { useState } from "react";
import { scrapeUrl } from "./api";
import SourcePreview from "./SourcePreview";

export default function AdminPage() {
  const [url, setUrl] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceText, setSourceText] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleScrape() {
    if (!url.trim()) {
      setError("Please enter a government website URL.");
      return;
    }

    setLoading(true);
    setError("");
    setSourceUrl("");
    setSourceText("");

    try {
      const result = await scrapeUrl(url.trim());

      setSourceUrl(result.source_url);
      setSourceText(result.source_text);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to scrape the website.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1>ProcedureAssist AI</h1>

        <p style={styles.subtitle}>
          Government Procedure Source Extraction
        </p>

        <label style={styles.label}>
          Official Government URL
        </label>

        <input
          type="url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://www.tn.gov.in/"
          disabled={loading}
          style={styles.input}
        />

        <button
          onClick={handleScrape}
          disabled={loading}
          style={styles.button}
        >
          {loading ? "Scraping..." : "Scrape Source"}
        </button>

        {error && (
          <div style={styles.error}>
            {error}
          </div>
        )}
      </div>

      {sourceUrl && sourceText && (
        <SourcePreview
          sourceUrl={sourceUrl}
          sourceText={sourceText}
        />
      )}
    </div>
  );
}

const styles = {
  page: {
    maxWidth: "1100px",
    margin: "0 auto",
    padding: "40px 20px",
    fontFamily: "Arial, sans-serif",
  },

  card: {
    padding: "30px",
    border: "1px solid #ddd",
    borderRadius: "10px",
    background: "#ffffff",
  },

  subtitle: {
    color: "#666",
    marginBottom: "30px",
  },

  label: {
    display: "block",
    marginBottom: "8px",
    fontWeight: "bold",
  },

  input: {
    width: "100%",
    boxSizing: "border-box" as const,
    padding: "12px",
    fontSize: "16px",
    border: "1px solid #bbb",
    borderRadius: "6px",
    marginBottom: "12px",
  },

  button: {
    padding: "12px 20px",
    fontSize: "16px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },

  error: {
    marginTop: "16px",
    padding: "12px",
    borderRadius: "6px",
    background: "#ffecec",
    border: "1px solid #ffaaaa",
  },
};
