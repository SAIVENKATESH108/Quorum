/**
 * Research Studio — React hooks for research job lifecycle management.
 * Uses TanStack Query for caching, polling, and optimistic updates.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE = () =>
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");


// ─── Types ────────────────────────────────────────────────────────────────────

export type ResearchJobStatus =
  | "draft"
  | "scrub_required"
  | "awaiting_consent"
  | "planning"
  | "retrieving_sources"
  | "extracting_evidence"
  | "verifying_sources"
  | "synthesizing"
  | "citation_validation"
  | "generating_artifacts"
  | "needs_review"
  | "approved"
  | "rejected"
  | "failed";

export const ACTIVE_JOB_STATUSES: ResearchJobStatus[] = [
  "planning",
  "retrieving_sources",
  "extracting_evidence",
  "verifying_sources",
  "synthesizing",
  "citation_validation",
  "generating_artifacts",
];

export const TERMINAL_JOB_STATUSES: ResearchJobStatus[] = [
  "needs_review",
  "approved",
  "rejected",
  "failed",
];

export interface EvidenceBlock {
  id: string;
  provider: string;
  source_identifier: string | null;
  canonical_url: string;
  title: string;
  authors: string[] | null;
  publisher: string | null;
  publication_date: string | null;
  source_class: string;
  access_level: string;
  retrieved_excerpt: string | null;
  topic_tags: string[] | null;
  inclusion_reason: string | null;
  is_excluded: boolean;
  retrieval_timestamp: string;
}

export interface ClaimMapping {
  id: string;
  claim_id: string;
  claim_text: string;
  claim_type: string;
  citation_strength: "directly_supported" | "partially_supported" | "contextual_only" | "unsupported";
  requires_review: boolean;
  section_reference: string | null;
  inline_citation_marker: string | null;
  validation_passed: boolean | null;
  validation_note: string | null;
  evidence_id: string | null;
}

export interface ResearchJobSummary {
  id: string;
  report_id: string;
  status: ResearchJobStatus;
  paper_title: string | null;
  research_question: string;
  paper_type: string;
  depth: string;
  citation_format: string;
  consent_confirmed: boolean;
  sources_retrieved: number;
  sources_excluded: number;
  evidence_coverage_pct: number | null;
  citation_validity_count: number;
  citation_total_count: number;
  flagged_claims_count: number;
  providers_attempted: string[] | null;
  providers_succeeded: string[] | null;
  providers_failed: Record<string, string> | null;
  error_message: string | null;
  failed_stage: string | null;
  created_at: string;
  updated_at: string | null;
  approved_at: string | null;
}

export interface ResearchJobDetail extends ResearchJobSummary {
  scrub_findings: {
    findings: Array<{ type: string; excerpt: string; start: number; end: number }>;
    sanitized: string;
    warning: string;
    finding_count: number;
  } | null;
  sanitized_question: string | null;
  research_plan: {
    sub_questions: string[];
    search_queries: string[];
    scope_note: string;
    excluded_topics: string[];
  } | null;
  executed_queries: Array<{
    provider: string;
    query: string;
    success: boolean;
    results_returned: number;
    executed_at: string;
  }> | null;
  citation_validation_result: {
    passed: boolean;
    inline_citations_found: number;
    orphaned_citations: number[];
    sources_cited: number;
    sources_available: number;
    total_claims: number;
    supported_claims: number;
    unsupported_claims: Array<{ claim_id: string; claim_text: string }>;
    flagged_claims: Array<{ claim_id: string; reason: string }>;
    evidence_coverage_pct: number;
    access_level_summary: Record<string, number>;
    validation_notes: string[];
  } | null;
  review_checklist: Record<string, boolean> | null;
  reviewer_notes: string | null;
  paper_content: string | null;
  artifact_pdf_path: string | null;
  evidence_blocks: EvidenceBlock[];
  claim_mappings: ClaimMapping[];
}

export interface ProviderHealth {
  providers: Record<string, boolean>;
  available_count: number;
  total_count: number;
  timestamp: string;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const researchJobKeys = {
  all: (reportId: string) => ["research-jobs", reportId] as const,
  detail: (jobId: string) => ["research-jobs", "detail", jobId] as const,
  providers: () => ["research-jobs", "providers"] as const,
};

// ─── API Helpers ──────────────────────────────────────────────────────────────

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useResearchJobs(reportId: string) {
  return useQuery({
    queryKey: researchJobKeys.all(reportId),
    queryFn: () =>
      apiFetch<ResearchJobSummary[]>(
        `${API_BASE()}/api/research-jobs?report_id=${reportId}`
      ),
    enabled: Boolean(reportId),
    staleTime: 30_000,
  });
}

export function useResearchJob(jobId: string | null) {
  const isActive = (status?: ResearchJobStatus) =>
    status ? ACTIVE_JOB_STATUSES.includes(status) : false;

  return useQuery({
    queryKey: researchJobKeys.detail(jobId ?? ""),
    queryFn: () =>
      apiFetch<ResearchJobDetail>(
        `${API_BASE()}/api/research-jobs/${jobId}`
      ),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return isActive(status) ? 3000 : false;
    },
    staleTime: 5000,
  });
}

export function useProviderHealth() {
  return useQuery({
    queryKey: researchJobKeys.providers(),
    queryFn: () =>
      apiFetch<ProviderHealth>(`${API_BASE()}/api/research-jobs/providers/health`),
    staleTime: 60_000,
    retry: 1,
  });
}

export function useCreateResearchJob(reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      research_question: string;
      paper_title?: string;
      authors?: string[];
      domain_keywords?: string[];
      paper_type?: string;
      depth?: string;
      citation_format?: string;
      date_from?: string;
      date_to?: string;
      preferred_source_types?: string[];
      excluded_domains?: string[];
    }) =>
      apiFetch<ResearchJobDetail>(
        `${API_BASE()}/api/research-jobs?report_id=${reportId}`,
        { method: "POST", body: JSON.stringify(data) }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: researchJobKeys.all(reportId) }),
  });
}

export function useConfirmConsent(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { confirmed: boolean; sanitized_question_override?: string }) =>
      apiFetch<ResearchJobDetail>(
        `${API_BASE()}/api/research-jobs/${jobId}/confirm-consent`,
        { method: "POST", body: JSON.stringify(data) }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: researchJobKeys.detail(jobId) }),
  });
}

export function useUpdatePlan(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      sub_questions?: string[];
      search_queries?: string[];
      excluded_topics?: string[];
    }) =>
      apiFetch<ResearchJobDetail>(
        `${API_BASE()}/api/research-jobs/${jobId}/plan`,
        { method: "PUT", body: JSON.stringify(data) }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: researchJobKeys.detail(jobId) }),
  });
}

export function useRunResearchJob(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<ResearchJobDetail>(
        `${API_BASE()}/api/research-jobs/${jobId}/run`,
        { method: "POST" }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: researchJobKeys.detail(jobId) }),
  });
}

export function useApproveOrRejectJob(jobId: string, reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      action: "approve" | "reject";
      reviewer_notes?: string;
      checklist: Record<string, boolean>;
    }) =>
      apiFetch<ResearchJobDetail>(
        `${API_BASE()}/api/research-jobs/${jobId}/approve-or-reject`,
        { method: "POST", body: JSON.stringify(data) }
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: researchJobKeys.detail(jobId) });
      qc.invalidateQueries({ queryKey: researchJobKeys.all(reportId) });
    },
  });
}
