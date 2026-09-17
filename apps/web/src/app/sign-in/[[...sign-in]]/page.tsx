import React from "react";
import Link from "next/link";
import { Metadata } from "next";
import { ArrowLeft, ArrowRight, Sparkles, UserCheck } from "lucide-react";
import { ClerkSignInCard } from "./clerk-sign-in";

export const metadata: Metadata = {
  title: "Sign In — Quorum AI Intelligence Platform",
  description:
    "Sign in to Quorum or access the full platform instantly with 1-click Hackathon Judge Quick-Access.",
};

export default function SignInPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-bg selection:bg-accent/20 selection:text-accent">
      <div className="w-full max-w-md space-y-6">
        {/* Quorum Branding Header - Server Rendered */}
        <header className="text-center space-y-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-xs font-medium text-text-secondary hover:text-text-primary transition-colors mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Public Landing Page</span>
          </Link>

          <div className="flex items-center justify-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">
              Quorum
            </h1>
          </div>

          <p className="text-xs sm:text-sm text-text-secondary max-w-xs mx-auto">
            Autonomous multi-agent research platform. Sign in to launch parallel swarms and synthesize verified intelligence.
          </p>
        </header>

        {/* 1-Click Judge / Demo Evaluation Callout - Server Action Form */}
        <section
          aria-label="Hackathon Judge Quick-Access"
          className="rounded-xl border-2 border-accent/40 bg-surface p-4 shadow-sm space-y-3"
        >
          <div className="flex items-center gap-2 text-xs font-semibold text-accent">
            <UserCheck className="h-4 w-4" />
            <span>Hackathon Judge Quick-Access</span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            Evaluating without creating an account? Jump straight into the workspace with full access to project metrics, live pipeline telemetry, and sample reports.
          </p>

          <form action="/api/guest-session" method="POST">
            <button
              type="submit"
              className="w-full inline-flex items-center justify-center gap-2 text-xs font-semibold rounded-lg bg-accent text-accent-foreground hover:opacity-90 transition-all h-9 px-4 cursor-pointer"
            >
              <span>Enter as Guest Judge</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </form>
        </section>

        {/* Clerk Sign In Form (Client Component) */}
        <div className="flex justify-center">
          <ClerkSignInCard />
        </div>

        <footer className="text-center text-[11px] text-text-secondary">
          <span>Protected by Quorum Enterprise Security &amp; Clerk Auth</span>
        </footer>
      </div>
    </main>
  );
}
