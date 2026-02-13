import { getSession } from "next-auth/react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function getAuthHeaders(): Promise<HeadersInit> {
  const session = await getSession();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (session?.accessToken) {
    headers["Authorization"] = `Bearer ${session.accessToken}`;
  }
  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    // Handle 401 — redirect to login with return URL
    if (response.status === 401 && typeof window !== "undefined") {
      const currentPath = window.location.pathname;
      window.location.href = `/login?callbackUrl=${encodeURIComponent(currentPath)}`;
      return undefined as T;
    }

    let detail = "An error occurred";
    try {
      const body = await response.json();
      detail = body.detail || body.error || detail;
    } catch {
      // response may not be JSON
    }
    throw new ApiError(response.status, detail);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const apiClient = {
  async get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
    const url = new URL(`${API_BASE_URL}${path}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      });
    }
    const headers = await getAuthHeaders();
    const response = await fetch(url.toString(), { headers });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async patch<T>(path: string, body: unknown): Promise<T> {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "PATCH",
      headers,
      body: JSON.stringify(body),
    });
    return handleResponse<T>(response);
  },

  async del(path: string): Promise<void> {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "DELETE",
      headers,
    });
    return handleResponse<void>(response);
  },
};
