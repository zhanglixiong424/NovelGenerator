import { create } from "zustand";
import { authApi, type UserInfo, ApiError } from "@/lib/api";

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  needsSetup: boolean;
  loading: boolean;

  init: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  setup: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("token"),
  user: null,
  needsSetup: false,
  loading: true,

  init: async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      // Check if setup is needed by trying to login with empty creds
      // If auth/me fails with 401 and no users exist, setup is needed
      try {
        await authApi.me();
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) {
          // Forbidden = bearer token but invalid
        }
      }
      set({ loading: false, token: null });
      return;
    }
    try {
      const user = await authApi.me();
      set({ user, token, loading: false });
    } catch {
      localStorage.removeItem("token");
      set({ token: null, user: null, loading: false });
    }
  },

  login: async (username, password) => {
    const res = await authApi.login(username, password);
    localStorage.setItem("token", res.access_token);
    const user = await authApi.me();
    set({ token: res.access_token, user });
  },

  setup: async (username, password) => {
    const res = await authApi.setup(username, password);
    localStorage.setItem("token", res.access_token);
    const user = await authApi.me();
    set({ token: res.access_token, user, needsSetup: false });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, user: null });
  },
}));
