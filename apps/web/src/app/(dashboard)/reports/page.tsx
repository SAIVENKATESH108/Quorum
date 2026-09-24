"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Plus,
  Clock,
  ArrowUpRight,
  Trash2,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { reportKeys, useReports } from "@/hooks/useReports";

function getBadgeVariant(status: string): "complete" | "failed" | "pending" | "running" {
  const s = status?.toLowerCase() || "";
  if (s === "complete" || s === "completed" || s === "succeeded") return "complete";
  if (s === "failed") return "failed";
  if (s === "pending") return "pending";
  return "running";
}

function matchesStatusFilter(status: string, filter: string): boolean {
  if (filter === "all") return true;
  const s = status?.toLowerCase() || "";
  if (filter === "complete") {
    return s === "complete" || s === "completed" || s === "succeeded";
  }
  if (filter === "researching") {
    return s === "researching" || s === "fact_checking" || s === "writing" || s === "running";
  }
  if (filter === "planning") {
    return s === "planning" || s === "queued";
  }
  if (filter === "pending") {
    return s === "pending";
  }
  return s === filter;
}

export default function ReportsListPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // The reports page is a workspace-wide view.
  const { data: reports = [], isLoading: isReportsLoading } = useReports();

  const handleDeleteReport = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this research report?")) return;
    setDeletingId(id);
    try {
      await apiClient.deleteReport(id);
      queryClient.invalidateQueries({ queryKey: reportKeys.all });
    } finally {
      setDeletingId(null);
    }
  };

  const displayedReports = reports;
  const filteredReports = displayedReports.filter((r) =>
    matchesStatusFilter(r.status, statusFilter)
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Research Reports
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Browse and inspect intelligence briefs compiled by the Quorum multi-agent pipeline.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button asChild size="sm" className="flex items-center gap-2 bg-accent text-accent-foreground">
            <Link href="/reports/new">
              <Plus className="h-4 w-4" />
              <span>New Report</span>
            </Link>
          </Button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {["all", "complete", "researching", "planning", "pending"].map((status) => {
          const count = status === "all"
            ? reports.length
            : reports.filter((r) => matchesStatusFilter(r.status, status)).length;
          return (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className={`inline-flex items-center gap-2 rounded-control px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                statusFilter === status
                  ? "bg-accent text-accent-foreground font-semibold shadow-xs"
                  : "border border-border bg-surface text-text-secondary hover:text-text-primary"
              }`}
            >
              <span>{status}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono font-medium ${
                  statusFilter === status
                    ? "bg-black/15 dark:bg-white/20 text-accent-foreground"
                    : "bg-surface-subtle text-text-secondary"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Reports Grid */}
      {isReportsLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full rounded-card" />
          <Skeleton className="h-20 w-full rounded-card" />
          <Skeleton className="h-20 w-full rounded-card" />
        </div>
      ) : filteredReports.length === 0 ? (
        <Card className="border-dashed border-border bg-surface/50 p-8 text-center">
          <CardContent className="space-y-3">
            <FileText className="mx-auto h-8 w-8 text-text-secondary" />
            <div className="text-sm font-medium text-text-primary">No reports found</div>
            <p className="text-xs text-text-secondary">
              Deploy a new autonomous swarm to begin researching this topic.
            </p>
            <Button asChild size="sm" variant="outline" className="mt-2">
              <Link href="/reports/new">Create Report</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredReports.map((report) => (
            <Link
              key={report.id}
              href={`/reports/${report.id}`}
              className="group flex flex-col justify-between rounded-card border border-border bg-surface p-5 transition-all hover:border-accent/50 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant={getBadgeVariant(report.status)} dot>
                    {report.status}
                  </Badge>
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1 text-[11px] text-text-secondary" suppressHydrationWarning>
                      <Clock className="h-3 w-3" />
                      {report.created_at ? report.created_at.slice(0, 10) : "Recent"}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => handleDeleteReport(e, report.id)}
                      disabled={deletingId === report.id}
                      className="p-1 text-text-secondary hover:text-danger rounded hover:bg-danger/10 transition-colors"
                      title="Delete report"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                <h3 className="text-sm font-semibold text-text-primary line-clamp-2 group-hover:text-accent transition-colors">
                  {report.query}
                </h3>
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-border/60 pt-3 text-xs text-text-secondary group-hover:text-text-primary">
                <span>View Live Pipeline</span>
                <ArrowUpRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
