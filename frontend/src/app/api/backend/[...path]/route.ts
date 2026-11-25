import { readFile } from "node:fs/promises";
import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxyRequest(request: NextRequest, context: RouteContext) {
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
      body: request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.text(),
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
