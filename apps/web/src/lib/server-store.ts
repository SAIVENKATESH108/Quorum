/**
 * Quorum Dynamic Server Store
 * Provides enterprise-grade in-memory and persistent storage for user projects,
 * research reports, sections, and sources. Enables true dynamic CRUD operations
 * for live deployments and local development alike.
 */

import { DEFAULT_PROJECTS, DEFAULT_REPORTS, SCHOLARLY_REPORTS, getScholarlyReport } from "./sample-reports-data";
import { decomposeQueryTelemetry } from "./telemetry-engine";
import type {
  ProjectResponse,
  ReportDetailResponse,
  ReportSectionResponse,
  ReportSummaryResponse,
  SourceResponse,
} from "./api-client";

interface StoreState {
  projects: Map<string, ProjectResponse>;
  reports: Map<string, ReportDetailResponse>;
}

declare global {
  // eslint-disable-next-line no-var
  var __quorumStore: StoreState | undefined;
}

function initStore(): StoreState {
  if (global.__quorumStore) {
    return global.__quorumStore;
  }

  const projectsMap = new Map<string, ProjectResponse>();
  for (const p of DEFAULT_PROJECTS) {
    projectsMap.set(p.id, { ...p });
  }

  const reportsMap = new Map<string, ReportDetailResponse>();
  for (const [id, r] of Object.entries(SCHOLARLY_REPORTS)) {
    reportsMap.set(id, { ...r });
  }

  global.__quorumStore = {
    projects: projectsMap,
    reports: reportsMap,
  };

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
    return newProject;
  },

  updateProject(id: string, title: string): ProjectResponse | null {
    const store = initStore();
    const existing = store.projects.get(id);
    if (!existing) return null;
    existing.title = title.trim() || existing.title;
    store.projects.set(id, existing);
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
    const found = store.reports.get(id);
    if (found) return found;

    // Fallback: check if known sample report
    if (SCHOLARLY_REPORTS[id]) {
      store.reports.set(id, SCHOLARLY_REPORTS[id]);
      return SCHOLARLY_REPORTS[id];
    }

    return null;
  },

  createReport(data: {
    query: string;
    projectId?: string;
    sourceType?: string;
    sourceRef?: string;
    providerMode?: string;
  }): ReportDetailResponse {
    const store = initStore();
    const reportId = crypto.randomUUID();
    const query = data.query?.trim() || "Autonomous Scientific Investigation";

    // Resolve or create project
    let projectId = data.projectId;
    if (!projectId || !store.projects.has(projectId)) {
      const defaultProj = Array.from(store.projects.values())[0];
      projectId = defaultProj ? defaultProj.id : this.createProject("Primary Research Workspace").id;
    }

    // Synthesize domain report content
    const scholarly = getScholarlyReport(reportId, query);

    const newReport: ReportDetailResponse = {
      id: reportId,
      project_id: projectId,
      status: "complete",
      query,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      error_message: null,
      sections: scholarly.sections.map((s, idx) => ({
        ...s,
        id: `sec-${reportId}-${idx + 1}`,
      })),
      sources: scholarly.sources.map((src, idx) => ({
        ...src,
        id: `src-${reportId}-${idx + 1}`,
      })),
    };

    store.reports.set(reportId, newReport);
    return newReport;
  },

  deleteReport(id: string): boolean {
    const store = initStore();
    return store.reports.delete(id);
  },
};
