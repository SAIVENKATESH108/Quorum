"use client";

/**
 * Research Studio Modal — Evidence-First Research Paper Generator
 *
 * Step 1: Define paper (metadata form)
 * Step 2: Data-safety review (PII scrub + consent)
 * Step 3: Research plan review/edit
 * Step 4: Live pipeline execution (real-time job status)
 * Step 5: Evidence review + human approval gate
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  FileSearch,
  FileText,
  Loader2,
  ShieldCheck,
  X,
  XCircle,
} from "lucide-react";
import {
  ACTIVE_JOB_STATUSES,
  ResearchJobDetail,
  useConfirmConsent,
  useCreateResearchJob,
  useProviderHealth,
  useResearchJob,
  useRunResearchJob,
  useUpdatePlan,
} from "@/hooks/useResearchJob";
import { ReportDetailResponse } from "@/lib/api-client";

// ─── Step Configuration ────────────────────────────────────────────────────

const STEPS = [
  { id: 1, label: "Define Paper", icon: BookOpen },
  { id: 2, label: "Safety Review", icon: ShieldCheck },
  { id: 3, label: "Research Plan", icon: FileSearch },
  { id: 4, label: "Executing", icon: Loader2 },
  { id: 5, label: "Review & Approve", icon: ClipboardCheck },
];

// ─── Job Status Labels for display ────────────────────────────────────────

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: "Draft", color: "text-zinc-400" },
  scrub_required: { label: "Awaiting Review", color: "text-amber-400" },
  awaiting_consent: { label: "Awaiting Consent", color: "text-amber-400" },
  planning: { label: "Planning…", color: "text-indigo-400" },
  retrieving_sources: { label: "Retrieving Sources…", color: "text-cyan-400" },
  extracting_evidence: { label: "Extracting Evidence…", color: "text-cyan-400" },
  verifying_sources: { label: "Verifying Sources…", color: "text-cyan-400" },
  synthesizing: { label: "Synthesising Paper…", color: "text-purple-400" },
  citation_validation: { label: "Validating Citations…", color: "text-purple-400" },
  generating_artifacts: { label: "Generating PDF…", color: "text-emerald-400" },
  needs_review: { label: "Ready for Review", color: "text-emerald-400" },
  approved: { label: "Approved ✓", color: "text-emerald-400" },
  rejected: { label: "Rejected", color: "text-rose-400" },
  failed: { label: "Failed", color: "text-rose-400" },
};

// ─── Props ─────────────────────────────────────────────────────────────────

interface ResearchStudioModalProps {
  report: ReportDetailResponse;
  isOpen: boolean;
  onClose: () => void;
}

// ─── Main Modal ────────────────────────────────────────────────────────────

export function ResearchStudioModal({
  report,
  isOpen,
  onClose,
}: ResearchStudioModalProps) {
  const [step, setStep] = useState(1);
  const [jobId, setJobId] = useState<string | null>(null);

  // Form state — Step 1
  const [form, setForm] = useState({
    research_question: `What are the key findings and implications of research on ${report.query || "the topic"}?`,
    paper_title: "",
    authors: [] as string[],
    authorInput: "",
    domain_keywords: [] as string[],
    keywordInput: "",
    paper_type: "literature_review",
    depth: "standard",
    citation_format: "ieee",
    date_from: "",
    date_to: "",
    preferred_source_types: ["peer_reviewed", "preprint"] as string[],
    excluded_domains: [] as string[],
    excludeDomainInput: "",
  });

  // Step 2 state
  const [sanitizedOverride, setSanitizedOverride] = useState("");
  const [consentChecked, setConsentChecked] = useState(false);

  // Step 3 state
  const [editedPlan, setEditedPlan] = useState<{
    sub_questions: string[];
    search_queries: string[];
    scope_note?: string;
    excluded_topics?: string[];
    [key: string]: any;
  } | null>(null);

  // Step 5 checklist
  const [approvalChecklist, setApprovalChecklist] = useState<Record<string, boolean>>({
    reviewed_sources: false,
    verified_facts: false,
    understood_disclaimers: false,
    reviewed_sensitive_content: false,
    approve_for_use: false,
  });
  const [reviewerNotes, setReviewerNotes] = useState("");

  // Mutations
  const createJob = useCreateResearchJob(report.id);
  const confirmConsent = useConfirmConsent(jobId ?? "");
  const updatePlan = useUpdatePlan(jobId ?? "");
  const runJob = useRunResearchJob(jobId ?? "");

  // Poll job detail
  const { data: job, isLoading: jobLoading } = useResearchJob(jobId);
  const { data: providerHealth } = useProviderHealth();

  // Auto-advance to review step when job reaches terminal status
  useEffect(() => {
    if (!job) return;
    if (job.status === "needs_review" || job.status === "approved" || job.status === "failed") {
      setStep(5);
    }
  }, [job?.status]);

  // Initialize plan editor when plan is available
  useEffect(() => {
    if (job?.research_plan && !editedPlan) {
      setEditedPlan({
        sub_questions: job.research_plan.sub_questions ?? [],
        search_queries: job.research_plan.search_queries ?? [],
      });
    }
  }, [job?.research_plan]);

  const handleClose = useCallback(() => {
    onClose();
    // Reset on close
    setTimeout(() => {
      setStep(1);
      setJobId(null);
      setConsentChecked(false);
      setEditedPlan(null);
    }, 300);
  }, [onClose]);

  if (!isOpen) return null;

  // ─── Step 1: Define Paper ────────────────────────────────────────────────

  const handleStep1Submit = async () => {
    const result = await createJob.mutateAsync({
      research_question: form.research_question,
      paper_title: form.paper_title || undefined,
      authors: form.authors.length ? form.authors : undefined,
      domain_keywords: form.domain_keywords.length ? form.domain_keywords : undefined,
      paper_type: form.paper_type,
      depth: form.depth,
      citation_format: form.citation_format,
      date_from: form.date_from || undefined,
      date_to: form.date_to || undefined,
      preferred_source_types: form.preferred_source_types,
      excluded_domains: form.excluded_domains.length ? form.excluded_domains : undefined,
    });
    setJobId(result.id);
    setSanitizedOverride(result.sanitized_question ?? result.research_question);
    setStep(2);
  };

  // ─── Step 2: Consent ────────────────────────────────────────────────────

  const handleConsentSubmit = async () => {
    await confirmConsent.mutateAsync({
      confirmed: true,
      sanitized_question_override: sanitizedOverride !== job?.research_question
        ? sanitizedOverride
        : undefined,
    });
    setStep(3);
  };

  // ─── Step 3: Plan + Execute ──────────────────────────────────────────────

  const handleRunPipeline = async () => {
    if (editedPlan && job?.research_plan) {
      await updatePlan.mutateAsync({
        sub_questions: editedPlan.sub_questions,
        search_queries: editedPlan.search_queries,
      });
    }
    await runJob.mutateAsync();
    setStep(4);
  };

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-4xl max-h-[92vh] mx-4 flex flex-col rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/80">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100">
                Quorum Research Studio
              </h2>
              <p className="text-xs text-zinc-400">
                Evidence-first research paper generation
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Step Breadcrumb */}
        <div className="flex items-center gap-1 px-6 py-3 border-b border-zinc-800/60 bg-zinc-900/40 overflow-x-auto">
          {STEPS.map((s, idx) => {
            const Icon = s.icon;
            const isActive = s.id === step;
            const isDone = s.id < step;
            return (
              <React.Fragment key={s.id}>
                <div
                  className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full shrink-0 transition-colors ${
                    isActive
                      ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                      : isDone
                      ? "text-emerald-400"
                      : "text-zinc-600"
                  }`}
                >
                  {isDone ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <Icon className={`h-3.5 w-3.5 ${isActive && s.id === 4 ? "animate-spin" : ""}`} />
                  )}
                  {s.label}
                </div>
                {idx < STEPS.length - 1 && (
                  <ChevronRight className="h-3 w-3 text-zinc-700 shrink-0" />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto no-scrollbar">
          {step === 1 && (
            <StepDefinePaper
              form={form}
              setForm={setForm}
              providerHealth={providerHealth}
              onNext={handleStep1Submit}
              isLoading={createJob.isPending}
              error={createJob.error?.message}
            />
          )}
          {step === 2 && job && (
            <StepSafetyReview
              job={job}
              sanitizedOverride={sanitizedOverride}
              setSanitizedOverride={setSanitizedOverride}
              consentChecked={consentChecked}
              setConsentChecked={setConsentChecked}
              onConfirm={handleConsentSubmit}
              isLoading={confirmConsent.isPending}
              error={confirmConsent.error?.message}
            />
          )}
          {step === 3 && job && (
            <StepResearchPlan
              job={job}
              editedPlan={editedPlan}
              setEditedPlan={setEditedPlan}
              onRun={handleRunPipeline}
              isLoading={runJob.isPending || updatePlan.isPending}
              error={runJob.error?.message}
            />
          )}
          {step === 4 && (
            <StepExecution job={job} isLoading={jobLoading} />
          )}
          {step === 5 && (
            <StepReviewApprove
              job={job}
              checklist={approvalChecklist}
              setChecklist={setApprovalChecklist}
              reviewerNotes={reviewerNotes}
              setReviewerNotes={setReviewerNotes}
              jobId={jobId ?? ""}
              reportId={report.id}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-step components
// ─────────────────────────────────────────────────────────────────────────────

// ─── Step 1: Define Paper ──────────────────────────────────────────────────

function StepDefinePaper({
  form,
  setForm,
  providerHealth,
  onNext,
  isLoading,
  error,
}: {
  form: any;
  setForm: (f: any) => void;
  providerHealth: any;
  onNext: () => void;
  isLoading: boolean;
  error?: string;
}) {
  const set = (k: string, v: any) => setForm((prev: any) => ({ ...prev, [k]: v }));

  return (
    <div className="p-6 space-y-6">
      {/* Provider availability */}
      {providerHealth && (
        <div className="flex items-center gap-2 text-xs text-zinc-400 bg-zinc-900 rounded-lg px-3 py-2 border border-zinc-800">
          <span className={`h-2 w-2 rounded-full ${providerHealth.available_count > 0 ? "bg-emerald-400" : "bg-rose-400"}`} />
          <span>
            {providerHealth.available_count}/{providerHealth.total_count} academic source providers reachable (
            {Object.entries(providerHealth.providers)
              .filter(([, ok]) => ok)
              .map(([name]) => name)
              .join(", ") || "none"}
            )
          </span>
        </div>
      )}

      {/* Research question */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-300">
          Research Question <span className="text-rose-400">*</span>
        </label>
        <textarea
          value={form.research_question}
          onChange={(e) => set("research_question", e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          placeholder="What are the key findings and evidence on...?"
        />
      </div>

      {/* Paper title */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-300">
          Paper Title <span className="text-zinc-500">(optional)</span>
        </label>
        <input
          type="text"
          value={form.paper_title}
          onChange={(e) => set("paper_title", e.target.value)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          placeholder="Leave blank to auto-generate"
        />
      </div>

      {/* Authors */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-300">
          Authors <span className="text-zinc-500">(never invented — leave blank if unknown)</span>
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={form.authorInput}
            onChange={(e) => set("authorInput", e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && form.authorInput.trim()) {
                set("authors", [...form.authors, form.authorInput.trim()]);
                set("authorInput", "");
              }
            }}
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Type name and press Enter"
          />
        </div>
        <div className="flex flex-wrap gap-1.5 mt-1">
          {form.authors.map((a: string) => (
            <span key={a} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 text-xs border border-indigo-500/20">
              {a}
              <button onClick={() => set("authors", form.authors.filter((x: string) => x !== a))}>
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Paper Type */}
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-300">Paper Type</label>
          <select
            value={form.paper_type}
            onChange={(e) => set("paper_type", e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="literature_review">Literature Review</option>
            <option value="technical_research_report">Technical Research Report</option>
            <option value="system_design_paper">System Design Paper</option>
            <option value="comparative_analysis">Comparative Analysis</option>
            <option value="project_capstone_paper">Project / Capstone Paper</option>
          </select>
        </div>

        {/* Depth */}
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-300">Research Depth</label>
          <select
            value={form.depth}
            onChange={(e) => set("depth", e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="quick">Quick evidence review (~3 queries)</option>
            <option value="standard">Standard literature review (~5 queries)</option>
            <option value="thorough">Thorough research review (~8 queries)</option>
          </select>
        </div>

        {/* Citation format */}
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-300">Citation Format</label>
          <select
            value={form.citation_format}
            onChange={(e) => set("citation_format", e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="ieee">IEEE-style draft</option>
            <option value="apa">APA-style draft</option>
            <option value="mla">MLA-style draft</option>
          </select>
        </div>

        {/* Date range */}
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-300">Date Range (year)</label>
          <div className="flex gap-2">
            <input
              type="text"
              maxLength={4}
              value={form.date_from}
              onChange={(e) => set("date_from", e.target.value)}
              placeholder="From YYYY"
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <input
              type="text"
              maxLength={4}
              value={form.date_to}
              onChange={(e) => set("date_to", e.target.value)}
              placeholder="To YYYY"
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>
      </div>

      {/* Keywords */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-300">Domain / Topic Keywords</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={form.keywordInput}
            onChange={(e) => set("keywordInput", e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && form.keywordInput.trim()) {
                set("domain_keywords", [...form.domain_keywords, form.keywordInput.trim()]);
                set("keywordInput", "");
              }
            }}
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Type keyword and press Enter"
          />
        </div>
        <div className="flex flex-wrap gap-1.5 mt-1">
          {form.domain_keywords.map((k: string) => (
            <span key={k} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 text-xs border border-cyan-500/20">
              {k}
              <button onClick={() => set("domain_keywords", form.domain_keywords.filter((x: string) => x !== k))}>
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      </div>

      {/* Safety note */}
      <div className="flex gap-2 p-3 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-300 text-xs">
        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
        <p>
          A data-safety review of your research question will be performed on the next step.
          You will see exactly what content will be transmitted to external academic providers before confirming.
          No external requests are made until you explicitly consent.
        </p>
      </div>

      {error && (
        <div className="flex gap-2 p-3 rounded-lg bg-rose-950/30 border border-rose-800/40 text-rose-300 text-xs">
          <XCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex justify-end pt-2">
        <button
          onClick={onNext}
          disabled={isLoading || form.research_question.trim().length < 10}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ChevronRight className="h-4 w-4" />}
          Continue to Safety Review
        </button>
      </div>
    </div>
  );
}

// ─── Step 2: Safety Review + Consent ───────────────────────────────────────

function StepSafetyReview({
  job,
  sanitizedOverride,
  setSanitizedOverride,
  consentChecked,
  setConsentChecked,
  onConfirm,
  isLoading,
  error,
}: {
  job: ResearchJobDetail;
  sanitizedOverride: string;
  setSanitizedOverride: (v: string) => void;
  consentChecked: boolean;
  setConsentChecked: (v: boolean) => void;
  onConfirm: () => void;
  isLoading: boolean;
  error?: string;
}) {
  const findings = job.scrub_findings?.findings ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-zinc-100">Data-Safety Review</h3>
        <p className="text-xs text-zinc-400">
          Review your research question for sensitive content before transmitting it to external academic providers.
        </p>
      </div>

      {/* Scrub findings */}
      {findings.length > 0 ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-amber-400 text-xs font-medium">
            <AlertTriangle className="h-4 w-4" />
            {findings.length} potential sensitive item{findings.length > 1 ? "s" : ""} detected
          </div>
          <div className="space-y-1.5 max-h-40 overflow-y-auto no-scrollbar">
            {findings.map((f, i) => (
              <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-amber-950/20 border border-amber-800/30 text-xs">
                <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-medium shrink-0">
                  {f.type.replace(/_/g, " ")}
                </span>
                <code className="text-amber-200 break-all">{f.excerpt}</code>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-emerald-300 text-xs">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          No sensitive patterns detected in the research question.
        </div>
      )}

      {/* System warning */}
      <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-400 text-xs">
        <p className="font-medium text-zinc-300 mb-1">⚠ Important</p>
        <p>{job.scrub_findings?.warning}</p>
      </div>

      {/* Sanitized question preview */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-300">
          Sanitized research question that will be transmitted
          <span className="text-zinc-500 ml-1">(you may edit)</span>
        </label>
        <textarea
          value={sanitizedOverride}
          onChange={(e) => setSanitizedOverride(e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {/* Consent checkbox */}
      <label className="flex items-start gap-3 cursor-pointer p-4 rounded-xl border border-indigo-500/30 bg-indigo-950/20">
        <input
          type="checkbox"
          checked={consentChecked}
          onChange={(e) => setConsentChecked(e.target.checked)}
          className="mt-0.5 h-4 w-4 accent-indigo-500"
        />
        <span className="text-sm text-zinc-200">
          I confirm that the displayed sanitized content may be sent to external research and academic providers (CrossRef, OpenAlex, arXiv, Semantic Scholar).
        </span>
      </label>

      {error && (
        <div className="flex gap-2 p-3 rounded-lg bg-rose-950/30 border border-rose-800/40 text-rose-300 text-xs">
          <XCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={onConfirm}
          disabled={isLoading || !consentChecked}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
          Confirm & Continue to Research Plan
        </button>
      </div>
    </div>
  );
}

// ─── Step 3: Research Plan Review ─────────────────────────────────────────

function StepResearchPlan({
  job,
  editedPlan,
  setEditedPlan,
  onRun,
  isLoading,
  error,
}: {
  job: ResearchJobDetail;
  editedPlan: { sub_questions: string[]; search_queries: string[]; scope_note?: string; excluded_topics?: string[]; [key: string]: any } | null;
  setEditedPlan: (p: any) => void;
  onRun: () => void;
  isLoading: boolean;
  error?: string;
}) {
  const plan: any = editedPlan ?? job.research_plan;

  return (
    <div className="p-6 space-y-6">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-zinc-100">Research Plan</h3>
        <p className="text-xs text-zinc-400">
          Review and optionally edit the sub-questions and search queries before retrieval begins.
          This plan is persisted before any external source is contacted.
        </p>
      </div>

      {!plan ? (
        <div className="flex items-center gap-2 text-zinc-400 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          Generating research plan…
        </div>
      ) : (
        <>
          <div className="space-y-2">
            <label className="block text-xs font-medium text-zinc-300">
              Sub-Questions ({plan.sub_questions?.length ?? 0})
            </label>
            {((plan.sub_questions as string[]) ?? []).map((q: string, i: number) => (
              <div key={i} className="flex gap-2 items-start">
                <span className="text-xs text-zinc-500 mt-2 shrink-0 w-6">{i + 1}.</span>
                <input
                  value={q}
                  onChange={(e) => {
                    const updated = [...((plan.sub_questions as string[]) ?? [])];
                    updated[i] = e.target.value;
                    setEditedPlan({ ...plan, sub_questions: updated });
                  }}
                  className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-medium text-zinc-300">
              Search Queries ({plan.search_queries?.length ?? 0})
            </label>
            {((plan.search_queries as string[]) ?? []).map((q: string, i: number) => (
              <div key={i} className="flex gap-2 items-start">
                <span className="text-xs text-zinc-500 mt-2 shrink-0 w-6">Q{i + 1}.</span>
                <input
                  value={q}
                  onChange={(e) => {
                    const updated = [...((plan.search_queries as string[]) ?? [])];
                    updated[i] = e.target.value;
                    setEditedPlan({ ...plan, search_queries: updated });
                  }}
                  className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            ))}
          </div>

          {plan.scope_note && (
            <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-400 text-xs">
              <span className="text-zinc-300 font-medium">Evidence scope: </span>
              {plan.scope_note}
            </div>
          )}
        </>
      )}

      {error && (
        <div className="flex gap-2 p-3 rounded-lg bg-rose-950/30 border border-rose-800/40 text-rose-300 text-xs">
          <XCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={onRun}
          disabled={isLoading || !plan}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
          Start Evidence Retrieval Pipeline
        </button>
      </div>
    </div>
  );
}

// ─── Step 4: Live Execution Tracking ──────────────────────────────────────

const PIPELINE_STAGES: Array<{ key: string; label: string }> = [
  { key: "planning", label: "Research Plan" },
  { key: "retrieving_sources", label: "Source Retrieval" },
  { key: "verifying_sources", label: "Verification & Dedup" },
  { key: "extracting_evidence", label: "Evidence Extraction" },
  { key: "synthesizing", label: "LLM Synthesis" },
  { key: "citation_validation", label: "Citation Validation" },
  { key: "generating_artifacts", label: "PDF Generation" },
  { key: "needs_review", label: "Ready for Review" },
];

const STATUS_ORDER = PIPELINE_STAGES.map((s) => s.key);

function StepExecution({ job, isLoading }: { job?: ResearchJobDetail | null; isLoading: boolean }) {
  const currentIdx = job ? STATUS_ORDER.indexOf(job.status) : -1;
  const statusInfo = job ? STATUS_LABELS[job.status] : null;
  const isFailed = job?.status === "failed";

  return (
    <div className="p-6 space-y-6">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-zinc-100">Pipeline Execution</h3>
        <p className="text-xs text-zinc-400">
          The evidence-first research pipeline is running. Each stage completes before the next begins.
        </p>
      </div>

      {/* Overall status */}
      <div className={`flex items-center gap-3 p-4 rounded-xl border ${
        isFailed ? "bg-rose-950/20 border-rose-800/40" : "bg-zinc-900 border-zinc-700"
      }`}>
        {isFailed ? (
          <XCircle className="h-5 w-5 text-rose-400 shrink-0" />
        ) : (
          <Loader2 className="h-5 w-5 text-indigo-400 animate-spin shrink-0" />
        )}
        <div>
          <p className={`text-sm font-medium ${statusInfo?.color ?? "text-zinc-300"}`}>
            {statusInfo?.label ?? "Starting…"}
          </p>
          {isFailed && job?.error_message && (
            <p className="text-xs text-rose-300 mt-0.5">{job.error_message}</p>
          )}
        </div>
      </div>

      {/* Stage progress */}
      <div className="space-y-2">
        {PIPELINE_STAGES.map((stage, idx) => {
          const isDone = currentIdx > idx || job?.status === "needs_review";
          const isActive = currentIdx === idx;
          return (
            <div key={stage.key} className="flex items-center gap-3">
              <div className={`h-6 w-6 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                isDone
                  ? "bg-emerald-500/20 text-emerald-400"
                  : isActive
                  ? "bg-indigo-500/20 text-indigo-400 ring-2 ring-indigo-500/40"
                  : "bg-zinc-800 text-zinc-600"
              }`}>
                {isDone ? <CheckCircle2 className="h-3.5 w-3.5" /> : idx + 1}
              </div>
              <span className={`text-sm ${isDone ? "text-emerald-400" : isActive ? "text-indigo-300" : "text-zinc-600"}`}>
                {stage.label}
              </span>
              {isActive && !isFailed && (
                <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin ml-auto" />
              )}
            </div>
          );
        })}
      </div>

      {/* Live metrics */}
      {job && job.sources_retrieved > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Sources Retrieved", value: job.sources_retrieved },
            { label: "Sources Excluded", value: job.sources_excluded },
            { label: "Coverage", value: job.evidence_coverage_pct != null ? `${job.evidence_coverage_pct}%` : "—" },
            { label: "Flagged Claims", value: job.flagged_claims_count },
          ].map((m) => (
            <div key={m.label} className="rounded-xl border border-zinc-800 bg-zinc-900 p-3 text-center">
              <p className="text-lg font-bold text-zinc-100">{m.value}</p>
              <p className="text-[10px] text-zinc-500 mt-0.5">{m.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Providers */}
      {job?.providers_succeeded && job.providers_succeeded.length > 0 && (
        <div className="text-xs text-zinc-500">
          <span className="text-zinc-300">Providers succeeded: </span>
          {job.providers_succeeded.join(", ")}
          {job.providers_failed && Object.keys(job.providers_failed).length > 0 && (
            <span className="ml-2 text-amber-500">
              • Failed: {Object.keys(job.providers_failed).join(", ")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Step 5: Review & Approve ───────────────────────────────────────────────

function StepReviewApprove({
  job,
  checklist,
  setChecklist,
  reviewerNotes,
  setReviewerNotes,
  jobId,
  reportId,
}: {
  job?: ResearchJobDetail | null;
  checklist: Record<string, boolean>;
  setChecklist: React.Dispatch<React.SetStateAction<Record<string, boolean>>> | ((c: Record<string, boolean>) => void);
  reviewerNotes: string;
  setReviewerNotes: (n: string) => void;
  jobId: string;
  reportId: string;
}) {
  const { mutateAsync: approveOrReject, isPending, error } = useApproveOrRejectJobDirect(jobId, reportId);
  const [activeTab, setActiveTab] = useState<"preview" | "sources" | "matrix" | "validation" | "checklist">("preview");

  const isApproved = job?.status === "approved";
  const isRejected = job?.status === "rejected";
  const isFailed = job?.status === "failed";
  const allChecked = Object.values(checklist).every(Boolean);

  const handleApprove = async () => {
    await approveOrReject({ action: "approve", checklist, reviewer_notes: reviewerNotes });
  };
  const handleReject = async () => {
    await approveOrReject({ action: "reject", checklist, reviewer_notes: reviewerNotes });
  };

  const TABS = ["preview", "sources", "matrix", "validation", "checklist"] as const;
  const TAB_LABELS: Record<typeof TABS[number], string> = {
    preview: "Paper Preview",
    sources: `Sources (${job?.evidence_blocks?.length ?? 0})`,
    matrix: `Claim Matrix (${job?.claim_mappings?.length ?? 0})`,
    validation: "Citation Validation",
    checklist: "Approval Checklist",
  };

  return (
    <div className="flex flex-col h-full">
      {/* Status banner */}
      {(isApproved || isRejected || isFailed) && (
        <div className={`mx-6 mt-4 flex items-center gap-2 p-3 rounded-xl text-sm font-medium ${
          isApproved ? "bg-emerald-950/30 border border-emerald-800/40 text-emerald-300" :
          isFailed ? "bg-rose-950/30 border border-rose-800/40 text-rose-300" :
          "bg-zinc-900 border border-zinc-700 text-zinc-400"
        }`}>
          {isApproved ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          {isApproved ? "This research paper has been approved." :
           isFailed ? `Pipeline failed at stage: ${job?.failed_stage}. ${job?.error_message}` :
           "This research paper has been rejected."}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 px-6 pt-4 border-b border-zinc-800 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 whitespace-nowrap transition-colors ${
              activeTab === tab
                ? "border-indigo-500 text-indigo-300 bg-indigo-500/10"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto no-scrollbar p-6">
        {activeTab === "preview" && (
          <PaperPreviewTab job={job} />
        )}
        {activeTab === "sources" && (
          <SourcesTab evidence={job?.evidence_blocks ?? []} />
        )}
        {activeTab === "matrix" && (
          <ClaimMatrixTab claims={job?.claim_mappings ?? []} evidence={job?.evidence_blocks ?? []} />
        )}
        {activeTab === "validation" && (
          <CitationValidationTab result={job?.citation_validation_result ?? null} />
        )}
        {activeTab === "checklist" && (
          <ApprovalChecklistTab
            checklist={checklist}
            setChecklist={setChecklist}
            reviewerNotes={reviewerNotes}
            setReviewerNotes={setReviewerNotes}
            onApprove={handleApprove}
            onReject={handleReject}
            isLoading={isPending}
            error={error?.message}
            isApproved={isApproved}
            isRejected={isRejected}
            allChecked={allChecked}
            jobId={jobId}
          />
        )}
      </div>
    </div>
  );
}

// ─── Sub-tabs ──────────────────────────────────────────────────────────────

function PaperPreviewTab({ job }: { job?: ResearchJobDetail | null }) {
  if (!job?.paper_content) {
    return (
      <div className="flex items-center justify-center h-40 text-zinc-500 text-sm">
        {ACTIVE_JOB_STATUSES.includes(job?.status as any)
          ? "Paper is being generated…"
          : "No paper content available yet."}
      </div>
    );
  }
  return (
    <div className="prose prose-invert prose-sm max-w-none text-zinc-200 text-sm leading-relaxed whitespace-pre-wrap">
      {job.paper_content}
    </div>
  );
}

const SOURCE_CLASS_LABELS: Record<string, { label: string; color: string }> = {
  peer_reviewed: { label: "Peer-Reviewed", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
  preprint: { label: "Preprint", color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
  gov_standards: { label: "Gov / Standards", color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
  tech_pub: { label: "Technical Pub", color: "text-purple-400 bg-purple-500/10 border-purple-500/20" },
  unverified: { label: "Unverified", color: "text-zinc-400 bg-zinc-800 border-zinc-700" },
};

function SourcesTab({ evidence }: { evidence: EvidenceBlock[] }) {
  if (!evidence.length) {
    return <div className="text-zinc-500 text-sm text-center py-12">No evidence sources available.</div>;
  }
  return (
    <div className="space-y-3">
      {evidence.map((ev, idx) => {
        const cls = SOURCE_CLASS_LABELS[ev.source_class] ?? SOURCE_CLASS_LABELS.unverified;
        return (
          <div key={ev.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2 flex-1 min-w-0">
                <span className="text-xs text-zinc-500 shrink-0 mt-0.5">[{idx + 1}]</span>
                <div className="min-w-0">
                  <a
                    href={ev.canonical_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-indigo-300 hover:text-indigo-200 hover:underline break-words"
                  >
                    {ev.title}
                  </a>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    {ev.authors?.slice(0, 3).join("; ")}
                    {ev.authors && ev.authors.length > 3 ? " et al." : ""}
                    {ev.publisher ? ` · ${ev.publisher}` : ""}
                    {ev.publication_date ? ` · ${ev.publication_date}` : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${cls.color}`}>
                  {cls.label}
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] bg-zinc-800 text-zinc-400 border border-zinc-700">
                  {ev.access_level.replace(/_/g, " ")}
                </span>
              </div>
            </div>
            {ev.retrieved_excerpt && (
              <p className="text-xs text-zinc-400 border-t border-zinc-800 pt-2 line-clamp-3">
                {ev.retrieved_excerpt}
              </p>
            )}
            <p className="text-[10px] text-zinc-600">
              Retrieved: {new Date(ev.retrieval_timestamp).toLocaleString()} · Provider: {ev.provider}
              {ev.source_identifier ? ` · ID: ${ev.source_identifier}` : ""}
            </p>
          </div>
        );
      })}
    </div>
  );
}

