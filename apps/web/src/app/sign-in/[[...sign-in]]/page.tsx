"use client";

import React from "react";
import Link from "next/link";
import { SignIn } from "@clerk/nextjs";
import { ArrowLeft, Sparkles } from "lucide-react";

export default function SignInPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-bg selection:bg-accent/20 selection:text-accent">
      <div className="w-full max-w-md space-y-6">
        {/* Quorum Branding Header */}
        <div className="text-center space-y-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-xs text-text-secondary hover:text-text-primary transition-colors mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Quorum</span>
          </Link>

          <div className="flex items-center justify-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-card bg-accent text-accent-foreground shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <span className="text-2xl font-bold tracking-tight text-text-primary">
              Quorum
            </span>
          </div>

          <p className="text-xs text-text-secondary">
            Sign in to access your autonomous research swarms and verified reports.
          </p>
        </div>

        {/* Clerk Prebuilt SignIn Component */}
        <div className="flex justify-center">
          <SignIn
            path="/sign-in"
            routing="path"
            signUpUrl="/sign-up"
            redirectUrl="/"
            appearance={{
              variables: {
                colorPrimary: "#6366f1",
                colorBackground: "#14141F",
                colorText: "#F1EFE8",
                colorTextSecondary: "#9E9EA0",
                colorInputBackground: "#1D1D2C",
                colorInputText: "#F1EFE8",
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
                  "border-border bg-surface text-text-primary rounded-control text-xs py-2 px-3 focus:ring-2 focus:ring-accent/20 focus:border-accent",
                footerActionLink: "text-accent hover:underline text-xs font-medium",
                identityPreviewText: "text-text-primary text-xs",
                identityPreviewEditButton: "text-accent text-xs",
              },
            }}
          />
        </div>
      </div>
    </main>
  );
}
