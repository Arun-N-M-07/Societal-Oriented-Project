interface SourcePreviewProps {
  sourceUrl: string;
  sourceText: string;
}

export default function SourcePreview({
  sourceUrl,
  sourceText,
}: SourcePreviewProps) {
  return (
    <div style={styles.container}>
      <h2>Official Source</h2>

      <div style={styles.urlBox}>
        <strong>Source URL</strong>

        <div style={styles.url}>
          {sourceUrl}
        </div>
      </div>

      <div style={styles.textBox}>
        <strong>Extracted Source Text</strong>

        <pre style={styles.text}>
          {sourceText}
        </pre>
      </div>
    </div>
  );
}

const styles = {
  container: {
    marginTop: "24px",
    padding: "24px",
    border: "1px solid #ddd",
    borderRadius: "10px",
    background: "#ffffff",
  },

  urlBox: {
    marginTop: "16px",
    padding: "12px",
    background: "#f5f5f5",
    borderRadius: "6px",
  },

  url: {
    marginTop: "6px",
    wordBreak: "break-all" as const,
  },

  textBox: {
    marginTop: "20px",
  },

  text: {
    marginTop: "10px",
    padding: "16px",
    background: "#f7f7f7",
    border: "1px solid #ddd",
    borderRadius: "6px",
    whiteSpace: "pre-wrap" as const,
    maxHeight: "500px",
    overflowY: "auto" as const,
    fontFamily: "inherit",
    lineHeight: "1.5",
  },
};
