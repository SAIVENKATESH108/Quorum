import { ReportStatus } from "@/stores/agentEventsStore";

// --- Types matching Prompt C2 Pydantic Schemas ---

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

// --- Mode Configuration ---

export function isMockApiMode(): boolean {
  if (typeof window !== "undefined") {
    const override = localStorage.getItem("quorum-use-mock-api");
    if (override !== null) return override === "true";
  }
  return process.env.NEXT_PUBLIC_USE_MOCK_API === "true";
}

export function setMockApiMode(enabled: boolean): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("quorum-use-mock-api", enabled ? "true" : "false");
  }
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

// --- Realistic In-Memory Mock Database (for offline / dev / demo) ---

const mockProjects: ProjectResponse[] = [
  {
    id: "proj-1",
    user_id: "user-default",
    title: "Fault-Tolerant Consensus Mechanisms",
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
  },
  {
    id: "proj-2",
    user_id: "user-default",
    title: "Autonomous Agent Swarms & Coordination",
    created_at: new Date(Date.now() - 3600000 * 48).toISOString(),
  },
  {
    id: "proj-3",
    user_id: "user-default",
    title: "Post-Quantum Cryptographic Protocols",
    created_at: new Date(Date.now() - 3600000 * 72).toISOString(),
  },
];

const mockReports: Record<string, ReportDetailResponse> = {
  "rep-1": {
    id: "rep-1",
    project_id: "proj-1",
    status: "researching",
    query: "Fault-Tolerant Consensus in Asynchronous Networks",
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    completed_at: null,
    sections: [
      {
        id: "sec-1",
        heading: "1. Executive Summary & Problem Formulation",
        content:
          "In asynchronous distributed systems, consensus cannot be guaranteed in the presence of unannounced fail-stop faults without partial synchrony assumptions or randomized consensus protocols (FLP Impossibility Result).",
        order_index: 1,
      },
      {
        id: "sec-2",
        heading: "2. Byzantine Fault Tolerance Bounds",
        content:
          "Standard BFT protocols require 3f + 1 replicas to tolerate f Byzantine participants. Recent advances in DAG-based consensus (e.g., Bullshark, Narwhal) decouple transaction dissemination from ordering.",
        order_index: 2,
      },
    ],
    sources: [
      {
        id: "src-1",
        url: "https://dl.acm.org/doi/10.1145/3149.214121",
        title: "Impossibility of Distributed Consensus with One Faulty Process (Fischer, Lynch, Paterson)",
      },
      {
        id: "src-2",
        url: "https://arxiv.org/abs/2201.05677",
        title: "Bullshark: DAG BFT Protocols with Low Latency",
      },
    ],
  },
  "rep-2": {
    id: "rep-2",
    project_id: "proj-1",
    status: "complete",
    query: "Optimistic Rollups vs ZK Rollups Performance Benchmark",
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    completed_at: new Date(Date.now() - 3600000 * 4).toISOString(),
    sections: [
      {
        id: "sec-3",
        heading: "1. Comparative Proof Generation Latency",
        content:
          "ZK-SNARK proofs provide cryptographic finality in under 2 minutes using GPU provers, while Optimistic Rollups rely on a 7-day fraud-proof dispute window for trustless withdrawals.",
        order_index: 1,
      },
    ],
    sources: [
      {
        id: "src-3",
        url: "https://vitalik.eth.limo/general/2021/01/05/rollup.html",
        title: "An Incomplete Guide to Rollups (Vitalik Buterin)",
      },
    ],
  },
};

// --- HTTP Fetch Helper with Error Serialization ---

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  let authHeader = "";
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("quorum-auth-token") || "mock_token";
    authHeader = `Bearer ${token}`;
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

    // If backend connection fails (e.g. backend down during early UI development), fall through to mock
    if (
      err instanceof TypeError &&
      (err.message.includes("fetch") || err.message.includes("Failed to fetch"))
    ) {
      console.warn(`[API Client] Connection to ${url} unreachable. Falling back to local mock API.`);
      return handleMockFallback<T>(path, options);
    }

    throw new ApiError(500, "network_error", (err as Error).message || "Network request failed");
  }
}

// --- Mock Fallback Handler ---

