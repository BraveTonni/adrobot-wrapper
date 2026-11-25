import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

afterEach(() => {
  vi.unstubAllEnvs();
});

function request(authorization?: string): NextRequest {
  return new NextRequest("http://localhost/", {
    headers: authorization ? { authorization } : undefined,
  });
}

describe("frontend access middleware", () => {
  it("fails closed when the password is not configured", async () => {
    vi.stubEnv("FRONTEND_AUTH_PASSWORD", "");

    const response = await middleware(request());

    expect(response.status).toBe(503);
  });

  it("requires browser Basic authentication", async () => {
    vi.stubEnv("FRONTEND_AUTH_PASSWORD", "a".repeat(32));

    const response = await middleware(request());

    expect(response.status).toBe(401);
    expect(response.headers.get("www-authenticate")).toContain("Basic");
  });

  it("allows the configured admin and attaches a nonce CSP", async () => {
    const password = "b".repeat(32);
    vi.stubEnv("FRONTEND_AUTH_PASSWORD", password);

    const response = await middleware(
      request(`Basic ${btoa(`admin:${password}`)}`),
    );
    const csp = response.headers.get("content-security-policy") ?? "";

    expect(response.status).toBe(200);
    expect(csp).toContain("script-src 'self' 'nonce-");
    expect(csp).not.toContain("script-src 'self' 'unsafe-inline'");
  });
});
