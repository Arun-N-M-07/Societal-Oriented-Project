import { afterEach, describe, expect, it, vi } from "vitest";

async function requestedUrl() {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ source_text: "x", procedure: {} })),
  );
  vi.stubGlobal("fetch", fetchMock);
  vi.resetModules();
  const { extractProcedure } = await import("./api");
  await extractProcedure("https://example.gov.in/page");
  return fetchMock.mock.calls[0][0];
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("API base URL", () => {
  it("defaults to the local backend", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    expect(await requestedUrl()).toBe("http://localhost:8000/api/admin/extract");
  });

  it("uses VITE_API_BASE_URL when set", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.test:9000");
    expect(await requestedUrl()).toBe("http://api.test:9000/api/admin/extract");
  });
});
