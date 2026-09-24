const API = "http://localhost:8000/api";

export async function extractProcedure(source_url: string) {
  const res = await fetch(`${API}/admin/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_url }),
  });

  if (!res.ok) throw new Error("Extraction failed");
  return res.json();
}

export async function reExtract(source_url: string, source_text: string) {
  const res = await fetch(`${API}/admin/re-extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_url, source_text }),
  });

  if (!res.ok) throw new Error("Re-extraction failed");
  return res.json();
}

export async function approveProcedure(procedure: unknown, source_text: string) {
  const res = await fetch(`${API}/admin/procedures`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ procedure, source_text }),
  });

  if (!res.ok) throw new Error("Approval failed");
  return res.json();
}