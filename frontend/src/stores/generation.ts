import { create } from "zustand";
import {
  projectApi, generateApi, knowledgeApi, connectSSE,
  type Project, type Chapter, type ChapterListItem,
  type KnowledgeEntity, type KnowledgeVersion,
} from "@/lib/api";

interface GenerationState {
  // Project context
  project: Project | null;
  chapters: ChapterListItem[];
  currentChapter: Chapter | null;

  // Workflow
  workflowState: string; // idle, outline_generating, outline_pending, etc.
  isGenerating: boolean;
  generationText: string; // Accumulated SSE text for current operation
  progress: { current: number; total: number; message: string };
  sseController: AbortController | null;

  // Knowledge
  entities: KnowledgeEntity[];
  pendingChanges: {
    chapterNo: number;
    versionId: string;
    changes: unknown[];
    needsConfirm: boolean;
  } | null;

  // System log
  logs: { time: string; message: string; type: string }[];

  // Trust mode
  trustMode: boolean;
  setTrustMode: (v: boolean) => void;

  // Actions
  loadProject: (id: string) => Promise<void>;
  refreshChapters: () => Promise<void>;
  loadChapter: (chapterId: string) => Promise<void>;

  generateOutline: () => void;
  confirmOutline: (outline?: string) => Promise<void>;
  generateOpening: () => void;
  generateBatch: (startChapter?: number) => void;
  regenerateChapter: (chapterNo: number) => void;
  stopGeneration: () => void;

  confirmKnowledge: (confirmAll: boolean, changeIds?: string[]) => Promise<void>;
  loadKnowledge: () => Promise<void>;

  exportTxt: () => Promise<{ filename: string; content: string } | null>;

  addLog: (message: string, type?: string) => void;
}

const now = () => new Date().toLocaleTimeString("zh-CN", { hour12: false });

