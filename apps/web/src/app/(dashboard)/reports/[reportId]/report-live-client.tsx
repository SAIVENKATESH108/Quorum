"use client";

import React, { useEffect, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ActivityFeed } from "@/components/report/activity-feed";
import { PipelineStages } from "@/components/report/pipeline-stages";
import { ReportHeader } from "@/components/report/report-header";
import { ReportView } from "@/components/report/report-view";
import { useReportEvents } from "@/hooks/useReportEvents";
import { reportKeys, useCreateReport } from "@/hooks/useReports";
import { ReportDetailResponse, ReportStatus } from "@/lib/api-client";
import { useAgentEventsStore } from "@/stores/agentEventsStore";
import { useUiStore } from "@/stores/uiStore";

interface ReportLiveClientProps {
  initialReport: ReportDetailResponse;
  reportId: string;
}

export function ReportLiveClient({ initialReport, reportId }: ReportLiveClientProps) {
  const queryClient = useQueryClient();
  const setSelectedReportId = useUiStore((state) => state.setSelectedReportId);

  // Sync selected report id in ephemeral UI store
  useEffect(() => {
    if (reportId) {
      setSelectedReportId(reportId);
    }
  }, [reportId, setSelectedReportId]);

  const reportStatus = initialReport?.status;
  const reportQuery = initialReport?.query;
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

  // Effective status considers live WebSocket stream first, then server initial data
  const effectiveStatus: ReportStatus =
    liveStatus || initialReport?.status || "complete";

  // Invalidate queries if status transitions to complete
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
  const createReportMutation = useCreateReport(initialReport?.project_id);
  const handleRetry = () => {
    if (!initialReport?.project_id || !initialReport?.query) return;
    createReportMutation.mutate({
      projectId: initialReport.project_id,
      data: { query: initialReport.query },
    });
  };

  const displayReport: ReportDetailResponse = {
    ...initialReport,
    status: effectiveStatus,
  };

  const isComplete = effectiveStatus === "complete";

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto px-1 sm:px-2">
      {/* 1. Dashboard Header */}
      <ReportHeader
        reportId={reportId}
        query={initialReport.query}
        status={effectiveStatus}
        createdAt={initialReport.created_at}
        connectionState={connectionState}
        onRetry={handleRetry}
      />

      {/* 2. Top-level Pipeline Stages & Parallel Research Multi-Agent Sub-Cards */}
      <section aria-label="Orchestration Pipeline Visualization">
        <PipelineStages
          status={effectiveStatus}
          query={initialReport.query}
          researchTasks={researchTasks}
          errorMessage={initialReport.error_message || undefined}
        />
      </section>

      {/* 3. Live Streaming Activity Feed */}
      <section aria-label="Real-time Activity Stream">
        <ActivityFeed
          events={events}
          overallStatus={effectiveStatus}
          query={initialReport.query}
        />
      </section>

      {/* 4. Interactive Report View */}
      {isComplete && (
        <section aria-label="Finished Research Report">
          <ReportView report={displayReport} />
        </section>
      )}
    </div>
  );
}
