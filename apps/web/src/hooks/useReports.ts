import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  apiClient,
  ApiError,
  ReportCreate,
  ReportCreateResponse,
  ReportDetailResponse,
  ReportSummaryResponse,
} from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";

export const reportKeys = {
  all: ["reports"] as const,
  list: (projectId?: string) => ["projects", projectId, "reports"] as const,
  detail: (reportId: string) => ["reports", reportId] as const,
};

export function useReports(projectId?: string) {
  return useQuery<ReportSummaryResponse[], ApiError>({
    queryKey: reportKeys.list(projectId),
    // Reports are always API-backed: an empty workspace renders the empty state
    // rather than being backfilled with demo/seed entries.
    queryFn: async () =>
      projectId
        ? apiClient.getProjectReports(projectId)
        : apiClient.getAllReports(),
  });
}

export function useReport(reportId: string | null) {
  const { toast } = useToast();
  const { isLoaded } = useAuth();

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
    enabled: isLoaded && !!reportId,
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
      // Invalidate project reports query cache
      const targetProjectId = variables.projectId || defaultProjectId;
      if (targetProjectId) {
        queryClient.invalidateQueries({
          queryKey: reportKeys.list(targetProjectId),
        });
      }
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
      if (variables.projectId) {
        queryClient.invalidateQueries({
          queryKey: reportKeys.list(variables.projectId),
        });
      }
      queryClient.invalidateQueries({
        queryKey: reportKeys.detail(variables.reportId),
      });
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
