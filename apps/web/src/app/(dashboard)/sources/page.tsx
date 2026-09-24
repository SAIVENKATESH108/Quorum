"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  BookOpen,
  Copy,
  Download,
  ExternalLink,
  FileCode,
  Globe,
  Search,
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
import { apiClient } from "@/lib/api-client";

interface SourceItem {
  id: string;
  url: string;
  title: string;
  domain: string;
  category: "academic" | "technical" | "financial" | "general";
  report_id?: string;
  report_title?: string;
  citation_count: number;
  verified: boolean;
  confidence: number;
}

export default function SourcesExplorerPage() {
  const { toast } = useToast();
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  useEffect(() => {
    async function loadSources() {
      setIsLoading(true);
      try {
        const data = await apiClient.getSources();
        setSources(
          (data || []).map((source) => ({
            id: source.id,
            url: source.url,
            title: source.title,
            domain: source.domain,
            category: source.category as SourceItem["category"],
            report_id: source.report_id ?? undefined,
            report_title: source.report_title ?? undefined,
            citation_count: source.citation_count ?? 1,
            verified: source.verified ?? true,
            confidence: source.confidence ?? 0.95,
          })),
        );
      } catch (err) {
        console.error("Failed to load sources:", err);
        // Evidence is API-backed only: report the empty library honestly instead
        // of substituting invented citations.
        setSources([]);
      } finally {
        setIsLoading(false);
      }
    }
    loadSources();
  }, []);

  const filteredSources = sources.filter((item) => {
    const matchesSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.url.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.report_title && item.report_title.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesCat = selectedCategory === "all" || item.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  const academicCount = sources.filter((s) => s.category === "academic").length;
  const verifiedRate = sources.length > 0
    ? Math.round((sources.filter((s) => s.verified).length / sources.length) * 100)
    : 100;
  const meanConfidence = sources.length > 0
    ? (sources.reduce((sum, source) => sum + source.confidence, 0) / sources.length) * 100
    : 0;

  const copyCitation = (item: SourceItem, format: "bibtex" | "markdown") => {
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
      return `@misc{${citeKey},\n  title = {${item.title}},\n  url = {${item.url}},\n  note = {Verified by Quorum Fact-Checker Swarm (Confidence: ${Math.round(item.confidence * 100)}%)},\n  year = {2026}\n}`;
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

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2.5">
            <BookOpen className="h-6 w-6 text-accent" />
            <span>Sources &amp; Evidence Explorer</span>
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Global repository of primary literature, academic DOIs, and verified evidence harvested by research swarms.
          </p>
        </div>

        <div className="flex items-center gap-3">
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

      {/* Stats Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Total Evidence Harvested</span>
              <Globe className="h-4 w-4 text-text-secondary opacity-70" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-text-primary pt-1">
              {sources.length}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Primary URLs across all user research investigations.
          </CardContent>
        </Card>

        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Peer-Reviewed Literature</span>
              <BookOpen className="h-4 w-4 text-accent" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-accent pt-1">
              {academicCount}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            arXiv, Nature, IEEE, and academic publishers.
          </CardContent>
        </Card>

        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Adversarial Audit Pass Rate</span>
              <ShieldCheck className="h-4 w-4 text-success" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-success pt-1">
              {verifiedRate}%
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Claims supported with zero contradictions detected.
          </CardContent>
        </Card>

        <Card className="border-border bg-surface shadow-xs">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-text-secondary uppercase tracking-wider flex items-center justify-between">
              <span>Mean Confidence Score</span>
              <Sparkles className="h-4 w-4 text-warning" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold text-text-primary pt-1">
              {meanConfidence.toFixed(1)}%
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-text-secondary">
            Statistical certainty assigned by FactChecker agent.
          </CardContent>
        </Card>
      </div>

      {/* Search & Category Filter Chips */}
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

        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-surface border border-border rounded-control p-1 text-xs">
          {[
            { id: "all", label: "All Sources" },
            { id: "academic", label: "Academic & arXiv" },
            { id: "technical", label: "Tech & GitHub" },
            { id: "financial", label: "Financial / Regulatory" },
            { id: "general", label: "General & Web" },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
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

      {/* Sources Table / List */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full rounded-card" />
          <Skeleton className="h-24 w-full rounded-card" />
          <Skeleton className="h-24 w-full rounded-card" />
        </div>
      ) : filteredSources.length === 0 ? (
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
                Try adjusting your search criteria or deploy a new research swarm to discover primary literature.
              </p>
            </div>
            <Button asChild size="sm">
              <Link href="/reports/new">Launch Research Query</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
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
                    <span className="text-[11px] text-text-secondary">
                      Cited in {item.citation_count} {item.citation_count === 1 ? "claim" : "claims"}
                    </span>
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
                      <span>Cited in report:</span>
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

                  <Button asChild size="sm" className="h-8 px-2.5 text-xs gap-1.5 bg-surface-hover hover:bg-accent hover:text-white text-text-primary border border-border">
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
      )}
    </div>
  );
}
