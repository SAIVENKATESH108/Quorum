"use client";

import React, { useState } from "react";
import { Sidebar } from "./sidebar";
import { TopNav } from "./top-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  return (
    <div className="min-h-screen bg-bg text-text-primary flex flex-col">
      {/* Sticky Top Navigation */}
      <TopNav onOpenMobileMenu={() => setMobileDrawerOpen(true)} />

      {/* Main Layout Area: Sidebar + Page Content */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          isOpen={mobileDrawerOpen}
          onClose={() => setMobileDrawerOpen(false)}
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
    </div>
  );
}
