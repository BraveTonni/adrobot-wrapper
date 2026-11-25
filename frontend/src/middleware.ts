import { NextRequest, NextResponse } from "next/server";

const encoder = new TextEncoder();

function constantTimeEqual(left: string, right: string): Promise<boolean> {
  return Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(left)),
    crypto.subtle.digest("SHA-256", encoder.encode(right)),
  ]).then(([leftDigest, rightDigest]) => {
    const a = new Uint8Array(leftDigest);
    const b = new Uint8Array(rightDigest);
    let difference = 0;
    for (let index = 0; index < a.length; index += 1) {
      difference |= a[index] ^ b[index];
    }
    return difference === 0;
  });
}

function createNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return btoa(String.fromCharCode(...bytes));
}

function contentSecurityPolicy(nonce: string): string {
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob:",
    "connect-src 'self'",
  ].join("; ");
}

function setSecurityHeaders(response: NextResponse, csp: string): NextResponse {
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=()",
  );
  return response;
}

function unauthorized(csp: string): NextResponse {
  return setSecurityHeaders(
    new NextResponse("Authentication required", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="Adrobot", charset="UTF-8"',
        "Cache-Control": "no-store",
      },
    }),
    csp,
  );
}

export async function middleware(request: NextRequest): Promise<NextResponse> {
  const nonce = createNonce();
  const csp = contentSecurityPolicy(nonce);
  const expectedPassword = process.env.FRONTEND_AUTH_PASSWORD;

  if (!expectedPassword || expectedPassword.length < 32) {
    return setSecurityHeaders(
      NextResponse.json(
        { detail: "Frontend authentication is not configured" },
        { status: 503, headers: { "Cache-Control": "no-store" } },
      ),
      csp,
    );
  }

  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Basic ")) return unauthorized(csp);

  let credentials: string;
  try {
    credentials = atob(authorization.slice("Basic ".length));
  } catch {
    return unauthorized(csp);
  }

  const separator = credentials.indexOf(":");
  if (separator < 0 || credentials.slice(0, separator) !== "admin") {
    return unauthorized(csp);
  }

  const password = credentials.slice(separator + 1);
  if (!(await constantTimeEqual(password, expectedPassword))) {
    return unauthorized(csp);
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("Content-Security-Policy", csp);
  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  return setSecurityHeaders(response, csp);
}

export const config = { matcher: ["/:path*"] };
