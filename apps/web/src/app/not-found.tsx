import React from "react";
import Link from "next/link";
import { Compass, FileSearch, Home, Sparkles } from "lucide-react";

export default function NotFoundPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-bg text-text-primary selection:bg-accent/20 selection:text-accent">
      <div className="w-full max-w-lg text-center space-y-6 animate-in fade-in zoom-in-95 duration-300">
        {/* Visual Badge & Icon */}
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/10 text-accent ring-8 ring-accent/5">
          <Compass className="h-8 w-8 animate-pulse" aria-hidden="true" />
        </div>

        <div className="space-y-2">
          <div className="text-xs font-mono font-semibold tracking-widest text-accent uppercase">
            Error 404 &bull; Entity Disconnected
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-text-primary">
            Research Node Not Found
          </h1>
          <p className="text-sm text-text-secondary max-w-md mx-auto leading-relaxed">
            The requested report, workspace, or resource has been migrated, deleted, or never existed in the multi-agent registry.
          </p>
        </div>

        {/* Quick Navigation Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-left">
          <Link
            href="/projects"
            className="group p-4 rounded-xl border border-border bg-surface hover:border-accent/40 hover:bg-surface-hover transition-all"
          >
            <div className="flex items-center gap-2 text-xs font-semibold text-text-primary group-hover:text-accent">
              <Sparkles className="h-4 w-4" />
              <span>Active Projects</span>
            </div>
            <p className="text-[11px] text-text-secondary mt-1">
              Access your autonomous swarms and execution pipelines.
            </p>
          </Link>

          <Link
            href="/sources"
            className="group p-4 rounded-xl border border-border bg-surface hover:border-accent/40 hover:bg-surface-hover transition-all"
          >
            <div className="flex items-center gap-2 text-xs font-semibold text-text-primary group-hover:text-accent">
              <FileSearch className="h-4 w-4" />
              <span>Evidence Library</span>
            </div>
            <p className="text-[11px] text-text-secondary mt-1">
              Explore primary peer-reviewed DOIs and harvested citations.
            </p>
          </Link>
        </div>

        {/* Primary Return Button */}
        <div className="pt-2">
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-xs font-semibold text-accent-foreground shadow-sm hover:opacity-90 transition-all"
          >
            <Home className="h-4 w-4" />
            <span>Return to Quorum Home</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
