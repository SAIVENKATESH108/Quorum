"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  FilePlus,
  FileText,
  Folder,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjects } from "@/hooks/useProjects";
import { useReports } from "@/hooks/useReports";

function getBadgeVariant(status: string): "complete" | "failed" | "pending" | "running" {
  if (status === "complete") return "complete";
  if (status === "failed") return "failed";
  if (status === "pending") return "pending";
  return "running";
}

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const queryClient = useQueryClient();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDeleteReport = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Delete this research report?")) return;
    setDeletingId(id);
    try {
      await apiClient.deleteReport(id);
      queryClient.invalidateQueries({ queryKey: ["reports", projectId] });
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    } finally {
      setDeletingId(null);
    }
  };

  const { data: projects = [], isLoading: projectsLoading } = useProjects();
  const { data: reports = [], isLoading: reportsLoading } = useReports(projectId);

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const project = projects.find((p) => p.id === projectId);

  const filteredReports = reports.filter((report) => {
    const matchesSearch = report.query.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || report.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const completeCount = reports.filter((r) => r.status === "complete").length;
  const runningCount = reports.filter((r) =>
    ["planning", "researching", "fact_checking", "writing", "running"].includes(r.status)
  ).length;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Top Breadcrumb / Back Link */}
      <div>
        <Link
          href="/projects"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-text-primary transition-colors mb-3"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to all projects</span>
        </Link>

        {/* Project Header Banner */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-card bg-accent/10 text-accent shadow-xs">
              <Folder className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-2xl font-bold tracking-tight text-text-primary">
                  {projectsLoading ? <Skeleton className="h-8 w-48" /> : project?.title || "Research Project"}
                </h1>
                <Badge variant="outline" className="text-xs font-mono">
                  {reports.length} {reports.length === 1 ? "report" : "reports"}
                </Badge>
              </div>
              <p className="text-sm text-text-secondary mt-1 flex items-center gap-2">
                <span>Autonomous multi-agent research domain.</span>
                {project && (
                  <span className="text-xs text-text-secondary/80" suppressHydrationWarning>
                    Created on {project.created_at ? project.created_at.slice(0, 10) : "Recent"}
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Button asChild size="sm" className="gap-2 bg-accent text-white shadow-xs">
              <Link href={`/reports/new?projectId=${projectId}`}>
                <Plus className="h-4 w-4" />
                <span>New Research Query</span>
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Total Investigations</span>
              <FileText className="h-4 w-4 text-text-secondary opacity-70" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-text-primary pt-1">
              {reports.length}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Multi-agent research pipelines executed in this project.
          </CardContent>
        </Card>

        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Verified &amp; Completed</span>
              <CheckCircle2 className="h-4 w-4 text-success" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-success pt-1">
              {completeCount}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Reports with fact-checked claims and structured citations.
          </CardContent>
        </Card>

        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Active Agent Swarms</span>
              <Sparkles className="h-4 w-4 text-accent" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-accent pt-1">
              {runningCount}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Pipelines currently executing in the distributed queue.
          </CardContent>
        </Card>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-secondary" />
          <input
            type="text"
            placeholder="Search report topics or questions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-control border border-border bg-surface text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1 bg-surface border border-border rounded-control p-1 text-xs">
          {["all", "complete", "researching", "failed"].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-xs font-medium capitalize transition-colors ${
                statusFilter === status
                  ? "bg-accent text-white shadow-xs"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
              }`}
            >
              {status === "all" ? "All Reports" : status}
            </button>
          ))}
        </div>
      </div>

      {/* Reports List */}
      {reportsLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full rounded-card" />
          <Skeleton className="h-20 w-full rounded-card" />
          <Skeleton className="h-20 w-full rounded-card" />
        </div>
      ) : filteredReports.length === 0 ? (
        <Card className="border-dashed border-border bg-surface/40 text-center py-12 px-4">
          <CardContent className="flex flex-col items-center justify-center space-y-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 text-accent">
              <FilePlus className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-text-primary">
                {searchQuery || statusFilter !== "all"
                  ? "No matching reports found"
                  : "No reports in this project yet"}
              </h3>
              <p className="text-sm text-text-secondary max-w-sm">
                {searchQuery || statusFilter !== "all"
                  ? "Try adjusting your search query or status filter."
                  : "Deploy autonomous researcher agents to generate your first intelligence report."}
              </p>
            </div>
            <Button asChild size="sm" className="gap-2">
              <Link href={`/reports/new?projectId=${projectId}`}>
                <Plus className="h-4 w-4" />
                <span>Launch First Report</span>
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredReports.map((report) => (
            <Card
              key={report.id}
              className="group border-border bg-surface hover:border-accent/40 transition-all shadow-xs hover:shadow-sm"
            >
              <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2.5">
                    <Badge variant={getBadgeVariant(report.status)}>
                      {report.status}
                    </Badge>
                    <span className="flex items-center gap-1 text-[11px] text-text-secondary" suppressHydrationWarning>
                      <Clock className="h-3 w-3" />
                      {report.created_at ? report.created_at.slice(0, 10) : "Recent"}
                    </span>
                  </div>

                  <Link
                    href={`/reports/${report.id}`}
                    className="block text-base font-semibold text-text-primary hover:text-accent transition-colors truncate"
                  >
                    {report.query}
                  </Link>

                  <p className="text-xs text-text-secondary">
                    Asynchronous multi-agent topological DAG execution with verified academic claims.
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button asChild variant="outline" size="sm" className="gap-1.5">
                    <Link href={`/reports/${report.id}`}>
                      <span>View Report</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleDeleteReport(e, report.id)}
                    disabled={deletingId === report.id}
                    className="h-8 w-8 p-0 text-text-secondary hover:text-danger hover:bg-danger/10"
                    title="Delete report"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
