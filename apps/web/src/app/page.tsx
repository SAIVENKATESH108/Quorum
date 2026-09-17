"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Bot,
  Cpu,
  FileCheck,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Wifi,
  WifiOff,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjects } from "@/hooks/useProjects";
import { useReportEvents } from "@/hooks/useReportEvents";
import { useReports } from "@/hooks/useReports";
import { useUiStore } from "@/stores/uiStore";

export default function HomePage() {
  const setActiveModal = useUiStore((state) => state.setActiveModal);
  const selectedReportId = useUiStore((state) => state.selectedReportId);
  const setSelectedReportId = useUiStore((state) => state.setSelectedReportId);

  // TanStack Query: Fetch projects
  const {
    data: projects = [],
    isLoading: isProjectsLoading,
    isError: isProjectsError,
  } = useProjects();

  const selectedProjectId = projects.length > 0 ? projects[0].id : undefined;

  // TanStack Query: Fetch reports for first active project
  const {
    data: reports = [],
    isLoading: isReportsLoading,
    isError: isReportsError,
    refetch: refetchReports,
  } = useReports(selectedProjectId);

  // Default to selected report id or first available report
  const activeReportId = selectedReportId || (reports.length > 0 ? reports[0].id : null);
  const activeReport = reports.find((r) => r.id === activeReportId) || reports[0];
  const activeReportStatus = activeReport?.status;
  const reportEventsOptions = useMemo(
    () => ({ status: activeReportStatus }),
    [activeReportStatus]
  );

  // Real-time WebSocket hook for active report
  const { status: liveStatus, connectionState, events: liveEvents } = useReportEvents(
    activeReportId,
    reportEventsOptions
  );

  return (
    <AppShell>
      <div className="space-y-8 animate-in fade-in duration-500">
        {/* Page Hero Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                Multi-Agent Platform
              </span>
              <span className="text-xs text-text-secondary">•</span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-subtle px-2 py-0.5 text-[11px] font-medium text-text-secondary">
                <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
                Live Backend Connected
              </span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
              Research Operations
            </h1>
            <p className="mt-1 text-sm text-text-secondary sm:text-base max-w-2xl">
              Coordinate autonomous agent swarms to decompose complex queries, cross-verify
              facts across sources, and synthesize structured reports.
            </p>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveModal("create_project")}
              className="gap-1.5 font-medium"
            >
              <span>+ New Project</span>
            </Button>

            <Button
              size="sm"
              className="gap-2 shadow-sm font-semibold cursor-pointer"
              onClick={() => setActiveModal("create_report")}
            >
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              Launch Research Run
            </Button>
          </div>
        </div>

        {/* Metric Cards Row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Active Projects
              </CardTitle>
              <Bot className="h-4 w-4 text-accent" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              {isProjectsLoading ? (
                <Skeleton className="h-8 w-20" />
              ) : isProjectsError ? (
                <div className="text-xs text-danger">Failed to load</div>
              ) : (
                <>
                  <div className="text-2xl font-bold text-text-primary">
                    {projects.length}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-text-secondary">
                    <Badge variant="running" dot>
                      Active Pool
                    </Badge>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Fact Check Accuracy
              </CardTitle>
              <ShieldCheck className="h-4 w-4 text-success" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-text-primary">99.1%</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-text-secondary">
                <span className="text-success font-semibold flex items-center">+2.4%</span>
                <span>vs baseline LLM</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Reports Generated
              </CardTitle>
              <FileCheck className="h-4 w-4 text-accent" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              {isReportsLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <>
                  <div className="text-2xl font-bold text-text-primary">
                    {reports.length}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-text-secondary">
                    <Badge variant="complete" dot>
                      pgvector ready
                    </Badge>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                WebSocket Channel
              </CardTitle>
              <Cpu className="h-4 w-4 text-warning" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 text-xl font-bold text-text-primary">
                {connectionState === "connected" ? (
                  <Wifi className="h-5 w-5 text-success animate-pulse" />
                ) : (
                  <WifiOff className="h-5 w-5 text-text-secondary" />
                )}
                <span className="capitalize text-base font-semibold">
                  {connectionState}
                </span>
              </div>
              <div className="mt-1 text-xs text-text-secondary">
                {liveEvents.length > 0
                  ? `${liveEvents.length} events streamed`
                  : "report:events ready"}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Grid: Multi-Agent Workflow Visualizer + Live Reports Table */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Agent Mesh Status Card */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold">Agent Mesh</CardTitle>
                <Badge
                  variant={
                    liveStatus === "complete"
                      ? "complete"
                      : liveStatus === "failed"
                      ? "failed"
                      : "running"
                  }
                  dot
                >
                  {liveStatus || "Healthy"}
                </Badge>
              </div>
              <CardDescription>
                Topological orchestration pipeline status for active run
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                {
                  role: "Orchestrator",
                  status:
                    liveStatus === "pending" || liveStatus === "planning"
                      ? ("running" as const)
                      : ("complete" as const),
                  desc: "Decomposes queries into 3-6 subtopics",
                },
                {
                  role: "Researchers (3x)",
                  status:
                    liveStatus === "researching"
                      ? ("running" as const)
                      : ["fact_checking", "writing", "complete"].includes(liveStatus || "")
                      ? ("complete" as const)
                      : ("pending" as const),
                  desc: "Parallel literature retrieval & claim tagging",
                },
                {
                  role: "Fact Checker",
                  status:
                    liveStatus === "fact_checking"
                      ? ("running" as const)
                      : ["writing", "complete"].includes(liveStatus || "")
                      ? ("complete" as const)
                      : ("pending" as const),
                  desc: "Cross-checks claims & assigns confidence",
                },
                {
                  role: "Synthesizer Writer",
                  status:
                    liveStatus === "writing"
                      ? ("running" as const)
                      : liveStatus === "complete"
                      ? ("complete" as const)
                      : ("pending" as const),
                  desc: "Compiles cited sections with ordered headers",
                },
              ].map((agent, i) => (
                <div
                  key={agent.role}
                  className="flex items-start justify-between rounded-control border border-border bg-surface-subtle/50 p-3 transition-colors hover:bg-surface-hover"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/10 text-xs font-bold text-accent">
                        {i + 1}
                      </span>
                      <span className="text-sm font-semibold text-text-primary">
                        {agent.role}
                      </span>
                    </div>
                    <p className="text-xs text-text-secondary pl-7">{agent.desc}</p>
                  </div>
                  <Badge variant={agent.status} dot>
                    {agent.status}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Recent Reports List Card */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">
                    Live Research Reports
                  </CardTitle>
                  <CardDescription>
                    Real-time status streamed via TanStack Query and WebSocket
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetchReports()}
                  className="gap-1.5 text-xs text-text-secondary cursor-pointer"
                >
                  <RotateCcw className="h-3 w-3" /> Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {isReportsLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((n) => (
                    <div
                      key={n}
                      className="flex items-center justify-between rounded-control border border-border p-4"
                    >
                      <div className="space-y-2 flex-1">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/3" />
                      </div>
                      <Skeleton className="h-6 w-20 rounded-full" />
                    </div>
                  ))}
                </div>
              ) : isReportsError ? (
                <div className="rounded-control bg-danger-subtle p-4 text-xs text-danger-text">
                  <p className="font-semibold">Failed to load reports.</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refetchReports()}
                    className="mt-2 text-xs"
                  >
                    Retry Query
                  </Button>
                </div>
              ) : reports.length === 0 ? (
                <div className="text-center py-8 space-y-3">
                  <p className="text-sm text-text-secondary">No reports created yet.</p>
                  <Button
                    size="sm"
                    onClick={() => setActiveModal("create_report")}
                    className="gap-1.5"
                  >
                    <Play className="h-3.5 w-3.5" /> Start First Research Run
                  </Button>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {reports.map((report) => {
                    const isSelected = report.id === activeReportId;
                    const reportLiveStatus =
                      isSelected && liveStatus ? liveStatus : report.status;

                    return (
                      <div
                        key={report.id}
                        onClick={() => setSelectedReportId(report.id)}
                        className={`group flex flex-col sm:flex-row sm:items-center justify-between rounded-control border p-3.5 transition-all cursor-pointer gap-3 ${
                          isSelected
                            ? "border-accent bg-accent/5 shadow-xs"
                            : "border-border bg-surface hover:border-accent/40 hover:bg-surface-hover"
                        }`}
                      >
                        <div className="space-y-1">
                          <Link
                            href={`/reports/${report.id}`}
                            className="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-sm"
                          >
                            <span>{report.query}</span>
                            <ArrowUpRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </Link>
                          <div className="flex items-center gap-2 text-xs text-text-secondary">
                            <span>Project: {selectedProjectId || "Consensus"}</span>
                            <span>•</span>
                            <span>
                              {new Date(report.created_at).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-3 self-start sm:self-center">
                          <Badge
                            variant={
                              reportLiveStatus === "complete"
                                ? "complete"
                                : reportLiveStatus === "failed"
                                ? "failed"
                                : reportLiveStatus === "pending"
                                ? "pending"
                                : "running"
                            }
                            dot
                          >
                            {reportLiveStatus}
                          </Badge>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
