import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 90;
const uuid =
  "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";

function allowed(path: string, method: string) {
  if (path === "me") return method === "GET";
  if (path === "ai/status") return method === "GET";
  if (new RegExp(`^events/${uuid}/intake$`).test(path))
    return method === "POST";
  if (new RegExp(`^events/${uuid}/generations$`).test(path))
    return method === "GET" || method === "POST";
  if (new RegExp(`^events/${uuid}/plans$`).test(path)) return method === "GET";
  if (new RegExp(`^events/${uuid}/plans/${uuid}$`).test(path))
    return method === "GET" || method === "PATCH";
  if (new RegExp(`^events/${uuid}/vendors$`).test(path))
    return method === "GET" || method === "POST";
  if (new RegExp(`^events/${uuid}/vendors/${uuid}/quotes$`).test(path))
    return method === "POST";
  if (new RegExp(`^events/${uuid}/replans$`).test(path))
    return method === "GET" || method === "POST";
  if (new RegExp(`^events/${uuid}/export$`).test(path)) return method === "GET";
  if (
    new RegExp(`^events/${uuid}/replans/${uuid}/(approve|reject)$`).test(path)
  )
    return method === "POST";
  if (new RegExp(`^events/${uuid}/budget$`).test(path)) return method === "GET";
  if (new RegExp(`^events/${uuid}/budget/items$`).test(path))
    return method === "POST";
  if (new RegExp(`^events/${uuid}/budget/items/${uuid}$`).test(path))
    return method === "PATCH";
  if (new RegExp(`^events/${uuid}/timeline$`).test(path))
    return method === "GET";
  if (new RegExp(`^events/${uuid}/timeline/tasks$`).test(path))
    return method === "POST";
  if (new RegExp(`^events/${uuid}/timeline/tasks/${uuid}$`).test(path))
    return method === "PATCH";
  if (/^auth\/(login|register|logout)$/.test(path)) return method === "POST";
  if (path === "events") return method === "GET" || method === "POST";
  if (new RegExp(`^events/${uuid}$`).test(path))
    return method === "GET" || method === "PATCH";
  return new RegExp(`^events/${uuid}/archive$`).test(path) && method === "POST";
}

