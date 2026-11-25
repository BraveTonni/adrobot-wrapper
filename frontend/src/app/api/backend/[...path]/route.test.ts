import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

const context = { params: Promise.resolve({ path: ["v1", "campaigns"] }) };

describe("backend proxy request security", () => {
  it("rejects cross-origin mutations", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/backend/v1/campaigns", {
        method: "POST",
        headers: { origin: "https://attacker.example" },
        body: "{}",
      }),
      context,
    );

    expect(response.status).toBe(403);
  });

  it("forwards same-origin mutations with the server-side API token", async () => {
    vi.stubEnv("BACKEND_API_URL", "http://backend:8000");
    vi.stubEnv("API_ACCESS_TOKEN", "a".repeat(32));
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({ id: 7 }, { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      new NextRequest("http://localhost/api/backend/v1/campaigns", {
        method: "POST",
        headers: {
          origin: "http://localhost",
          "content-type": "application/json",
        },
        body: "{}",
      }),
      context,
    );

    expect(response.status).toBe(201);
    const [, options] = fetchMock.mock.calls[0] as [URL, RequestInit];
    expect(new Headers(options.headers).get("authorization")).toBe(
      `Bearer ${"a".repeat(32)}`,
    );
  });

  it("rejects oversized request bodies before contacting the backend", async () => {
    vi.stubEnv("BACKEND_API_URL", "http://backend:8000");
    vi.stubEnv("API_ACCESS_TOKEN", "a".repeat(32));
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      new NextRequest("http://localhost/api/backend/v1/campaigns", {
        method: "POST",
        headers: {
          origin: "http://localhost",
          "content-type": "application/json",
        },
        body: new Uint8Array(65 * 1024),
      }),
      context,
    );

    expect(response.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
