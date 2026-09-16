"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { FilePlus2, Loader2, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useProjects } from "@/hooks/useProjects";
import { useCreateReport } from "@/hooks/useReports";
import { useUiStore } from "@/stores/uiStore";

export function CreateReportModal() {
  const router = useRouter();
  const activeModal = useUiStore((state) => state.activeModal);
  const closeModal = useUiStore((state) => state.closeModal);
  const setSelectedReportId = useUiStore((state) => state.setSelectedReportId);

  const { data: projects = [] } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [query, setQuery] = useState("");

  const effectiveProjectId =
    selectedProjectId || (projects.length > 0 ? projects[0].id : "");

  const createReport = useCreateReport(effectiveProjectId);
  const isOpen = activeModal === "create_report";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !effectiveProjectId || createReport.isPending) return;

    createReport.mutate(
      {
        projectId: effectiveProjectId,
        data: { query: query.trim() },
      },
      {
        onSuccess: (res) => {
          const reportId = res.report_id || res.id;
          setSelectedReportId(reportId);
          setQuery("");
          closeModal();
          router.push(`/reports/${reportId}`);
        },
      }
    );
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-report-title"
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeModal}
            className="fixed inset-0 bg-black/60 backdrop-blur-xs"
            aria-hidden="true"
          />

          {/* Modal Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 350, damping: 25 }}
            className="relative w-full max-w-lg rounded-card border border-border bg-surface p-6 shadow-2xl z-10"
          >
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-control bg-accent/10 text-accent">
                  <FilePlus2 className="h-4 w-4" aria-hidden="true" />
                </div>
                <div>
                  <h3 id="create-report-title" className="text-base font-semibold text-text-primary">
                    Launch Autonomous Research Run
                  </h3>
                  <p className="text-xs text-text-secondary">
                    Decomposes query into parallel agents with verified citations.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={closeModal}
                className="rounded-control p-1 text-text-secondary hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                aria-label="Close modal"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
              {/* Project Selection */}
              <div>
                <label
                  htmlFor="project-select"
                  className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1.5"
                >
                  Target Project
                </label>
                <select
                  id="project-select"
                  value={effectiveProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full rounded-control border border-border bg-surface-subtle px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-all"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title}
                    </option>
                  ))}
                </select>
              </div>

              {/* Research Query Prompt */}
              <div>
                <label
                  htmlFor="research-query-input"
                  className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1.5"
                >
                  Research Query / Thesis
                </label>
                <textarea
                  id="research-query-input"
                  required
                  rows={3}
                  placeholder="e.g. Compare Byzantine fault tolerance thresholds in DAG-based consensus protocols vs traditional linear chains."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full rounded-control border border-border bg-surface-subtle px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/60 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-all resize-none"
                  autoFocus
                />
              </div>

              {createReport.isError && (
                <div className="rounded-control bg-danger-subtle p-2.5 text-xs text-danger-text">
                  {createReport.error.detail || "Failed to schedule report. Please check your query or rate limits."}
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-text-secondary flex items-center gap-1">
                  <Sparkles className="h-3 w-3 text-accent" aria-hidden="true" />
                  Streamed via WebSocket in &lt;500ms
                </span>

                <div className="flex items-center gap-2.5">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={closeModal}
                    disabled={createReport.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={!query.trim() || !effectiveProjectId || createReport.isPending}
                    className="gap-1.5 min-w-28"
                  >
                    {createReport.isPending ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                        <span>Dispatching...</span>
                      </>
                    ) : (
                      <span>Dispatch Swarm</span>
                    )}
                  </Button>
                </div>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
