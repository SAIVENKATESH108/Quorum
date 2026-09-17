"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, Home, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Structured client telemetry logging
    console.error("[Quorum Uncaught Exception]", {
      message: error.message,
      stack: error.stack,
      digest: error.digest,
      timestamp: new Date().toISOString(),
    });
  }, [error]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-bg text-text-primary selection:bg-accent/20 selection:text-accent">
      <div className="w-full max-w-md text-center space-y-6 animate-in fade-in zoom-in-95 duration-300">
        {/* Visual Badge */}
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-danger/10 text-danger ring-8 ring-danger/5">
          <AlertTriangle className="h-8 w-8 text-rose-500" aria-hidden="true" />
        </div>

        <div className="space-y-2">
          <div className="text-xs font-mono font-semibold tracking-widest text-rose-500 uppercase">
            Error 500 &bull; Pipeline Disruption
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary">
            Execution Interrupted
          </h1>
          <p className="text-xs sm:text-sm text-text-secondary max-w-sm mx-auto leading-relaxed">
            The multi-agent orchestration runtime encountered an unexpected state. State snapshots have been preserved.
          </p>
        </div>

        {error.digest && (
          <div className="p-2.5 rounded-lg border border-border bg-surface-subtle text-[11px] font-mono text-text-secondary">
            Incident Digest: <span className="text-text-primary">{error.digest}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Button
            onClick={() => reset()}
            className="w-full sm:w-auto gap-2 bg-accent text-accent-foreground text-xs font-semibold h-9"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Re-initialize State</span>
          </Button>

          <Link
            href="/projects"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-xs font-semibold text-text-primary hover:bg-surface-hover transition-colors h-9"
          >
            <Home className="h-3.5 w-3.5" />
            <span>Return to Workspace</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
