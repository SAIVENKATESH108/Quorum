import { create } from "zustand";

export type ActiveModal =
  | "create_project"
  | "create_report"
  | "settings"
  | null;

interface UiState {
  // Sidebar state
  isSidebarOpen: boolean;
  setSidebarOpen: (isOpen: boolean) => void;
  toggleSidebar: () => void;

  // Active modal
  activeModal: ActiveModal;
  setActiveModal: (modal: ActiveModal) => void;
  closeModal: () => void;

  // Selected report for master-detail views
  selectedReportId: string | null;
  setSelectedReportId: (id: string | null) => void;
}

export const useUiStore = create<UiState>((set) => ({
  isSidebarOpen: false,
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  activeModal: null,
  setActiveModal: (modal) => set({ activeModal: modal }),
  closeModal: () => set({ activeModal: null }),

  selectedReportId: null,
  setSelectedReportId: (id) => set({ selectedReportId: id }),
}));
