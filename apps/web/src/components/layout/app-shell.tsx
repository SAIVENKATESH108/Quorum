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
    <div className="h-screen w-screen overflow-hidden bg-bg text-text-primary flex flex-col fixed inset-0">
      {/* Fixed Top Navigation - Fixed at top, never scrolls */}
      <TopNav onOpenMobileMenu={() => setSidebarOpen(true)} />

      {/* Main Layout Area: Fixed Sidebar + Scrollable Content Viewport */}
      <div className="flex flex-1 h-[calc(100vh-3.5rem)] w-full overflow-hidden relative">
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Scrollable Main Content Container - The ONLY scrolling element in dashboard */}
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 h-full overflow-y-auto overflow-x-hidden no-scrollbar focus:outline-none scroll-smooth bg-bg/50"
        >
          <div className="p-4 sm:p-6 md:p-8 lg:p-10 max-w-7xl mx-auto w-full pb-24">
            {children}
          </div>
        </main>
      </div>

      {/* Modals managed by uiStore */}
      <CreateProjectModal />
      <CreateReportModal />
    </div>
  );
}
