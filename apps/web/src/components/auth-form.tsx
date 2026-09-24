"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mode === "login" ? { email, password } : { email, password, name }),
      });
      let data: any = {};
      try {
        data = await response.json();
      } catch {
        throw new Error("Unable to reach backend service. Please check your network and API deployment.");
      }
      if (!response.ok) throw new Error(data.detail || data.error || "Authentication failed");
      await refresh();
      router.push("/projects");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="w-full max-w-md space-y-3 rounded-xl border border-border bg-surface p-6 shadow-xl">
      {mode === "register" && <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" required className="w-full rounded-control border border-border bg-surface-subtle px-3 py-2 text-sm" />}
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" required className="w-full rounded-control border border-border bg-surface-subtle px-3 py-2 text-sm" />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" minLength={8} required className="w-full rounded-control border border-border bg-surface-subtle px-3 py-2 text-sm" />
      {error && <p className="text-sm text-rose-500">{error}</p>}
      <button disabled={busy} className="w-full rounded-control bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground disabled:opacity-50 transition-opacity">
        {busy ? "Authenticating..." : mode === "login" ? "Sign in" : "Create account"}
      </button>

      {mode === "login" && (
        <div className="pt-2 border-t border-border/60 space-y-2">
          <p className="text-[11px] font-medium text-text-secondary text-center">
            Or select a verified workspace account:
          </p>
          <div className="grid grid-cols-1 gap-1.5 text-xs">
            <button
              type="button"
              onClick={() => {
                setEmail("venkateshsai589@gmail.com");
                setPassword("QuorumAdmin2026!");
              }}
              className="flex items-center justify-between px-2.5 py-1.5 rounded border border-border/70 bg-surface-subtle hover:bg-surface-hover text-text-secondary hover:text-text-primary transition-colors text-left"
            >
              <div className="flex flex-col">
                <span className="font-semibold text-text-primary">Sai Venkatesh (Admin)</span>
                <span className="font-mono text-[10px] text-text-secondary">venkateshsai589@gmail.com</span>
              </div>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent/15 text-accent">Auto-fill</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setEmail("researcher@quorum.ai");
                setPassword("Research2026!");
              }}
              className="flex items-center justify-between px-2.5 py-1.5 rounded border border-border/70 bg-surface-subtle hover:bg-surface-hover text-text-secondary hover:text-text-primary transition-colors text-left"
            >
              <div className="flex flex-col">
                <span className="font-semibold text-text-primary">Dr. Elena Vance (Researcher)</span>
                <span className="font-mono text-[10px] text-text-secondary">researcher@quorum.ai</span>
              </div>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent/15 text-accent">Auto-fill</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setEmail("analyst@quorum.ai");
                setPassword("Analyst2026!");
              }}
              className="flex items-center justify-between px-2.5 py-1.5 rounded border border-border/70 bg-surface-subtle hover:bg-surface-hover text-text-secondary hover:text-text-primary transition-colors text-left"
            >
              <div className="flex flex-col">
                <span className="font-semibold text-text-primary">Marcus Chen (Analyst)</span>
                <span className="font-mono text-[10px] text-text-secondary">analyst@quorum.ai</span>
              </div>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent/15 text-accent">Auto-fill</span>
            </button>
          </div>
        </div>
      )}
    </form>
  );
}
