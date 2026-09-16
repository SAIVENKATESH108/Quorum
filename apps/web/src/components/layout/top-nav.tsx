"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Layers, Menu } from "lucide-react";
import { SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

interface TopNavProps {
  onOpenMobileMenu?: () => void;
}

export function TopNav({ onOpenMobileMenu }: TopNavProps) {
  const pathname = usePathname();

  const navLinks = [
    { href: "/projects", label: "Projects" },
    { href: "/reports", label: "Reports" },
    { href: "/agents", label: "Agent Mesh" },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-surface/80 backdrop-blur-md">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        {/* Left: Mobile menu toggle + Logo */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenMobileMenu}
            className="inline-flex h-9 w-9 items-center justify-center rounded-control border border-border text-text-secondary hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent md:hidden"
            aria-label="Open project sidebar menu"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>

          <Link
            href="/"
            className="flex items-center gap-2.5 rounded-control font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            aria-label="Quorum home"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-control bg-accent text-white shadow-sm shadow-accent/30">
              <Layers className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-lg font-bold tracking-tight text-text-primary">
                Quorum
              </span>
              <span className="hidden rounded-full bg-accent/10 px-1.5 py-0.5 text-[10px] font-semibold text-accent sm:inline-block">
                AI SQUAD
              </span>
            </div>
          </Link>
        </div>

        {/* Center: Desktop Navigation Links */}
        <nav
          aria-label="Main Navigation"
          className="hidden md:flex items-center space-x-1"
        >
          {navLinks.map((link) => {
            const isActive =
              pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-control px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                  isActive
                    ? "bg-surface-hover text-text-primary font-semibold"
                    : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right: Theme Toggle + Clerk User Authentication */}
        <div className="flex items-center gap-2.5">
          <ThemeToggle />

          <SignedOut>
            <Link
              href="/sign-in"
              className="rounded-control px-3 py-1.5 text-xs font-semibold bg-accent text-accent-foreground hover:bg-accent/90 transition-colors"
            >
              Sign In
            </Link>
          </SignedOut>
          <SignedIn>
            <UserButton afterSignOutUrl="/sign-in" />
          </SignedIn>
        </div>
      </div>
    </header>
  );
}
