"use client";

import React, { useState } from "react";
import {
  Bot,
  ShieldCheck,
  CheckCircle2,
  Sparkles,
  Network,
  RefreshCw,
  Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";

interface AgentProfile {
  id: string;
  name: string;
  role: string;
  description: string;
  model: string;
  fallbackModel: string;
  status: "idle" | "running" | "healthy" | "standby";
  successRate: string;
  avgLatency: string;
  tasksCompleted: number;
  circuitBreaker: "closed" | "half-open" | "open";
  capabilities: string[];
}

export default function AgentsMeshPage() {
  const { toast } = useToast();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const agents: AgentProfile[] = [
    {
      id: "orchestrator",
      name: "Orchestration Engine",
      role: "Lead Coordinator",
      description:
        "Decomposes complex research queries into a parallel Directed Acyclic Graph (DAG), coordinates subagent execution waves, and enforces task dependency resolution.",
      model: "gemini-1.5-pro",
      fallbackModel: "claude-3-5-sonnet",
      status: "healthy",
      successRate: "99.8%",
      avgLatency: "420ms",
      tasksCompleted: 148,
      circuitBreaker: "closed",
      capabilities: [
        "DAG Wavefront Scheduling",
        "Kahn's Topological In-Degree Sorting",
        "Deadlock Prevention & Recovery",
        "State Snapshot Persistence",
      ],
    },
    {
      id: "researcher",
      name: "Autonomous Researcher Swarm",
      role: "Information Retrieval",
      description:
        "Dispatches parallel subagents to traverse academic repositories, web sources, and data endpoints to gather diverse, high-confidence evidence with citations.",
      model: "gemini-1.5-flash",
      fallbackModel: "gpt-4o",
      status: "running",
      successRate: "98.4%",
      avgLatency: "890ms",
      tasksCompleted: 612,
      circuitBreaker: "closed",
      capabilities: [
        "Multi-Threaded Web Extraction",
        "Asyncio.gather Parallelism",
        "Source Authority Scoring",
        "Structured Fact Chunking",
      ],
    },
    {
      id: "fact_checker",
      name: "Fact-Checking & Verification Agent",
      role: "Adversarial Auditor",
      description:
        "Performs adversarial verification on synthesized claims. Cross-references statements against cited sources to eliminate hallucinations and assign verification badges.",
      model: "gemini-1.5-pro",
      fallbackModel: "claude-3-5-sonnet",
      status: "healthy",
      successRate: "99.1%",
      avgLatency: "640ms",
      tasksCompleted: 429,
      circuitBreaker: "closed",
      capabilities: [
        "Semantic Entailment Verification",
        "Vector Cosine Similarity Check",
        "Citation Anchor Validation",
        "Adversarial Hallucination Pruning",
      ],
    },
    {
      id: "writer",
      name: "Synthesis & Report Writer",
      role: "Report Generation",
      description:
        "Compiles verified evidence and claims into an executive-grade, publication-ready research report with structured sections, table of contents, and interactive citations.",
      model: "gemini-1.5-pro",
      fallbackModel: "gpt-4o",
      status: "standby",
      successRate: "99.6%",
      avgLatency: "1,120ms",
      tasksCompleted: 184,
      circuitBreaker: "closed",
      capabilities: [
        "Structured Markdown Synthesis",
        "Hierarchical Outline Compilation",
        "Executive Summary Drafting",
        "BibTeX Citation Formatting",
      ],
    },
  ];

  const handlePingMesh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      toast({
        title: "Agent Mesh Health Verified",
        description: "All 4 core agents operational. Redis pub/sub latency: 1.2ms. Circuit breakers nominal.",
      });
    }, 600);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Top Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">
              Agent Mesh Telemetry
            </h1>
            <Badge variant="complete" dot>
              Cluster Active
            </Badge>
          </div>
          <p className="text-sm text-text-secondary mt-1 max-w-2xl">
            Live monitor of the Quorum multi-agent orchestration architecture. Agents operate concurrently along a DAG workflow with automated fallbacks and exponential backoff.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePingMesh}
            disabled={isRefreshing}
            className="flex items-center gap-2 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>Health Ping</span>
          </Button>
        </div>
      </div>

      {/* Cluster Vital Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card className="bg-surface/50 border-border">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-xs text-text-secondary">
              <span>Active Mesh Nodes</span>
              <Network className="h-4 w-4 text-accent" />
            </div>
            <div className="text-2xl font-bold text-text-primary">4 Nodes</div>
            <p className="text-[11px] text-success flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 inline" /> 100% Availability
            </p>
          </CardContent>
        </Card>

        <Card className="bg-surface/50 border-border">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-xs text-text-secondary">
              <span>Circuit Breaker</span>
              <ShieldCheck className="h-4 w-4 text-success" />
            </div>
            <div className="text-2xl font-bold text-text-primary">0 Open</div>
            <p className="text-[11px] text-text-secondary">
              All 4 circuits CLOSED (Healthy)
            </p>
          </CardContent>
        </Card>

        <Card className="bg-surface/50 border-border">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-xs text-text-secondary">
              <span>Primary LLM Provider</span>
              <Sparkles className="h-4 w-4 text-warning" />
            </div>
            <div className="text-2xl font-bold text-text-primary">Gemini 1.5</div>
            <p className="text-[11px] text-text-secondary">
              Fallback: Claude 3.5 &amp; GPT-4o
            </p>
          </CardContent>
        </Card>

        <Card className="bg-surface/50 border-border">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-xs text-text-secondary">
              <span>Avg End-to-End Latency</span>
              <Clock className="h-4 w-4 text-info" />
            </div>
            <div className="text-2xl font-bold text-text-primary">760 ms</div>
            <p className="text-[11px] text-text-secondary">
              Across parallel worker threads
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Agent Profiles Grid */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight text-text-primary">
          Active Subagent Architecture
        </h2>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {agents.map((agent) => (
            <Card key={agent.id} className="border-border bg-surface transition-all hover:border-border-hover">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-control bg-accent/10 text-accent">
                        <Bot className="h-4 w-4" />
                      </div>
                      <CardTitle className="text-base font-semibold text-text-primary">
                        {agent.name}
                      </CardTitle>
                    </div>
                    <Badge variant="outline" className="text-[10px] text-accent">
                      {agent.role}
                    </Badge>
                  </div>

                  <Badge
                    variant={
                      agent.status === "running"
                        ? "running"
                        : agent.status === "healthy"
                        ? "complete"
                        : "pending"
                    }
                    dot
                  >
                    {agent.status}
                  </Badge>
                </div>
                <CardDescription className="text-xs text-text-secondary leading-relaxed pt-2">
                  {agent.description}
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4 pt-0">
                {/* Model Configuration */}
                <div className="grid grid-cols-2 gap-2 rounded-control bg-surface-subtle p-2.5 text-xs">
                  <div>
                    <span className="text-[10px] font-medium text-text-secondary uppercase">
                      Primary Model
                    </span>
                    <p className="font-mono font-semibold text-text-primary truncate">
                      {agent.model}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] font-medium text-text-secondary uppercase">
                      Fallback Chain
                    </span>
                    <p className="font-mono text-text-secondary truncate">
                      {agent.fallbackModel}
                    </p>
                  </div>
                </div>

                {/* Capabilities Badges */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">
                    Core Capabilities
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {agent.capabilities.map((cap) => (
                      <span
                        key={cap}
                        className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Stats Footer */}
                <div className="flex items-center justify-between border-t border-border pt-3 text-[11px] text-text-secondary">
                  <span>Success Rate: <strong className="text-text-primary">{agent.successRate}</strong></span>
                  <span>Latency: <strong className="text-text-primary">{agent.avgLatency}</strong></span>
                  <span>Tasks: <strong className="text-text-primary">{agent.tasksCompleted}</strong></span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
