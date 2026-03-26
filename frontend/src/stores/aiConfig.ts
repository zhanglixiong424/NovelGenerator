import { create } from "zustand";
import {
  aiConfigApi,
  type AIProvider,
  type AIProviderCreate,
  type AIProviderTestResult,
} from "@/lib/api";

interface AIConfigState {
  providers: AIProvider[];
  loading: boolean;

  fetch: () => Promise<void>;
  add: (data: AIProviderCreate) => Promise<AIProvider>;
  update: (id: string, data: Partial<AIProviderCreate>) => Promise<void>;
  remove: (id: string) => Promise<void>;
  test: (id: string) => Promise<AIProviderTestResult>;
}

export const useAIConfigStore = create<AIConfigState>((set, get) => ({
  providers: [],
  loading: false,

  fetch: async () => {
    set({ loading: true });
    try {
      const providers = await aiConfigApi.list();
      set({ providers });
    } finally {
      set({ loading: false });
    }
  },

  add: async (data) => {
    const provider = await aiConfigApi.create(data);
    set({ providers: [...get().providers, provider] });
    return provider;
  },

  update: async (id, data) => {
    const updated = await aiConfigApi.update(id, data);
    set({
      providers: get().providers.map((p) => (p.id === id ? updated : p)),
    });
  },

  remove: async (id) => {
    await aiConfigApi.delete(id);
    set({ providers: get().providers.filter((p) => p.id !== id) });
  },

  test: async (id) => {
    const result = await aiConfigApi.test(id);
    // Refresh to get updated test status
    await get().fetch();
    return result;
  },
}));
