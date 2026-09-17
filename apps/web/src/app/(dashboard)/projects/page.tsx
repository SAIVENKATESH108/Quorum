"use client";

import React from "react";
import Link from "next/link";
import {
  Folder,
  Plus,
  Clock,
  ArrowUpRight,
  FileText,
  FolderPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjects } from "@/hooks/useProjects";
import { useUiStore } from "@/stores/uiStore";

export default function ProjectsListPage() {
  const { data: projects = [], isLoading } = useProjects();
  const setActiveModal = useUiStore((state) => state.setActiveModal);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Research Projects
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Organize and manage your multi-agent research domains and report archives.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            size="sm"
            onClick={() => setActiveModal("create_project")}
            className="flex items-center gap-2 bg-accent text-accent-foreground"
          >
            <Plus className="h-4 w-4" />
            <span>New Project</span>
          </Button>
        </div>
      </div>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-32 w-full rounded-card" />
          <Skeleton className="h-32 w-full rounded-card" />
          <Skeleton className="h-32 w-full rounded-card" />
        </div>
      ) : projects.length === 0 ? (
        <Card className="border-dashed border-border bg-surface/50 text-center py-12 px-4">
          <CardContent className="flex flex-col items-center justify-center space-y-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 text-accent">
              <FolderPlus className="h-6 w-6" aria-hidden="true" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-text-primary">
                No research projects yet
              </h3>
              <p className="text-sm text-text-secondary max-w-sm">
                Create your first project to organize multi-agent research swarms and generated reports.
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => setActiveModal("create_project")}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              <span>Create Project</span>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Card
              key={project.id}
              className="group flex flex-col justify-between border-border bg-surface transition-all hover:border-accent/50 hover:shadow-md"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-control bg-accent/10 text-accent">
                    <Folder className="h-5 w-5" />
                  </div>
                  <span className="flex items-center gap-1 text-[11px] text-text-secondary">
                    <Clock className="h-3 w-3" />
                    {new Date(project.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </div>
                <CardTitle className="text-base font-semibold text-text-primary group-hover:text-accent transition-colors pt-2">
                  <Link href={`/projects/${project.id}`} className="hover:underline">
                    {project.title}
                  </Link>
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary">
                  Active research domain with autonomous agent pipelines.
                </CardDescription>
              </CardHeader>

              <CardContent className="pt-0">
                <div className="flex items-center justify-between border-t border-border/60 pt-3 text-xs text-text-secondary">
                  <Link
                    href={`/projects/${project.id}`}
                    className="flex items-center gap-1 font-medium text-accent hover:underline"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    <span>Workspace Hub</span>
                  </Link>

                  <Button asChild variant="ghost" size="sm" className="h-7 px-2 text-xs">
                    <Link href={`/reports/new?projectId=${project.id}`}>
                      <span>Launch Swarm</span>
                      <ArrowUpRight className="h-3 w-3 ml-1" />
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
