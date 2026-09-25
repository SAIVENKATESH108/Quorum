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
  const handleIncomingEvent = useAgentEventsStore((state) => state.handleIncomingEvent);

  // Sync selected report id in ephemeral UI store
  useEffect(() => {
    if (reportId) {
      setSelectedReportId(reportId);
    }
  }, [reportId, setSelectedReportId]);

  // ── KEY FIX ────────────────────────────────────────────────────────────────
  // Seed the Zustand store with the persisted DB status on first client mount.
  // Without this, the store is empty after a page refresh and the pipeline
  // stage visualizer falls back to "pending" until a WebSocket event arrives —
  // which never comes for already-completed reports (WS is skipped for terminal
  // statuses). With the seed, the store immediately reflects the real status
  // so PipelineStages renders the correct DONE/FAILED indicators.
  const initialStatus = initialReport?.status;
  useEffect(() => {
    if (reportId && initialStatus) {
      handleIncomingEvent(reportId, {
        type: "report_status",
        data: {
          report_id: reportId,
          status: initialStatus,
          metadata: {
            message: "Seeded from server-rendered initial report status",
            source: "ssr_seed",
          },
        },
        timestamp: new Date().toISOString(),
      });
    }
    // Intentionally only re-run when the server-provided status changes (e.g.
    // after router.refresh()). handleIncomingEvent is a stable Zustand action.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId, initialStatus]);
  // ──────────────────────────────────────────────────────────────────────────

  const reportEventsOptions = useMemo(
    () => ({ status: initialStatus, query: initialReport?.query }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [initialStatus, initialReport?.query]
  );

  // Real-time WebSocket hook: subscribes to live execution events.
  // For terminal statuses (complete/failed), the hook exits early and the seed
  // above is the only status source.
  const {
    status: liveStatus,
    connectionState,
    events,
  } = useReportEvents(reportId, reportEventsOptions);

  // Effective status: live WS stream > seeded store > server SSR > safe fallback
  const effectiveStatus: ReportStatus =
    liveStatus || initialReport?.status || "complete";

  // Invalidate queries when the pipeline reaches a terminal state
  useEffect(() => {
    if (effectiveStatus === "complete" || effectiveStatus === "needs_review") {
      queryClient.invalidateQueries({
        queryKey: reportKeys.detail(reportId),
      });
      router.refresh();
    }
  }, [effectiveStatus, reportId, queryClient, router]);

  // Parallel research task sub-cards
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

  // Retry: re-queue the same query into a new report
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
    <div className="space-y-8 animate-in fade-in duration-500 w-full max-w-full overflow-x-hidden">
      {/* 1. Report Dashboard Header */}
      <ReportHeader
        reportId={reportId}
        query={initialReport.query}
        status={effectiveStatus}
        createdAt={initialReport.created_at}
        connectionState={connectionState}
        onRetry={handleRetry}
      />

      {/* 2. Post-Generation Action Suite (only shown for completed reports) */}
      {isComplete && (
        <section aria-label="Post-Generation Action Suite">
          <ReportActionSuite
            report={displayReport}
            onRetry={handleRetry}
            onStatusChange={() => {
              queryClient.invalidateQueries({
                queryKey: reportKeys.detail(reportId),
              });
              router.refresh();
            }}
          />
        </section>
      )}

      {/* 3. Pipeline Stage Visualization */}
      <section aria-label="Orchestration Pipeline Visualization" className="w-full min-w-0">
        <PipelineStages
          status={effectiveStatus}
          query={initialReport.query}
          researchTasks={researchTasks}
          errorMessage={initialReport.error_message || undefined}
        />
      </section>

      {/* 4. Live Telemetry Console */}
      <section aria-label="Real-time Execution Telemetry Console" className="w-full min-w-0">
        <LiveTelemetryConsole
          reportId={reportId}
          query={initialReport.query}
          status={effectiveStatus}
          events={events}
          createdAt={initialReport.created_at}
        />
      </section>

      {/* 5. Activity Feed */}
      <section aria-label="Real-time Activity Stream" className="w-full min-w-0">
        <ActivityFeed
          events={events}
          overallStatus={effectiveStatus}
          query={initialReport.query}
        />
      </section>

      {/* 6. Completed Report Body */}
      {isComplete && (
        <section aria-label="Finished Research Report" className="w-full min-w-0">
          <ReportView report={displayReport} />
        </section>
      )}
    </div>
  );
}
