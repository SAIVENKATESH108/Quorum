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
  source_type?: string;
  source_ref?: string;
  provider_mode?: string;
  file_tree?: any;
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
  source_type?: string;
  source_ref?: string;
  provider_mode?: string;
}

export interface ReportDetailResponse extends ReportSummaryResponse {
  sections: ReportSectionResponse[];
  sources: SourceResponse[];
}

export interface HarvestedSourceItem {
  id: string;
  url: string;
  title: string;
  domain: string;
  category: string;
  report_id?: string | null;
  report_title?: string | null;
  citation_count?: number;
  verified?: boolean;
  confidence?: number;
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

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

// Detect if frontend is hosted on HTTPS while backend is configured as localhost (Mixed Content / CORS barrier)
export function isLocalhostBlocked(): boolean {
  if (typeof window === "undefined") return false;
  const isHttps = window.location.protocol === "https:";
  const isBackendLocalhost =
    API_BASE_URL.includes("localhost") || API_BASE_URL.includes("127.0.0.1");
  return isHttps && isBackendLocalhost;
}

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
    // Legacy local token support for local development only.
    const localToken = localStorage.getItem("quorum-auth-token");
    if (localToken) return localToken;
  }

  return null;
}

// --- HTTP Fetch Helper with Error Serialization ---

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
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

  // 1. Use same-origin proxies first so the HTTP-only session cookie is forwarded.
  if (typeof window !== "undefined" && path.startsWith("/api/")) {
    try {
      const res = await fetch(path, { ...options, headers });
      if (res.ok) {
        if (res.status === 204) return {} as T;
        return await res.json();
      }
    } catch {
      // Try the direct backend below for local development.
    }
  }

  // 2. Direct backend access remains useful for local development.
  if (!isLocalhostBlocked()) {
    try {
      const url = `${API_BASE_URL}${path}`;
      const res = await fetch(url, { ...options, headers });
      if (res.ok) {
        if (res.status === 204) return {} as T;
        return await res.json();
      }
    } catch {
      // Fall through to error
    }
  }

  throw new ApiError(
    503,
    "service_unavailable",
    "The Quorum API is temporarily unreachable. Please retry in a moment."
  );
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

  async updateProject(projectId: string, title: string): Promise<ProjectResponse> {
    return request<ProjectResponse>(`/api/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
  },

  async deleteProject(projectId: string): Promise<void> {
    await request<void>(`/api/projects/${projectId}`, { method: "DELETE" });
  },

  // Project Reports
  async getProjectReports(projectId: string): Promise<ReportSummaryResponse[]> {
    return request<ReportSummaryResponse[]>(`/api/projects/${projectId}/reports`);
  },

  async getAllReports(): Promise<ReportSummaryResponse[]> {
    return request<ReportSummaryResponse[]>("/api/reports");
  },

  async createReport(projectId: string, data: ReportCreate): Promise<ReportCreateResponse> {
    // Pipeline creation is always server-authoritative: if the API cannot
    // schedule the agent swarm we surface the failure instead of registering a
    // placeholder report.
    return request<ReportCreateResponse>(`/api/projects/${projectId}/reports`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Reports
  async getReport(reportId: string): Promise<ReportDetailResponse> {
    return request<ReportDetailResponse>(`/api/reports/${reportId}`);
  },

  async deleteReport(reportId: string): Promise<void> {
    await request<void>(`/api/reports/${reportId}`, { method: "DELETE" });
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
    try {
      return await request(`/api/reports/${reportId}/chat`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
    } catch {
      return {
        reply:
          "The Quorum research assistant is temporarily unavailable. The verified report sections and cited sources above remain the authoritative source.",
        citations: [],
      };
    }
  },

  async getSources(params?: { q?: string; category?: string }): Promise<HarvestedSourceItem[]> {
    try {
      const searchParams = new URLSearchParams();
      if (params?.q) searchParams.set("q", params.q);
      if (params?.category) searchParams.set("category", params.category);
      const qs = searchParams.toString();
      return await request<HarvestedSourceItem[]>(`/api/sources${qs ? `?${qs}` : ""}`);
    } catch {
      // Evidence is always API-backed. An empty library is reported honestly
      // instead of substituting invented citations.
      return [];
    }
  },

};
