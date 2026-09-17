"use client";

import React, { useEffect, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ActivityFeed } from "@/components/report/activity-feed";
import { PipelineStages } from "@/components/report/pipeline-stages";
import { ReportEmptyState } from "@/components/report/report-empty-state";
import { ReportHeader } from "@/components/report/report-header";
import { ReportView } from "@/components/report/report-view";
import { Skeleton } from "@/components/ui/skeleton";
import { useReportEvents } from "@/hooks/useReportEvents";
import { reportKeys, useCreateReport, useReport } from "@/hooks/useReports";
import {
  generateDynamicReportData,
  ReportDetailResponse,
  ReportStatus,
} from "@/lib/api-client";
import { useAgentEventsStore } from "@/stores/agentEventsStore";
import { useUiStore } from "@/stores/uiStore";

interface ReportDetailPageProps {
  params: {
    reportId: string;
  };
}

export default function ReportDetailPage({ params }: ReportDetailPageProps) {
  const { reportId } = params;
  const queryClient = useQueryClient();
  const setSelectedReportId = useUiStore((state) => state.setSelectedReportId);

  // Sync selected report id in ephemeral UI store
  useEffect(() => {
    if (reportId) {
      setSelectedReportId(reportId);
    }
  }, [reportId, setSelectedReportId]);

  // TanStack Query: Fetch initial/current report state
  const {
    data: report,
    isLoading,
    isError,
    error,
    refetch,
  } = useReport(reportId);

  const reportStatus = report?.status;
  const reportQuery = report?.query;
  const reportEventsOptions = useMemo(
    () => ({ status: reportStatus, query: reportQuery }),
    [reportStatus, reportQuery]
  );

  // Real-time WebSocket hook: Subscribes to live execution events
  const {
    status: liveStatus,
    connectionState,
    events,
  } = useReportEvents(reportId, reportEventsOptions);

  // Effective status considers live WebSocket stream first, then server data
  const effectiveStatus: ReportStatus =
    liveStatus || report?.status || "pending";

  // Re-fetch report details when report completes to pull sections and sources
  useEffect(() => {
    if (effectiveStatus === "complete") {
      queryClient.invalidateQueries({
        queryKey: reportKeys.detail(reportId),
      });
    }
  }, [effectiveStatus, reportId, queryClient]);

  // Extract parallel research tasks from Zustand store for the Researching stage
  const allTasks = useAgentEventsStore((state) => state.tasks);
  const researchTasks = useMemo(() => {
    return Object.values(allTasks).filter(
      (t) =>
        t.reportId === reportId &&
        (t.taskType === "research" ||
          t.id.includes("research") ||
          t.id.includes("-r"))
    );
  }, [allTasks, reportId]);

  // Retry mutation handler if report failed
  const createReportMutation = useCreateReport(report?.project_id);
  const handleRetry = () => {
    if (!report?.project_id || !report?.query) return;
    createReportMutation.mutate({
      projectId: report.project_id,
      data: { query: report.query },
    });
  };

  // 1. Loading State: Render shimmer Skeletons (never a blank screen)
  if (isLoading && !report) {
    return (
      <div className="space-y-8 animate-in fade-in duration-300">
        {/* Header Skeleton */}
        <div className="space-y-3 pb-4 border-b border-border">
          <Skeleton className="h-4 w-32 rounded-full" />
          <Skeleton className="h-8 w-3/4 rounded-control" />
          <Skeleton className="h-4 w-48 rounded-full" />
        </div>

        {/* Pipeline Skeleton Grid */}
        <div className="space-y-3">
          <Skeleton className="h-5 w-40 rounded-full" />
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-28 rounded-card" />
            ))}
          </div>
        </div>

        {/* Research Swarm Skeleton */}
        <div className="space-y-3">
          <Skeleton className="h-32 rounded-card" />
        </div>

        {/* Activity Stream Skeleton */}
        <div className="space-y-3">
          <Skeleton className="h-56 rounded-card" />
        </div>
      </div>
    );
  }

  // 2. Error State: Report not found or 404
  if (isError || !report) {
    return (
      <ReportEmptyState
        reportId={reportId}
        errorMessage={error?.detail || error?.message}
        onRetry={() => refetch()}
      />
    );
  }

  // Fallback enriched report data for mock demonstration preview
  const fallbackData = generateDynamicReportData(reportId, report.query);
  const displayReport: ReportDetailResponse = {
    ...report,
    status: effectiveStatus,
    // Provide fallback sections for preview if backend not yet generating them
    sections:
      report.sections && report.sections.length > 0
        ? report.sections
        : fallbackData.sections,
    sources:
      report.sources && report.sources.length > 0
        ? report.sources
        : fallbackData.sources,
  };

  const isComplete = effectiveStatus === "complete";

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto px-1 sm:px-2">
      {/* 1. Dashboard Header */}
      <ReportHeader
        reportId={reportId}
        query={report.query}
        status={effectiveStatus}
        createdAt={report.created_at}
        connectionState={connectionState}
        onRetry={handleRetry}
      />

      {/* 2. Top-level Pipeline Stages & Parallel Research Multi-Agent Sub-Cards */}
      <section aria-label="Orchestration Pipeline Visualization">
        <PipelineStages
          status={effectiveStatus}
          query={report.query}
          researchTasks={researchTasks}
          errorMessage={report.error_message || undefined}
        />
      </section>

      {/* 3. Live Streaming Activity Feed */}
      <section aria-label="Real-time Activity Stream">
        <ActivityFeed
          events={events}
          overallStatus={effectiveStatus}
          query={report.query}
        />
      </section>

      {/* 4. Finished Report Reveal on Completion */}
      {isComplete && (
        <section aria-label="Finished Research Report">
          <ReportView report={displayReport} />
        </section>
      )}
    </div>
  );
}
