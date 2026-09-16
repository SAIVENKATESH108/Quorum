"use client";

import { useEffect, useRef } from "react";
import { isMockApiMode } from "@/lib/api-client";
import {
  ConnectionState,
  ReportEventPayload,
  ReportStatus,
  useAgentEventsStore,
} from "@/stores/agentEventsStore";

const TERMINAL_STATUSES: ReportStatus[] = ["complete", "failed"];

interface UseReportEventsOptions {
  status?: ReportStatus;
  enabled?: boolean;
  onEvent?: (event: ReportEventPayload) => void;
}

export function useReportEvents(
  reportId: string | null,
  options: UseReportEventsOptions = {}
) {
  const { status, enabled = true, onEvent } = options;

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
    if (isMockApiMode()) {
      setConnectionStatus(reportId, "connected");

      const mockEvents: Array<{ delay: number; event: ReportEventPayload }> = [
        {
          delay: 500,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              status: "planning",
              agent_role: "orchestrator",
              metadata: { stage: "DAG generation", subtopics: 3 },
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
              run_id: `run-${reportId}-1`,
              task_id: `task-${reportId}-1`,
              status: "running",
              agent_role: "researcher",
              metadata: { task_type: "research_subtopic", node_id: "research_1" },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 5500,
          event: {
            type: "task_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-1`,
              task_id: `task-${reportId}-1`,
              status: "succeeded",
              agent_role: "researcher",
              metadata: { claims: 4, citations: 3 },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 7500,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-2`,
              status: "fact_checking",
              agent_role: "fact_checker",
              metadata: { confidence_score: 0.98 },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 10500,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              run_id: `run-${reportId}-3`,
              status: "writing",
              agent_role: "writer",
              metadata: { sections_authored: 2 },
            },
            timestamp: new Date().toISOString(),
          },
        },
        {
          delay: 13500,
          event: {
            type: "report_status",
            data: {
              report_id: reportId,
              status: "complete",
              metadata: { total_duration_seconds: 13.5 },
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
            onEvent?.(event);
            if (event.data.status === "complete") {
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
    function connect() {
      if (!reportId) return;

      const wsBase =
        process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, "") ||
        "ws://localhost:8000/ws";

      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("quorum-auth-token") || "mock_token"
          : "";

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
            onEvent?.(parsed);

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
  }, [reportId, enabled, isReportActive, handleIncomingEvent, setConnectionStatus, onEvent]);

  // Read current live states from Zustand store
  const liveStatus = useAgentEventsStore(
    (state) => (reportId ? state.reportStatuses[reportId] : undefined)
  );
  const liveConnection = useAgentEventsStore(
    (state) =>
      reportId ? state.connectionStatuses[reportId] || "disconnected" : "disconnected"
  );
  const liveEvents = useAgentEventsStore(
    (state) => (reportId ? state.eventsLog[reportId] || [] : [])
  );

  return {
    status: liveStatus || status,
    connectionState: liveConnection as ConnectionState,
    events: liveEvents,
  };
}
