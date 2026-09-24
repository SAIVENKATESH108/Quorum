/**
 * Quorum Dynamic Server Store
 * In-memory storage backing the Next.js route handlers so project/report CRUD keeps
 * working when the FastAPI backend is not directly reachable from the edge runtime.
 *
 * The store starts empty and only ever contains records created by the user
 * through the API. No demo/seed data is injected, so deleted records stay deleted.
 */

import fs from "fs";
import path from "path";

import type {
  ProjectResponse,
  ReportDetailResponse,
  ReportSummaryResponse,
} from "./api-client";

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
  } catch (err) {
    // Non-fatal if filesystem is read-only
    console.warn("[Quorum Store] Warning: Failed to persist store to disk:", err);
  }
}

function initStore(): StoreState {
  if (!global.__quorumStore) {
    const projects = new Map<string, ProjectResponse>();
    const reports = new Map<string, ReportDetailResponse>();

    try {
      const filePath = getStorageFilePath();
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, "utf-8");
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed.projects)) {
          for (const p of parsed.projects) {
            if (p && p.id) projects.set(p.id, p);
          }
        }
        if (Array.isArray(parsed.reports)) {
          for (const r of parsed.reports) {
            if (r && r.id) reports.set(r.id, r);
          }
        }
      }
    } catch (err) {
      console.warn("[Quorum Store] Warning: Failed to read persisted store from disk:", err);
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
  getProjects(): ProjectResponse[] {
    const store = initStore();
    return Array.from(store.projects.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  },

  getProject(id: string): ProjectResponse | null {
    const store = initStore();
    return store.projects.get(id) || null;
  },

  createProject(title: string, userId = "user-primary"): ProjectResponse {
    const store = initStore();
    const newProject: ProjectResponse = {
      id: crypto.randomUUID(),
      user_id: userId,
      title: title.trim() || "Untitled Research Domain",
      created_at: new Date().toISOString(),
    };
    store.projects.set(newProject.id, newProject);
    saveStore(store);
    return newProject;
  },

  updateProject(id: string, title: string): ProjectResponse | null {
    const store = initStore();
    const existing = store.projects.get(id);
    if (!existing) return null;
    existing.title = title.trim() || existing.title;
    store.projects.set(id, existing);
    saveStore(store);
    return existing;
  },

  deleteProject(id: string): boolean {
    const store = initStore();
    const existed = store.projects.delete(id);
    if (existed) {
      // Cascade delete reports in this project
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
  getReports(projectId?: string): ReportSummaryResponse[] {
    const store = initStore();
    const all = Array.from(store.reports.values()).map((r) => ({
      id: r.id,
      project_id: r.project_id,
      status: r.status,
      query: r.query,
      created_at: r.created_at,
      completed_at: r.completed_at,
      error_message: r.error_message,
    }));

    if (projectId) {
      return all
        .filter((r) => r.project_id === projectId)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }

    return all.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  },

  getReport(id: string): ReportDetailResponse | null {
    const store = initStore();
    return store.reports.get(id) || null;
  },

  /**
   * Registers a report for an existing project. The record starts in the
   * `pending` state with no synthesized content: sections and citations are only
   * ever produced by the multi-agent pipeline (FastAPI backend).
   *
   * Returns `null` when the target project does not exist so callers can respond
   * with an honest 404 instead of inventing a project/report.
   */
  createReport(data: {
    query: string;
    projectId?: string;
    sourceType?: string;
    sourceRef?: string;
    providerMode?: string;
  }): ReportDetailResponse | null {
    const store = initStore();
    if (!data.projectId || !store.projects.has(data.projectId)) {
      return null;
    }

    const reportId = crypto.randomUUID();
    const newReport: ReportDetailResponse = {
      id: reportId,
      project_id: data.projectId,
      status: "pending",
      query: data.query?.trim() || "Untitled Research Query",
      created_at: new Date().toISOString(),
      completed_at: null,
      error_message: null,
      sections: [],
      sources: [],
    };

    store.reports.set(reportId, newReport);
    saveStore(store);
    return newReport;
  },

  deleteReport(id: string): boolean {
    const store = initStore();
    const existed = store.reports.delete(id);
    if (existed) {
      saveStore(store);
    }
    return existed;
  },
};
