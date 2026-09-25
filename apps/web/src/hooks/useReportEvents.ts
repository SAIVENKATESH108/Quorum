"use client";

import { useEffect, useRef } from "react";
import { getAuthToken } from "@/lib/api-client";
import {
  ConnectionState,
  ReportEventPayload,
  ReportStatus,
  useAgentEventsStore,
} from "@/stores/agentEventsStore";

const TERMINAL_STATUSES: ReportStatus[] = ["complete", "needs_review", "failed"];
const EMPTY_EVENTS: ReportEventPayload[] = [];

function resolveWebSocketBaseUrl(): string | null {
  const configuredWsUrl = process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, "");
  const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  // If explicitly configured, use it
  if (configuredWsUrl) {
    return configuredWsUrl;
  }

  // If frontend is running on localhost/127.0.0.1 in browser, use localhost WebSocket backend
  if (typeof window !== "undefined") {
    const isLocalhost =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1";
    if (isLocalhost) {
      return "ws://localhost:8000/ws";
    }
  }

  if (configuredApiUrl && !configuredApiUrl.includes("localhost")) {
    return `${configuredApiUrl.replace(/^http/, "ws")}/ws`;
  }

  // On deployed cloud instances without custom WebSocket server, fallback to Neon Polling
  return null;
}

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
  const handleIncomingEvent = useAgentEventsStore((state) => state.handleIncomingEvent);
  const setConnectionStatus = useAgentEventsStore((state) => state.setConnectionStatus);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const isManuallyClosedRef = useRef(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const isReportActive = reportId && (!status || !TERMINAL_STATUSES.includes(status));

  useEffect(() => {
    if (!reportId || !enabled) {
      if (reportId) setConnectionStatus(reportId, "disconnected");
      return;
    }

    if (!isReportActive) {
      // Completed or failed report is fully synchronized
      setConnectionStatus(reportId, "connected");
      return;
    }

    isManuallyClosedRef.current = false;

    async function connect() {
      if (!reportId) return;

      const wsBase = resolveWebSocketBaseUrl();

      // If WebSocket is not deployed in current environment, activate resilient Neon polling fallback
      if (!wsBase) {
        // Informational only — not an error. Production deployments without a
        // dedicated WebSocket server use HTTP polling as the fallback transport.
        console.info(
          "[Quorum] WebSocket transport unavailable (NEXT_PUBLIC_WS_URL not set). "
          + "Using HTTP polling fallback for pipeline status updates."
        );
        setConnectionStatus(reportId, "connected");

        // Polling fallback: polls the report endpoint every 3 s until terminal
        const poll = async () => {
          if (isManuallyClosedRef.current || !reportId) return;
          try {
            const res = await fetch(`/api/reports/${reportId}`, { cache: "no-store" });
            if (res.ok) {
              const data = await res.json();
              if (data && data.status) {
                const polledStatus = data.status as ReportStatus;
                handleIncomingEvent(reportId, {
                  type: "report_status",
                  data: {
                    report_id: reportId,
                    status: polledStatus,
                    metadata: {
                      message: `Pipeline polled: ${polledStatus}`,
                      source: "http_polling_fallback",
                    },
                  },
                  timestamp: new Date().toISOString(),
                });

                if (TERMINAL_STATUSES.includes(polledStatus)) {
                  if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                  }
                }
              }
            }
          } catch {
            // Polling retry — network blip, will retry on next interval
          }
        };

        poll();
        pollIntervalRef.current = setInterval(poll, 3000);
        return;
      }

      const token = await getAuthToken();
      const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : "";
      const wsUrl = `${wsBase}/reports/${reportId}${tokenQuery}`;

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

            const currentStatus = parsed.data?.status;
            if (
              typeof currentStatus === "string" &&
              TERMINAL_STATUSES.includes(currentStatus.toLowerCase() as ReportStatus)
            ) {
              isManuallyClosedRef.current = true;
              ws.close(1000, "Report complete");
              setConnectionStatus(reportId, "connected");
            }
          } catch (parseErr) {
            console.warn("[WS] Error parsing incoming WebSocket payload:", parseErr);
          }
        };

        ws.onerror = () => {
          // Socket error handled by onclose fallback
        };

        ws.onclose = (event) => {
          if (isManuallyClosedRef.current || event.code === 1000 || event.code === 1008) {
            setConnectionStatus(reportId, "connected");
            return;
          }

          const maxRetries = 4;
          if (retryCountRef.current < maxRetries) {
            const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 8000);
            retryCountRef.current += 1;
            setConnectionStatus(reportId, "reconnecting");
            reconnectTimeoutRef.current = setTimeout(connect, delay);
          } else {
            // Fallback to active polling if WebSocket server closes
            setConnectionStatus(reportId, "connected");
          }
        };
      } catch {
        setConnectionStatus(reportId, "connected");
      }
    }

    connect();

    return () => {
      isManuallyClosedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      socketRef.current?.close(1000, "Component unmounted");
      socketRef.current = null;
    };
  }, [reportId, enabled, isReportActive, handleIncomingEvent, setConnectionStatus]);

  const liveStatus = useAgentEventsStore((state) =>
    reportId ? state.reportStatuses[reportId] : undefined
  );
  const liveConnection = useAgentEventsStore(
    (state) => (reportId ? state.connectionStatuses[reportId] || "connected" : "connected")
  );
  const liveEvents = useAgentEventsStore((state) =>
    reportId && state.eventsLog[reportId] ? state.eventsLog[reportId] : EMPTY_EVENTS
  );

  return {
    status: liveStatus || status,
    connectionState: liveConnection as ConnectionState,
    events: liveEvents,
  };
}
