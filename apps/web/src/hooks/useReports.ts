import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/auth-provider";
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
  lists: () => ["reports", "list"] as const,
  list: (projectId?: string) => ["reports", "list", projectId ?? "all"] as const,
  details: () => ["reports", "detail"] as const,
  detail: (reportId: string) => ["reports", "detail", reportId] as const,
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
      // Invalidate all report lists and caches (sidebar and list page)
      queryClient.invalidateQueries({
        queryKey: reportKeys.all,
      });
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
      queryClient.invalidateQueries({
        queryKey: reportKeys.all,
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
