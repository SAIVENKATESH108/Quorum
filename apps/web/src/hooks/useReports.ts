import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/auth-provider";
import {
  apiClient,
  ApiError,
  ReportCountsResponse,
  ReportCreate,
  ReportCreateResponse,
  ReportDetailResponse,
  ReportListResponse,
  ReportSummaryResponse,
  ProvidersStatusResponse,
} from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";

export const reportKeys = {
  all: ["reports"] as const,
  lists: () => ["reports", "list"] as const,
  /** Key for workspace-wide paginated list with optional status + pagination params. */
  list: (projectId?: string, params?: { status?: string; limit?: number; offset?: number }) =>
    ["reports", "list", projectId ?? "all", params ?? {}] as const,
  details: () => ["reports", "detail"] as const,
  detail: (reportId: string) => ["reports", "detail", reportId] as const,
  counts: () => ["reports", "counts"] as const,
};

export interface UseReportsParams {
  status?: string;
  limit?: number;
  offset?: number;
}

/**
 * Fetch reports for a specific project (unbounded plain array, project-scoped).
 */
export function useProjectReports(projectId: string) {
  return useQuery<ReportSummaryResponse[], ApiError>({
    queryKey: reportKeys.list(projectId),
    queryFn: () => apiClient.getProjectReports(projectId),
  });
}

/**
 * Fetch workspace-wide paginated report list.
 * Status filter and pagination are server-side.
 */
export function useReports(params?: UseReportsParams) {
  return useQuery<ReportListResponse, ApiError>({
    queryKey: reportKeys.list(undefined, params),
    queryFn: () =>
      apiClient.getAllReports(params),
  });
}

/**
 * Per-status-group report counts scoped to the caller's visible reports.
 * Uses the same visibility rules as the report list.
 */
export function useReportCounts() {
  return useQuery<ReportCountsResponse, ApiError>({
    queryKey: reportKeys.counts(),
    queryFn: () => apiClient.getReportCounts(),
  });
}

/**
 * Fetch provider availability statuses without external probing.
 */
export function useProvidersStatus() {
  return useQuery<ProvidersStatusResponse, ApiError>({
    queryKey: ["providers", "status"],
    queryFn: () => apiClient.getProvidersStatus(),
    staleTime: 60_000,
    retry: false,
  });
}

export function useReport(reportId: string | null) {
  const { toast } = useToast();
  const { loading } = useAuth();

  return useQuery<ReportDetailResponse, ApiError>({
    queryKey: reportKeys.detail(reportId || ""),
    queryFn: async () => {
      if (!reportId) throw new Error("Report ID is required");
      try {
        return await apiClient.getReport(reportId);
      } catch (err) {
        if (err instanceof ApiError) {
          toast({
            title: "Failed to load report",
            description: err.detail,
            variant: "destructive",
          });
        }
        throw err;
      }
    },
    enabled: !loading && !!reportId,
  });
}

export function useCreateReport(defaultProjectId?: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<
    ReportCreateResponse,
    ApiError,
    { projectId: string; data: ReportCreate }
  >({
    mutationFn: ({ projectId: pid, data }) => apiClient.createReport(pid, data),
    onSuccess: (newReport, variables) => {
      // Invalidate all report lists, sidebar, and counts
      queryClient.invalidateQueries({ queryKey: reportKeys.all });
      toast({
        title: "Report Pipeline Initiated",
        description: `Autonomous agent swarm scheduled for "${newReport.query}". Real-time updates live on WebSocket.`,
        variant: "success",
      });
    },
    onError: (err) => {
      toast({
        title: "Report Creation Failed",
        description: err.detail || err.message,
        variant: "destructive",
      });
    },
  });
}

export function useDeleteReport() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<void, ApiError, { reportId: string; projectId?: string }>({
    mutationFn: ({ reportId }) => apiClient.deleteReport(reportId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: reportKeys.all });
      toast({
        title: "Report Deleted",
        description: "Report and associated agent runs have been removed.",
      });
    },
    onError: (err) => {
      toast({
        title: "Delete Failed",
        description: err.detail || err.message,
        variant: "destructive",
      });
    },
  });
}
