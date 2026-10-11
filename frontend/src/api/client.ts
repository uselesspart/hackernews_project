export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

type Params = Record<string, string | number | undefined>;

export async function getJson<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  const query = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) query.set(k, String(v));
  }
  const qs = query.toString();
  const response = await fetch(`/api${path}${qs ? `?${qs}` : ""}`, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // тело не JSON (например, страница nginx 502) — остаётся statusText
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}
