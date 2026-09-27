"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Menu, Shield } from "lucide-react";
import { UserAvatarDropdown } from "./user-avatar-dropdown";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/components/auth-provider";
import { cn } from "@/lib/utils";

interface TopNavProps {
  onOpenMobileMenu?: () => void;
}

export function TopNav({ onOpenMobileMenu }: TopNavProps) {
  const pathname = usePathname();
  const { user } = useAuth();

  const navLinks = [
    { href: "/projects", label: "Projects" },
    { href: "/reports", label: "Reports" },
    { href: "/sources", label: "Evidence" },
    { href: "/agents", label: "Agent Mesh" },
    { href: "/settings", label: "Settings" },
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
            <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-control bg-white shadow-sm shadow-accent/30">
              <Image
                src="/quorum-logo.png"
                alt=""
                aria-hidden="true"
                width={32}
                height={32}
                className="h-full w-full object-cover"
              />
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

        {/* Right: Guest Badge + Theme Toggle + Tailored User Avatar Dropdown */}
        <div className="flex items-center gap-2.5">
          {user?.role === "guest" && (
            <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-500">
              <Shield className="h-3.5 w-3.5" />
              <span>Guest Judge — Read-only</span>
            </div>
          )}
          <ThemeToggle />
          <UserAvatarDropdown />
        </div>
      </div>
    </header>
  );
}