async function boundedBody(
  stream: ReadableStream<Uint8Array> | null,
  maximum: number,
) {
  if (!stream) return new Uint8Array();
  const reader = stream.getReader();
  const parts: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > maximum) {
        await reader.cancel();
        throw new RangeError("Body limit");
      }
      parts.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) {
    bytes.set(part, offset);
    offset += part.length;
  }
  return bytes;
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path: segments } = await context.params;
  const path = segments.join("/");
  const requestId = crypto.randomUUID();
  const headers = new Headers({
    "Cache-Control": "private, no-store",
    Vary: "Cookie",
    "X-Request-ID": requestId,
  });
  const fail = (status: number, code: string, message: string) =>
    NextResponse.json(
      { error: { code, message }, request_id: requestId },
      { status, headers },
    );
  if (!allowed(path, request.method))
    return fail(404, "NOT_FOUND", "Not found.");
  let body: Uint8Array<ArrayBuffer> | undefined;
  if (request.method !== "GET") {
    // Next's internal URL may normalize the host to localhost. Compare the
    // browser origin to the HTTP Host; FastAPI also enforces the exact APP_URL
    // (including scheme) and session-bound CSRF token. Ignore forwarded hosts.
    let sameHost = false;
    try {
      const browserOrigin = new URL(request.headers.get("origin") ?? "");
      sameHost =
        ["http:", "https:"].includes(browserOrigin.protocol) &&
        browserOrigin.host === request.headers.get("host");
    } catch {
      sameHost = false;
    }
    if (!sameHost)
      return fail(
        403,
        "ORIGIN_REJECTED",
        "Refresh this page from the PlanIT address and try again.",
      );
    if (!request.headers.get("content-type")?.startsWith("application/json"))
      return fail(415, "JSON_REQUIRED", "Send an application/json request.");
    try {
      body = await boundedBody(request.body, 65536);
    } catch {
      return fail(413, "REQUEST_TOO_LARGE", "The request is too large.");
    }
  }
  try {
    const origin = new URL(
      process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000",
    );
    if (
      !["http:", "https:"].includes(origin.protocol) ||
      origin.username ||
      origin.password ||
      origin.pathname !== "/" ||
      origin.search ||
      origin.hash
    )
      throw new Error("Invalid API origin");
    const upstream = new URL(`/api/v1/${path}`, origin);
    if (path === "events" && request.method === "GET") {
      for (const [key, value] of request.nextUrl.searchParams) {
        if (!["limit", "cursor", "status"].includes(key) || value.length > 256)
          return fail(422, "VALIDATION_ERROR", "Invalid event list query.");
        upstream.searchParams.append(key, value);
      }
    } else if (
      new RegExp(`^events/${uuid}/plans$`).test(path) &&
      request.method === "GET"
    ) {
      for (const [key, value] of request.nextUrl.searchParams) {
        if (key !== "before" || !/^\d{1,10}$/.test(value))
          return fail(422, "VALIDATION_ERROR", "Invalid plan list query.");
        upstream.searchParams.append(key, value);
      }
    } else if (
      request.nextUrl.search &&
      (/\/vendors$/.test(path) ||
        /\/budget$/.test(path) ||
        /\/export$/.test(path))
    ) {
      for (const [key, value] of request.nextUrl.searchParams) {
        if (
          !["category", "provenance", "sort", "scenario", "format"].includes(
            key,
          ) ||
          value.length > 80
        )
          return fail(422, "VALIDATION_ERROR", "Invalid comparison query.");
        upstream.searchParams.append(key, value);
      }
    } else if (request.nextUrl.search)
      return fail(
        422,
        "VALIDATION_ERROR",
        "This endpoint does not accept query parameters.",
      );
    const forwarded = new Headers({
      "X-Request-ID": requestId,
      "Content-Type": "application/json",
    });
    for (const name of [
      "origin",
      "x-csrf-token",
      "x-requested-with",
      "if-match",
      "idempotency-key",
    ]) {
      const value = request.headers.get(name);
      if (value && value.length <= 256) forwarded.set(name, value);
    }
    const cookies = ["eventora_session", "__Host-eventora_session"].flatMap(
      (name) => {
        const value = request.cookies.get(name)?.value;
        return value && /^[A-Za-z0-9_-]{40,64}$/.test(value)
          ? [`${name}=${value}`]
          : [];
      },
    );
    if (cookies.length) forwarded.set("Cookie", cookies.join("; "));
    const response = await fetch(upstream, {
      method: request.method,
      headers: forwarded,
      body,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(
        request.method === "POST" && /\/(intake|generations)$/.test(path)
          ? 75000
          : 8000,
      ),
    });
    for (const name of [
      "etag",
      "retry-after",
      "location",
      "content-disposition",
      "content-type",
    ]) {
      const value = response.headers.get(name);
      if (value) headers.set(name, value);
    }
    for (const cookie of response.headers.getSetCookie()) {
      if (/^(eventora_session|__Host-eventora_session)=/.test(cookie))
        headers.append("Set-Cookie", cookie);
    }
    if (response.status === 204)
      return new NextResponse(null, { status: 204, headers });
    const bytes = await boundedBody(response.body, 2 * 1024 * 1024);
    if (path.endsWith("/export"))
      return new NextResponse(bytes, { status: response.status, headers });
    if (!response.headers.get("content-type")?.includes("application/json"))
      throw new Error("Invalid upstream response");
    const data: unknown = JSON.parse(new TextDecoder().decode(bytes));
    return NextResponse.json(data, { status: response.status, headers });
  } catch {
    return fail(
      503,
      "SERVICE_UNAVAILABLE",
      "The service is unavailable. Please try again shortly.",
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
