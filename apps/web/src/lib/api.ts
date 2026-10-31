export type FieldError = { path: string; message: string };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fields: FieldError[] = [],
    public code = "REQUEST_FAILED",
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: {
    method?: "GET" | "POST" | "PATCH";
    data?: unknown;
    csrf?: string;
    revision?: number;
    signal?: AbortSignal;
    requestKey?: string;
    timeoutMs?: number;
  } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Requested-With": "Eventora",
  };
  if (options.csrf) headers["X-CSRF-Token"] = options.csrf;
  if (options.requestKey) headers["Idempotency-Key"] = options.requestKey;
  if (options.revision !== undefined)
    headers["If-Match"] = `"${options.revision}"`;
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method: options.method ?? "GET",
      headers,
      body:
        options.data === undefined ? undefined : JSON.stringify(options.data),
      credentials: "same-origin",
      cache: "no-store",
      signal: options.signal
        ? AbortSignal.any([
            options.signal,
            AbortSignal.timeout(options.timeoutMs ?? 12000),
          ])
        : AbortSignal.timeout(options.timeoutMs ?? 12000),
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      503,
      "The connection was interrupted. Check your connection and try again.",
    );
  }
  if (response.status === 204) return undefined as T;
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401 && path !== "/me" && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("eventora:unauthorized"));
    throw new ApiError(
      response.status,
      result.error?.message ?? "The request could not be completed.",
      result.error?.fields ?? [],
      result.error?.code,
    );
  }
  return result as T;
}

export function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
