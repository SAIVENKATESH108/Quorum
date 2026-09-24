"use client";

import React, { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ActivityFeed } from "@/components/report/activity-feed";
import { LiveTelemetryConsole } from "@/components/report/live-telemetry-console";
import { PipelineStages } from "@/components/report/pipeline-stages";
import { ReportActionSuite } from "@/components/report/report-action-suite";
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
  const router = useRouter();
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

  // Invalidate queries if status transitions to complete or needs_review
  useEffect(() => {
    if (effectiveStatus === "complete" || effectiveStatus === "needs_review") {
      queryClient.invalidateQueries({
        queryKey: reportKeys.detail(reportId),
      });
      router.refresh();
    }
  }, [effectiveStatus, reportId, queryClient, router]);

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

  const isComplete = effectiveStatus === "complete" || effectiveStatus === "needs_review";

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

      {/* 2. Post-Generation Action Suite: Regenerate, Swarm Chat, College vs Enterprise Docs, IEEE Novelty Paper, PDF Viewer, & Approval */}
      {isComplete && (
        <section aria-label="Post-Generation Action Suite">
          <ReportActionSuite
            report={displayReport}
            onRetry={handleRetry}
            onStatusChange={(newStatus) => {
              queryClient.invalidateQueries({
                queryKey: reportKeys.detail(reportId),
              });
              router.refresh();
            }}
          />
        </section>
      )}

      {/* 3. Top-level Pipeline Stages & Parallel Research Multi-Agent Sub-Cards */}
      <section aria-label="Orchestration Pipeline Visualization">
        <PipelineStages
          status={effectiveStatus}
          query={initialReport.query}
          researchTasks={researchTasks}
          errorMessage={initialReport.error_message || undefined}
        />
      </section>

      {/* 3. Real-time Process Initialization & Swarm Telemetry Console */}
      <section aria-label="Real-time Execution Telemetry Console">
        <LiveTelemetryConsole
          reportId={reportId}
          query={initialReport.query}
          status={effectiveStatus}
          events={events}
          createdAt={initialReport.created_at}
        />
      </section>

      {/* 4. Live Streaming Activity Feed */}
      <section aria-label="Real-time Activity Stream">
        <ActivityFeed
          events={events}
          overallStatus={effectiveStatus}
          query={initialReport.query}
        />
      </section>

      {/* 5. Interactive Report View */}
      {isComplete && (
        <section aria-label="Finished Research Report">
          <ReportView report={displayReport} />
        </section>
      )}
    </div>
  );
}
