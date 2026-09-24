"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ChevronDown,
  User,
  Shield,
  Sparkles,
  Search,
  Layers,
  Database,
  Settings,
  LogOut,
  Check,
  Cpu,
  Radio,
  ExternalLink,
  Users,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Badge } from "@/components/ui/badge";

const PRESET_ACCOUNTS = [
  {
    email: "venkateshsai589@gmail.com",
    password: "QuorumAdmin2026!",
    name: "Sai Venkatesh",
    role: "admin",
    roleLabel: "Administrator",
    initials: "SV",
    gradient: "from-indigo-600 to-purple-600",
  },
  {
    email: "researcher@quorum.ai",
    password: "Research2026!",
    name: "Dr. Elena Vance",
    role: "member",
    roleLabel: "Lead Researcher",
    initials: "EV",
    gradient: "from-emerald-600 to-teal-600",
  },
  {
    email: "analyst@quorum.ai",
    password: "Analyst2026!",
    name: "Marcus Chen",
    role: "member",
    roleLabel: "Senior Analyst",
    initials: "MC",
    gradient: "from-blue-600 to-cyan-600",
  },
];

export function UserAvatarDropdown() {
  const { user, logout, refresh } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [preferredModel, setPreferredModel] = useState<string>("neural_pulse");
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Close dropdown on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setIsOpen(false);
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  if (!user) {
    return (
      <Link
        href="/sign-in"
        className="rounded-control px-3.5 py-1.5 text-xs font-semibold bg-accent text-accent-foreground hover:bg-accent/90 transition-all shadow-xs"
      >
        Sign In
      </Link>
    );
  }

  // Determine user initials and role label
  const displayName = user.name || user.email.split("@")[0] || "User";
  const initials = displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const isGuest = user.id.includes("guest") || user.email.includes("guest");
  const roleDisplay = isGuest
    ? "Guest Judge"
    : user.role === "admin"
    ? "Admin"
    : "Researcher";

  const handleQuickSwitch = async (acc: (typeof PRESET_ACCOUNTS)[0]) => {
    if (user.email === acc.email) return;
    setSwitching(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: acc.email, password: acc.password }),
      });
      if (res.ok) {
        await refresh();
        setIsOpen(false);
        router.refresh();
      }
    } catch {
      // fallback
    } finally {
      setSwitching(false);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Avatar Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        className={`group flex items-center gap-2 rounded-full py-1 pl-1.5 pr-2.5 transition-all cursor-pointer border ${
          isOpen
            ? "border-accent ring-2 ring-accent/30 bg-surface-hover shadow-sm"
            : "border-border/80 hover:border-border hover:bg-surface-hover"
        }`}
      >
        {/* Avatar Graphic */}
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-tr from-accent to-indigo-500 text-[11px] font-bold text-white shadow-xs">
          {initials}
        </div>

        {/* User Name & Chevron */}
        <div className="flex items-center gap-1.5 text-left">
          <span className="text-xs font-semibold text-text-primary max-w-[120px] truncate hidden sm:inline-block">
            {displayName}
          </span>
          <ChevronDown
            className={`h-3.5 w-3.5 text-text-secondary transition-transform duration-200 ${
              isOpen ? "rotate-180 text-accent" : ""
            }`}
          />
        </div>
      </button>

      {/* Dropdown Card */}
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-2xl border border-border bg-surface text-text-primary shadow-2xl p-2.5 z-50 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-md"
        >
          {/* 1. Header: Profile Info */}
          <div className="p-3 rounded-xl bg-surface-subtle/80 border border-border/60 mb-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-accent to-indigo-500 text-sm font-bold text-white shadow-sm">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <h4 className="text-xs font-bold text-text-primary truncate">
                    {displayName}
                  </h4>
                  <Badge
                    variant="outline"
                    className="text-[9px] uppercase px-1.5 py-0 border-accent/40 bg-accent/10 text-accent font-semibold"
                  >
                    {roleDisplay}
                  </Badge>
                </div>
                <p className="text-[11px] text-text-secondary font-mono truncate">
                  {user.email}
                </p>
              </div>
            </div>
          </div>

          {/* 2. Tailored Application Navigation */}
          <div className="py-1">
            <span className="px-2 text-[10px] font-bold uppercase tracking-wider text-text-secondary">
              Tailored Shortcuts
            </span>
            <div className="mt-1 space-y-0.5">
              <Link
                href="/reports/new"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-text-primary hover:bg-surface-hover transition-colors font-medium"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded bg-accent/15 text-accent">
                  <Sparkles className="h-3.5 w-3.5" />
                </div>
                <span>New Research Swarm Run</span>
              </Link>

              <Link
                href="/reports"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-text-primary hover:bg-surface-hover transition-colors"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded bg-zinc-800/10 text-text-secondary">
                  <Layers className="h-3.5 w-3.5" />
                </div>
                <span>Reports & Telemetry Library</span>
              </Link>

              <Link
                href="/sources"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-text-primary hover:bg-surface-hover transition-colors"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded bg-zinc-800/10 text-text-secondary">
                  <Search className="h-3.5 w-3.5" />
                </div>
                <span>Evidence & Harvested Citations</span>
              </Link>

              <Link
                href="/agents"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-text-primary hover:bg-surface-hover transition-colors"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded bg-zinc-800/10 text-text-secondary">
                  <Cpu className="h-3.5 w-3.5" />
                </div>
                <span>Autonomous Agent Mesh Status</span>
              </Link>
            </div>
          </div>

          <div className="my-2 border-t border-border/70" />

          {/* 3. User Preferences: AI Engine & Telemetry Mode */}
          <div className="py-1">
            <span className="px-2 text-[10px] font-bold uppercase tracking-wider text-text-secondary">
              Preferences & AI Engine
            </span>
            <div className="mt-1.5 px-2 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-secondary flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5 text-accent" />
                  Primary Engine
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setPreferredModel(
                      preferredModel === "neural_pulse"
                        ? "cloud_multi"
                        : "neural_pulse"
                    )
                  }
                  className="px-2 py-0.5 rounded text-[10px] font-semibold bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 transition-colors cursor-pointer"
                >
                  {preferredModel === "neural_pulse"
                    ? "Evorozen Neural Pulse"
                    : "Cloud Chain (Multi)"}
                </button>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-text-secondary flex items-center gap-1.5">
                  <Radio className="h-3.5 w-3.5 text-emerald-500 animate-pulse" />
                  Live Telemetry
                </span>
                <span className="text-[10px] font-medium text-emerald-500">
                  Active (WS + Polling)
                </span>
              </div>
            </div>
          </div>

          <div className="my-2 border-t border-border/70" />

          {/* 4. Fast Account / Persona Switcher */}
          <div className="py-1">
            <span className="px-2 text-[10px] font-bold uppercase tracking-wider text-text-secondary flex items-center justify-between">
              <span>Switch Verified Account</span>
              {switching && (
                <span className="text-[10px] text-accent font-normal animate-pulse">
                  Switching...
                </span>
              )}
            </span>
            <div className="mt-1 space-y-1">
              {PRESET_ACCOUNTS.map((acc) => {
                const isCurrent = user.email === acc.email;
                return (
                  <button
                    key={acc.email}
                    type="button"
                    disabled={switching}
                    onClick={() => handleQuickSwitch(acc)}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left transition-colors cursor-pointer ${
                      isCurrent
                        ? "bg-accent/10 border border-accent/30"
                        : "hover:bg-surface-hover border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div
                        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr ${acc.gradient} text-[10px] font-bold text-white`}
                      >
                        {acc.initials}
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-text-primary leading-tight truncate">
                          {acc.name}
                        </p>
                        <p className="text-[10px] text-text-secondary font-mono truncate">
                          {acc.roleLabel}
                        </p>
                      </div>
                    </div>
                    {isCurrent && (
                      <Check className="h-4 w-4 text-accent shrink-0" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="my-2 border-t border-border/70" />

          {/* 5. Footer Actions: Settings & Sign Out */}
          <div className="space-y-0.5">
            <Link
              href="/settings"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
            >
              <Settings className="h-3.5 w-3.5" />
              <span>Workspace Settings & API Keys</span>
            </Link>

            <button
              type="button"
              onClick={async () => {
                setIsOpen(false);
                await logout();
              }}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-rose-500 hover:bg-rose-500/10 transition-colors font-medium cursor-pointer"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Sign Out of Quorum</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
