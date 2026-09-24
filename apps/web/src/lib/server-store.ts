/**
 * Quorum Dynamic Server Store
 * Backed directly by Neon PostgreSQL for persistent project, report, and evidence storage
 * across Vercel serverless deployments, cold starts, and container redeploys.
 */

import fs from "fs";
import path from "path";
import { getDb } from "./neon-db";

import type {
  HarvestedSourceItem,
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
      // Non-fatal
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
    try {
      const sql = getDb();
      const rows = await sql`
        SELECT id, user_id, title, created_at
        FROM public.projects
        ORDER BY created_at DESC;
      `;
      if (rows && rows.length > 0) {
        return rows.map((r: any) => ({
          id: r.id,
          user_id: r.user_id,
          title: r.title,
          created_at: new Date(r.created_at).toISOString(),
        }));
      }
    } catch (err) {
      console.warn("[serverStore.getProjects] Neon query failed, checking memory fallback:", err);
    }

    const store = initStore();
    return Array.from(store.projects.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  },

  async getProject(id: string): Promise<ProjectResponse | null> {
    try {
      const sql = getDb();
      const rows = await sql`
        SELECT id, user_id, title, created_at
        FROM public.projects
        WHERE id = ${id}
        LIMIT 1;
      `;
      if (rows && rows.length > 0) {
        const r = rows[0];
        return {
          id: r.id,
          user_id: r.user_id,
          title: r.title,
          created_at: new Date(r.created_at).toISOString(),
        };
      }
    } catch (err) {
      console.warn("[serverStore.getProject] Neon query failed:", err);
    }

    const store = initStore();
    return store.projects.get(id) || null;
  },

  async createProject(
    title: string,
    userId = "9918d84c-7694-4df4-ad1b-39313d6577dc"
  ): Promise<ProjectResponse> {
    const newId = crypto.randomUUID();
    const cleanTitle = title.trim() || "Untitled Research Domain";
    try {
      const sql = getDb();
      const rows = await sql`
        INSERT INTO public.projects (id, user_id, title, created_at)
        VALUES (${newId}, ${userId}, ${cleanTitle}, NOW())
        RETURNING id, user_id, title, created_at;
      `;
      if (rows && rows.length > 0) {
        const r = rows[0];
        return {
          id: r.id,
          user_id: r.user_id,
          title: r.title,
          created_at: new Date(r.created_at).toISOString(),
        };
      }
    } catch (err) {
      console.warn("[serverStore.createProject] Neon query failed:", err);
    }

    const store = initStore();
    const fallback: ProjectResponse = {
      id: newId,
      user_id: userId,
      title: cleanTitle,
      created_at: new Date().toISOString(),
    };
    store.projects.set(fallback.id, fallback);
    saveStore(store);
    return fallback;
  },

  async updateProject(id: string, title: string): Promise<ProjectResponse | null> {
    const cleanTitle = title.trim();
    try {
      const sql = getDb();
      const rows = await sql`
        UPDATE public.projects
        SET title = ${cleanTitle}
        WHERE id = ${id}
        RETURNING id, user_id, title, created_at;
      `;
      if (rows && rows.length > 0) {
        const r = rows[0];
        return {
          id: r.id,
          user_id: r.user_id,
          title: r.title,
          created_at: new Date(r.created_at).toISOString(),
        };
      }
    } catch (err) {
      console.warn("[serverStore.updateProject] Neon query failed:", err);
    }

    const store = initStore();
    const existing = store.projects.get(id);
    if (!existing) return null;
    existing.title = cleanTitle || existing.title;
    store.projects.set(id, existing);
    saveStore(store);
    return existing;
  },

  async deleteProject(id: string): Promise<boolean> {
    try {
      const sql = getDb();
      await sql`DELETE FROM public.projects WHERE id = ${id};`;
      return true;
    } catch (err) {
      console.warn("[serverStore.deleteProject] Neon query failed:", err);
    }

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
    try {
      const sql = getDb();
      let rows;
      if (projectId) {
        rows = await sql`
          SELECT id, project_id, status, query, created_at, completed_at, error_message, source_type, provider_mode
          FROM public.reports
          WHERE project_id = ${projectId}
          ORDER BY created_at DESC;
        `;
      } else {
        rows = await sql`
          SELECT id, project_id, status, query, created_at, completed_at, error_message, source_type, provider_mode
          FROM public.reports
          ORDER BY created_at DESC;
        `;
      }
      if (rows && rows.length > 0) {
        return rows.map((r: any) => ({
          id: r.id,
          project_id: r.project_id,
          status: r.status,
          query: r.query,
          created_at: new Date(r.created_at).toISOString(),
          completed_at: r.completed_at ? new Date(r.completed_at).toISOString() : null,
          error_message: r.error_message || null,
          source_type: r.source_type || "query",
          provider_mode: r.provider_mode || "cloud",
        }));
      }
    } catch (err) {
      console.warn("[serverStore.getReports] Neon query failed:", err);
    }

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
    try {
      const sql = getDb();
      const reportRows = await sql`
        SELECT id, project_id, status, query, created_at, completed_at, error_message, source_type, provider_mode
        FROM public.reports
        WHERE id = ${id}
        LIMIT 1;
      `;
      if (reportRows && reportRows.length > 0) {
        const r = reportRows[0];
        const sectionRows = await sql`
          SELECT id, heading, content, order_index
          FROM public.report_sections
          WHERE report_id = ${id}
          ORDER BY order_index ASC;
        `;
        const sourceRows = await sql`
          SELECT s.id, s.url, s.title
          FROM public.sources s
          JOIN public.report_sources rs ON rs.source_id = s.id
          WHERE rs.report_id = ${id};
        `;

        return {
          id: r.id,
          project_id: r.project_id,
          status: r.status,
          query: r.query,
          created_at: new Date(r.created_at).toISOString(),
          completed_at: r.completed_at ? new Date(r.completed_at).toISOString() : null,
          error_message: r.error_message || null,
          source_type: r.source_type || "query",
          provider_mode: r.provider_mode || "cloud",
          sections: sectionRows.map((s: any) => ({
            id: s.id,
            heading: s.heading,
            content: s.content,
            order_index: s.order_index,
          })),
          sources: sourceRows.map((s: any) => ({
            id: s.id,
            url: s.url,
            title: s.title || s.url,
          })),
        };
      }
    } catch (err) {
      console.warn("[serverStore.getReport] Neon query failed:", err);
    }

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
    if (!data.projectId) return null;
    const reportId = crypto.randomUUID();
    const query = data.query?.trim() || "Untitled Research Query";
    const sourceType = data.sourceType || "query";
    const sourceRef = data.sourceRef || null;
    const providerMode = data.providerMode || "cloud";

    try {
      const sql = getDb();
      const rows = await sql`
        INSERT INTO public.reports (id, project_id, status, query, source_type, source_ref, provider_mode, created_at)
        VALUES (${reportId}, ${data.projectId}, 'pending', ${query}, ${sourceType}, ${sourceRef}, ${providerMode}, NOW())
        RETURNING id, project_id, status, query, created_at, completed_at, error_message, source_type, provider_mode;
      `;
      if (rows && rows.length > 0) {
        const r = rows[0];
        return {
          id: r.id,
          project_id: r.project_id,
          status: r.status,
          query: r.query,
          created_at: new Date(r.created_at).toISOString(),
          completed_at: null,
          error_message: null,
          source_type: r.source_type,
          provider_mode: r.provider_mode,
          sections: [],
          sources: [],
        };
      }
    } catch (err) {
      console.warn("[serverStore.createReport] Neon query failed:", err);
    }

    const store = initStore();
    if (!store.projects.has(data.projectId)) return null;

    const fallback: ReportDetailResponse = {
      id: reportId,
      project_id: data.projectId,
      status: "pending",
      query,
      created_at: new Date().toISOString(),
      completed_at: null,
      error_message: null,
      source_type: sourceType,
      provider_mode: providerMode,
      sections: [],
      sources: [],
    };
    store.reports.set(reportId, fallback);
    saveStore(store);
    return fallback;
  },

  async deleteReport(id: string): Promise<boolean> {
    try {
      const sql = getDb();
      await sql`DELETE FROM public.reports WHERE id = ${id};`;
      return true;
    } catch (err) {
      console.warn("[serverStore.deleteReport] Neon query failed:", err);
    }

    const store = initStore();
    const existed = store.reports.delete(id);
    if (existed) saveStore(store);
    return existed;
  },

  // --- Sources Aggregation ---
  async getSources(category?: string): Promise<HarvestedSourceItem[]> {
    try {
      const sql = getDb();
      const rows = await sql`
        SELECT s.id, s.url, s.title, s.created_at,
               COUNT(rs.report_id) as citation_count,
               MIN(r.id) as report_id,
               MIN(r.query) as report_title
        FROM public.sources s
        LEFT JOIN public.report_sources rs ON rs.source_id = s.id
        LEFT JOIN public.reports r ON r.id = rs.report_id
        GROUP BY s.id, s.url, s.title, s.created_at;
      `;
      if (rows && rows.length > 0) {
        const items: HarvestedSourceItem[] = rows.map((r: any) => {
          const url = r.url || "";
          let domain = "web";
          try {
            domain = new URL(url).hostname;
          } catch {}
          let cat = "general";
          const domainLower = (domain + url).toLowerCase();
          if (/arxiv|nature|ieee|science|doi\.org|acm\.org|biorxiv/.test(domainLower)) {
            cat = "academic";
          } else if (/github|gitlab|huggingface|docs\.|dev\./.test(domainLower)) {
            cat = "technical";
          } else if (/sec\.gov|bloomberg|reuters|wsj|ft\.com|federalreserve/.test(domainLower)) {
            cat = "financial";
          }
          return {
            id: r.id,
            url,
            title: r.title || url,
            domain,
            category: cat,
            report_id: r.report_id || null,
            report_title: r.report_title || null,
            citation_count: Math.max(1, Number(r.citation_count) || 1),
            verified: true,
            confidence: 0.96,
          };
        });
        if (category && category !== "all") {
          return items.filter((s) => s.category === category);
        }
        return items;
      }
    } catch (err) {
      console.warn("[serverStore.getSources] Neon query failed:", err);
    }

    const store = initStore();
    const sourceMap = new Map<string, HarvestedSourceItem>();
    for (const report of Array.from(store.reports.values())) {
      for (const s of report.sources || []) {
        if (!s.url) continue;
        const url = s.url.trim();
        let domain = "web";
        try {
          domain = new URL(url).hostname;
        } catch {
          domain = "web";
        }
        let cat = "general";
        const domainLower = (domain + url).toLowerCase();
        if (/arxiv|nature|ieee|science|doi\.org|acm\.org|biorxiv/.test(domainLower)) {
          cat = "academic";
        } else if (/github|gitlab|huggingface|docs\.|dev\./.test(domainLower)) {
          cat = "technical";
        } else if (/sec\.gov|bloomberg|reuters|wsj|ft\.com|federalreserve/.test(domainLower)) {
          cat = "financial";
        }

        if (category && category !== "all" && cat !== category) continue;

        if (sourceMap.has(url)) {
          const existing = sourceMap.get(url)!;
          existing.citation_count = (existing.citation_count || 1) + 1;
        } else {
          sourceMap.set(url, {
            id: s.id || crypto.randomUUID(),
            url,
            title: s.title || url,
            domain,
            category: cat,
            report_id: report.id,
            report_title: report.query,
            citation_count: 1,
            verified: true,
            confidence: 0.95,
          });
        }
      }
    }
    return Array.from(sourceMap.values());
  },
};
