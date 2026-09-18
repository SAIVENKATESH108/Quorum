"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Code2,
  FolderSearch,
  HardDrive,
  Loader2,
  Play,
  Server,
  Sparkles,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useProjects } from "@/hooks/useProjects";
import { useCreateReport } from "@/hooks/useReports";
import { useUiStore } from "@/stores/uiStore";

type InputSourceType = "query" | "github_repo" | "local_folder";
type ProviderMode = "cloud" | "local";

const PROMPT_SUGGESTIONS = [
  "Fault-Tolerant Consensus in Asynchronous Networks and FLP Impossibility",
  "Formal Verification of Distributed Systems and Safety Invariants in TLA+",
  "Autonomous Multi-Agent Orchestration & Topological DAG Workflows",
  "Post-Quantum Cryptographic Transition: Lattice-based Signatures vs Dilithium",
];

const GITHUB_SUGGESTIONS = [
  "https://github.com/facebook/react",
  "https://github.com/astral-sh/uv",
  "https://github.com/fastapi/fastapi",
];

export default function NewReportPage() {
  const router = useRouter();
  const setSelectedReportId = useUiStore((state) => state.setSelectedReportId);

  const { data: projects = [], isLoading: isProjectsLoading } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [sourceType, setSourceType] = useState<InputSourceType>("query");
  const [providerMode, setProviderMode] = useState<ProviderMode>("cloud");

  // Inputs
  const [query, setQuery] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [selectedFolderName, setSelectedFolderName] = useState("");
  const [scannedFiles, setScannedFiles] = useState<{ path: string; size: number }[]>([]);
  const [isScanningFolder, setIsScanningFolder] = useState(false);
  const [folderError, setFolderError] = useState("");

  const effectiveProjectId =
    selectedProjectId || (projects.length > 0 ? projects[0].id : "");

  const createReport = useCreateReport(effectiveProjectId);

  // Chromium File System Access API handler
  const handleSelectLocalFolder = async () => {
    setFolderError("");
    if (typeof window === "undefined" || !("showDirectoryPicker" in window)) {
      setFolderError(
        "Local folder access requires a Chromium-based browser (Chrome, Edge, Brave). On Firefox or Safari, please use the GitHub repository option."
      );
      return;
    }

    try {
      setIsScanningFolder(true);
      // @ts-expect-error - File System Access API
      const dirHandle = await window.showDirectoryPicker();
      setSelectedFolderName(dirHandle.name);

      const files: { path: string; size: number }[] = [];
      let totalBytes = 0;
      const MAX_BYTES = 2 * 1024 * 1024; // 2MB budget

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const scanDirectory = async (handle: any, currentPath = "") => {
        for await (const entry of handle.values()) {
          const path = currentPath ? `${currentPath}/${entry.name}` : entry.name;
          if (
            entry.name.startsWith(".") ||
            ["node_modules", "dist", "build", "target", "vendor", "__pycache__"].includes(entry.name)
          ) {
            continue;
          }

          if (entry.kind === "directory") {
            await scanDirectory(entry, path);
          } else if (entry.kind === "file") {
            const file = await entry.getFile();
            if (file.size < 100000) {
              // only text files < 100kb
              files.push({ path, size: file.size });
              totalBytes += file.size;
              if (totalBytes > MAX_BYTES) break;
            }
          }
        }
      };

      await scanDirectory(dirHandle);
      setScannedFiles(files);
      if (!query.trim()) {
        setQuery(`Architecture Specification & Research Paper: ${dirHandle.name}`);
      }
    } catch (err: unknown) {
      const errorObj = err as { name?: string; message?: string };
      if (errorObj?.name !== "AbortError") {
        setFolderError(`Could not read local folder: ${errorObj?.message || String(err)}`);
      }
    } finally {
      setIsScanningFolder(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveProjectId || createReport.isPending) return;

    let targetQuery = query.trim();
    let sourceRef: string | undefined = undefined;

    if (sourceType === "github_repo") {
      if (!githubUrl.trim()) return;
      sourceRef = githubUrl.trim();
      targetQuery = targetQuery || `Technical Architecture & Research Paper for ${githubUrl.trim()}`;
    } else if (sourceType === "local_folder") {
      if (!selectedFolderName) return;
      sourceRef = selectedFolderName;
      targetQuery = targetQuery || `Local Project Architecture Paper: ${selectedFolderName}`;
    }

    if (!targetQuery) return;

    createReport.mutate(
      {
        projectId: effectiveProjectId,
        data: {
          query: targetQuery,
          // @ts-expect-error - extended payload
          source_type: sourceType,
          source_ref: sourceRef,
          provider_mode: providerMode,
        },
      },
      {
        onSuccess: (res) => {
          const reportId = res.report_id || res.id;
          setSelectedReportId(reportId);
          router.push(`/reports/${reportId}`);
        },
      }
    );
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300 py-2">
      {/* Back link */}
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Dashboard</span>
        </Link>
      </div>

      {/* Main Form Card */}
      <Card className="border border-border bg-surface shadow-md">
        <CardHeader className="pb-4 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-card bg-accent/15 text-accent">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg font-bold text-text-primary">
                  Launch Multi-Agent Synthesis Swarm
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary">
                  Decomposes research, repositories, or local codebases into a topological DAG.
                </CardDescription>
              </div>
            </div>

            {/* Offline Local Ollama / Cloud Swarm Badge */}
            <div className="hidden sm:flex items-center gap-1 text-[11px] font-mono px-2.5 py-1 rounded-full border border-border bg-surface-subtle">
              {providerMode === "local" ? (
                <>
                  <HardDrive className="h-3.5 w-3.5 text-amber-500" />
                  <span className="text-amber-500 font-semibold">Local (Ollama Offline)</span>
                </>
              ) : (
                <>
                  <Server className="h-3.5 w-3.5 text-accent" />
                  <span className="text-accent font-semibold">Cloud Swarm</span>
                </>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 1. Target Project */}
            <div className="space-y-1.5">
              <label
                htmlFor="new-report-project"
                className="text-xs font-semibold text-text-primary flex items-center justify-between"
              >
                <span>Target Project Workspace</span>
                {isProjectsLoading && (
                  <span className="text-[11px] font-normal text-text-secondary">
                    Loading workspaces...
                  </span>
                )}
              </label>

              <select
                id="new-report-project"
                value={effectiveProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                disabled={isProjectsLoading || createReport.isPending}
                className="w-full rounded-control border border-border bg-surface px-3 py-2 text-xs sm:text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-colors cursor-pointer"
              >
                {projects.map((proj) => (
                  <option key={proj.id} value={proj.id}>
                    {proj.title}
                  </option>
                ))}
              </select>
            </div>

            {/* 2. Source Type Selector Tabs */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-text-primary">
                Analysis Mode &amp; Input Source
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setSourceType("query")}
                  className={`flex items-center gap-2 p-3 rounded-lg border text-left text-xs font-medium transition-all cursor-pointer ${
                    sourceType === "query"
                      ? "border-accent bg-accent/10 text-accent font-semibold ring-1 ring-accent"
                      : "border-border bg-surface-subtle text-text-secondary hover:border-accent/40"
                  }`}
                >
                  <BookOpen className="h-4 w-4 shrink-0" />
                  <div>
                    <div className="text-text-primary">Research Query</div>
                    <div className="text-[10px] text-text-secondary">Literature &amp; academic synthesis</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setSourceType("github_repo")}
                  className={`flex items-center gap-2 p-3 rounded-lg border text-left text-xs font-medium transition-all cursor-pointer ${
                    sourceType === "github_repo"
                      ? "border-accent bg-accent/10 text-accent font-semibold ring-1 ring-accent"
                      : "border-border bg-surface-subtle text-text-secondary hover:border-accent/40"
                  }`}
                >
                  <Code2 className="h-4 w-4 shrink-0" />
                  <div>
                    <div className="text-text-primary">GitHub Repository</div>
                    <div className="text-[10px] text-text-secondary">Repo docs &amp; research paper</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setSourceType("local_folder")}
                  className={`flex items-center gap-2 p-3 rounded-lg border text-left text-xs font-medium transition-all cursor-pointer ${
                    sourceType === "local_folder"
                      ? "border-accent bg-accent/10 text-accent font-semibold ring-1 ring-accent"
                      : "border-border bg-surface-subtle text-text-secondary hover:border-accent/40"
                  }`}
                >
                  <FolderSearch className="h-4 w-4 shrink-0" />
                  <div>
                    <div className="text-text-primary">Local Folder</div>
                    <div className="text-[10px] text-text-secondary">Browser File System API</div>
                  </div>
                </button>
              </div>
            </div>

            {/* 3. Dynamic Inputs based on Source Type */}
            {sourceType === "query" && (
              <div className="space-y-2">
                <label htmlFor="new-report-query" className="text-xs font-semibold text-text-primary">
                  Research Topic or Hypothesis
                </label>
                <textarea
                  id="new-report-query"
                  rows={4}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="State your technical hypothesis, comparative question, or investigation scope in detail..."
                  disabled={createReport.isPending}
                  required
                  className="w-full rounded-control border border-border bg-surface p-3 text-xs sm:text-sm text-text-primary placeholder:text-text-secondary/60 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-colors resize-y min-h-[90px]"
                />
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">
                    Suggested Research Topics
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {PROMPT_SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setQuery(s)}
                        className="rounded-full border border-border bg-surface-subtle px-2.5 py-0.5 text-left text-[11px] text-text-secondary hover:border-accent hover:text-accent transition-all cursor-pointer"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {sourceType === "github_repo" && (
              <div className="space-y-3">
                <label htmlFor="github-repo-url" className="text-xs font-semibold text-text-primary">
                  Public GitHub Repository URL
                </label>
                <input
                  id="github-repo-url"
                  type="text"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/owner/repository"
                  disabled={createReport.isPending}
                  required
                  className="w-full rounded-control border border-border bg-surface px-3 py-2 text-xs sm:text-sm text-text-primary placeholder:text-text-secondary/60 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 transition-colors"
                />
                <div className="space-y-1.5">
                  <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">
                    Sample Repositories
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {GITHUB_SUGGESTIONS.map((url) => (
                      <button
                        key={url}
                        type="button"
                        onClick={() => setGithubUrl(url)}
                        className="rounded-full border border-border bg-surface-subtle px-2.5 py-0.5 text-left text-[11px] text-text-secondary hover:border-accent hover:text-accent transition-all cursor-pointer font-mono"
                      >
                        {url.replace("https://github.com/", "")}
                      </button>
                    ))}
                  </div>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  Quorum will fetch the repository tree and core module files, decomposing them for parallel
                  analysis by the <strong>DocumentAnalysisAgent</strong> into an institutional architecture paper.
                </p>
              </div>
            )}

            {sourceType === "local_folder" && (
              <div className="space-y-3 p-4 rounded-xl border border-border bg-surface-subtle">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-semibold text-text-primary">
                      Scan Local Project Directory
                    </h4>
                    <p className="text-[11px] text-text-secondary">
                      Uses Chromium File System Access API. Your files remain local or can be analyzed via local Ollama.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleSelectLocalFolder}
                    disabled={isScanningFolder || createReport.isPending}
                    className="gap-1.5 text-xs"
                  >
                    {isScanningFolder ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <FolderSearch className="h-3.5 w-3.5" />
                    )}
                    <span>{selectedFolderName ? "Change Folder" : "Select Folder"}</span>
                  </Button>
                </div>

                {selectedFolderName && (
                  <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-xs text-emerald-700 dark:text-emerald-300 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                      <span>
                        Folder <strong>{selectedFolderName}</strong> selected ({scannedFiles.length} source files indexed)
                      </span>
                    </div>
                  </div>
                )}

                {folderError && (
                  <div className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/10 text-xs text-rose-600 dark:text-rose-400 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{folderError}</span>
                  </div>
                )}
              </div>
            )}

            {/* 4. AI Provider Strategy Mode (Cloud vs Local Ollama) */}
            <div className="space-y-2 pt-2 border-t border-border">
              <span className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5 text-accent" />
                <span>Execution Inference Provider</span>
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setProviderMode("cloud")}
                  className={`p-3 rounded-lg border text-left text-xs transition-all cursor-pointer ${
                    providerMode === "cloud"
                      ? "border-accent bg-accent/10 text-accent font-semibold ring-1 ring-accent"
                      : "border-border bg-surface text-text-secondary hover:border-accent/40"
                  }`}
                >
                  <div className="text-text-primary font-medium">Cloud Multi-Provider Swarm</div>
                  <div className="text-[10px] text-text-secondary mt-0.5">
                    OpenRouter + Gemini + OpenAI with automatic circuit-breaker fallback.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setProviderMode("local")}
                  className={`p-3 rounded-lg border text-left text-xs transition-all cursor-pointer ${
                    providerMode === "local"
                      ? "border-amber-500 bg-amber-500/10 text-amber-600 dark:text-amber-400 font-semibold ring-1 ring-amber-500"
                      : "border-border bg-surface text-text-secondary hover:border-accent/40"
                  }`}
                >
                  <div className="text-text-primary font-medium">Local Ollama (Offline Capable)</div>
                  <div className="text-[10px] text-text-secondary mt-0.5">
                    Pins strictly to http://localhost:11434 (llama3/mistral). Zero cloud telemetry.
                  </div>
                </button>
              </div>
            </div>

            {/* Submit Bar */}
            <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
              <Link href="/">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={createReport.isPending}
                >
                  Cancel
                </Button>
              </Link>

              <Button
                type="submit"
                size="sm"
                disabled={
                  !effectiveProjectId ||
                  createReport.isPending ||
                  (sourceType === "query" && !query.trim()) ||
                  (sourceType === "github_repo" && !githubUrl.trim()) ||
                  (sourceType === "local_folder" && !selectedFolderName)
                }
                className="gap-1.5 px-5 shadow-xs"
              >
                {createReport.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Launching Pipeline...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-current" />
                    <span>
                      {sourceType === "github_repo"
                        ? "Generate Architecture Paper"
                        : sourceType === "local_folder"
                        ? "Analyze Local Codebase"
                        : "Start Autonomous Pipeline"}
                    </span>
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
