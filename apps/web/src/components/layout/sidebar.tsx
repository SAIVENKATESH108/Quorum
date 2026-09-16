"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  Clock,
  FileText,
  Folder,
  Plus,
  Radio,
  RotateCcw,
  Settings,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjects } from "@/hooks/useProjects";
import { useUiStore } from "@/stores/uiStore";
import { cn } from "@/lib/utils";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const setActiveModal = useUiStore((state) => state.setActiveModal);
  const { data: projects = [], isLoading, isError, refetch } = useProjects();

  // Demo recent reports with live status badges
  const recentReports = [
    {
      id: "rep-1",
      query: "Asynchronous BFT Consensus Bounds",
      status: "running" as const,
      timestamp: "12m ago",
    },
    {
      id: "rep-2",
      query: "Multi-Agent Supply Chain Optimization",
      status: "complete" as const,
      timestamp: "1h ago",
    },
    {
      id: "rep-3",
      query: "Post-Quantum Lattice Signatures",
      status: "pending" as const,
      timestamp: "2h ago",
    },
  ];

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between p-4">
      {/* Upper Navigation section */}
      <div className="space-y-6">
        {/* Action Button: Create New Project */}
        <div>
          <Button
            onClick={() => {
              setActiveModal("create_project");
              onClose();
            }}
            className="w-full justify-start gap-2 shadow-sm font-semibold cursor-pointer"
            size="sm"
            aria-label="Create a new research project"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            <span>New Research Project</span>
          </Button>
        </div>

        {/* Projects Section */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between px-2 text-xs font-semibold tracking-wider text-text-secondary uppercase">
            <span>Projects</span>
            <span className="text-[11px] font-normal lowercase opacity-70">
              {isLoading ? "loading..." : `${projects.length} active`}
            </span>
          </div>

          <nav aria-label="Projects list" className="space-y-1">
            {isLoading ? (
              <div className="space-y-2 py-1">
                <Skeleton className="h-8 w-full rounded-control" />
                <Skeleton className="h-8 w-full rounded-control" />
                <Skeleton className="h-8 w-3/4 rounded-control" />
              </div>
            ) : isError ? (
              <div className="rounded-control bg-danger-subtle p-2 text-xs text-danger-text">
                <p>Failed to load projects.</p>
                <button
                  type="button"
                  onClick={() => refetch()}
                  className="mt-1 inline-flex items-center gap-1 font-semibold underline cursor-pointer"
                >
                  <RotateCcw className="h-3 w-3" /> Retry
                </button>
              </div>
            ) : projects.length === 0 ? (
              <div className="px-2 py-3 text-xs text-text-secondary">
                No projects created yet.
              </div>
            ) : (
              projects.map((proj) => {
                const active = pathname.includes(`/projects/${proj.id}`);
                return (
                  <Link
                    key={proj.id}
                    href={`/projects/${proj.id}`}
                    onClick={() => onClose()}
                    className={cn(
                      "group flex items-center justify-between rounded-control px-2.5 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                      active
                        ? "bg-surface-hover font-semibold text-text-primary"
                        : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                    )}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <Folder className="h-4 w-4 shrink-0 text-accent/80" aria-hidden="true" />
                      <span className="truncate">{proj.title}</span>
                    </div>
                  </Link>
                );
              })
            )}
          </nav>
        </div>

        {/* Recent Reports Section */}
        <div className="space-y-1.5">
          <div className="px-2 text-xs font-semibold tracking-wider text-text-secondary uppercase">
            <span>Live Reports</span>
          </div>

          <nav aria-label="Live reports list" className="space-y-1">
            {recentReports.map((rep) => (
              <Link
                key={rep.id}
                href={`/reports/${rep.id}`}
                onClick={() => onClose()}
                className="group flex flex-col gap-1 rounded-control p-2 text-xs transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                <div className="flex items-center justify-between">
                  <span className="truncate font-medium text-text-primary group-hover:text-accent">
                    {rep.query}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-text-secondary">
                  <Badge variant={rep.status} dot>
                    {rep.status}
                  </Badge>
                  <span className="flex items-center gap-1 opacity-75">
                    <Clock className="h-3 w-3" aria-hidden="true" />
                    {rep.timestamp}
                  </span>
                </div>
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Footer / Agent Status section */}
      <div className="border-t border-border pt-4 space-y-3">
        {/* Real-time agent mesh heartbeat */}
        <div className="rounded-control bg-surface-subtle p-3 text-xs">
          <div className="flex items-center justify-between text-text-secondary mb-1">
            <span className="font-medium flex items-center gap-1.5">
              <Radio className="h-3.5 w-3.5 text-success animate-pulse" aria-hidden="true" />
              Agent Cluster
            </span>
            <span className="text-[10px] text-success font-semibold">ONLINE</span>
          </div>
          <p className="text-[11px] text-text-secondary leading-tight">
            Orchestrator, Researcher, Fact-Checker &amp; Writer ready.
          </p>
        </div>

        {/* Settings link */}
        <Link
          href="/settings"
          onClick={() => onClose()}
          className="flex items-center gap-2 rounded-control px-2.5 py-1.5 text-xs text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <Settings className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Workspace Settings</span>
        </Link>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (visible >= 768px md breakpoint) */}
      <aside
        aria-label="Desktop Project Sidebar"
        className="hidden md:flex w-64 shrink-0 flex-col border-r border-border bg-surface h-[calc(100vh-3.5rem)] sticky top-14 overflow-y-auto"
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer (visible < 768px when isOpen is true) */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex md:hidden" role="dialog" aria-modal="true">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onClose}
              className="fixed inset-0 bg-black/50 backdrop-blur-xs"
              aria-hidden="true"
            />

            {/* Slide-out drawer */}
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="relative flex w-4/5 max-w-xs flex-1 flex-col bg-surface border-r border-border shadow-2xl z-10"
            >
              {/* Mobile Drawer Header */}
              <div className="flex h-14 items-center justify-between px-4 border-b border-border">
                <div className="flex items-center gap-2 font-bold text-text-primary">
                  <div className="flex h-7 w-7 items-center justify-center rounded-control bg-accent text-white">
                    <FileText className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <span>Navigation</span>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-control p-1 text-text-secondary hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  aria-label="Close mobile sidebar drawer"
                >
                  <X className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>

              {/* Mobile Drawer Content */}
              <div className="flex-1 overflow-y-auto">
                {sidebarContent}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
