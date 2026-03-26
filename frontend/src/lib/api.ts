const BASE = "/api";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ─── Auth ──────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export const authApi = {
  setup: (username: string, password: string) =>
    request<TokenResponse>("/auth/setup", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request<UserInfo>("/auth/me"),
};

// ─── AI Config ─────────────────────────────────────────

export interface AIProvider {
  id: string;
  name: string;
  provider_type: string;
  api_key_masked: string;
  base_url: string;
  model_name: string;
  priority: number;
  is_enabled: boolean;
  max_tokens: number;
  temperature: number;
  last_test_status: string;
  last_test_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIProviderCreate {
  name: string;
  provider_type: string;
  api_key: string;
  base_url: string;
  model_name: string;
  priority?: number;
  is_enabled?: boolean;
  max_tokens?: number;
  temperature?: number;
}

export interface AIProviderTestResult {
  success: boolean;
  message: string;
  latency_ms: number | null;
}

export const aiConfigApi = {
  list: () => request<AIProvider[]>("/settings/ai"),
  create: (data: AIProviderCreate) =>
    request<AIProvider>("/settings/ai", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<AIProviderCreate>) =>
    request<AIProvider>(`/settings/ai/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request(`/settings/ai/${id}`, { method: "DELETE" }),
  test: (id: string) =>
    request<AIProviderTestResult>(`/settings/ai/${id}/test`, {
      method: "POST",
    }),
};

// ─── Projects ──────────────────────────────────────────

export interface Project {
  id: string;
  title: string;
  genre: string;
  target_platform: string;
  target_word_count: number;
  outline: string;
  world_setting: string;
  status: string;
  chapter_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  genre: string;
  target_platform?: string;
  target_word_count?: number;
}

export interface Chapter {
  id: string;
  chapter_no: number;
  title: string;
  outline: string;
  content: string;
  summary: string;
  word_count: number;
  compliance_status: string;
  consistency_status: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ChapterListItem {
  id: string;
  chapter_no: number;
  title: string;
  word_count: number;
  status: string;
  compliance_status: string;
  consistency_status: string;
}

export const projectApi = {
  list: () => request<Project[]>("/projects"),
  create: (data: ProjectCreate) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  get: (id: string) => request<Project>(`/projects/${id}`),
  update: (id: string, data: Partial<ProjectCreate>) =>
    request<Project>(`/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request(`/projects/${id}`, { method: "DELETE" }),
  listChapters: (projectId: string) =>
    request<ChapterListItem[]>(`/projects/${projectId}/chapters`),
  getChapter: (chapterId: string) =>
    request<Chapter>(`/chapters/${chapterId}`),
  updateChapter: (chapterId: string, data: Partial<{ title: string; outline: string; content: string; summary: string; status: string }>) =>
    request<Chapter>(`/chapters/${chapterId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

// ─── Knowledge ─────────────────────────────────────────

export interface KnowledgeEntity {
  id: string;
  entity_type: string;
  name: string;
  data: string;
  summary: string;
  is_important: boolean;
  first_appearance: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeChange {
  id: string;
  entity_type: string;
  entity_id: string;
  field: string;
  old_value: string;
  new_value: string;
  is_auto_extracted: boolean;
  is_confirmed: boolean;
  created_at: string;
}

export interface KnowledgeVersion {
  id: string;
  version_no: number;
  chapter_no: number;
  created_at: string;
  changes: KnowledgeChange[];
}

export interface WorkflowState {
  current_state: string;
  current_chapter_no: number;
  pending_data: string;
}

export const knowledgeApi = {
  list: (projectId: string, entityType?: string) => {
    const params = entityType ? `?entity_type=${entityType}` : "";
    return request<KnowledgeEntity[]>(`/projects/${projectId}/knowledge${params}`);
  },
  get: (projectId: string, entityId: string) =>
    request<KnowledgeEntity>(`/projects/${projectId}/knowledge/${entityId}`),
  update: (projectId: string, entityId: string, data: Partial<{ name: string; data: string; summary: string; is_important: boolean }>) =>
    request<KnowledgeEntity>(`/projects/${projectId}/knowledge/${entityId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  listVersions: (projectId: string) =>
    request<KnowledgeVersion[]>(`/projects/${projectId}/knowledge/versions`),
  confirm: (projectId: string, versionId: string, changeIds: string[], confirmAll: boolean = false) =>
    request<{ confirmed: number; total: number }>(`/projects/${projectId}/knowledge/confirm`, {
      method: "POST",
      body: JSON.stringify({
        version_id: versionId,
        confirmed_change_ids: changeIds,
        confirm_all: confirmAll,
      }),
    }),
};

// ─── Generation ────────────────────────────────────────

export const generateApi = {
  getStatus: (projectId: string) =>
    request<WorkflowState>(`/projects/${projectId}/generate/status`),
  confirmOutline: (projectId: string, outline?: string) =>
    request<{ status: string }>(`/projects/${projectId}/generate/outline/confirm`, {
      method: "POST",
      body: JSON.stringify({ outline }),
    }),
  exportTxt: (projectId: string) =>
    request<{ filename: string; content: string }>(`/projects/${projectId}/generate/export/txt`),
};

/**
 * Connect to an SSE generation endpoint. Returns an EventSource-like controller.
 */
export function connectSSE(
  projectId: string,
  endpoint: "outline" | "opening" | "batch" | `chapter/${number}`,
  options: { trust_mode?: boolean; start_chapter?: number } = {},
  handlers: {
    onChunk?: (data: { chapter_no?: number; text: string }) => void;
    onProgress?: (data: { status: string; current?: number; total?: number; message?: string; chapter_no?: number }) => void;
    onKnowledgeChange?: (data: { chapter_no: number; version_id: string; changes: unknown[]; needs_confirm: boolean }) => void;
    onDone?: (data: Record<string, unknown>) => void;
    onError?: (data: { code: string; message: string }) => void;
    onCompliance?: (data: { chapter_no: number; issues: unknown[] }) => void;
  },
): AbortController {
  const controller = new AbortController();
  const token = localStorage.getItem("token");

  const body: Record<string, unknown> = {};
  if (options.trust_mode) body.trust_mode = true;
  if (options.start_chapter) body.start_chapter = options.start_chapter;

  fetch(`${BASE}/projects/${projectId}/generate/${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        handlers.onError?.({ code: "HTTP_ERROR", message: err.detail || response.statusText });
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ") && currentEvent) {
            try {
              const data = JSON.parse(line.slice(6));
              switch (currentEvent) {
                case "chunk": handlers.onChunk?.(data); break;
                case "progress": handlers.onProgress?.(data); break;
                case "knowledge_change": handlers.onKnowledgeChange?.(data); break;
                case "done": handlers.onDone?.(data); break;
                case "error": handlers.onError?.(data); break;
                case "compliance": handlers.onCompliance?.(data); break;
              }
            } catch { /* ignore parse errors */ }
            currentEvent = "";
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        handlers.onError?.({ code: "NETWORK_ERROR", message: err.message });
      }
    });

  return controller;
}

export { ApiError };