export const useGenerationStore = create<GenerationState>((set, get) => ({
  project: null,
  chapters: [],
  currentChapter: null,
  workflowState: "idle",
  isGenerating: false,
  generationText: "",
  progress: { current: 0, total: 0, message: "" },
  sseController: null,
  entities: [],
  pendingChanges: null,
  logs: [],
  trustMode: false,

  setTrustMode: (v) => set({ trustMode: v }),

  addLog: (message, type = "info") => {
    set((s) => ({
      logs: [...s.logs.slice(-200), { time: now(), message, type }],
    }));
  },

  loadProject: async (id) => {
    const project = await projectApi.get(id);
    const chapters = await projectApi.listChapters(id);
    const status = await generateApi.getStatus(id);
    set({
      project,
      chapters,
      workflowState: status.current_state,
      currentChapter: null,
      generationText: "",
    });
  },

  refreshChapters: async () => {
    const { project } = get();
    if (!project) return;
    const chapters = await projectApi.listChapters(project.id);
    set({ chapters });
  },

  loadChapter: async (chapterId) => {
    const ch = await projectApi.getChapter(chapterId);
    set({ currentChapter: ch });
  },

  generateOutline: () => {
    const { project, trustMode } = get();
    if (!project) return;
    set({ isGenerating: true, generationText: "", workflowState: "outline_generating" });
    get().addLog("开始生成大纲...");

    const controller = connectSSE(project.id, "outline", { trust_mode: trustMode }, {
      onChunk: (data) => {
        set((s) => ({ generationText: s.generationText + data.text }));
      },
      onProgress: (data) => {
        if (data.message) get().addLog(data.message);
        set({ progress: { current: 0, total: 1, message: data.message || "" } });
      },
      onDone: () => {
        set({ isGenerating: false, workflowState: "outline_pending" });
        get().addLog("大纲生成完毕，等待确认");
      },
      onError: (data) => {
        set({ isGenerating: false });
        get().addLog(`错误: ${data.message}`, "error");
      },
    });
    set({ sseController: controller });
  },

  confirmOutline: async (outline) => {
    const { project } = get();
    if (!project) return;
    await generateApi.confirmOutline(project.id, outline);
    set({ workflowState: "outline_confirmed" });
    get().addLog("大纲已确认");
    // Reload project to get updated outline
    await get().loadProject(project.id);
  },

  generateOpening: () => {
    const { project, trustMode } = get();
    if (!project) return;
    set({ isGenerating: true, generationText: "", workflowState: "opening_generating" });
    get().addLog("开始生成开篇3章...");

    const controller = connectSSE(project.id, "opening", { trust_mode: trustMode }, {
      onChunk: (data) => {
        set((s) => ({ generationText: s.generationText + data.text }));
      },
      onProgress: (data) => {
        if (data.message) get().addLog(data.message);
        set((s) => ({
          progress: {
            current: data.current ?? s.progress.current,
            total: data.total ?? s.progress.total,
            message: data.message || "",
          },
        }));
      },
      onKnowledgeChange: (data) => {
        set({
          pendingChanges: {
            chapterNo: data.chapter_no,
            versionId: data.version_id,
            changes: data.changes,
            needsConfirm: data.needs_confirm,
          },
        });
        if (data.needs_confirm) {
          get().addLog(`第${data.chapter_no}章：检测到${data.changes.length}条知识变更，需确认`);
        }
      },
      onDone: (data) => {
        const chNo = data.chapter_no as number | undefined;
        if (chNo) {
          get().addLog(`第${chNo}章生成完毕(${data.word_count}字)`);
        }
        // Check if this is the final done (status message)
        if (data.status === "opening_pending") {
          set({ isGenerating: false, workflowState: "opening_pending" });
          get().addLog("开篇生成完毕");
          get().refreshChapters();
        }
      },
      onCompliance: (data) => {
        get().addLog(`第${data.chapter_no}章：合规检查发现${data.issues.length}个问题`, "warning");
      },
      onError: (data) => {
        set({ isGenerating: false });
        get().addLog(`错误: ${data.message}`, "error");
      },
    });
    set({ sseController: controller });
  },

  generateBatch: (startChapter) => {
    const { project, trustMode } = get();
    if (!project) return;
    set({ isGenerating: true, generationText: "", workflowState: "batch_generating" });
    get().addLog("开始批量生成...");

    const controller = connectSSE(project.id, "batch", {
      trust_mode: trustMode,
      start_chapter: startChapter,
    }, {
      onChunk: (data) => {
        set((s) => ({ generationText: s.generationText + data.text }));
      },
      onProgress: (data) => {
        if (data.message) get().addLog(data.message);
        set((s) => ({
          progress: {
            current: data.current ?? s.progress.current,
            total: data.total ?? s.progress.total,
            message: data.message || "",
          },
          workflowState: data.status || s.workflowState,
        }));
      },
      onKnowledgeChange: (data) => {
        set({
          pendingChanges: {
            chapterNo: data.chapter_no,
            versionId: data.version_id,
            changes: data.changes,
            needsConfirm: data.needs_confirm,
          },
        });
        if (data.needs_confirm) {
          get().addLog(`第${data.chapter_no}章：${data.changes.length}条知识变更待确认`);
        }
      },
      onDone: (data) => {
        const chNo = data.chapter_no as number | undefined;
        if (chNo) {
          get().addLog(`第${chNo}章完成(${data.word_count}字)`);
          get().refreshChapters();
        }
        if (data.status === "export_ready") {
          set({ isGenerating: false, workflowState: "export_ready" });
          get().addLog("全部章节生成完毕！");
        }
      },
      onCompliance: (data) => {
        get().addLog(`第${data.chapter_no}章：合规${data.issues.length}个问题`, "warning");
      },
      onError: (data) => {
        set({ isGenerating: false });
        get().addLog(`错误: ${data.message}`, "error");
      },
    });
    set({ sseController: controller });
  },

  regenerateChapter: (chapterNo) => {
    const { project, trustMode } = get();
    if (!project) return;
    set({ isGenerating: true, generationText: "" });
    get().addLog(`重新生成第${chapterNo}章...`);

    const controller = connectSSE(project.id, `chapter/${chapterNo}`, { trust_mode: trustMode }, {
      onChunk: (data) => {
        set((s) => ({ generationText: s.generationText + data.text }));
      },
      onProgress: (data) => {
        if (data.message) get().addLog(data.message);
      },
      onKnowledgeChange: (data) => {
        set({
          pendingChanges: {
            chapterNo: data.chapter_no,
            versionId: data.version_id,
            changes: data.changes,
            needsConfirm: data.needs_confirm,
          },
        });
      },
      onDone: () => {
        set({ isGenerating: false });
        get().addLog(`第${chapterNo}章重新生成完毕`);
        get().refreshChapters();
      },
      onError: (data) => {
        set({ isGenerating: false });
        get().addLog(`错误: ${data.message}`, "error");
      },
    });
    set({ sseController: controller });
  },

  stopGeneration: () => {
    const { sseController } = get();
    sseController?.abort();
    set({ isGenerating: false, sseController: null });
    get().addLog("已停止生成");
  },

  confirmKnowledge: async (confirmAll, changeIds) => {
    const { project, pendingChanges } = get();
    if (!project || !pendingChanges) return;
    await knowledgeApi.confirm(
      project.id,
      pendingChanges.versionId,
      changeIds || [],
      confirmAll,
    );
    set({ pendingChanges: null });
    get().addLog("知识变更已确认");
    await get().loadKnowledge();
  },

  loadKnowledge: async () => {
    const { project } = get();
    if (!project) return;
    const entities = await knowledgeApi.list(project.id);
    set({ entities });
  },

  exportTxt: async () => {
    const { project } = get();
    if (!project) return null;
    const result = await generateApi.exportTxt(project.id);
    get().addLog(`导出成功: ${result.filename}`);
    return result;
  },
}));
