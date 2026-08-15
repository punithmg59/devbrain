import { create } from "zustand";
import { authService } from "../services/authService";

export interface User {
  id: string;
  github_id: string;
  username: string;
  email: string | null;
  avatar_url: string | null;
  plan: string;
  created_at: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  authError: string | null;
  setUser: (user: User | null) => void;
  initialize: () => Promise<void>;
  logout: () => Promise<void>;
}

const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,
  authError: null,

  setUser: (user) => set({ user }),

  initialize: async () => {
    console.log("[AUTH_BOOT] Starting authentication initialization...");
    set({ loading: true, authError: null });
    try {
      const user = await authService.getCurrentUser();
      if (user) {
        console.log(
          `[AUTH_BOOT] Authentication confirmed for user: ${user.username} (plan: ${user.plan})`
        );
        set({ user, initialized: true, loading: false, authError: null });
      } else {
        console.log("[AUTH_BOOT] No active user session detected.");
        set({ user: null, initialized: true, loading: false, authError: null });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to authenticate";
      console.error("[AUTH_BOOT] Authentication initialization exception:", err);
      set({ user: null, initialized: true, loading: false, authError: message });
    }
  },

  logout: async () => {
    console.log("[AUTH_BOOT] Clearing user auth state...");
    set({ user: null, initialized: true, loading: false });
    await authService.logout();
  },
}));

export default useAuthStore;
