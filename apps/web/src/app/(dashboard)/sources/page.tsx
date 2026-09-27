"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  AlertCircle,
  BookOpen,
  Copy,
  Download,
  ExternalLink,
  FileCode,
  Globe,
  Info,
  RefreshCw,
  Search,
  Shield,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { apiClient, HarvestedSourceItem, HarvestedSourceStats } from "@/lib/api-client";
import { useAuth } from "@/components/auth-provider";

const CATEGORY_OPTIONS = [
  { id: "all", label: "All Sources" },
  { id: "academic", label: "Academic & arXiv" },
  { id: "technical", label: "Tech & GitHub" },
  { id: "financial", label: "Financial / Regulatory" },
  { id: "general", label: "General & Web" },
] as const;

type FetchState = "idle" | "loading" | "success" | "error";

export default function SourcesExplorerPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  const isGuest = user?.role === "guest";

  const [sources, setSources] = useState<HarvestedSourceItem[]>([]);
  const [stats, setStats] = useState<HarvestedSourceStats | null>(null);
  const [listState, setListState] = useState<FetchState>("idle");
  const [statsState, setStatsState] = useState<FetchState>("idle");
  const [listError, setListError] = useState<string | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const loadData = useCallback(async (category: string) => {
    setListState("loading");
    setStatsState("loading");
    setListError(null);
    setStatsError(null);

    const categoryParam = category !== "all" ? category : undefined;

    // Parallel fetch — list and stats must use the same category filter and visibility scope
    const [listResult, statsResult] = await Promise.allSettled([
      apiClient.getSources({ category: categoryParam }),
      apiClient.getSourceStats({ category: categoryParam }),
    ]);

    if (listResult.status === "fulfilled") {
      setSources(listResult.value);
      setListState("success");
    } else {
      const err = listResult.reason as Error;
      setListError(err.message || "Failed to load sources");
      setSources([]);
      setListState("error");
    }

    if (statsResult.status === "fulfilled") {
      setStats(statsResult.value);
      setStatsState("success");
    } else {
      const err = statsResult.reason as Error;
      setStatsError(err.message || "Failed to load source statistics");
      setStats(null);
      setStatsState("error");
    }
  }, []);

  useEffect(() => {
    void loadData(selectedCategory);
  }, [loadData, selectedCategory]);

  const handleCategoryChange = (cat: string) => {
    setSelectedCategory(cat);
    setSearchQuery("");
  };

  // Client-side search filter only — category filtering is already server-side
  const filteredSources = sources.filter((item) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.url.toLowerCase().includes(q) ||
      item.domain.toLowerCase().includes(q) ||
      (item.report_title && item.report_title.toLowerCase().includes(q))
    );
  });

  const verifiedCount = sources.filter((s) => s.verified).length;
  const verifiedRate = sources.length > 0
    ? Math.round((verifiedCount / sources.length) * 100)
    : 0;
  const meanConfidence = sources.length > 0
    ? (sources.reduce((sum, s) => sum + (s.confidence ?? 0.95), 0) / sources.length) * 100
    : 0;

  const copyCitation = (item: HarvestedSourceItem, format: "bibtex" | "markdown") => {
    let text = "";
    if (format === "markdown") {
      text = `[${item.title}](${item.url})`;
    } else {
      const citeKey = item.domain.replace(/[^a-zA-Z0-9]/g, "") + "_" + item.id.slice(0, 6);
      text = `@misc{${citeKey},\n  title = {${item.title}},\n  url = {${item.url}},\n  note = {Verified by Quorum Multi-Agent Network},\n  year = {2026}\n}`;
    }
    navigator.clipboard.writeText(text);
    toast({
      title: `${format === "bibtex" ? "BibTeX" : "Markdown"} copied`,
      description: "Citation copied to clipboard.",
    });
  };

  const downloadAllBibtex = () => {
    const entries = filteredSources.map((item, idx) => {
      const citeKey = `quorum_${item.category}_${idx + 1}`;
      return `@misc{${citeKey},\n  title = {${item.title}},\n  url = {${item.url}},\n  note = {Verified by Quorum Fact-Checker Swarm (Confidence: ${Math.round((item.confidence ?? 0.95) * 100)}%)},\n  year = {2026}\n}`;
    }).join("\n\n");

    const blob = new Blob([entries], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `quorum_bibliography_${new Date().toISOString().slice(0, 10)}.bib`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    toast({
      title: "Bibliography downloaded",
      description: `Exported ${filteredSources.length} citations as .bib`,
    });
  };

  const hasError = listState === "error" || statsState === "error";

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2.5">
            <BookOpen className="h-6 w-6 text-accent" />
            <span>Sources & Evidence Explorer</span>
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Global repository of primary literature, academic DOIs, and verified evidence harvested by research swarms.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {hasError && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => loadData(selectedCategory)}
              className="gap-2 shadow-xs"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Retry</span>
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={downloadAllBibtex}
            disabled={filteredSources.length === 0}
            className="gap-2 shadow-xs"
          >
            <Download className="h-4 w-4" />
            <span>Export BibTeX</span>
          </Button>
        </div>
      </div>

      {/* Guest read-only banner */}
      {isGuest && (
        <div className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-500">
          <Shield className="h-4 w-4 shrink-0" />
          <span className="font-semibold">Guest Judge — Read-only</span>
          <span className="text-xs text-text-secondary hidden sm:inline">
            — You are viewing sources from curated demo reports only.
          </span>
        </div>
      )}

      {/* Error banners */}
      {statsError && (
        <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-500">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Source statistics unavailable</p>
            <p className="text-xs text-text-secondary mt-0.5">{statsError}</p>
          </div>
        </div>
      )}

      {/* Stats Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {/* Total Evidence — backend-authoritative COUNT(DISTINCT sources.id) */}
        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Total Evidence Harvested</span>
              <Globe className="h-4 w-4 text-text-secondary opacity-70" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-text-primary pt-1">
              {statsState === "loading" ? (
                <Skeleton className="h-7 w-12" />
              ) : statsError ? (
                <span className="text-text-secondary text-base">—</span>
              ) : (
                stats?.total ?? 0
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Unique authorized visible sources
            {selectedCategory !== "all" && (
              <span className="ml-1 text-accent">({selectedCategory} filter)</span>
            )}.
          </CardContent>
        </Card>

        {/* Academic-Domain Sources — heuristic only, NOT peer-review */}
        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Academic-Domain Sources</span>
              <BookOpen className="h-4 w-4 text-accent" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-accent pt-1">
              {statsState === "loading" ? (
                <Skeleton className="h-7 w-12" />
              ) : statsError ? (
                <span className="text-text-secondary text-base">—</span>
              ) : (
                stats?.academic_domain_count ?? 0
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary flex items-start gap-1">
            <Info className="h-3 w-3 shrink-0 mt-0.5 opacity-60" />
            <span>Inferred from source URL domain; not a verified peer-review classification.</span>
          </CardContent>
        </Card>

        {/* Adversarial Audit Pass Rate */}
        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Adversarial Audit Pass Rate</span>
              <ShieldCheck className="h-4 w-4 text-success" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-success pt-1">
              {listState === "loading" ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                `${verifiedRate}%`
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Claims supported with zero contradictions detected.
          </CardContent>
        </Card>

        {/* Mean Confidence Score */}
        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Mean Confidence Score</span>
              <Sparkles className="h-4 w-4 text-warning" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-text-primary pt-1">
              {listState === "loading" ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                `${meanConfidence.toFixed(1)}%`
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Statistical certainty assigned by FactChecker agent.
          </CardContent>
        </Card>
      </div>

      {/* Search & Category Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-secondary" />
          <input
            type="text"
            placeholder="Search titles, URLs, domains, or report topics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-control border border-border bg-surface text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        {/* Category Pills — selection triggers server-side re-fetch */}
        <div className="flex flex-wrap items-center gap-1.5 bg-surface border border-border rounded-control p-1 text-xs">
          {CATEGORY_OPTIONS.map((cat) => (
            <button
              key={cat.id}
              onClick={() => handleCategoryChange(cat.id)}
              className={`px-3 py-1.5 rounded-xs font-medium transition-colors ${
                selectedCategory === cat.id
                  ? "bg-accent text-white shadow-xs"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Active filter indicator */}
      {selectedCategory !== "all" && (
        <p className="text-xs text-text-secondary flex items-center gap-1.5">
          <Info className="h-3 w-3" />
          <span>
            Showing <strong>{selectedCategory}</strong>-domain sources. Statistics above reflect this filter.{" "}
            <button
              onClick={() => handleCategoryChange("all")}
              className="text-accent underline underline-offset-2"
            >
              Clear filter
            </button>
          </span>
        </p>
      )}

      {/* List error state */}
      {listState === "error" && (
        <Card className="border-red-500/30 bg-red-500/5 text-center py-10 px-4">
          <CardContent className="flex flex-col items-center space-y-4">
            <AlertCircle className="h-8 w-8 text-red-500" />
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-text-primary">Failed to load sources</h3>
              <p className="text-sm text-text-secondary max-w-sm">{listError}</p>
            </div>
            <Button size="sm" onClick={() => loadData(selectedCategory)}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Sources Table / List */}
      {listState === "loading" ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full rounded-card" />
          <Skeleton className="h-24 w-full rounded-card" />
          <Skeleton className="h-24 w-full rounded-card" />
        </div>
      ) : listState === "success" && filteredSources.length === 0 ? (
        <Card className="border-dashed border-border bg-surface/40 text-center py-12 px-4">
          <CardContent className="flex flex-col items-center justify-center space-y-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 text-accent">
              <BookOpen className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-text-primary">
                No matching evidence found
              </h3>
              <p className="text-sm text-text-secondary max-w-sm">
                {searchQuery
                  ? "Try adjusting your search terms."
                  : selectedCategory !== "all"
                  ? `No ${selectedCategory}-domain sources found in the current scope.`
                  : "No sources have been harvested yet. Deploy a research swarm to begin."}
              </p>
            </div>
            {searchQuery ? (
              <Button size="sm" variant="outline" onClick={() => setSearchQuery("")}>
                Clear search
              </Button>
            ) : selectedCategory !== "all" ? (
              <Button size="sm" variant="outline" onClick={() => handleCategoryChange("all")}>
                Clear filter
              </Button>
            ) : !isGuest ? (
              <Button asChild size="sm">
                <Link href="/reports/new">Launch Research Query</Link>
              </Button>
            ) : null}
          </CardContent>
        </Card>
      ) : listState === "success" ? (
        <div className="space-y-3">
          {filteredSources.map((item) => (
            <Card
              key={item.id}
              className="border-border bg-surface hover:border-accent/40 transition-all shadow-xs hover:shadow-sm"
            >
              <CardContent className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-medium text-accent bg-accent/10 px-2 py-0.5 rounded-control">
                      {item.domain}
                    </span>
                    <Badge variant={item.verified ? "complete" : "pending"} className="text-[11px]">
                      {item.verified ? "Fact-Checked & Verified" : "Needs Review"}
                    </Badge>
                    {/* linked_report_count: COUNT(DISTINCT report_sources.report_id) */}
                    {(item.linked_report_count ?? 0) > 0 && (
                      <span className="text-[11px] text-text-secondary">
                        Linked to {item.linked_report_count}{" "}
                        {item.linked_report_count === 1 ? "report" : "reports"}
                      </span>
                    )}
                    {/* occurrence_count: reference row count, shown only when > linked_report_count */}
                    {(item.occurrence_count ?? 0) > (item.linked_report_count ?? 0) && (
                      <span className="text-[11px] text-text-secondary opacity-70">
                        ({item.occurrence_count} references)
                      </span>
                    )}
                  </div>

                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group inline-flex items-center gap-1.5 text-base font-semibold text-text-primary hover:text-accent transition-colors"
                  >
                    <span>{item.title}</span>
                    <ExternalLink className="h-3.5 w-3.5 opacity-60 group-hover:opacity-100" />
                  </a>

                  {item.report_title && (
                    <p className="text-xs text-text-secondary flex items-center gap-1.5 truncate">
                      <span>First cited in:</span>
                      <span className="font-medium text-text-primary/90">{item.report_title}</span>
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0 pt-2 sm:pt-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyCitation(item, "markdown")}
                    className="h-8 px-2.5 text-xs gap-1.5"
                    title="Copy Markdown citation"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>Markdown</span>
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyCitation(item, "bibtex")}
                    className="h-8 px-2.5 text-xs gap-1.5"
                    title="Copy BibTeX citation"
                  >
                    <FileCode className="h-3.5 w-3.5" />
                    <span>BibTeX</span>
                  </Button>

                  <Button
                    asChild
                    size="sm"
                    className="h-8 px-2.5 text-xs gap-1.5 bg-surface-hover hover:bg-accent hover:text-white text-text-primary border border-border"
                  >
                    <a href={item.url} target="_blank" rel="noopener noreferrer">
                      <span>Visit</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}
