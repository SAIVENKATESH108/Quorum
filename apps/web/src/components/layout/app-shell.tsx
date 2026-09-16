"use client";

import React from "react";
import { Sidebar } from "./sidebar";
import { TopNav } from "./top-nav";
import { useUiStore } from "@/stores/uiStore";
import { CreateProjectModal } from "@/components/modals/create-project-modal";
import { CreateReportModal } from "@/components/modals/create-report-modal";

export function AppShell({ children }: { children: React.ReactNode }) {
  const isSidebarOpen = useUiStore((state) => state.isSidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);

  return (
    <div className="min-h-screen bg-bg text-text-primary flex flex-col">
      {/* Sticky Top Navigation */}
      <TopNav onOpenMobileMenu={() => setSidebarOpen(true)} />

      {/* Main Layout Area: Sidebar + Page Content */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Scrollable Main Content Container */}
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 lg:p-10 max-w-7xl mx-auto w-full focus:outline-none"
        >
          {children}
        </main>
      </div>

      {/* Modals managed by uiStore */}
      <CreateProjectModal />
      <CreateReportModal />
    </div>
  );
}
