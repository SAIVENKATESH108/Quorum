"use client";

import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FolderPlus, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCreateProject } from "@/hooks/useProjects";
import { useUiStore } from "@/stores/uiStore";

export function CreateProjectModal() {
  const activeModal = useUiStore((state) => state.activeModal);
  const closeModal = useUiStore((state) => state.closeModal);
  const createProject = useCreateProject();

  const [title, setTitle] = useState("");

  const isOpen = activeModal === "create_project";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || createProject.isPending) return;

    createProject.mutate(
      { title: title.trim() },
      {
        onSuccess: () => {
          setTitle("");
          closeModal();
        },
      }
    );
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-project-title"
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeModal}
            className="fixed inset-0 bg-black/60 backdrop-blur-xs"
            aria-hidden="true"
          />

          {/* Modal Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 350, damping: 25 }}
            className="relative w-full max-w-md rounded-card border border-border bg-surface p-6 shadow-2xl z-10"
          >
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-control bg-accent/10 text-accent">
                  <FolderPlus className="h-4 w-4" aria-hidden="true" />
                </div>
                <h3 id="create-project-title" className="text-base font-semibold text-text-primary">
                  Create Research Project
                </h3>
              </div>
              <button
                type="button"
                onClick={closeModal}
                className="rounded-control p-1 text-text-secondary hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                aria-label="Close modal"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
              <div>
                <label
                  htmlFor="project-title-input"
                  className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1.5"
                >
                  Project Title
                </label>
                <input
                  id="project-title-input"
                  type="text"
                  required
                  placeholder="e.g. Asynchronous BFT Protocols"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full rounded-control border border-border bg-surface-subtle px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/60 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-all"
                  autoFocus
                />
              </div>

              {createProject.isError && (
                <div className="rounded-control bg-danger-subtle p-2.5 text-xs text-danger-text">
                  {createProject.error.detail || "Failed to create project. Please try again."}
                </div>
              )}

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={closeModal}
                  disabled={createProject.isPending}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={!title.trim() || createProject.isPending}
                  className="gap-1.5 min-w-24"
                >
                  {createProject.isPending ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <span>Create Project</span>
                  )}
                </Button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
