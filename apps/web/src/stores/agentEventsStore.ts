import { create } from "zustand";

export type ReportStatus =
  | "pending"
  | "planning"
  | "researching"
  | "fact_checking"
  | "writing"
  | "complete"
  | "needs_review"
  | "failed";

export type AgentRole =
  | "orchestrator"
  | "researcher"
  | "fact_checker"
  | "writer";

export type TaskStatus = "queued" | "running" | "succeeded" | "failed";

export interface AgentRunState {
  id: string;
  reportId: string;
  agentRole: AgentRole;
  status: TaskStatus;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

export interface TaskState {
  id: string;
  runId?: string;
  reportId: string;
  taskType: string;
  status: TaskStatus;
  nodeId?: string;
  result?: Record<string, unknown>;
  error?: string;
}

export interface ReportEventPayload {
  type: "report_status" | "task_status" | "agent_status" | "status_event";
  data: {
    event_type?: string;
    report_id: string;
    status?: string;
    agent_role?: string;
    run_id?: string;
    task_id?: string;
    metadata?: Record<string, unknown>;
    [key: string]: unknown;
  };
  timestamp: string;
}

export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting";

interface AgentEventsState {
  // Map of report_id -> overall report status
  reportStatuses: Record<string, ReportStatus>;

  // Map of run_id -> AgentRunState
  agentRuns: Record<string, AgentRunState>;

  // Map of task_id -> TaskState
  tasks: Record<string, TaskState>;

  // Map of report_id -> array of raw events
  eventsLog: Record<string, ReportEventPayload[]>;

  // Map of report_id -> connection status
  connectionStatuses: Record<string, ConnectionState>;

  // Actions
  handleIncomingEvent: (reportId: string, event: ReportEventPayload) => void;
  setConnectionStatus: (reportId: string, status: ConnectionState) => void;
  clearReportEvents: (reportId: string) => void;
}

export const useAgentEventsStore = create<AgentEventsState>((set) => ({
  reportStatuses: {},
  agentRuns: {},
  tasks: {},
  eventsLog: {},
  connectionStatuses: {},

  setConnectionStatus: (reportId, status) =>
    set((state) => ({
      connectionStatuses: {
        ...state.connectionStatuses,
        [reportId]: status,
      },
    })),

  clearReportEvents: (reportId) =>
    set((state) => {
      const nextLog = { ...state.eventsLog };
      delete nextLog[reportId];
      return { eventsLog: nextLog };
    }),

  handleIncomingEvent: (reportId, event) =>
    set((state) => {
      const data = event.data || {};
      const nextLog = [
        ...(state.eventsLog[reportId] || []),
        event,
      ];

      const updates: Partial<AgentEventsState> = {
        eventsLog: {
          ...state.eventsLog,
          [reportId]: nextLog,
        },
      };

      // 1. Update overall Report Status if present
      if (data.status && typeof data.status === "string") {
        const rawStatus = data.status.toLowerCase();
        if (
          [
            "pending",
            "planning",
            "researching",
            "fact_checking",
            "writing",
            "complete",
            "needs_review",
            "failed",
          ].includes(rawStatus)
        ) {
          updates.reportStatuses = {
            ...state.reportStatuses,
            [reportId]: rawStatus as ReportStatus,
          };
        }
      }

      // 2. Update Agent Run State if run_id and agent_role exist
      if (data.run_id) {
        const runId = data.run_id;
        const currentRun = state.agentRuns[runId] || {
          id: runId,
          reportId,
          agentRole: (data.agent_role as AgentRole) || "researcher",
          status: "running",
        };

        const updatedRun: AgentRunState = {
          ...currentRun,
          status: (data.status as TaskStatus) || currentRun.status,
          startedAt: currentRun.startedAt || event.timestamp,
          completedAt:
            data.status === "succeeded" || data.status === "failed"
              ? event.timestamp
              : currentRun.completedAt,
          error: (data.metadata?.error as string) || currentRun.error,
        };

        updates.agentRuns = {
          ...state.agentRuns,
          [runId]: updatedRun,
        };
      }

      // 3. Update Task State if task_id exists
      if (data.task_id) {
        const taskId = data.task_id;
        const currentTask = state.tasks[taskId] || {
          id: taskId,
          runId: data.run_id,
          reportId,
          taskType: (data.metadata?.task_type as string) || "agent_task",
          status: "running",
          nodeId: data.metadata?.node_id as string,
        };

        const updatedTask: TaskState = {
          ...currentTask,
          status: (data.status as TaskStatus) || currentTask.status,
          error: (data.metadata?.error as string) || currentTask.error,
        };

        updates.tasks = {
          ...state.tasks,
          [taskId]: updatedTask,
        };
      }

      return updates as AgentEventsState;
    }),
}));
