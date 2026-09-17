"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  X,
  Bot,
  User,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api-client";

interface CitationItem {
  index: number;
  title: string;
  url: string;
}

interface ChatMessage {
  id: string;
  sender: "user" | "swarm";
  text: string;
  timestamp: string;
  citations?: CitationItem[];
}

interface ReportChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  reportId: string;
  reportQuery: string;
}

const SUGGESTED_PROMPTS = [
  "Summarize the core findings and conclusions",
  "What primary empirical evidence was verified?",
  "List literature sources and citations analyzed",
  "Detail strategic recommendations and trade-offs",
];

export function ReportChatDrawer({
  isOpen,
  onClose,
  reportId,
  reportQuery,
}: ReportChatDrawerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "swarm",
      text: `Hello! I'm your Quorum Research Swarm co-pilot for "${reportQuery}". Ask me anything grounded in the verified sections and literature citations of this report.`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  const handleSend = async (messageText?: string) => {
    const textToSend = (messageText || input).trim();
    if (!textToSend || isSending) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsSending(true);

    try {
      const res = await apiClient.chatWithReport(reportId, textToSend);

      const swarmMsg: ChatMessage = {
        id: `swarm-${Date.now()}`,
        sender: "swarm",
        text: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        citations: res.citations || [],
      };

      setMessages((prev) => [...prev, swarmMsg]);
    } catch {
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        sender: "swarm",
        text: "The research swarm encountered a network delay querying the synthesis cache. Please verify your connection or try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-xs"
          />

          {/* Drawer panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 280 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-surface border-l border-border shadow-2xl flex flex-col"
          >
            {/* Drawer Header */}
            <div className="p-4 sm:p-5 border-b border-border flex items-center justify-between bg-surface-subtle/50">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
                  <Bot className="h-4 w-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-text-primary text-sm">Ask the Swarm</h3>
                    <Badge variant="complete" dot className="text-[10px] py-0 px-1.5">
                      Grounded Q&A
                    </Badge>
                  </div>
                  <p className="text-xs text-text-secondary line-clamp-1 max-w-[260px]">
                    {reportQuery}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onClose}
                  className="h-8 w-8 text-text-secondary hover:text-text-primary"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Suggested Prompts Header Pill */}
            <div className="px-4 py-2 border-b border-border/60 bg-surface-subtle/30 overflow-x-auto no-scrollbar flex items-center gap-1.5">
              <span className="text-[11px] font-mono text-text-secondary flex items-center gap-1 shrink-0">
                <Sparkles className="h-3 w-3 text-accent" />
                Suggested:
              </span>
              {SUGGESTED_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(prompt)}
                  disabled={isSending}
                  className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-surface border border-border hover:border-accent/40 text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
                >
                  {prompt}
                </button>
              ))}
            </div>

            {/* Messages Thread Container */}
            <div className="flex-1 overflow-y-auto no-scrollbar p-4 space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${
                    msg.sender === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {msg.sender === "swarm" && (
                    <div className="h-7 w-7 rounded-full bg-accent/15 border border-accent/30 flex items-center justify-center text-accent shrink-0 mt-0.5">
                      <Bot className="h-3.5 w-3.5" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-accent text-accent-contrast rounded-tr-xs"
                        : "bg-surface-subtle border border-border text-text-primary rounded-tl-xs"
                    }`}
                  >
                    <p className="whitespace-pre-line">{msg.text}</p>

                    {/* Citations Attached */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-border/80 space-y-1.5">
                        <div className="flex items-center gap-1 text-[11px] font-mono text-text-secondary font-medium">
                          <ShieldCheck className="h-3 w-3 text-emerald-500" />
                          <span>Verified Evidence Citations:</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((c) => (
                            <a
                              key={c.index}
                              href={c.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-surface border border-border/80 text-accent hover:underline hover:border-accent transition-colors"
                              title={c.title}
                            >
                              <span>[{c.index}]</span>
                              <span className="truncate max-w-[140px]">{c.title}</span>
                              <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    <div
                      className={`text-[10px] font-mono mt-1 ${
                        msg.sender === "user" ? "text-accent-contrast/70 text-right" : "text-text-secondary"
                      }`}
                    >
                      {msg.timestamp}
                    </div>
                  </div>

                  {msg.sender === "user" && (
                    <div className="h-7 w-7 rounded-full bg-surface-subtle border border-border flex items-center justify-center text-text-secondary shrink-0 mt-0.5">
                      <User className="h-3.5 w-3.5" />
                    </div>
                  )}
                </div>
              ))}

              {isSending && (
                <div className="flex items-start gap-3">
                  <div className="h-7 w-7 rounded-full bg-accent/15 border border-accent/30 flex items-center justify-center text-accent shrink-0">
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  </div>
                  <div className="bg-surface-subtle border border-border rounded-2xl rounded-tl-xs px-4 py-3 text-xs text-text-secondary space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="inline-block h-2 w-2 rounded-full bg-accent animate-pulse" />
                      <span className="font-mono">Synthesizing verified claims...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Footer */}
            <div className="p-3 sm:p-4 border-t border-border bg-surface">
              <div className="relative flex items-center gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about this research..."
                  disabled={isSending}
                  className="flex-1 h-10 px-3.5 pr-10 text-xs sm:text-sm rounded-lg bg-surface-subtle border border-border focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent text-text-primary placeholder:text-text-secondary transition-all disabled:opacity-50"
                />
                <Button
                  size="icon"
                  disabled={!input.trim() || isSending}
                  onClick={() => handleSend()}
                  className="h-10 w-10 shrink-0 bg-accent text-accent-contrast hover:opacity-90"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono text-text-secondary mt-2 px-1">
                <span>Press Enter to send</span>
                <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                  <ShieldCheck className="h-3 w-3" />
                  Grounded in Swarm Context
                </span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
