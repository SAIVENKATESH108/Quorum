"use client";

import { useEffect, useRef } from "react";
import { getAuthToken } from "@/lib/api-client";
import {
  ConnectionState,
  ReportEventPayload,
  ReportStatus,
  useAgentEventsStore,
} from "@/stores/agentEventsStore";

const TERMINAL_STATUSES: ReportStatus[] = ["complete", "failed"];
const EMPTY_EVENTS: ReportEventPayload[] = [];

function resolveWebSocketBaseUrl(): string | null {
  const configuredWsUrl = process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, "");
  const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  const isProduction = process.env.NODE_ENV === "production";

  if (configuredWsUrl && (!isProduction || !configuredWsUrl.includes("localhost"))) {
    return configuredWsUrl;
  }

  if (configuredApiUrl && !configuredApiUrl.includes("localhost")) {
    return `${configuredApiUrl.replace(/^http/, "ws")}/ws`;
  }

  return isProduction ? null : "ws://localhost:8000/ws";
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
  const retryCountRef = useRef(0);
  const isManuallyClosedRef = useRef(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const isReportActive = reportId && (!status || !TERMINAL_STATUSES.includes(status));

  useEffect(() => {
    if (!reportId || !enabled || !isReportActive) {
      if (reportId) setConnectionStatus(reportId, "disconnected");
      return;
    }

    isManuallyClosedRef.current = false;

    async function connect() {
      if (!reportId) return;

      const wsBase = resolveWebSocketBaseUrl();
      if (!wsBase) {
        console.error(
          "[WS] Production WebSocket is not configured. Set NEXT_PUBLIC_WS_URL to the deployed wss:// API endpoint."
        );
        setConnectionStatus(reportId, "disconnected");
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
          if (isManuallyClosedRef.current || event.code === 1000 || event.code === 1008) {
            setConnectionStatus(reportId, "disconnected");
            return;
          }

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
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      socketRef.current?.close(1000, "Component unmounted");
      socketRef.current = null;
      setConnectionStatus(reportId, "disconnected");
    };
  }, [reportId, enabled, isReportActive, handleIncomingEvent, setConnectionStatus]);

  const liveStatus = useAgentEventsStore((state) =>
    reportId ? state.reportStatuses[reportId] : undefined
  );
  const liveConnection = useAgentEventsStore(
    (state) => (reportId ? state.connectionStatuses[reportId] || "disconnected" : "disconnected")
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
