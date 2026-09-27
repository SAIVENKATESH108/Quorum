/**
 * Quorum Development-Only Fixture Store
 *
 * Strictly gated behind QUORUM_ALLOW_IN_MEMORY_STORE=true.
 * In production or preview environments, this store is disabled to guarantee
 * that all persistence and authorization occurs exclusively in the durable
 * FastAPI + PostgreSQL backend.
 */

import fs from "fs";
import path from "path";
import { isDevelopmentFixtureAllowed } from "./backend-proxy";
import type {
  ProjectResponse,
  ReportDetailResponse,
  ReportSummaryResponse,
} from "./api-client";

function assertFixtureAllowed(): void {
  if (!isDevelopmentFixtureAllowed()) {
    throw new Error(
      "serverStore is strictly disabled in production. Set QUORUM_ALLOW_IN_MEMORY_STORE=true for local dev fixtures only."
    );
  }
}

interface StoreState {
  projects: Map<string, ProjectResponse>;
  reports: Map<string, ReportDetailResponse>;
}

declare global {
  // eslint-disable-next-line no-var
  var __quorumStore: StoreState | undefined;
}

function getStorageFilePath(): string {
  if (process.env.QUORUM_DATA_FILE) {
    return process.env.QUORUM_DATA_FILE;
  }
  return path.join(process.cwd(), ".quorum-data.json");
}

function saveStore(store: StoreState): void {
  try {
    const filePath = getStorageFilePath();
    const data = {
      projects: Array.from(store.projects.values()),
      reports: Array.from(store.reports.values()),
    };
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
  } catch {
    // Non-fatal if filesystem is read-only
  }
}

function initStore(): StoreState {
  assertFixtureAllowed();
  if (!global.__quorumStore) {
    const projects = new Map<string, ProjectResponse>();
    const reports = new Map<string, ReportDetailResponse>();

    try {
      const filePath = getStorageFilePath();
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, "utf-8");
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed.projects)) {
          parsed.projects.forEach((p: ProjectResponse) => projects.set(p.id, p));
        }
        if (Array.isArray(parsed.reports)) {
          parsed.reports.forEach((r: ReportDetailResponse) => reports.set(r.id, r));
        }
      }
    } catch {
      // Ignore file reading errors in ephemeral dev environments
    }

    global.__quorumStore = {
      projects,
      reports,
    };
  }
  return global.__quorumStore;
}

export const serverStore = {
  // --- Projects CRUD ---
  async getProjects(): Promise<ProjectResponse[]> {
    assertFixtureAllowed();
    const store = initStore();
    return Array.from(store.projects.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  },

  async getProject(id: string): Promise<ProjectResponse | null> {
    assertFixtureAllowed();
    const store = initStore();
    return store.projects.get(id) || null;
  },

  async createProject(
    title: string,
    userId?: string
  ): Promise<ProjectResponse> {
    assertFixtureAllowed();
    if (!userId) {
      throw new Error("Cannot create project without authenticated user ownership.");
    }
    const newId = crypto.randomUUID();
    const cleanTitle = title.trim() || "Untitled Research Domain";
    const store = initStore();
    const project: ProjectResponse = {
      id: newId,
      user_id: userId,
      title: cleanTitle,
      created_at: new Date().toISOString(),
    };
    store.projects.set(project.id, project);
    saveStore(store);
    return project;
  },

  async updateProject(id: string, title: string): Promise<ProjectResponse | null> {
    assertFixtureAllowed();
    const cleanTitle = title.trim();
    const store = initStore();
    const existing = store.projects.get(id);
    if (!existing) return null;
    existing.title = cleanTitle || existing.title;
    store.projects.set(id, existing);
    saveStore(store);
    return existing;
  },

  async deleteProject(id: string): Promise<boolean> {
    assertFixtureAllowed();
    const store = initStore();
    const existed = store.projects.delete(id);
    if (existed) {
      Array.from(store.reports.entries()).forEach(([reportId, report]) => {
        if (report.project_id === id) {
          store.reports.delete(reportId);
        }
      });
      saveStore(store);
    }
    return existed;
  },

  // --- Reports CRUD ---
  async getReports(projectId?: string): Promise<ReportSummaryResponse[]> {
    assertFixtureAllowed();
    const store = initStore();
    const all = Array.from(store.reports.values()).map((r) => ({
      id: r.id,
      project_id: r.project_id,
      status: r.status,
      query: r.query,
      created_at: r.created_at,
      completed_at: r.completed_at,
      error_message: r.error_message,
      source_type: r.source_type,
      provider_mode: r.provider_mode,
    }));

    if (projectId) {
      return all
        .filter((r) => r.project_id === projectId)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }

    return all.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  },

  async getReport(id: string): Promise<ReportDetailResponse | null> {
    assertFixtureAllowed();
    const store = initStore();
    return store.reports.get(id) || null;
  },

  async createReport(data: {
    query: string;
    projectId?: string;
    sourceType?: string;
    sourceRef?: string;
    providerMode?: string;
  }): Promise<ReportDetailResponse | null> {
    assertFixtureAllowed();
    if (!data.projectId) return null;
    const store = initStore();
    if (!store.projects.has(data.projectId)) return null;

    const reportId = crypto.randomUUID();
    const query = data.query?.trim() || "Untitled Research Query";
    const report: ReportDetailResponse = {
      id: reportId,
      project_id: data.projectId,
      status: "pending",
      query,
      created_at: new Date().toISOString(),
      completed_at: null,
      error_message: null,
      source_type: data.sourceType || "query",
      provider_mode: data.providerMode || "cloud",
      sections: [],
      sources: [],
    };
    store.reports.set(report.id, report);
    saveStore(store);
    return report;
  },

  async updateReportStatus(
    id: string,
    status: ReportDetailResponse["status"],
    errorMessage?: string
  ): Promise<ReportDetailResponse | null> {
    assertFixtureAllowed();
    const store = initStore();
    const existing = store.reports.get(id);
    if (!existing) return null;
    existing.status = status;
    if (errorMessage !== undefined) {
      existing.error_message = errorMessage;
    }
    if (status === "complete" || status === "failed") {
      existing.completed_at = new Date().toISOString();
    }
    store.reports.set(id, existing);
    saveStore(store);
    return existing;
  },

  async deleteReport(id: string): Promise<boolean> {
    assertFixtureAllowed();
    const store = initStore();
    const existed = store.reports.delete(id);
    if (existed) {
      saveStore(store);
    }
    return existed;
  },

  async getSourceCount(projectId?: string): Promise<number> {
    assertFixtureAllowed();
    const store = initStore();
    let count = 0;
    for (const r of Array.from(store.reports.values())) {
      if (!projectId || r.project_id === projectId) {
        count += r.sources?.length || 0;
      }
    }
    return count;
  },

};
