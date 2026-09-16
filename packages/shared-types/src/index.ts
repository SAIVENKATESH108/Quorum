/**
 * Shared TypeScript types for Quorum platform.
 */

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  version?: string;
  timestamp?: string;
}

export type AgentRole =
  | 'coordinator'
  | 'researcher'
  | 'analyst'
  | 'fact_checker'
  | 'writer'
  | 'critic';

export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'aggregating'
  | 'completed'
  | 'failed';

export interface AgentMessage {
  id: string;
  agentId: string;
  agentRole: AgentRole;
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface ResearchReport {
  id: string;
  title: string;
  topic: string;
  status: TaskStatus;
  summary?: string;
  markdownContent?: string;
  citations: string[];
  createdAt: string;
  updatedAt: string;
}

export interface UserSession {
  id: string;
  email: string;
  name?: string;
}
