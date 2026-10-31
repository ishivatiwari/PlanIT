import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ probe: string }> },
) {
  const { probe } = await context.params;
  const requestId = crypto.randomUUID();
  const headers = { "Cache-Control": "no-store", "X-Request-ID": requestId };
  if (probe !== "live" && probe !== "ready") {
    return NextResponse.json(
      {
        error: { code: "NOT_FOUND", message: "Not found." },
        request_id: requestId,
      },
      { status: 404, headers },
    );
  }
  try {
    const origin = new URL(
      process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000",
    );
    if (
      !["http:", "https:"].includes(origin.protocol) ||
      origin.username ||
      origin.password ||
      origin.pathname !== "/"
    )
      throw new Error("Invalid API origin");
    const response = await fetch(new URL(`/api/v1/health/${probe}`, origin), {
      cache: "no-store",
      headers: { "X-Request-ID": requestId },
      redirect: "error",
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) {
      const body: unknown = await response.json();
      const expected = probe === "live" ? "ok" : "ready";
      if (
        typeof body === "object" &&
        body !== null &&
        "status" in body &&
        body.status === expected
      ) {
        return NextResponse.json({ status: expected }, { headers });
      }
    }
  } catch {
    // Deliberately do not expose upstream error bodies or configuration.
  }
  return NextResponse.json(
    {
      error: {
        code: "SERVICE_UNAVAILABLE",
        message: "The service is not available. Please try again shortly.",
      },
      request_id: requestId,
    },
    { status: 503, headers },
  );
}
