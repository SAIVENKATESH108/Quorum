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
      <button disabled={busy} className="w-full rounded-control bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground disabled:opacity-50">
        {busy ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
      </button>
    </form>
  );
}
