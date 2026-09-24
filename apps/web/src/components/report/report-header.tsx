"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Clock,
  FilePlus2,
  RotateCcw,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConnectionState, ReportStatus } from "@/stores/agentEventsStore";
import { useUiStore } from "@/stores/uiStore";

interface ReportHeaderProps {
  reportId: string;
  query: string;
  status: ReportStatus;
  createdAt: string;
  connectionState: ConnectionState;
  onRetry?: () => void;
}

export function ReportHeader({
  reportId,
  query,
  status,
  createdAt,
  connectionState,
  onRetry,
}: ReportHeaderProps) {
  const setActiveModal = useUiStore((state) => state.setActiveModal);

  const formattedDate = createdAt ? createdAt.slice(0, 10) : "Recent";
  const isTerminal = status === "complete" || status === "failed";
  const connectionLabel = isTerminal
    ? "complete"
    : connectionState === "disconnected"
    ? "offline"
    : connectionState;

  const getStatusVariant = (
    s: ReportStatus
  ): "complete" | "needs_review" | "failed" | "pending" | "running" | "secondary" => {
    if (s === "complete") return "complete";
    if (s === "needs_review") return "needs_review";
    if (s === "failed") return "failed";
    if (s === "pending") return "pending";
    return "running";
  };

  return (
    <div className="space-y-4 pb-2 border-b border-border/80">
      {/* Top navigation row */}
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Dashboard</span>
        </Link>

        <div className="flex items-center gap-2">
          {/* WebSocket Connection Status */}
          <div
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono border ${
              connectionState === "connected"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : connectionState === "connecting" ||
                  connectionState === "reconnecting"
                ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                : "border-border bg-surface-subtle text-text-secondary"
            }`}
          >
            {connectionState === "connected" ? (
              <Wifi className="h-3 w-3" />
            ) : (
              <WifiOff className="h-3 w-3" />
            )}
            <span className="capitalize">{connectionLabel}</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setActiveModal("create_report")}
            className="text-xs gap-1.5 h-8"
          >
            <FilePlus2 className="h-3.5 w-3.5" />
            New Report
          </Button>
        </div>
      </div>

      {/* Main Title & Status Row */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono font-medium text-text-secondary">
              Report ID: {reportId}
            </span>
            <span>•</span>
            <Badge variant={getStatusVariant(status)} dot className="capitalize">
              {status.replace(/_/g, " ")}
            </Badge>
          </div>

          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold tracking-tight text-text-primary break-words">
            {query}
          </h1>

          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <Clock className="h-3 w-3" />
            <span suppressHydrationWarning>Initiated on {formattedDate}</span>
          </div>
        </div>

        {status === "failed" && onRetry && (
          <Button
            variant="destructive"
            size="sm"
            onClick={onRetry}
            className="gap-1.5 self-start md:self-center"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Retry Pipeline
          </Button>
        )}
      </div>
    </div>
  );
}
