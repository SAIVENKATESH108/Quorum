"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ShieldCheck, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";

export function GuestJudgeCallout() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { refresh } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGuestAccess = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/guest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        await refresh();
        // Clear all cached workspace data before navigating so no stale
        // owner reports/sources/projects render briefly in guest mode.
        queryClient.clear();
        router.push("/projects");
        router.refresh();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "Failed to enter guest demo workspace. Please try again.");
      }
    } catch (e) {
      console.error("Guest login failed:", e);
      setError("Unable to connect to service. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-accent/40 bg-surface p-4 shadow-sm space-y-3">
      <div className="flex items-center gap-2 text-xs font-semibold text-accent">
        <ShieldCheck className="h-4 w-4" />
        <span>Hackathon Evaluator Quick-Access</span>
      </div>
      <p className="text-xs text-text-secondary leading-relaxed">
        Explore a read-only demo workspace. No private user data is available.
      </p>

      {error && (
        <div
          role="alert"
          aria-live="polite"
          className="flex items-center gap-2 p-2 rounded-md bg-destructive/10 border border-destructive/20 text-xs text-destructive"
        >
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <Button
        id="enter-as-guest-judge"
        onClick={handleGuestAccess}
        disabled={loading}
        className="w-full gap-2 text-xs font-semibold bg-accent text-accent-foreground hover:opacity-90 transition-all h-9 cursor-pointer"
      >
        {loading ? (
          <span>Activating Demo Session...</span>
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
