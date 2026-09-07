import type {
  AssembleResponse,
  ExtractResponse,
  FieldValueInput,
  HealthResponse,
  LogResponse,
  Role,
  TooltipResponse,
} from "../types";

export class ApiError extends Error {}

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(`Could not reach ${baseUrl} — is the server running?`);
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? "");
    } catch {
      /* body wasn't JSON */
    }
    throw new ApiError(`${path} failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export async function checkHealth(baseUrl: string): Promise<HealthResponse> {
  return request<HealthResponse>(baseUrl, "/health");
}

export async function extract(baseUrl: string, query: string): Promise<ExtractResponse> {
  return request<ExtractResponse>(baseUrl, "/extract", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export async function assemble(
  baseUrl: string,
  query: string,
  fields: Record<Role, FieldValueInput>,
): Promise<AssembleResponse> {
  return request<AssembleResponse>(baseUrl, "/assemble", {
    method: "POST",
    body: JSON.stringify({ query, fields }),
  });
}

export async function tooltip(baseUrl: string, masterPrompt: string): Promise<TooltipResponse> {
  return request<TooltipResponse>(baseUrl, "/tooltip", {
    method: "POST",
    body: JSON.stringify({ master_prompt: masterPrompt }),
  });
}

export async function logEntry(
  baseUrl: string,
  entry: Record<string, unknown>,
): Promise<LogResponse> {
  return request<LogResponse>(baseUrl, "/log", {
    method: "POST",
    body: JSON.stringify({ entry }),
  });
}
