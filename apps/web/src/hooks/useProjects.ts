import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  apiClient,
  ApiError,
  ProjectCreate,
  ProjectResponse,
} from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";

export const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => ["projects", id] as const,
};

export function useProjects() {
  return useQuery<ProjectResponse[], ApiError>({
    queryKey: projectKeys.all,
    queryFn: async () => apiClient.getProjects(),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<ProjectResponse, ApiError, ProjectCreate>({
    mutationFn: (data) => apiClient.createProject(data),
    onSuccess: (newProject) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
      toast({
        title: "Project Created",
        description: `Project "${newProject.title}" has been successfully created.`,
        variant: "success",
      });
    },
    onError: (err) => {
      toast({
        title: "Project Creation Failed",
        description: err.detail || err.message,
        variant: "destructive",
      });
    },
  });
}
