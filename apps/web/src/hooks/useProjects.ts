import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  apiClient,
  ApiError,
  ProjectCreate,
  ProjectResponse,
} from "@/lib/api-client";
import { DEFAULT_PROJECTS } from "@/lib/sample-reports-data";
import { useToast } from "@/components/ui/toast";

export const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => ["projects", id] as const,
};

export function useProjects() {
  const { toast } = useToast();
  const { isLoaded } = useAuth();

  return useQuery<ProjectResponse[], ApiError>({
    queryKey: projectKeys.all,
    queryFn: async () => {
      try {
        const res = await apiClient.getProjects();
        return res && res.length > 0 ? res : DEFAULT_PROJECTS;
      } catch (err) {
        return DEFAULT_PROJECTS;
      }
    },
    initialData: DEFAULT_PROJECTS,
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
