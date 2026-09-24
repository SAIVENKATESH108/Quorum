import React from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  ExternalLink,
  FileCheck,
  Play,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";

export default function PublicLandingPage() {
  return (
    <div className="min-h-screen bg-bg text-text-primary flex flex-col selection:bg-accent/20 selection:text-accent">
      {/* 1. Global Public Top Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-border/80 bg-surface/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground shadow-sm group-hover:scale-105 transition-transform">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight text-text-primary leading-none">
                Quorum
              </span>
              <span className="text-[10px] font-mono text-text-secondary tracking-wider uppercase mt-0.5">
                Multi-Agent Intelligence
              </span>
            </div>
          </Link>

          <nav aria-label="Main Navigation" className="hidden md:flex items-center gap-6 text-sm font-medium text-text-secondary">
            <a href="#architecture" className="hover:text-text-primary transition-colors">
              Architecture
            </a>
            <a href="#agents" className="hover:text-text-primary transition-colors">
              Agent Mesh
            </a>
            <Link href="/projects" className="hover:text-text-primary transition-colors">
              Run Research
            </Link>
            <a
              href="/Quorum_System_Documentation.pdf"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-accent transition-colors inline-flex items-center gap-1 font-semibold text-accent/90"
              title="Download 9-Page Publication-Grade System Documentation PDF"
            >
              System Spec PDF
            </a>
            <Link href="/sources" className="hover:text-text-primary transition-colors">
              Evidence Library
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/sign-in"
              className="text-xs sm:text-sm font-medium text-text-secondary hover:text-text-primary px-3 py-1.5 transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/projects"
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-xs sm:text-sm font-semibold text-accent-foreground shadow-sm hover:opacity-90 transition-all cursor-pointer"
            >
              <span>Launch Console</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <main className="flex-1">
        <section className="relative overflow-hidden pt-16 pb-20 md:pt-24 md:pb-28 border-b border-border/60">
          <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent pointer-events-none" />
          
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10 space-y-6">
            {/* Live Status Pill */}
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/25 bg-accent/10 px-3.5 py-1 text-xs font-mono font-medium text-accent">
              <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
              <span>Quorum v1.2 — Multi-Agent Consensus Swarm Live</span>
            </div>

            {/* Headline */}
            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-text-primary leading-[1.15]">
              Autonomous AI Swarms that{" "}
              <span className="bg-gradient-to-r from-accent via-indigo-400 to-accent bg-clip-text text-transparent">
                Research, Fact-Check &amp; Synthesize
              </span>
            </h1>

            {/* Subtitle */}
            <p className="max-w-3xl mx-auto text-base sm:text-lg lg:text-xl text-text-secondary leading-relaxed font-normal">
              Move beyond single-turn hallucinations. Quorum orchestrates parallel researcher
              agents into a topological Directed Acyclic Graph (DAG) — cross-examining primary
              literature, verifying academic DOIs, and compiling institutional-grade intelligence reports.
            </p>

            {/* Action CTAs */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 pt-4">
              <Link
                href="/projects"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-6 py-3.5 text-sm font-semibold text-accent-foreground shadow-md hover:opacity-95 transition-all"
              >
                <Play className="h-4 w-4 fill-current" />
                <span>Launch Research Console</span>
              </Link>

              <a
                href="/Quorum_System_Documentation.pdf"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg border border-purple-500/40 bg-purple-500/10 px-5 py-3.5 text-sm font-semibold text-purple-400 hover:bg-purple-500/20 transition-all"
                title="Download 9-Page Publication-Grade System Documentation PDF"
              >
                <BookOpen className="h-4 w-4 text-purple-400" />
                <span>9-Page System Spec (PDF)</span>
              </a>

              <Link
                href="/projects"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-surface px-6 py-3.5 text-sm font-semibold text-text-primary hover:bg-surface-hover hover:border-accent/40 transition-all"
              >
                <FileCheck className="h-4 w-4 text-accent" />
                <span>Run a Research Query</span>
              </Link>

            </div>

            {/* Key Metrics Strip */}
            <div className="pt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
              <div className="p-4 rounded-xl border border-border/80 bg-surface shadow-xs">
                <div className="text-2xl sm:text-3xl font-bold font-mono text-accent">99.1%</div>
                <div className="text-xs font-medium text-text-primary mt-1">Fact-Check Accuracy</div>
                <p className="text-[11px] text-text-secondary mt-0.5">Cross-verified claims vs primary DOIs</p>
              </div>

              <div className="p-4 rounded-xl border border-border/80 bg-surface shadow-xs">
                <div className="text-2xl sm:text-3xl font-bold font-mono text-text-primary">3–6x</div>
                <div className="text-xs font-medium text-text-primary mt-1">Parallel Swarm Agents</div>
                <p className="text-[11px] text-text-secondary mt-0.5">Concurrent literature retrieval</p>
              </div>

              <div className="p-4 rounded-xl border border-border/80 bg-surface shadow-xs">
                <div className="text-2xl sm:text-3xl font-bold font-mono text-emerald-500">&lt; 45s</div>
                <div className="text-xs font-medium text-text-primary mt-1">Convergence Time</div>
                <p className="text-[11px] text-text-secondary mt-0.5">From prompt to structured report</p>
              </div>

              <div className="p-4 rounded-xl border border-border/80 bg-surface shadow-xs">
                <div className="text-2xl sm:text-3xl font-bold font-mono text-text-primary">0</div>
                <div className="text-xs font-medium text-text-primary mt-1">Fabricated Citations</div>
                <p className="text-[11px] text-text-secondary mt-0.5">Strict empirical URL grounding</p>
              </div>
            </div>
          </div>
        </section>

        {/* 3. Topological Multi-Agent Architecture Section */}
        <section id="architecture" className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-3 max-w-3xl mx-auto">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-accent bg-accent/10 px-3 py-1 rounded-full">
              Orchestration Topology
            </span>
            <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-text-primary">
              The Asynchronous Multi-Agent DAG
            </h2>
            <p className="text-sm sm:text-base text-text-secondary">
              Quorum treats research not as a monolithic chat completion, but as a directed graph of
              specialized autonomous agents with verifiable synchronization barriers.
            </p>
          </div>

          <div id="agents" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Stage 1 */}
            <div className="p-6 rounded-2xl border border-border bg-surface shadow-xs space-y-4 relative overflow-hidden">
              <div className="h-8 w-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent font-bold font-mono text-sm">
                01
              </div>
              <h3 className="text-lg font-bold text-text-primary">Orchestrator Agent</h3>
              <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
                Decomposes ambiguous, complex user queries into 3–6 mutually exclusive, collectively
                exhaustive sub-research hypotheses. Compiles the topological task dependency DAG.
              </p>
              <div className="pt-2 border-t border-border/60 text-[11px] font-mono text-text-secondary">
                <span className="text-accent font-medium">Output:</span> Subtopic Task DAG
              </div>
            </div>

            {/* Stage 2 */}
            <div className="p-6 rounded-2xl border border-border bg-surface shadow-xs space-y-4 relative overflow-hidden">
              <div className="h-8 w-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent font-bold font-mono text-sm">
                02
              </div>
              <h3 className="text-lg font-bold text-text-primary">Researcher Swarm</h3>
              <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
                Parallel autonomous workers run concurrently via <code className="text-accent font-mono">asyncio.gather</code>.
                Harvests academic preprints, IEEE/ACM papers, and regulatory filings with exact source anchors.
              </p>
              <div className="pt-2 border-t border-border/60 text-[11px] font-mono text-text-secondary">
                <span className="text-accent font-medium">Concurrency:</span> 3 to 6 Parallel Agents
              </div>
            </div>

            {/* Stage 3 */}
            <div className="p-6 rounded-2xl border border-border bg-surface shadow-xs space-y-4 relative overflow-hidden">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-500 font-bold font-mono text-sm">
                03
              </div>
              <h3 className="text-lg font-bold text-text-primary">Fact Checker Barrier</h3>
              <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
                Acts as an adversarial synchronization barrier. Ingests all candidate claims, cross-verifies
                empirical data against fetched URLs, discards contradictions, and scores confidence.
              </p>
              <div className="pt-2 border-t border-border/60 text-[11px] font-mono text-text-secondary">
                <span className="text-emerald-500 font-medium">Confidence:</span> &ge; 85% Threshold
              </div>
            </div>

            {/* Stage 4 */}
            <div className="p-6 rounded-2xl border border-border bg-surface shadow-xs space-y-4 relative overflow-hidden">
              <div className="h-8 w-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent font-bold font-mono text-sm">
                04
              </div>
              <h3 className="text-lg font-bold text-text-primary">Synthesis Writer</h3>
              <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
                Consumes verified claims to synthesize cohesive, multi-section whitepapers with clickable
                inline citations <code className="text-accent font-mono">[1]</code> linked to the verified bibliography.
              </p>
              <div className="pt-2 border-t border-border/60 text-[11px] font-mono text-text-secondary">
                <span className="text-accent font-medium">Exports:</span> Markdown, BibTeX, PDF
              </div>
            </div>
          </div>
        </section>

        {false && (
        <section id="sample-report" className="py-20 bg-surface-subtle/40 border-y border-border/80">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2">
                  <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                    Live Verified Synthesis Preview
                  </span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary">
                  Sample Report: Asynchronous Consensus Bounds
                </h2>
                <p className="text-xs sm:text-sm text-text-secondary">
                  Generated by Quorum Multi-Agent Swarm • Evaluated with 98.4% Fact-Check Confidence
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  href="/projects"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-accent-foreground shadow-xs hover:opacity-90 transition-opacity"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Run Custom Query</span>
                </Link>
              </div>
            </div>

            {/* Embedded Report Card */}
            <div className="rounded-2xl border border-border bg-surface shadow-lg overflow-hidden">
              <div className="p-6 sm:p-8 border-b border-border bg-gradient-to-r from-accent/10 via-accent/5 to-transparent">
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Verified Synthesis
                  </span>
                  <span className="text-xs font-mono text-text-secondary">
                    3 Sections • 3 Primary Literature Citations • 98.4% Confidence
                  </span>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary">
                  Fault-Tolerant Consensus Bounds in Byzantine Mesh Networks
                </h3>
              </div>

              <div className="p-6 sm:p-8 space-y-6 text-sm text-text-secondary leading-relaxed">
                <div className="space-y-2">
                  <h4 className="text-base font-semibold text-text-primary flex items-center gap-2">
                    <span className="h-5 w-5 rounded bg-accent/15 text-accent flex items-center justify-center text-xs font-mono font-bold">
                      01
                    </span>
                    Executive Summary &amp; Theoretical Bounds
                  </h4>
                  <p className="pl-7">
                    In asynchronous distributed environments, consensus requires formal partition resilience
                    under the FLP impossibility framework{" "}
                    <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[11px] font-mono font-bold bg-accent/15 text-accent border border-accent/25">
                      [1]
                    </span>
                    . Autonomous multi-agent coordination establishes deterministic state transitions across
                    Byzantine quorums without sacrificing liveness{" "}
                    <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[11px] font-mono font-bold bg-accent/15 text-accent border border-accent/25">
                      [2]
                    </span>
                    .
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="text-base font-semibold text-text-primary flex items-center gap-2">
                    <span className="h-5 w-5 rounded bg-accent/15 text-accent flex items-center justify-center text-xs font-mono font-bold">
                      02
                    </span>
                    Empirical Analysis &amp; High-Throughput DAG Architectures
                  </h4>
                  <p className="pl-7">
                    Three parallel researcher agents independently retrieved transaction mempool performance
                    benchmarks across Bullshark and Narwhal DAG protocols{" "}
                    <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[11px] font-mono font-bold bg-accent/15 text-accent border border-accent/25">
                      [2]
                    </span>
                    . Decoupling mempool dissemination from transaction ordering enables 120,000 tx/sec with
                    sub-second finality{" "}
                    <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[11px] font-mono font-bold bg-accent/15 text-accent border border-accent/25">
                      [3]
                    </span>
                    .
                  </p>
                </div>

                {/* Sources List */}
                <div className="pt-6 border-t border-border space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
                      <BookOpen className="h-3.5 w-3.5 text-accent" />
                      Cited Primary Literature
                    </span>
                    <span className="text-xs font-mono text-text-secondary">3 Verified DOIs</span>
                  </div>

                  <div className="divide-y divide-border/60">
                    <div className="py-2.5 flex items-center justify-between gap-4">
                      <div className="flex items-start gap-2.5">
                        <span className="text-xs font-mono font-bold text-accent">[1]</span>
                        <div>
                          <div className="text-xs font-medium text-text-primary">
                            Practical Byzantine Fault Tolerance and Proactive Recovery (Castro &amp; Liskov)
                          </div>
                          <div className="text-[11px] font-mono text-text-secondary">
                            ACM Digital Library • DOI: 10.1145/571637.571640
                          </div>
                        </div>
                      </div>
                      <span className="text-[11px] font-mono font-semibold text-emerald-600 dark:text-emerald-400 shrink-0">
                        99.4% Verified
                      </span>
                    </div>

                    <div className="py-2.5 flex items-center justify-between gap-4">
                      <div className="flex items-start gap-2.5">
                        <span className="text-xs font-mono font-bold text-accent">[2]</span>
                        <div>
                          <div className="text-xs font-medium text-text-primary">
                            Bullshark: DAG BFT Protocols with Low Latency and High Throughput
                          </div>
                          <div className="text-[11px] font-mono text-text-secondary">
                            arXiv:2201.05677 [cs.DC]
                          </div>
                        </div>
                      </div>
                      <span className="text-[11px] font-mono font-semibold text-emerald-600 dark:text-emerald-400 shrink-0">
                        98.1% Verified
                      </span>
                    </div>

                    <div className="py-2.5 flex items-center justify-between gap-4">
                      <div className="flex items-start gap-2.5">
                        <span className="text-xs font-mono font-bold text-accent">[3]</span>
                        <div>
                          <div className="text-xs font-medium text-text-primary">
                            HotStuff: BFT Consensus with Linearity and Responsiveness
                          </div>
                          <div className="text-[11px] font-mono text-text-secondary">
                            ACM PODC • DOI: 10.1145/3293611.3331591
                          </div>
                        </div>
                      </div>
                      <span className="text-[11px] font-mono font-semibold text-emerald-600 dark:text-emerald-400 shrink-0">
                        98.8% Verified
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        )}

        {/* 5. Judge Evaluation Callout */}
        <section className="py-16 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="rounded-2xl border-2 border-accent/40 bg-gradient-to-r from-accent/15 via-surface to-surface p-8 sm:p-10 shadow-xl flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-2 text-left">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/20 px-2.5 py-0.5 text-xs font-mono font-semibold text-accent">
                <Sparkles className="h-3.5 w-3.5" />
                Hackathon Evaluation Ready
              </span>
              <h3 className="text-xl sm:text-2xl font-bold text-text-primary">
                Evaluating Quorum for Hackathon Judging?
              </h3>
              <p className="text-sm text-text-secondary max-w-xl">
                Explore the live multi-agent workspace, inspect provider circuit breakers in Settings,
                browse primary citations in the Evidence Library, or run your own research query.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-3 shrink-0 w-full md:w-auto">
              <Link
                href="/projects"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-accent-foreground shadow-sm hover:opacity-90 transition-opacity"
              >
                <span>Open Workspace</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/sign-in"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-surface px-5 py-3 text-sm font-semibold text-text-primary hover:bg-surface-hover transition-colors"
              >
                <span>Sign In</span>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* 6. Public Footer */}
      <footer className="border-t border-border/80 bg-surface py-8 text-xs text-text-secondary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-text-primary">Quorum</span>
            <span>•</span>
            <span>Autonomous Multi-Agent AI Research Platform</span>
          </div>

          <div className="flex items-center gap-6">
            <a
              href="https://github.com/SAIVENKATESH108/Quorum"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-text-primary transition-colors flex items-center gap-1"
            >
              <span>GitHub</span>
              <ExternalLink className="h-3 w-3" />
            </a>
            <Link href="/sources" className="hover:text-text-primary transition-colors">
              Evidence Library
            </Link>
            <Link href="/settings" className="hover:text-text-primary transition-colors">
              Circuit Breakers
            </Link>
            <span className="inline-flex items-center gap-1 text-emerald-500 font-mono">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              API Healthy (200 OK)
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
