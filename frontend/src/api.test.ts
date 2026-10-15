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

describe("admin requests", () => {
  it("send the session cookie and report expired sessions", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Admin authentication required." }), {
        status: 401,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const listener = vi.fn();
    window.addEventListener("admin-unauthorized", listener);
    vi.resetModules();
    const { extractProcedure } = await import("./api");

    await expect(extractProcedure("https://example.gov.in/x")).rejects.toThrow(
      "Admin authentication required.",
    );
    expect(fetchMock.mock.calls[0][1].credentials).toBe("include");
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener("admin-unauthorized", listener);
  });
});

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
