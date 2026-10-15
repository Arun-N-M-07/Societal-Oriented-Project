/// <reference types="vite/client" />

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

export type ReExtractRequest = ScrapeResult & { provenance_token: string };

export type ExtractionResponse = {
  source_text: string;
  procedure: ProcedureSpine;
  provenance_token: string;
};

export type ApprovalRequest = {
  procedure: ProcedureSpine;
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

async function request<T>(
  path: string,
  fallback: string,
  body?: unknown,
  method = body === undefined ? "GET" : "POST",
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    credentials: "include",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
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

export const reExtractProcedure = (source: ReExtractRequest) =>
  request<ProcedureSpine>(
    "/api/admin/re-extract",
    "Unable to re-extract procedure.",
    source,
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
