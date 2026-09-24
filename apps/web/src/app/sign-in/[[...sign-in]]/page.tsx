import React from "react";
import Link from "next/link";
import { Metadata } from "next";
import { ArrowLeft, Sparkles } from "lucide-react";
import { AuthForm } from "@/components/auth-form";
import { GuestJudgeCallout } from "@/components/guest-judge-button";

export const metadata: Metadata = {
  title: "Sign In — Quorum AI Intelligence Platform",
  description: "Sign in to Quorum to launch research and manage your private workspace.",
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

        {/* 1-Click Judge / Demo Evaluation Callout */}
        <GuestJudgeCallout />

        <div className="flex justify-center"><AuthForm mode="login" /></div>

        <footer className="text-center text-[11px] text-text-secondary">
          <span>Protected by Quorum database authentication</span>
        </footer>
      </div>
    </main>
  );
}
