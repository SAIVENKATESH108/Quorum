"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, FilePlus2, FileQuestion } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useUiStore } from "@/stores/uiStore";

interface ReportEmptyStateProps {
  reportId?: string;
  errorMessage?: string;
  onRetry?: () => void;
}

export function ReportEmptyState({
  reportId,
  errorMessage,
  onRetry,
}: ReportEmptyStateProps) {
  const setActiveModal = useUiStore((state) => state.setActiveModal);

  return (
    <Card className="border border-border bg-surface p-8 text-center max-w-xl mx-auto my-12 shadow-sm">
      <CardContent className="space-y-4 pt-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 text-accent">
          <FileQuestion className="h-6 w-6" />
        </div>

        <div className="space-y-1.5">
          <h3 className="text-lg font-semibold text-text-primary">
            Report Not Found
          </h3>
          <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
            {errorMessage ||
              (reportId
                ? `No research report matching ID "${reportId}" could be located on this workspace.`
                : "No active report selected.")}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Link href="/">
            <Button variant="outline" size="sm" className="gap-1.5 w-full sm:w-auto">
              <ArrowLeft className="h-3.5 w-3.5" />
              Return to Dashboard
            </Button>
          </Link>

          <Button
            size="sm"
            onClick={() => setActiveModal("create_report")}
            className="gap-1.5 w-full sm:w-auto"
          >
            <FilePlus2 className="h-3.5 w-3.5" />
            Launch New Report
          </Button>

          {onRetry && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onRetry}
              className="w-full sm:w-auto"
            >
              Retry
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