function handleMockFallback<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();

  // POST /api/projects
  if (path === "/api/projects" && method === "POST") {
    const body: ProjectCreate = JSON.parse((options.body as string) || "{}");
    const newProj: ProjectResponse = {
      id: `proj-${Date.now()}`,
      user_id: "user-default",
      title: body.title || "Untitled Project",
      created_at: new Date().toISOString(),
    };
    mockProjects.unshift(newProj);
    return Promise.resolve(newProj as T);
  }

  // GET /api/projects
  if (path === "/api/projects" && method === "GET") {
    return Promise.resolve([...mockProjects] as T);
  }

  // POST /api/projects/{id}/reports
  const projectReportsMatch = path.match(/^\/api\/projects\/([^/]+)\/reports$/);
  if (projectReportsMatch) {
    const projectId = projectReportsMatch[1];
    if (method === "POST") {
      const body: ReportCreate = JSON.parse((options.body as string) || "{}");
      const reportId = `rep-${Date.now()}`;
      const newReport: ReportDetailResponse = {
        id: reportId,
        project_id: projectId,
        status: "pending",
        query: body.query || "Autonomous Investigation",
        created_at: new Date().toISOString(),
        completed_at: null,
        sections: [],
        sources: [],
      };
      mockReports[reportId] = newReport;

      const responsePayload: ReportCreateResponse = {
        id: reportId,
        report_id: reportId,
        status: "pending",
        query: newReport.query,
        created_at: newReport.created_at,
      };
      return Promise.resolve(responsePayload as T);
    }

    if (method === "GET") {
      const filtered = Object.values(mockReports).filter(
        (r) => r.project_id === projectId
      );
      return Promise.resolve(filtered as T);
    }
  }

  // GET /api/reports/{id}
  const reportDetailMatch = path.match(/^\/api\/reports\/([^/]+)$/);
  if (reportDetailMatch) {
    const reportId = reportDetailMatch[1];
    if (method === "GET") {
      const rep = mockReports[reportId];
      if (!rep) {
        throw new ApiError(404, "not_found", `Report ${reportId} not found`);
      }
      return Promise.resolve(rep as T);
    }

    if (method === "DELETE") {
      delete mockReports[reportId];
      return Promise.resolve({} as T);
    }
  }

  throw new ApiError(404, "not_found", `Mock path ${method} ${path} not found`);
}

// --- Exported API Client Methods ---

export const apiClient = {
  // Projects
  async getProjects(): Promise<ProjectResponse[]> {
    if (isMockApiMode()) return handleMockFallback<ProjectResponse[]>("/api/projects", { method: "GET" });
    return request<ProjectResponse[]>("/api/projects");
  },

  async createProject(data: ProjectCreate): Promise<ProjectResponse> {
    if (isMockApiMode())
      return handleMockFallback<ProjectResponse>("/api/projects", {
        method: "POST",
        body: JSON.stringify(data),
      });
    return request<ProjectResponse>("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Project Reports
  async getProjectReports(projectId: string): Promise<ReportSummaryResponse[]> {
    const path = `/api/projects/${projectId}/reports`;
    if (isMockApiMode()) return handleMockFallback<ReportSummaryResponse[]>(path, { method: "GET" });
    return request<ReportSummaryResponse[]>(path);
  },

  async createReport(projectId: string, data: ReportCreate): Promise<ReportCreateResponse> {
    const path = `/api/projects/${projectId}/reports`;
    if (isMockApiMode())
      return handleMockFallback<ReportCreateResponse>(path, {
        method: "POST",
        body: JSON.stringify(data),
      });
    return request<ReportCreateResponse>(path, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Reports
  async getReport(reportId: string): Promise<ReportDetailResponse> {
    const path = `/api/reports/${reportId}`;
    if (isMockApiMode()) return handleMockFallback<ReportDetailResponse>(path, { method: "GET" });
    return request<ReportDetailResponse>(path);
  },

  async deleteReport(reportId: string): Promise<void> {
    const path = `/api/reports/${reportId}`;
    if (isMockApiMode()) return handleMockFallback<void>(path, { method: "DELETE" });
    return request<void>(path, { method: "DELETE" });
  },
};
