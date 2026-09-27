"use client";

import React, { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  ChevronDown,
  Clock,
  FileText,
  Loader2,
  Plus,
  Shield,
  Trash2,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { reportKeys, useReportCounts } from "@/hooks/useReports";
import { useAuth } from "@/components/auth-provider";
import { useQuery } from "@tanstack/react-query";
import { ReportSummaryResponse, ReportListResponse, ApiError } from "@/lib/api-client";

const PAGE_LIMIT = 50;

/**
 * Status filter tabs — Option B (user-friendly grouped).
 * "In progress" maps server-side to: researching, fact_checking, writing.
 * "running" is NOT a persisted ReportStatus and is excluded.
 */
const STATUS_TABS = [
  { id: "all", label: "All" },
  { id: "pending", label: "Pending" },
  { id: "planning", label: "Planning" },
  { id: "in_progress", label: "In progress" },
  { id: "complete", label: "Complete" },
  { id: "needs_review", label: "Needs review" },
  { id: "failed", label: "Failed" },
] as const;

type StatusTabId = typeof STATUS_TABS[number]["id"];

function getBadgeVariant(status: string): "complete" | "failed" | "pending" | "running" {
  const s = status?.toLowerCase() || "";
  if (s === "complete") return "complete";
  if (s === "failed") return "failed";
  if (s === "pending") return "pending";
  return "running";
}

export default function ReportsListPage() {
  const { user } = useAuth();
  const isGuest = user?.role === "guest";
  const [statusFilter, setStatusFilter] = useState<StatusTabId>("all");
  const [offset, setOffset] = useState(0);
  const [accumulatedItems, setAccumulatedItems] = useState<ReportSummaryResponse[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // ── Server-side status filter + first page ────────────────────────────────
  const { data: pageData, isLoading: isPageLoading } = useQuery<ReportListResponse, ApiError>({
    queryKey: reportKeys.list(undefined, { status: statusFilter, limit: PAGE_LIMIT, offset: 0 }),
    queryFn: () =>
      apiClient.getAllReports({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: PAGE_LIMIT,
        offset: 0,
      }),
  });

  // When the filter changes and fresh first-page data arrives, reset accumulated list
  useEffect(() => {
    if (pageData) {
      setAccumulatedItems(pageData.items);
      setOffset(0);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, pageData]);

  // First page items
  const firstPageItems = pageData?.items ?? [];
  // Total for current filter
  const total = pageData?.total ?? 0;
  const hasMore = pageData?.has_more ?? false;

  // Display either accumulated (after Load More) or first page
  const displayedItems = accumulatedItems.length > 0 ? accumulatedItems : firstPageItems;

  // ── Per-status counts for tab badges ─────────────────────────────────────
  const { data: counts } = useReportCounts();

  const getTabCount = (tabId: StatusTabId): number => {
    if (!counts) return 0;
    if (tabId === "all") return counts.all;
    return counts[tabId as keyof typeof counts] as number ?? 0;
  };

  // ── Filter tab change ─────────────────────────────────────────────────────
  const handleStatusFilter = useCallback((tab: StatusTabId) => {
    setStatusFilter(tab);
    setOffset(0);
    setAccumulatedItems([]);
  }, []);

  // ── Load More ─────────────────────────────────────────────────────────────
  const handleLoadMore = async () => {
    const nextOffset = offset + PAGE_LIMIT;
    setLoadingMore(true);
    try {
      const nextPage = await apiClient.getAllReports({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: PAGE_LIMIT,
        offset: nextOffset,
      });
      setAccumulatedItems((prev) => {
        const existingIds = new Set(prev.map((r) => r.id));
        const newItems = nextPage.items.filter((r) => !existingIds.has(r.id));
        return [...prev, ...newItems];
      });
      setOffset(nextOffset);
    } finally {
      setLoadingMore(false);
    }
  };

  // ── Delete ────────────────────────────────────────────────────────────────
  const handleDeleteReport = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this research report?")) return;
    setDeletingId(id);
    try {
      await apiClient.deleteReport(id);
      setAccumulatedItems((prev) => prev.filter((r) => r.id !== id));
      queryClient.invalidateQueries({ queryKey: reportKeys.all });
    } finally {
      setDeletingId(null);
    }
  };

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
          {!isGuest ? (
            <Button asChild size="sm" className="flex items-center gap-2 bg-accent text-accent-foreground">
              <Link href="/reports/new">
                <Plus className="h-4 w-4" />
                <span>New Report</span>
              </Link>
            </Button>
          ) : (
            <Button
              size="sm"
              disabled
              className="flex items-center gap-2 bg-accent text-accent-foreground opacity-50 cursor-not-allowed"
              title="Guest Judge: Read-only evaluation mode"
            >
              <Plus className="h-4 w-4" />
              <span>Read-Only Mode</span>
            </Button>
          )}
        </div>
      </div>

      {/* Guest read-only banner */}
      {isGuest && (
        <div className="flex items-center justify-between rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-500">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 shrink-0" />
            <span className="font-semibold">Guest Judge — Read-only</span>
            <span className="text-xs text-text-secondary hidden sm:inline">
              — You are viewing curated demo reports. Generating or modifying reports is disabled.
            </span>
          </div>
        </div>
      )}

      {/* Status Filter Tabs — server-side, backend-authoritative counts */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {STATUS_TABS.map((tab) => {
          const count = getTabCount(tab.id);
          const isActive = statusFilter === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => handleStatusFilter(tab.id)}
              className={`inline-flex items-center gap-2 rounded-control px-3 py-1.5 text-xs font-medium capitalize transition-colors whitespace-nowrap ${
                isActive
                  ? "bg-accent text-accent-foreground font-semibold shadow-xs"
                  : "border border-border bg-surface text-text-secondary hover:text-text-primary"
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono font-medium ${
                  isActive
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

      {/* Total visible count */}
      {!isPageLoading && pageData && (
        <p className="text-xs text-text-secondary">
          Showing{" "}
          <strong>{displayedItems.length}</strong> of{" "}
          <strong>{total}</strong> visible reports
          {statusFilter !== "all" && (
            <span>
              {" "}with status{" "}
              <strong>{STATUS_TABS.find((t) => t.id === statusFilter)?.label}</strong>
            </span>
          )}
          .
        </p>
      )}

      {/* Reports Grid */}
      {isPageLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full rounded-card" />
          <Skeleton className="h-20 w-full rounded-card" />
          <Skeleton className="h-20 w-full rounded-card" />
        </div>
      ) : displayedItems.length === 0 ? (
        <Card className="border-dashed border-border bg-surface/50 p-8 text-center">
          <CardContent className="space-y-3">
            <FileText className="mx-auto h-8 w-8 text-text-secondary" />
            <div className="text-sm font-medium text-text-primary">No reports found</div>
            <p className="text-xs text-text-secondary">
              {statusFilter !== "all"
                ? `No reports with status "${STATUS_TABS.find((t) => t.id === statusFilter)?.label}" found.`
                : "No reports exist in the current workspace."}
            </p>
            {statusFilter !== "all" ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleStatusFilter("all")}
                className="mt-2"
              >
                Clear filter
              </Button>
            ) : !isGuest ? (
              <Button asChild size="sm" variant="outline" className="mt-2">
                <Link href="/reports/new">Create Report</Link>
              </Button>
            ) : null}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {displayedItems.map((report) => (
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
                      <span
                        className="flex items-center gap-1 text-[11px] text-text-secondary"
                        suppressHydrationWarning
                      >
                        <Clock className="h-3 w-3" />
                        {report.created_at ? report.created_at.slice(0, 10) : "Recent"}
                      </span>
                      {!isGuest && (
                        <button
                          type="button"
                          onClick={(e) => handleDeleteReport(e, report.id)}
                          disabled={deletingId === report.id}
                          className="p-1 text-text-secondary hover:text-danger rounded hover:bg-danger/10 transition-colors"
                          title="Delete report"
                        >
                          {deletingId === report.id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="h-3.5 w-3.5" />
                          )}
                        </button>
                      )}
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

          {/* Load More — only when more pages exist */}
          {hasMore || displayedItems.length < total ? (
            <div className="flex justify-center pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="gap-2"
              >
                {loadingMore ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
                <span>
                  {loadingMore
                    ? "Loading..."
                    : `Load more (${total - displayedItems.length} remaining)`}
                </span>
              </Button>
            </div>
          ) : (
            <p className="text-center text-xs text-text-secondary pt-2">
              All {total} reports loaded.
            </p>
          )}
        </>
      )}
    </div>
  );
}
