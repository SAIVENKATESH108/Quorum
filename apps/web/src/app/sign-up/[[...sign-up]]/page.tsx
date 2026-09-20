"use client";

import React from "react";
import Link from "next/link";
import { AuthForm } from "@/components/auth-form";
import { ArrowLeft, Sparkles } from "lucide-react";

export default function SignUpPage() {
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
            Create an account to deploy multi-agent intelligence swarms.
          </p>
        </div>

        <div className="flex justify-center"><AuthForm mode="register" /></div>
      </div>
    </main>
  );
}
