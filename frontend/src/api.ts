const API_BASE_URL = "http://localhost:8000";

export type ScrapeResult = {
  source_url: string;
  source_text: string;
};

export type ProcedureSpine = {
  name: string;
  department: string | null;
  jurisdiction: string | null;
  summary: string;
  eligibility: string | null;
  steps: string[];
  source_url: string;
};

export type ExtractionResponse = {
  source_text: string;
  procedure: ProcedureSpine;
};

export type ApprovalRequest = {
  procedure: ProcedureSpine;
  source_text: string;
};

export type SavedProcedureResponse = {
  id: number;
  name: string;
  status: string;
};

async function errorMessage(response: Response, fallback: string) {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return typeof body?.detail === "string" ? body.detail : fallback;
}

export async function extractProcedure(
  sourceUrl: string,
): Promise<ExtractionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/admin/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_url: sourceUrl }),
  });

  if (!response.ok) {
    throw new Error(await errorMessage(response, "Unable to extract procedure."));
  }

  return response.json() as Promise<ExtractionResponse>;
}

export async function reExtractProcedure(
  source: ScrapeResult,
): Promise<ProcedureSpine> {
  const response = await fetch(`${API_BASE_URL}/api/admin/re-extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(source),
  });

  if (!response.ok) {
    throw new Error(
      await errorMessage(response, "Unable to re-extract procedure."),
    );
  }

  return response.json() as Promise<ProcedureSpine>;
}

export async function approveProcedure(
  request: ApprovalRequest,
): Promise<SavedProcedureResponse> {
  const response = await fetch(`${API_BASE_URL}/api/admin/procedures`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await errorMessage(response, "Unable to save procedure."));
  }

  return response.json() as Promise<SavedProcedureResponse>;
}
