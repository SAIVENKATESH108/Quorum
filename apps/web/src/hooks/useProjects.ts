import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
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
  const { toast } = useToast();
  const { isLoaded, isSignedIn } = useAuth();

  return useQuery<ProjectResponse[], ApiError>({
    queryKey: projectKeys.all,
    queryFn: async () => {
      try {
        return await apiClient.getProjects();
      } catch (err) {
        if (err instanceof ApiError) {
          toast({
            title: "Failed to load projects",
            description: err.detail,
            variant: "destructive",
          });
        }
        throw err;
      }
    },
    // Prevent fetching before Clerk is initialized to avoid unauthenticated/mock token queries
    enabled: isLoaded && !!isSignedIn,
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
