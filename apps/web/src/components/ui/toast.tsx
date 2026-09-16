"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ToastData {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "destructive" | "success";
  duration?: number;
}

interface ToastContextType {
  toasts: ToastData[];
  toast: (data: Omit<ToastData, "id">) => void;
  dismiss: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastData[]>([]);

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = React.useCallback(
    ({ title, description, variant = "default", duration = 4000 }: Omit<ToastData, "id">) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastData = { id, title, description, variant, duration };
      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ toasts, toast, dismiss }}>
      {children}
      <aside
        aria-label="Notifications"
        className="fixed bottom-4 right-4 z-50 flex max-h-screen w-full max-w-sm flex-col space-y-2 pointer-events-none p-4"
      >
        <AnimatePresence mode="popLayout">
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.15 } }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
              role={t.variant === "destructive" ? "alert" : "status"}
              aria-live={t.variant === "destructive" ? "assertive" : "polite"}
              className={cn(
                "pointer-events-auto flex items-start gap-3 rounded-card border p-4 shadow-lg transition-colors",
                t.variant === "destructive"
                  ? "border-danger/30 bg-danger-subtle text-danger-text dark:bg-rose-950/90 dark:text-rose-200"
                  : t.variant === "success"
                  ? "border-success/30 bg-success-subtle text-success-text dark:bg-emerald-950/90 dark:text-emerald-200"
                  : "border-border bg-surface text-text-primary dark:bg-surface"
              )}
            >
              {t.variant === "destructive" ? (
                <AlertCircle className="h-5 w-5 text-danger shrink-0 mt-0.5" aria-hidden="true" />
              ) : t.variant === "success" ? (
                <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" aria-hidden="true" />
              ) : (
                <Info className="h-5 w-5 text-accent shrink-0 mt-0.5" aria-hidden="true" />
              )}
              <div className="flex-1 space-y-1">
                {t.title && <h4 className="text-sm font-semibold leading-none">{t.title}</h4>}
                {t.description && (
                  <p className="text-xs opacity-90 leading-relaxed">{t.description}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="rounded-control p-1 opacity-70 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-accent"
                aria-label="Dismiss notification"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </aside>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
