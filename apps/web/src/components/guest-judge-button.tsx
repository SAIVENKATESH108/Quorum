"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";

export function GuestJudgeCallout() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleGuestAccess = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/auth/guest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        if (typeof window !== "undefined") {
          localStorage.setItem("quorum-auth-token", "judge-session-token");
          localStorage.setItem("quorum-demo-mode", "true");
        }
        await refresh();
        router.push("/projects");
        router.refresh();
      }
    } catch (e) {
      console.error("Guest login failed:", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border-2 border-accent/40 bg-surface p-4 shadow-sm space-y-3">
      <div className="flex items-center gap-2 text-xs font-semibold text-accent">
        <UserCheck className="h-4 w-4" />
        <span>Hackathon Judge Quick-Access</span>
      </div>
      <p className="text-xs text-text-secondary leading-relaxed">
        Evaluating without creating an account? Jump straight into the workspace with full access to project metrics, live pipeline telemetry, and research reports.
      </p>
      <Button
        id="enter-as-guest-judge"
        onClick={handleGuestAccess}
        disabled={loading}
        className="w-full gap-2 text-xs font-semibold bg-accent text-accent-foreground hover:opacity-90 transition-all h-9 cursor-pointer"
      >
        {loading ? (
          <span>Activating Guest Session...</span>
        ) : (
          <>
            <span>Enter as Guest Judge</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </>
        )}
      </Button>
    </div>
  );
}