const STRENGTH_COLORS: Record<string, string> = {
  directly_supported: "text-emerald-400",
  partially_supported: "text-amber-400",
  contextual_only: "text-zinc-400",
  unsupported: "text-rose-400",
};

function ClaimMatrixTab({
  claims,
  evidence,
}: {
  claims: ClaimMapping[];
  evidence: EvidenceBlock[];
}) {
  const evMap = Object.fromEntries(evidence.map((e) => [e.id, e]));
  if (!claims.length) {
    return <div className="text-zinc-500 text-sm text-center py-12">No claim matrix available yet.</div>;
  }
  return (
    <div className="space-y-2">
      {claims.map((c) => {
        const ev = c.evidence_id ? evMap[c.evidence_id] : null;
        return (
          <div
            key={c.id}
            className={`rounded-xl border p-4 space-y-1.5 ${
              c.requires_review ? "border-amber-800/40 bg-amber-950/10" : "border-zinc-800 bg-zinc-900"
            }`}
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono text-zinc-500">{c.claim_id}</span>
              <span className={`text-xs font-medium ${STRENGTH_COLORS[c.citation_strength] ?? "text-zinc-400"}`}>
                {c.citation_strength.replace(/_/g, " ")}
              </span>
              <span className="text-xs text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded">
                {c.claim_type}
              </span>
              {c.requires_review && (
                <span className="flex items-center gap-1 text-xs text-amber-400">
                  <AlertTriangle className="h-3 w-3" /> Requires review
                </span>
              )}
            </div>
            <p className="text-sm text-zinc-200">{c.claim_text}</p>
            {ev && (
              <p className="text-xs text-zinc-500">
                Evidence: <span className="text-zinc-400">{ev.title}</span>
              </p>
            )}
            {c.validation_note && (
              <p className="text-xs text-amber-400">{c.validation_note}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function CitationValidationTab({ result }: { result: any }) {
  if (!result) {
    return <div className="text-zinc-500 text-sm text-center py-12">Citation validation has not run yet.</div>;
  }
  return (
    <div className="space-y-4">
      {/* Pass/Fail banner */}
      <div className={`flex items-center gap-3 p-4 rounded-xl border ${
        result.passed ? "bg-emerald-950/30 border-emerald-800/40" : "bg-amber-950/20 border-amber-800/40"
      }`}>
        {result.passed
          ? <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          : <AlertTriangle className="h-5 w-5 text-amber-400" />
        }
        <span className={`text-sm font-medium ${result.passed ? "text-emerald-300" : "text-amber-300"}`}>
          {result.passed ? "Citation validation passed" : "Citation validation — issues found"}
        </span>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "Evidence Coverage", value: `${result.evidence_coverage_pct}%` },
          { label: "Citations Valid", value: `${result.inline_citations_found}/${result.sources_available}` },
          { label: "Total Claims", value: result.total_claims },
          { label: "Supported Claims", value: result.supported_claims },
          { label: "Unsupported Claims", value: result.unsupported_claims?.length ?? 0 },
          { label: "Orphaned Citations", value: result.orphaned_citations?.length ?? 0 },
        ].map((m) => (
          <div key={m.label} className="rounded-xl border border-zinc-800 bg-zinc-900 p-3 text-center">
            <p className="text-lg font-bold text-zinc-100">{m.value}</p>
            <p className="text-[10px] text-zinc-500 mt-0.5">{m.label}</p>
          </div>
        ))}
      </div>

      {/* Access level */}
      {result.access_level_summary && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs font-medium text-zinc-300 mb-2">Source Access Levels</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(result.access_level_summary).map(([k, v]) => (
              <span key={k} className="text-xs px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700">
                {String(v)} {k.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Validation notes */}
      {result.validation_notes?.length > 0 && (
        <div className="space-y-1.5">
          {result.validation_notes.map((note: string, i: number) => (
            <div key={i} className="flex gap-2 p-3 rounded-lg bg-amber-950/20 border border-amber-800/30 text-xs text-amber-300">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              {note}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const CHECKLIST_LABELS: Record<string, string> = {
  reviewed_sources: "I reviewed the sources and citations in the paper.",
  verified_facts: "I verified important facts, numbers, quotes, and technical statements.",
  understood_disclaimers:
    "I understand this system does not establish global novelty, patentability, legal safety, academic originality, or publication acceptance.",
  reviewed_sensitive_content:
    "I reviewed the document for sensitive information, bias, and misleading certainty.",
  approve_for_use: "I approve this draft for my intended use.",
};

function ApprovalChecklistTab({
  checklist,
  setChecklist,
  reviewerNotes,
  setReviewerNotes,
  onApprove,
  onReject,
  isLoading,
  error,
  isApproved,
  isRejected,
  allChecked,
  jobId,
}: {
  checklist: Record<string, boolean>;
  setChecklist: (c: Record<string, boolean>) => void;
  reviewerNotes: string;
  setReviewerNotes: (n: string) => void;
  onApprove: () => void;
  onReject: () => void;
  isLoading: boolean;
  error?: string;
  isApproved: boolean;
  isRejected: boolean;
  allChecked: boolean;
  jobId: string;
}) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-zinc-100">Human Review Checklist</h3>
        <p className="text-xs text-zinc-400">
          Approval is never automatic. Review all items before approving this research draft.
        </p>
      </div>

      <div className="space-y-3">
        {Object.entries(CHECKLIST_LABELS).map(([key, label]) => (
          <label key={key} className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={checklist[key] ?? false}
              onChange={(e) => setChecklist({ ...checklist, [key]: e.target.checked })}
              disabled={isApproved || isRejected}
              className="mt-0.5 h-4 w-4 accent-indigo-500"
            />
            <span className="text-sm text-zinc-300">{label}</span>
          </label>
        ))}
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-300">
          Reviewer Notes <span className="text-zinc-500">(optional)</span>
        </label>
        <textarea
          value={reviewerNotes}
          onChange={(e) => setReviewerNotes(e.target.value)}
          rows={3}
          disabled={isApproved || isRejected}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
          placeholder="Notes for review record…"
        />
      </div>

      {/* PDF download if available */}
      <a
        href={`/api/research-jobs/${jobId}/pdf`}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm transition-colors"
      >
        <FileText className="h-4 w-4" />
        Download PDF (if generated)
      </a>

      {error && (
        <div className="flex gap-2 p-3 rounded-lg bg-rose-950/30 border border-rose-800/40 text-rose-300 text-xs">
          <XCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!isApproved && !isRejected && (
        <div className="flex gap-3 justify-end">
          <button
            onClick={onReject}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-rose-800/40 bg-rose-950/20 hover:bg-rose-950/40 text-rose-300 text-sm font-medium transition-colors disabled:opacity-50"
          >
            <XCircle className="h-4 w-4" />
            Reject
          </button>
          <button
            onClick={onApprove}
            disabled={isLoading || !allChecked}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            Approve Research Paper
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Direct mutation hook for approval (avoids prop drilling) ──────────────

function useApproveOrRejectJobDirect(jobId: string, reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      action: "approve" | "reject";
      reviewer_notes?: string;
      checklist: Record<string, boolean>;
    }) => {
      const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
      return fetch(`${base}/api/research-jobs/${jobId}/approve-or-reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(data),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? `HTTP ${r.status}`);
        return r.json();
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["research-jobs", "detail", jobId] });
      qc.invalidateQueries({ queryKey: ["research-jobs", reportId] });
    },
  });
}

// Re-export EvidenceBlock/ClaimMapping for use in sub-components
import type { EvidenceBlock, ClaimMapping } from "@/hooks/useResearchJob";
import { useMutation, useQueryClient } from "@tanstack/react-query";
