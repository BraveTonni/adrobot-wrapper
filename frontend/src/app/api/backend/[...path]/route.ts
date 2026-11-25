import { readFile } from "node:fs/promises";
import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };
const MAX_REQUEST_BODY_BYTES = 64 * 1024;

async function readLimitedBody(request: Request): Promise<Blob | null> {
  const contentLength = request.headers.get("content-length");
  if (contentLength !== null && Number(contentLength) > MAX_REQUEST_BODY_BYTES) {
    return null;
  }

  if (!request.body) return new Blob();

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let totalBytes = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    totalBytes += value.byteLength;
    if (totalBytes > MAX_REQUEST_BODY_BYTES) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }

  const body = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new Blob([body.buffer]);
}

async function proxyRequest(request: NextRequest, context: RouteContext) {
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
    if (origin !== request.nextUrl.origin) {
      console.warn("Blocked cross-origin API proxy request", {
        origin,
        requestOrigin: request.nextUrl.origin,
        host: request.headers.get("host"),
        forwardedHost: request.headers.get("x-forwarded-host"),
        forwardedProto: request.headers.get("x-forwarded-proto"),
      });
      return NextResponse.json(
        { detail: "Cross-origin requests are not allowed" },
        { status: 403, headers: { "Cache-Control": "no-store" } },
      );
    }
  }

  const backendUrl = process.env.BACKEND_API_URL;
  if (!backendUrl) {
    return NextResponse.json(
      { detail: "Не задан адрес backend. Настройте BACKEND_API_URL." },
      { status: 503 },
    );
  }

  const apiToken = await readApiToken();
  if (!apiToken) {
    return NextResponse.json(
      { detail: "Токен доступа к API не настроен на сервере." },
      { status: 503 },
    );
  }

  const body = request.method === "GET" || request.method === "HEAD"
    ? undefined
    : await readLimitedBody(request);
  if (body === null) {
    return NextResponse.json(
      { detail: "Request body exceeds the 64 KiB limit" },
      { status: 413, headers: { "Cache-Control": "no-store" } },
    );
  }

  const { path } = await context.params;
  const target = new URL(
    `/api/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
    backendUrl,
  );
  const headers = new Headers();
  headers.set("authorization", `Bearer ${apiToken}`);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const idempotencyKey = request.headers.get("idempotency-key");
  if (idempotencyKey) headers.set("idempotency-key", idempotencyKey);

  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "Backend недоступен. Проверьте соединение и повторите запрос." },
      { status: 502 },
    );
  }
}

async function readApiToken(): Promise<string | null> {
  const tokenFile = process.env.API_ACCESS_TOKEN_FILE;
  if (tokenFile) {
    try {
      const token = (await readFile(tokenFile, "utf8")).trim();
      return token.length >= 32 ? token : null;
    } catch {
      return null;
    }
  }

  const token = process.env.API_ACCESS_TOKEN?.trim();
  return token && token.length >= 32 ? token : null;
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const DELETE = proxyRequest;
