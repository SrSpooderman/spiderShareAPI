import { env } from "@/shared/config/env";
import { clearStoredToken, getStoredToken } from "@/modules/auth/authStorage";

type RequestOptions = RequestInit & {
  skipAuth?: boolean;
};

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail: unknown,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = options.skipAuth ? null : getStoredToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = await response.clone().json();
    } catch {
      detail = await response.text();
    }

    if (response.status === 401 || response.status === 403) {
      clearStoredToken();
    }
    throw new ApiRequestError(`Request failed with status ${response.status}`, response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
