export type { ReportStatus } from "@/stores/agentEventsStore";
import { ReportStatus } from "@/stores/agentEventsStore";

// --- Types matching Pydantic Schemas ---

export interface ProjectCreate {
  title: string;
}

export interface ProjectResponse {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
}

export interface ReportCreate {
  query: string;
}

export interface ReportCreateResponse {
  id: string;
  report_id: string;
  status: ReportStatus;
  query: string;
  created_at: string;
}

export interface ReportSectionResponse {
  id: string;
  heading: string;
  content: string;
  order_index: number;
}

export interface SourceResponse {
  id: string;
  url: string;
  title?: string;
}

export interface ReportSummaryResponse {
  id: string;
  project_id: string;
  status: ReportStatus;
  query: string;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
}

export interface ReportDetailResponse extends ReportSummaryResponse {
  sections: ReportSectionResponse[];
  sources: SourceResponse[];
}

// --- Typed API Error ---

export class ApiError extends Error {
  status: number;
  error: string;
  detail: string;

  constructor(status: number, error: string, detail: string) {
    super(detail || error || `API error (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.error = error;
    this.detail = detail;
  }
}

export function isValidUuid(val: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(val);
}

// --- Mode Configuration ---
// Mock API mode is disabled to prevent data loss across page refreshes
export function isMockApiMode(): boolean {
  return false;
}

export function setMockApiMode(..._args: unknown[]): void {
  void _args;
  if (typeof window !== "undefined") {
    localStorage.removeItem("quorum-use-mock-api");
  }
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

// --- Auth Token Retrieval Helper ---

type TokenGetter = () => Promise<string | null>;
let customTokenGetter: TokenGetter | null = null;

export function setAuthTokenGetter(getter: TokenGetter) {
  customTokenGetter = getter;
}

export async function getAuthToken(): Promise<string | null> {
  if (customTokenGetter) {
    try {
      const t = await customTokenGetter();
      if (t) return t;
    } catch {
      // fallback
    }
  }

  if (typeof window !== "undefined") {
    // 1. Try Clerk session token if available on window
    try {
      const win = window as unknown as {
        Clerk?: {
          loaded?: boolean;
          load?: () => Promise<void>;
          session?: { getToken: () => Promise<string | null> };
        };
      };
      if (win.Clerk?.session) {
        const clerkToken = await win.Clerk.session.getToken();
        if (clerkToken) return clerkToken;
      }
    } catch {
      // ignore
    }

    // 2. Try localStorage token
    const localToken = localStorage.getItem("quorum-auth-token");
    if (localToken) return localToken;
  }

  return null;
}

// --- HTTP Fetch Helper with Error Serialization ---

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  let authHeader = "";
  if (typeof window !== "undefined") {
    const token = await getAuthToken();
    if (token) {
      authHeader = `Bearer ${token}`;
    }
  }

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(authHeader ? { Authorization: authHeader } : {}),
    ...options.headers,
  };

  try {
    const res = await fetch(url, { ...options, headers });

    if (!res.ok) {
      let errPayload = { error: "request_failed", detail: res.statusText };
      try {
        errPayload = await res.json();
      } catch {
        // use default
      }
      throw new ApiError(res.status, errPayload.error, errPayload.detail);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return await res.json();
  } catch (err: unknown) {
    if (err instanceof ApiError) throw err;

    throw new ApiError(
      503,
      "network_error",
      (err as Error).message || "Network request failed. Please ensure the backend is running."
    );
  }
}

// --- Exported API Client Methods ---

export const apiClient = {
  // Projects
  async getProjects(): Promise<ProjectResponse[]> {
    return request<ProjectResponse[]>("/api/projects");
  },

  async createProject(data: ProjectCreate): Promise<ProjectResponse> {
    return request<ProjectResponse>("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Project Reports
  async getProjectReports(projectId: string): Promise<ReportSummaryResponse[]> {
    const path = `/api/projects/${projectId}/reports`;
    return request<ReportSummaryResponse[]>(path);
  },

  async createReport(projectId: string, data: ReportCreate): Promise<ReportCreateResponse> {
    const path = `/api/projects/${projectId}/reports`;
    return request<ReportCreateResponse>(path, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Reports
  async getReport(reportId: string): Promise<ReportDetailResponse> {
    const path = `/api/reports/${reportId}`;
    return request<ReportDetailResponse>(path);
  },

  async deleteReport(reportId: string): Promise<void> {
    const path = `/api/reports/${reportId}`;
    return request<void>(path, { method: "DELETE" });
  },

  // Generic helper
  async get<T>(path: string): Promise<T> {
    return request<T>(path);
  },

  // Chat & Evidence
  async chatWithReport(
    reportId: string,
    message: string
  ): Promise<{ reply: string; citations: { index: number; title: string; url: string }[] }> {
    const path = `/api/reports/${reportId}/chat`;
    return request(path, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  },

  async getSources(params?: { q?: string; category?: string }): Promise<any[]> {
    const searchParams = new URLSearchParams();
    if (params?.q) searchParams.set("q", params.q);
    if (params?.category) searchParams.set("category", params.category);
    const qs = searchParams.toString();
    const path = `/api/sources${qs ? `?${qs}` : ""}`;
    return request<any[]>(path);
  },

  completeMockReport(..._args: unknown[]): void {
    void _args;
    // No-op for real live mode
  },
};


