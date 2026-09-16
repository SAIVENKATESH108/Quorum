"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  Play,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useProjects } from "@/hooks/useProjects";
import { useCreateReport } from "@/hooks/useReports";
import { useUiStore } from "@/stores/uiStore";

const PROMPT_SUGGESTIONS = [
  "Fault-Tolerant Consensus in Asynchronous Networks and FLP Impossibility",
  "Optimistic Rollups vs ZK Rollups: Prover Latency & Finality Benchmarks",
  "Autonomous Multi-Agent Consensus Mechanisms in Decentralized Computing",
  "Post-Quantum Cryptographic Transition: Lattice-based Signatures vs Dilithium",
];

export default function NewReportPage() {
  const router = useRouter();
  const setSelectedReportId = useUiStore((state) => state.setSelectedReportId);

  const { data: projects = [], isLoading: isProjectsLoading } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [query, setQuery] = useState("");

  const effectiveProjectId =
    selectedProjectId || (projects.length > 0 ? projects[0].id : "");

  const createReport = useCreateReport(effectiveProjectId);

  const handleSubmit = (e: React.FormEvent) => {
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
          router.push(`/reports/${reportId}`);
        },
      }
    );
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Back link */}
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Dashboard</span>
        </Link>
      </div>

      {/* Main Form Card */}
      <Card className="border border-border bg-surface shadow-md">
        <CardHeader className="pb-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-card bg-accent/15 text-accent">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold text-text-primary">
                Launch Autonomous Research Swarm
              </CardTitle>
              <CardDescription className="text-xs text-text-secondary">
                Decomposes your research topic into a topological DAG executed by parallel agents.
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Target Project */}
            <div className="space-y-1.5">
              <label
                htmlFor="new-report-project"
                className="text-xs font-semibold text-text-primary flex items-center justify-between"
              >
                <span>Target Project Workspace</span>
                {isProjectsLoading && (
                  <span className="text-[11px] font-normal text-text-secondary">
                    Loading workspaces...
                  </span>
                )}
              </label>

              <div className="relative">
                <select
                  id="new-report-project"
                  value={effectiveProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  disabled={isProjectsLoading || createReport.isPending}
                  className="w-full rounded-control border border-border bg-surface px-3 py-2 text-xs sm:text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-colors cursor-pointer"
                >
                  {projects.map((proj) => (
                    <option key={proj.id} value={proj.id}>
                      {proj.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Research Query Textarea */}
            <div className="space-y-1.5">
              <label
                htmlFor="new-report-query"
                className="text-xs font-semibold text-text-primary"
              >
                Research Topic or Hypothesis
              </label>
              <textarea
                id="new-report-query"
                rows={4}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="State your technical hypothesis, comparative question, or investigation scope in detail..."
                disabled={createReport.isPending}
                required
                className="w-full rounded-control border border-border bg-surface p-3 text-xs sm:text-sm text-text-primary placeholder:text-text-secondary/60 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-colors resize-y min-h-[100px]"
              />
              <p className="text-[11px] text-text-secondary">
                Orchestrator will synthesize 3-6 independent subtopics for parallel literature harvesting.
              </p>
            </div>

            {/* Prompt Suggestions */}
            <div className="space-y-2 pt-1">
              <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
                Sample Research Topics
              </span>
              <div className="flex flex-wrap gap-2">
                {PROMPT_SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => setQuery(suggestion)}
                    className="rounded-full border border-border bg-surface-subtle px-3 py-1 text-left text-xs text-text-secondary hover:border-accent hover:text-accent transition-all cursor-pointer"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>

            {/* Submit Bar */}
            <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
              <Link href="/">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={createReport.isPending}
                >
                  Cancel
                </Button>
              </Link>

              <Button
                type="submit"
                size="sm"
                disabled={!query.trim() || !effectiveProjectId || createReport.isPending}
                className="gap-1.5 px-5 shadow-xs"
              >
                {createReport.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Scheduling Swarm...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-current" />
                    <span>Start Autonomous Pipeline</span>
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
