/// <reference types="vite/client" />

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type ProcedureDraft = {
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
  procedure: ProcedureDraft;
  provenance_token: string;
};

export type ApprovalRequest = {
  procedure: ProcedureDraft;
  source_text: string;
  provenance_token: string;
};

export type SavedProcedureResponse = {
  id: number;
  name: string;
  status: string;
};

export type AdminSession = { username: string };

export type SavedProcedure = {
  id: number;
  name: string;
  department: string | null;
  jurisdiction: string | null;
  source_url: string;
};

// Fired when an admin request is rejected because the session has expired.
export const UNAUTHORIZED_EVENT = "admin-unauthorized";
const NO_SESSION_PATHS = ["/api/admin/login", "/api/admin/session"];

async function errorMessage(response: Response, fallback: string) {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return typeof body?.detail === "string" ? body.detail : fallback;
}

// A guidance request can chain several model calls of up to 60 s each; past this the citizen is told to retry.
const REQUEST_TIMEOUT_MS = 180_000;
export const UNREACHABLE = "The server cannot be reached. Check your connection and try again.";

async function request<T>(
  path: string,
  fallback: string,
  body?: unknown,
  method = body === undefined ? "GET" : "POST",
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    credentials: "include",
    headers: body === undefined ? undefined : { "Content-Type": body instanceof Blob ? body.type : "application/json" },
    body: body === undefined || body instanceof Blob ? body : JSON.stringify(body),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  }).catch((error: unknown) => {
    throw new Error(error instanceof DOMException && error.name === "TimeoutError"
      ? "The server took too long to answer. Try again." : UNREACHABLE);
  });

  if (response.status === 401 && !NO_SESSION_PATHS.includes(path)) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  if (!response.ok) {
    throw new Error(await errorMessage(response, fallback));
  }
  return (response.status === 204 ? undefined : response.json()) as Promise<T>;
}

export const extractProcedure = (sourceUrl: string) =>
  request<ExtractionResponse>(
    "/api/admin/extract",
    "Unable to extract procedure.",
    { source_url: sourceUrl },
  );

export const approveProcedure = (approval: ApprovalRequest) =>
  request<SavedProcedureResponse>(
    "/api/admin/procedures",
    "Unable to save procedure.",
    approval,
  );

export const login = (username: string, password: string) =>
  request<AdminSession>("/api/admin/login", "Unable to sign in.", {
    username,
    password,
  });

export const logout = () =>
  request<void>("/api/admin/logout", "Unable to sign out.", undefined, "POST");

export const getSession = () =>
  request<AdminSession>("/api/admin/session", "Not signed in.");

export const listSavedProcedures = () =>
  request<SavedProcedure[]>("/api/admin/procedures", "Unable to load procedures.");

export const deleteProcedure = (id: number) =>
  request<void>(`/api/admin/procedures/${id}`, "Unable to delete procedure.", undefined, "DELETE");

export type ProcedureSummary = {
  id: number;
  name: string;
  department: string | null;
  jurisdiction: string | null;
  summary: string;
};

export type ProcedureDetail = ProcedureSummary & {
  eligibility: string | null;
  steps: string[];
  source_url: string;
};

export type Need = {
  phrases: string[];
  question: string;
  status: "matched" | "ambiguous" | "no_match";
  candidates: ProcedureSummary[];
};

export type IdentifyResponse = {
  status: "matched" | "ambiguous" | "no_match" | "multiple";
  candidates: ProcedureSummary[];
  needs?: Need[];
  pending?: { phrase: string; question: string }[];
  relation_question?: string | null;
  // Tamil questions only: the English query that was searched, or a request for the service name.
  normalized_query?: string;
  clarification?: string;
  // Matched only: the question names that procedure itself ("What about EPS?").
  named?: boolean;
};

type Claim = { text: string; chunk_id: number; quote: string; procedure_id?: number; source_url?: string };

export type GuidanceResponse = {
  procedure_id: number;
  source_url: string;
  insufficient_evidence: boolean;
  claims: Claim[];
  omitted_claims: number;
  normalized_query?: string;
  partial?: boolean;
};

export type RelationResponse = {
  insufficient_evidence: boolean;
  claims: Required<Claim>[];
  omitted_claims: number;
  comparison?: boolean;
};

export type Language = "en" | "ta";

export const identifyProcedure = (question: string, language: Language = "en") =>
  request<IdentifyResponse>("/api/identify", "Unable to search procedures.", {
    question,
    language,
  });

export const getProcedure = (id: number) =>
  request<ProcedureDetail>(`/api/procedures/${id}`, "Unable to load the procedure.");

export const askRelation = (procedureIds: number[], question: string) =>
  request<RelationResponse>("/api/relation", "Unable to answer the question.", {
    procedure_ids: procedureIds,
    question,
  });

export const askGuidance = (procedureId: number, question: string, language: Language = "en") =>
  request<GuidanceResponse>("/api/guidance", "Unable to answer the question.", {
    procedure_id: procedureId,
    question,
    language,
  });

// The recording is transcribed on the ProcedureAssist server; it is not stored.
export const transcribeSpeech = (wav: Blob, language: Language) =>
  request<{ text: string; language: Language }>(
    `/api/speech/transcribe?language=${language}`,
    "Unable to transcribe the recording.",
    wav,
  );
