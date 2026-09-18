"use client";

import { useEffect, useRef } from "react";
import { apiClient, getAuthToken, isMockApiMode, isValidUuid } from "@/lib/api-client";
import {
  ConnectionState,
  ReportEventPayload,
  ReportStatus,
  useAgentEventsStore,
} from "@/stores/agentEventsStore";

const TERMINAL_STATUSES: ReportStatus[] = ["complete", "failed"];
const EMPTY_EVENTS: ReportEventPayload[] = [];

interface UseReportEventsOptions {
  status?: ReportStatus;
  query?: string;
  enabled?: boolean;
  onEvent?: (event: ReportEventPayload) => void;
}

import { decomposeQueryTelemetry } from "@/lib/telemetry-engine";

export function useReportEvents(
  reportId: string | null,
  options: UseReportEventsOptions = {}
) {
  const { status, query, enabled = true, onEvent } = options;

  const handleIncomingEvent = useAgentEventsStore(
    (state) => state.handleIncomingEvent
  );
  const setConnectionStatus = useAgentEventsStore(
    (state) => state.setConnectionStatus
  );

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const isManuallyClosedRef = useRef(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  // Check if report is actively in-progress
  const isReportActive = reportId && (!status || !TERMINAL_STATUSES.includes(status));

  useEffect(() => {
    if (!reportId || !enabled || !isReportActive) {
      if (reportId) {
        setConnectionStatus(reportId, "disconnected");
      }
      return;
    }

    isManuallyClosedRef.current = false;

    // --- Simulated Mock Stream for local preview / mock mode ---
    if (isMockApiMode() || !isValidUuid(reportId)) {
      setConnectionStatus(reportId, "connected");

      const userQuery = query?.trim() || "Active Research Inquiry";
      const decomp = decomposeQueryTelemetry(userQuery);
      const sub1 = decomp.subtopics[0].title;
      const sub2 = decomp.subtopics[1].title;
      const sub3 = decomp.subtopics[2].title;
      const src1 = decomp.subtopics[0].source;
      const src2 = decomp.subtopics[1].source;
      const src3 = decomp.subtopics[2].source;
      const claims1 = decomp.subtopics[0].claims;
      const claims2 = decomp.subtopics[1].claims;
      const claims3 = decomp.subtopics[2].claims;
      const cit1 = decomp.subtopics[0].citations;
      const cit2 = decomp.subtopics[1].citations;
      const cit3 = decomp.subtopics[2].citations;
      const totalClaims = claims1 + claims2 + claims3;
      const confScore = Number((decomp.confidenceScore / 100).toFixed(3));

      const mockEvents: Array<{ delay: number; event: ReportEventPayload }> = [
        {
          delay: 500,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              status: "planning",
              agent_role: "orchestrator",
              metadata: {
                message: `Orchestrator decomposing query into 3 parallel subtopics across ${decomp.domainName}`,
                stage: "DAG generation",
                subtopics: 3,
                domain: decomp.domain,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 1800,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              status: "researching",
              agent_role: "orchestrator",
              metadata: {
                message: `Dispatched 3 parallel researcher agents across ${decomp.sourcesSummary}`,
                parallel_tasks: 3,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 2200,
          event: {
            type: "task_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-r1`,
              task_id: `task-${reportId}-r1`,
              status: "running",
              agent_role: "researcher",
              metadata: {
                task_type: "research",
                subtopic: sub1,
                worker_index: 1,
                source: src1,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 2500,
          event: {
            type: "task_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-r2`,
              task_id: `task-${reportId}-r2`,
              status: "running",
              agent_role: "researcher",
              metadata: {
                task_type: "research",
                subtopic: sub2,
                worker_index: 2,
                source: src2,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 2800,
          event: {
            type: "task_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-r3`,
              task_id: `task-${reportId}-r3`,
              status: "running",
              agent_role: "researcher",
              metadata: {
                task_type: "research",
                subtopic: sub3,
                worker_index: 3,
                source: src3,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 4800,
          event: {
            type: "task_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-r1`,
              task_id: `task-${reportId}-r1`,
              status: "succeeded",
              agent_role: "researcher",
              metadata: {
                task_type: "research",
                subtopic: sub1,
                claims: claims1,
                citations: cit1,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 6000,
          event: {
            type: "task_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-r2`,
              task_id: `task-${reportId}-r2`,
              status: "succeeded",
              agent_role: "researcher",
              metadata: {
                task_type: "research",
                subtopic: sub2,
                claims: claims2,
                citations: cit2,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 7200,
          event: {
            type: "task_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-r3`,
              task_id: `task-${reportId}-r3`,
              status: "succeeded",
              agent_role: "researcher",
              metadata: {
                task_type: "research",
                subtopic: sub3,
                claims: claims3,
                citations: cit3,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 8400,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-fc`,
              status: "fact_checking",
              agent_role: "fact_checker",
              metadata: {
                message: `Cross-checked ${totalClaims} empirical claims across ${decomp.sourcesSummary}`,
                confidence_score: confScore,
                contradictions: 0,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 10800,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-wr`,
              status: "writing",
              agent_role: "writer",
              metadata: {
                message: `Synthesized ${totalClaims} verified claims with ${cit1 + cit2 + cit3} peer-reviewed citations`,
                sections_authored: 3,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 13200,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              status: "complete",
              metadata: {
                message: "Report finalized and ready for inspection",
                total_duration_seconds: 13.2,
              },
            },
            timestamp: new Date().toISOString(),
          },
        },
      ];

      const timeouts: NodeJS.Timeout[] = [];
      mockEvents.forEach(({ delay, event }) => {
        const t = setTimeout(() => {
          if (!isManuallyClosedRef.current) {
            handleIncomingEvent(reportId, event);
            onEventRef.current?.(event);
            if (event.data.status === "complete") {
              apiClient.completeMockReport(reportId);
              setConnectionStatus(reportId, "disconnected");
            }
          }
        }, delay);
        timeouts.push(t);
      });

      return () => {
        timeouts.forEach(clearTimeout);
      };
    }

    // --- Live WebSocket Connection ---
    async function connect() {
      if (!reportId) return;

      const wsBase =
        process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, "") ||
        "ws://localhost:8000/ws";

      const token = (await getAuthToken()) || "mock_token";
      const wsUrl = `${wsBase}/reports/${reportId}?token=${encodeURIComponent(token)}`;

      setConnectionStatus(reportId, retryCountRef.current > 0 ? "reconnecting" : "connecting");

      try {
        const ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          if (isManuallyClosedRef.current) {
            ws.close(1000);
            return;
          }
          retryCountRef.current = 0;
          setConnectionStatus(reportId, "connected");
        };

        ws.onmessage = (event) => {
          try {
            const parsed: ReportEventPayload = JSON.parse(event.data);
            handleIncomingEvent(reportId, parsed);
            onEventRef.current?.(parsed);

            // Clean up connection on terminal status
            const currentStatus = parsed.data?.status;
            if (
              typeof currentStatus === "string" &&
              TERMINAL_STATUSES.includes(currentStatus.toLowerCase() as ReportStatus)
            ) {
              isManuallyClosedRef.current = true;
              ws.close(1000, "Report complete");
              setConnectionStatus(reportId, "disconnected");
            }
          } catch (parseErr) {
            console.warn("[WS] Error parsing incoming WebSocket payload:", parseErr);
          }
        };

        ws.onerror = (err) => {
          console.warn("[WS] Socket encountered an error:", err);
        };

        ws.onclose = (event) => {
          if (isManuallyClosedRef.current) {
            setConnectionStatus(reportId, "disconnected");
            return;
          }

          // If closed cleanly with code 1000 or 1008 (unauthorized), do not reconnect
          if (event.code === 1000 || event.code === 1008) {
            setConnectionStatus(reportId, "disconnected");
            return;
          }

          // Exponential backoff reconnect: min(1000 * 2^retries, 15000) + jitter
          const maxRetries = 6;
          if (retryCountRef.current < maxRetries) {
            const delay =
              Math.min(1000 * Math.pow(2, retryCountRef.current), 15000) +
              Math.random() * 500;
            retryCountRef.current += 1;

            setConnectionStatus(reportId, "reconnecting");
            reconnectTimeoutRef.current = setTimeout(connect, delay);
          } else {
            setConnectionStatus(reportId, "disconnected");
          }
        };
      } catch (connErr) {
        console.warn("[WS] Connection initiation error:", connErr);
        setConnectionStatus(reportId, "disconnected");
      }
    }

    connect();

    return () => {
      isManuallyClosedRef.current = true;
      const timeoutId = reconnectTimeoutRef.current;
      if (timeoutId) {
        clearTimeout(timeoutId);
        reconnectTimeoutRef.current = null;
      }
      const ws = socketRef.current;
      if (ws) {
        ws.close(1000, "Component unmounted");
        socketRef.current = null;
      }
      setConnectionStatus(reportId, "disconnected");
    };
  }, [reportId, query, enabled, isReportActive, handleIncomingEvent, setConnectionStatus]);

  // Read current live states from Zustand store
  const liveStatus = useAgentEventsStore(
    (state) => (reportId ? state.reportStatuses[reportId] : undefined)
  );
  const liveConnection = useAgentEventsStore(
    (state) =>
      reportId ? state.connectionStatuses[reportId] || "disconnected" : "disconnected"
  );
  const liveEvents = useAgentEventsStore(
    (state) =>
      reportId && state.eventsLog[reportId]
        ? state.eventsLog[reportId]
        : EMPTY_EVENTS
  );

  return {
    status: liveStatus || status,
    connectionState: liveConnection as ConnectionState,
    events: liveEvents,
  };
}
