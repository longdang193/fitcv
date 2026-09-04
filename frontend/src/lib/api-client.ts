/**
 * FitCV API Client
 * Same-origin credentials, CSRF protection, standard error envelopes, CAS/ETag support,
 * safe text previews and file downloads.
 */

export interface FieldError {
  field: string;
  code: string;
  message: string;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: unknown;
    field_errors?: FieldError[];
    action?: string;
    retryable?: boolean;
  };
}

export class ApiClientError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly action?: string;
  public readonly fieldErrors?: FieldError[];
  public readonly details?: unknown;
  public readonly retryable?: boolean;

  constructor(
    status: number,
    code: string,
    message: string,
    action?: string,
    fieldErrors?: FieldError[],
    details?: unknown,
    retryable?: boolean
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.action = action;
    this.fieldErrors = fieldErrors;
    this.details = details;
    this.retryable = retryable ?? (
      details && typeof details === "object" && "retryable" in details && typeof (details as { retryable?: unknown }).retryable === "boolean"
        ? (details as { retryable: boolean }).retryable
        : undefined
    );
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  idempotencyKey?: string;
  ifMatch?: string;
  ifNoneMatch?: string;
  headers?: Record<string, string>;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  etag?: string | null;
}

export function getCsrfToken(): string {
  if (typeof document === "undefined") {
    return "";
  }
  const match = document.cookie.match(/(?:^|;\s*)fitcv_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  const etag = response.headers.get("ETag");

  if (!response.ok) {
    let errorCode = `http_${response.status}`;
    let errorMessage = response.statusText || `Request failed with status ${response.status}`;
    let action: string | undefined;
    let fieldErrors: FieldError[] | undefined;
    let details: unknown;
    let retryable: boolean | undefined;

    try {
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const payload = (await response.json()) as ApiErrorPayload | { detail?: unknown };
        if ("error" in payload && payload.error) {
          errorCode = payload.error.code || errorCode;
          errorMessage = payload.error.message || errorMessage;
          action = payload.error.action;
          fieldErrors = payload.error.field_errors;
          details = payload.error.details;
          retryable = payload.error.retryable;
        } else if ("detail" in payload) {
          errorMessage = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
        }
      } else {
        const text = await response.text();
        if (text) {
          errorMessage = text;
        }
      }
    } catch {
      // Body parse failure; retain statusText
    }

    throw new ApiClientError(response.status, errorCode, errorMessage, action, fieldErrors, details, retryable);
  }

  // 204 No Content
  if (response.status === 204) {
    return { data: null as unknown as T, status: response.status, etag };
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const data = (await response.json()) as T;
    return { data, status: response.status, etag };
  }

  const textData = (await response.text()) as unknown as T;
  return { data: textData, status: response.status, etag };
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  const { body, idempotencyKey, ifMatch, ifNoneMatch, headers = {}, ...rest } = options;

  const csrf = getCsrfToken();
  const reqHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };

  if (csrf) {
    reqHeaders["X-FitCV-CSRF"] = csrf;
  }
  if (idempotencyKey) {
    reqHeaders["Idempotency-Key"] = idempotencyKey;
  }
  if (ifMatch) {
    reqHeaders["If-Match"] = ifMatch;
  }
  if (ifNoneMatch) {
    reqHeaders["If-None-Match"] = ifNoneMatch;
  }

  let finalBody: BodyInit | undefined;
  if (body !== undefined) {
    if (typeof body === "string" || body instanceof FormData || body instanceof Blob) {
      finalBody = body as BodyInit;
    } else {
      reqHeaders["Content-Type"] = "application/json";
      finalBody = JSON.stringify(body);
    }
  }

  const fetchOptions: RequestInit = {
    ...rest,
    credentials: "same-origin",
    headers: reqHeaders,
    body: finalBody,
  };

  const response = await fetch(path, fetchOptions);
  return handleResponse<T>(response);
}

export const apiClient = {
  get<T = unknown>(path: string, options?: RequestOptions): Promise<ApiResponse<T>> {
    return apiRequest<T>(path, { ...options, method: "GET" });
  },

  post<T = unknown>(path: string, body?: unknown, options?: RequestOptions): Promise<ApiResponse<T>> {
    return apiRequest<T>(path, { ...options, method: "POST", body });
  },

  put<T = unknown>(path: string, body?: unknown, options?: RequestOptions): Promise<ApiResponse<T>> {
    return apiRequest<T>(path, { ...options, method: "PUT", body });
  },

  patch<T = unknown>(path: string, body?: unknown, options?: RequestOptions): Promise<ApiResponse<T>> {
    return apiRequest<T>(path, { ...options, method: "PATCH", body });
  },

  delete<T = unknown>(path: string, options?: RequestOptions): Promise<ApiResponse<T>> {
    return apiRequest<T>(path, { ...options, method: "DELETE" });
  },

  async previewText(path: string): Promise<string> {
    const csrf = getCsrfToken();
    const headers: Record<string, string> = {
      Accept: "text/plain, text/markdown, */*",
    };
    if (csrf) {
      headers["X-FitCV-CSRF"] = csrf;
    }
    const res = await fetch(path, {
      method: "GET",
      credentials: "same-origin",
      headers,
    });
    if (!res.ok) {
      throw new ApiClientError(res.status, `preview_failed`, `Failed to preview text content: ${res.statusText}`);
    }
    return res.text();
  },

  async download(path: string, fallbackFilename?: string): Promise<void> {
    const csrf = getCsrfToken();
    const headers: Record<string, string> = {};
    if (csrf) {
      headers["X-FitCV-CSRF"] = csrf;
    }
    const res = await fetch(path, {
      method: "GET",
      credentials: "same-origin",
      headers,
    });
    if (!res.ok) {
      throw new ApiClientError(res.status, `download_failed`, `Failed to download file: ${res.statusText}`);
    }

    const blob = await res.blob();
    let filename = fallbackFilename || "download";
    const disposition = res.headers.get("content-disposition");
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (match && match[1]) {
        filename = match[1].replace(/['"]/g, "");
      }
    }

    if (typeof window !== "undefined" && typeof document !== "undefined") {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }, 100);
    }
  },
};
