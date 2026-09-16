"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Bot,
  Cpu,
  FileCheck,
  Play,
  Radio,
  ShieldCheck,
  Sparkles,
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
import { useToast } from "@/components/ui/toast";

export default function HomePage() {
  const { toast } = useToast();
  const [loadingState, setLoadingState] = useState(false);

  const handleSimulateToast = (type: "success" | "destructive" | "default") => {
    if (type === "success") {
      toast({
        title: "Report Synthesis Complete",
        description: "12 citations verified with 98.4% confidence score across 4 agent runs.",
        variant: "success",
      });
    } else if (type === "destructive") {
      toast({
        title: "Rate Limit Exceeded",
        description: "Sliding window threshold reached (10/hr). Cooldown resets in 42 minutes.",
        variant: "destructive",
      });
    } else {
      toast({
        title: "Agent Swarm Dispatched",
        description: "3 parallel researcher nodes decomposed and queued for execution.",
      });
    }
  };

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
              <span className="text-xs text-text-secondary">v0.1.0 Alpha</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
              Research Operations
            </h1>
            <p className="mt-1 text-sm text-text-secondary sm:text-base max-w-2xl">
              Coordinate autonomous agent swarms to decompose complex queries, cross-verify
              facts, and synthesize structured intelligence reports.
            </p>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSimulateToast("default")}
              className="gap-1.5 font-medium"
            >
              <Radio className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
              Test Toast
            </Button>

            <Button
              size="sm"
              className="gap-2 shadow-sm font-semibold"
              onClick={() => handleSimulateToast("success")}
            >
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              New Research Run
            </Button>
          </div>
        </div>

        {/* Metric Cards Row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Active Swarms
              </CardTitle>
              <Bot className="h-4 w-4 text-accent" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-text-primary">4 / 4 Nodes</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-text-secondary">
                <Badge variant="running" dot>
                  Parallel Execution
                </Badge>
              </div>
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
                <span className="text-success font-semibold flex items-center">
                  +2.4%
                </span>
                <span>vs baseline LLM</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Sources Indexed
              </CardTitle>
              <FileCheck className="h-4 w-4 text-accent" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-text-primary">1,428</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-text-secondary">
                <Badge variant="complete" dot>
                  pgvector ready
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Circuit Breakers
              </CardTitle>
              <Cpu className="h-4 w-4 text-warning" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-text-primary">CLOSED</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-text-secondary">
                <span className="text-success font-semibold">100% Healthy</span>
                <span>(3 providers)</span>
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
                <Badge variant="running" dot>
                  Healthy
                </Badge>
              </div>
              <CardDescription>
                Topological orchestration pipeline status
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                {
                  role: "Orchestrator",
                  status: "complete" as const,
                  desc: "Decomposes queries into 3-6 subtopics",
                },
                {
                  role: "Researchers (3x)",
                  status: "running" as const,
                  desc: "Parallel literature retrieval & claim tagging",
                },
                {
                  role: "Fact Checker",
                  status: "pending" as const,
                  desc: "Cross-checks claims & assigns confidence",
                },
                {
                  role: "Synthesizer Writer",
                  status: "pending" as const,
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
                    <p className="text-xs text-text-secondary pl-7">
                      {agent.desc}
                    </p>
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
                    Recent Research Reports
                  </CardTitle>
                  <CardDescription>
                    Real-time status streamed via WebSocket channels
                  </CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setLoadingState(!loadingState)}
                  className="text-xs text-text-secondary"
                >
                  {loadingState ? "Show Real Data" : "Toggle Skeletons"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingState ? (
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
              ) : (
                <div className="space-y-2.5">
                  {[
                    {
                      id: "rep-1",
                      title: "Fault-Tolerant Consensus in Asynchronous Networks",
                      project: "Distributed Systems Benchmark",
                      status: "running" as const,
                      time: "Running for 42s",
                    },
                    {
                      id: "rep-2",
                      title: "Optimistic Rollups vs ZK Rollups Performance",
                      project: "High-Throughput Consensus",
                      status: "complete" as const,
                      time: "Completed 24m ago",
                    },
                    {
                      id: "rep-3",
                      title: "Transformer Memory Bottlenecks in Long-Context LLMs",
                      project: "Neural Architectures",
                      status: "pending" as const,
                      time: "Queued in task pool",
                    },
                    {
                      id: "rep-4",
                      title: "Zero-Knowledge SNARK Verification in EVM",
                      project: "Confidential Research",
                      status: "failed" as const,
                      time: "Failed: Provider timeout",
                    },
                  ].map((report) => (
                    <div
                      key={report.id}
                      className="group flex flex-col sm:flex-row sm:items-center justify-between rounded-control border border-border bg-surface p-3.5 transition-colors hover:border-accent/40 hover:bg-surface-hover gap-3"
                    >
                      <div className="space-y-1">
                        <Link
                          href={`/reports/${report.id}`}
                          className="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-sm"
                        >
                          <span>{report.title}</span>
                          <ArrowUpRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </Link>
                        <div className="flex items-center gap-2 text-xs text-text-secondary">
                          <span>{report.project}</span>
                          <span>•</span>
                          <span>{report.time}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 self-start sm:self-center">
                        <Badge variant={report.status} dot>
                          {report.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Design System & Accessibility Primitives Showcase */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">
              Design System Showcase
            </CardTitle>
            <CardDescription>
              Verified light and dark theme contrast tokens, button variants, status indicators, and focus states.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Status Badges Matrix */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-2.5">
                Status Badge Indicators
              </h4>
              <div className="flex flex-wrap gap-2.5">
                <Badge variant="pending" dot>
                  pending (Amber)
                </Badge>
                <Badge variant="running" dot>
                  running (Indigo Pulse)
                </Badge>
                <Badge variant="complete" dot>
                  complete (Emerald)
                </Badge>
                <Badge variant="failed" dot>
                  failed (Rose)
                </Badge>
                <Badge variant="secondary">
                  secondary token
                </Badge>
                <Badge variant="outline">
                  outline token
                </Badge>
              </div>
            </div>

            {/* Buttons Matrix */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-2.5">
                Button Component Variants & Accessibility Focus States
              </h4>
              <div className="flex flex-wrap items-center gap-2.5">
                <Button variant="default" size="sm">
                  Default (Primary)
                </Button>
                <Button variant="secondary" size="sm">
                  Secondary
                </Button>
                <Button variant="outline" size="sm">
                  Outline
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleSimulateToast("destructive")}
                >
                  Destructive
                </Button>
                <Button variant="ghost" size="sm">
                  Ghost
                </Button>
                <Button variant="link" size="sm">
                  Link
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
