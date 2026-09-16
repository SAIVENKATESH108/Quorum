import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 select-none",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-accent text-accent-foreground shadow-sm",
        secondary:
          "border-transparent bg-surface-subtle text-text-secondary",
        outline: "border-border text-text-primary",
        // Status indicator variants for Quorum agents & reports
        pending:
          "border-amber-500/20 bg-warning-subtle text-warning-text dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-400/20",
        running:
          "border-indigo-500/20 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-400/20",
        complete:
          "border-emerald-500/20 bg-success-subtle text-success-text dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-400/20",
        failed:
          "border-rose-500/20 bg-danger-subtle text-danger-text dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-400/20",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

function Badge({ className, variant, dot = false, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span
          className={cn(
            "mr-1.5 h-1.5 w-1.5 rounded-full",
            variant === "pending" && "bg-warning",
            variant === "running" && "bg-accent animate-pulse",
            variant === "complete" && "bg-success",
            variant === "failed" && "bg-danger",
            (!variant || variant === "default") && "bg-white",
            variant === "secondary" && "bg-text-secondary"
          )}
          aria-hidden="true"
        />
      )}
      {children}
    </div>
  );
}

export { Badge, badgeVariants };
