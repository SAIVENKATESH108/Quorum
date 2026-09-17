"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignIn } from "@clerk/nextjs";
import { ArrowLeft, Sparkles, ArrowRight, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function SignInPage() {
  const router = useRouter();
  const [isActivatingDemo, setIsActivatingDemo] = useState(false);

  const handleGuestJudgeAccess = () => {
    setIsActivatingDemo(true);
    if (typeof window !== "undefined") {
      localStorage.setItem("quorum-auth-token", "demo-judge-session-token");
      localStorage.setItem("quorum-demo-mode", "true");
    }
    setTimeout(() => {
      router.push("/projects");
    }, 400);
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-bg selection:bg-accent/20 selection:text-accent">
      <div className="w-full max-w-md space-y-6">
        {/* Quorum Branding Header */}
        <div className="text-center space-y-2">
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
            <span className="text-2xl font-bold tracking-tight text-text-primary">
              Quorum
            </span>
          </div>

          <p className="text-xs sm:text-sm text-text-secondary max-w-xs mx-auto">
            Autonomous multi-agent research platform. Sign in to launch parallel swarms and synthesize verified intelligence.
          </p>
        </div>

        {/* 1-Click Judge / Demo Evaluation Callout */}
        <div className="rounded-xl border-2 border-accent/40 bg-surface p-4 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-accent">
            <UserCheck className="h-4 w-4" />
            <span>Hackathon Judge Quick-Access</span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            Evaluating without creating an account? Jump straight into the workspace with full access to project metrics, live pipeline telemetry, and sample reports.
          </p>
          <Button
            onClick={handleGuestJudgeAccess}
            disabled={isActivatingDemo}
            className="w-full gap-2 text-xs font-semibold bg-accent text-accent-foreground hover:opacity-90 transition-all h-9"
          >
            {isActivatingDemo ? (
              <span>Activating Guest Session...</span>
            ) : (
              <>
                <span>Enter as Guest Judge</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </>
            )}
          </Button>
        </div>

        {/* Clerk Prebuilt SignIn Component */}
        <div className="flex justify-center">
          <SignIn
            path="/sign-in"
            routing="path"
            signUpUrl="/sign-up"
            fallbackRedirectUrl="/projects"
            appearance={{
              variables: {
                colorPrimary: "#6366f1",
                colorBackground: "var(--surface)",
                colorText: "var(--text-primary)",
                colorTextSecondary: "var(--text-secondary)",
                colorInputBackground: "var(--surface-subtle)",
                colorInputText: "var(--text-primary)",
                borderRadius: "0.5rem",
              },
              elements: {
                card: "border border-border bg-surface shadow-xl rounded-card",
                headerTitle: "text-text-primary font-semibold text-lg",
                headerSubtitle: "text-text-secondary text-xs",
                formButtonPrimary:
                  "bg-accent hover:bg-accent/90 text-accent-foreground font-medium text-xs py-2.5 rounded-control shadow-xs transition-colors",
                formFieldLabel: "text-text-secondary text-xs font-medium",
                formFieldInput:
                  "border-border bg-surface-subtle text-text-primary rounded-control text-xs py-2 px-3 focus:ring-2 focus:ring-accent/20 focus:border-accent",
                footerActionLink: "text-accent hover:underline text-xs font-medium",
                identityPreviewText: "text-text-primary text-xs",
                identityPreviewEditButton: "text-accent text-xs",
              },
            }}
          />
        </div>

        {/* Semantic Non-JS / SSR Fallback Information for Crawlers and Bots */}
        <noscript>
          <div className="rounded-xl border border-border bg-surface p-5 text-xs text-text-secondary space-y-2 text-center">
            <p className="font-semibold text-text-primary">JavaScript is currently disabled</p>
            <p>
              Please enable JavaScript in your browser or explore our public landing page and documentation.
            </p>
            <a href="/" className="text-accent underline font-medium block mt-2">
              Back to Home Page
            </a>
          </div>
        </noscript>
      </div>
    </main>
  );
}
