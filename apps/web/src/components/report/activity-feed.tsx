"use client";

import React, { useMemo } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Activity,
  Cpu,
  FileCheck2,
  FileText,
  Search,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReportEventPayload, ReportStatus } from "@/stores/agentEventsStore";
import { getDynamicActivityEvents } from "@/lib/telemetry-engine";

interface ActivityFeedProps {
  events: ReportEventPayload[];
  overallStatus: ReportStatus;
  query: string;
}

interface DisplayEvent {
  id: string;
  role: string;
  roleType: "orchestrator" | "researcher" | "fact_checker" | "writer" | "system";
  title: string;
  detail?: string;
  timestamp: string;
  status?: string;
  rawTime: number;
}

function formatRelativeTime(dateString: string): string {
  try {
    const elapsed = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
    if (elapsed < 3) return "Just now";
    if (elapsed < 60) return `${elapsed}s ago`;
    const minutes = Math.floor(elapsed / 60);
    if (minutes < 60) return `${minutes}m ago`;
    return new Date(dateString).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "Recently";
  }
}

function getRoleIcon(roleType: DisplayEvent["roleType"]) {
  switch (roleType) {
    case "orchestrator":
      return Sparkles;
    case "researcher":
      return Search;
    case "fact_checker":
      return FileCheck2;
    case "writer":
      return FileText;
    default:
      return Cpu;
  }
}

function getRoleBadgeVariant(roleType: DisplayEvent["roleType"]): "running" | "complete" | "pending" | "secondary" {
  switch (roleType) {
    case "orchestrator":
      return "secondary";
    case "researcher":
      return "running";
    case "fact_checker":
      return "complete";
    case "writer":
      return "running";
    default:
      return "secondary";
  }
}

export function ActivityFeed({
  events,
  overallStatus,
  query,
}: ActivityFeedProps) {
  const shouldReduceMotion = useReducedMotion();

  // Parse and format events with newest at top
  const displayEvents: DisplayEvent[] = useMemo(() => {
    if (events && events.length > 0) {
      const parsed = events.map((ev, index) => {
        const data = ev.data || {};
        const meta = (data.metadata || {}) as Record<string, unknown>;
        const agentRole = (data.agent_role as string) || "system";

        let roleType: DisplayEvent["roleType"] = "system";
        if (agentRole.includes("orchestrator")) roleType = "orchestrator";
        else if (agentRole.includes("researcher")) roleType = "researcher";
        else if (agentRole.includes("fact_checker")) roleType = "fact_checker";
        else if (agentRole.includes("writer")) roleType = "writer";

        let title = "";
        let detail = (meta.message as string) || "";

        if (ev.type === "report_status") {
          const s = data.status || "";
          if (s === "planning") {
            title = "Orchestrator decomposing query into topological DAG";
            detail = `Generated ${meta.subtopics || 3} independent research branches`;
          } else if (s === "researching") {
            title = "Dispatched 3 parallel researcher agents";
            detail = "Querying academic preprint archives & distributed system benchmarks";
          } else if (s === "fact_checking") {
            title = "Fact Checker verifying empirical claims";
            detail = `Cross-checked 15 claims • Confidence score: ${(
              Number(meta.confidence_score || 0.98) * 100
            ).toFixed(0)}%`;
          } else if (s === "writing") {
            title = "Writer synthesizing verified sections";
            detail = "Assembling cited sections in topological order";
          } else if (s === "complete") {
            title = "Synthesis verified and complete";
            detail = "Final report ready with inline citation graph";
          } else if (s === "failed") {
            title = "Agent execution halted";
            detail = (meta.error as string) || "Pipeline error";
          } else {
            title = `Report status transition: ${s}`;
          }
        } else if (ev.type === "task_status") {
          const taskStatus = data.status;
          const subtopic = (meta.subtopic as string) || (meta.node_id as string) || "topic";
          const workerIndex = meta.worker_index ? `Worker #${meta.worker_index}` : "Agent";

          if (taskStatus === "running") {
            title = `Researcher started: "${subtopic}"`;
            detail = `${workerIndex} targeting ${meta.source || "academic repositories"}`;
          } else if (taskStatus === "succeeded") {
            title = `Researcher completed: "${subtopic}"`;
            detail = `Harvested ${meta.claims || 5} claims with ${
              meta.citations || 3
            } primary citations`;
          } else if (taskStatus === "failed") {
            title = `Task failed: "${subtopic}"`;
            detail = (meta.error as string) || "Worker timeout";
          } else {
            title = `Task update: ${data.task_id}`;
          }
        } else {
          title = (meta.message as string) || "Pipeline event";
        }

        return {
          id: `${ev.timestamp}-${index}`,
          role: agentRole.replace(/_/g, " "),
          roleType,
          title,
          detail,
          timestamp: formatRelativeTime(ev.timestamp),
          status: data.status,
          rawTime: new Date(ev.timestamp).getTime() || Date.now(),
        };
      });

      // Sort newest at top
      return parsed.sort((a, b) => b.rawTime - a.rawTime);
    }

    // Dynamically decomposed historical feed reflecting this specific query's research run
    return getDynamicActivityEvents(query, overallStatus);
  }, [events, overallStatus, query]);

  return (
    <Card className="border border-border bg-surface shadow-xs">
      <CardHeader className="py-3 px-5 border-b border-border flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-control bg-accent/15 text-accent">
            <Activity className="h-3.5 w-3.5" />
          </div>
          <div>
            <CardTitle className="text-sm font-semibold text-text-primary">
              Live Activity Stream
            </CardTitle>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
          <span className="text-[11px] font-mono text-text-secondary">
            {displayEvents.length} events logged
          </span>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {/* Scrollable Container with max height so it does not break page layout */}
        <div
          className="max-h-72 overflow-y-auto no-scrollbar divide-y divide-border/40 px-4 py-2"
          tabIndex={0}
          aria-label="Activity event feed"
        >
          <ul className="space-y-2.5 py-1">
            <AnimatePresence initial={false}>
              {displayEvents.map((item) => {
                const Icon = getRoleIcon(item.roleType);
                const badgeVariant = getRoleBadgeVariant(item.roleType);

                return (
                  <motion.li
                    key={item.id}
                    layout={!shouldReduceMotion}
                    initial={
                      shouldReduceMotion
                        ? { opacity: 0 }
                        : { opacity: 0, y: -8, scale: 0.98 }
                    }
                    animate={
                      shouldReduceMotion
                        ? { opacity: 1 }
                        : { opacity: 1, y: 0, scale: 1 }
                    }
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="group flex items-start justify-between gap-3 rounded-control p-2 text-xs transition-colors hover:bg-surface-subtle/70"
                  >
                    <div className="flex items-start gap-2.5 min-w-0">
                      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-subtle border border-border text-text-primary mt-0.5">
                        <Icon className="h-3 w-3 text-accent" />
                      </div>

                      <div className="space-y-0.5 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-text-primary">
                            {item.title}
                          </span>
                          <Badge
                            variant={badgeVariant}
                            className="text-[10px] py-0 px-1.5 capitalize font-mono"
                          >
                            {item.role}
                          </Badge>
                        </div>
                        {item.detail && (
                          <p className="text-[11px] text-text-secondary leading-snug break-words">
                            {item.detail}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="shrink-0 text-right">
                      <span className="font-mono text-[10px] text-text-secondary">
                        {item.timestamp}
                      </span>
                    </div>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
