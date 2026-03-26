import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft, Play, Square, Check, FileText, Download,
  ChevronDown, ChevronRight, RefreshCw, Shield, Loader2,
  BookOpen, ScrollText, Zap, Eye, Users, Swords,
  Package, MapPin, Clock,
} from "lucide-react";
import { useGenerationStore } from "@/stores/generation";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { showToast } from "@/components/ui/Toast";
import type { ChapterListItem } from "@/lib/api";

interface ProjectDetailPageProps {
  projectId: string;
  onBack: () => void;
}

export function ProjectDetailPage({ projectId, onBack }: ProjectDetailPageProps) {
  const store = useGenerationStore();
  const {
    project, chapters, workflowState, isGenerating,
    generationText, progress, logs, trustMode,
    pendingChanges, entities,
  } = store;

  const [activeTab, setActiveTab] = useState<"content" | "chapters" | "knowledge">("content");
  const [showLog, setShowLog] = useState(true);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    store.loadProject(projectId).catch(() => showToast("error", "加载项目失败"));
    store.loadKnowledge().catch(() => {});
  }, [projectId]);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  if (!project) {
    return (
      <div className="min-h-dvh bg-bg-primary flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-text-muted" />
      </div>
    );
  }

  const handleExport = async () => {
    const result = await store.exportTxt();
    if (result) {
      const blob = new Blob([result.content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      a.click();
      URL.revokeObjectURL(url);
      showToast("success", "导出成功");
    }
  };

  return (
    <div className="min-h-dvh bg-bg-primary flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-bg-primary/80 backdrop-blur-md border-b border-bg-hover">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={onBack} aria-label="返回">
              <ArrowLeft size={18} />
            </Button>
            <BookOpen size={18} className="text-accent-orange" />
            <span className="font-bold text-text-primary truncate max-w-[200px]">
              《{project.title}》
            </span>
            <span className="text-xs text-text-muted">{project.genre}</span>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer">
              <input
                type="checkbox"
                checked={trustMode}
                onChange={(e) => store.setTrustMode(e.target.checked)}
                className="accent-accent-orange"
              />
              <Shield size={14} />
              信任模式
            </label>
            {chapters.length > 0 && (
              <Button variant="ghost" size="sm" onClick={handleExport}>
                <Download size={14} />
                <span className="hidden sm:inline">导出</span>
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Tab bar */}
      <div className="border-b border-bg-hover">
        <div className="max-w-7xl mx-auto px-4 flex gap-1">
          {(["content", "chapters", "knowledge"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2.5 text-sm transition-colors relative ${
                activeTab === tab
                  ? "text-accent-orange"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              {tab === "content" ? "生成" : tab === "chapters" ? `章节(${chapters.length})` : `知识库(${entities.length})`}
              {activeTab === tab && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-orange" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 py-4 w-full flex flex-col gap-4">
        {activeTab === "content" && (
          <ContentTab
            project={project}
            workflowState={workflowState}
            isGenerating={isGenerating}
            generationText={generationText}
            progress={progress}
            pendingChanges={pendingChanges}
            onGenerateOutline={() => store.generateOutline()}
            onConfirmOutline={(text) => store.confirmOutline(text)}
            onGenerateOpening={() => store.generateOpening()}
            onGenerateBatch={() => store.generateBatch()}
            onStop={() => store.stopGeneration()}
            onConfirmKnowledge={(all) => store.confirmKnowledge(all)}
          />
        )}
        {activeTab === "chapters" && (
          <ChaptersTab
            chapters={chapters}
            onSelectChapter={(ch) => {
              store.loadChapter(ch.id);
              setActiveTab("content");
            }}
            onRegenerate={(no) => store.regenerateChapter(no)}
            isGenerating={isGenerating}
          />
        )}
        {activeTab === "knowledge" && (
          <KnowledgeTab entities={entities} onRefresh={() => store.loadKnowledge()} />
        )}
      </main>

      {/* System Log */}
      <div className="border-t border-bg-hover bg-bg-secondary">
        <button
          onClick={() => setShowLog(!showLog)}
          className="w-full px-4 py-2 flex items-center gap-2 text-xs text-text-muted hover:text-text-secondary"
        >
          <ScrollText size={14} />
          系统日志 ({logs.length})
          {showLog ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        {showLog && (
          <div
            ref={logRef}
            className="max-h-40 overflow-y-auto px-4 pb-3 font-mono text-xs space-y-0.5"
          >
            {logs.map((log, i) => (
              <div key={i} className={`${
                log.type === "error" ? "text-accent-red"
                : log.type === "warning" ? "text-accent-orange"
                : "text-text-muted"
              }`}>
                <span className="text-text-muted/50">[{log.time}]</span> {log.message}
              </div>
            ))}
            {logs.length === 0 && (
              <div className="text-text-muted/30">等待操作...</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


// ─── Content Tab ───────────────────────────────────────

interface ContentTabProps {
  project: { title: string; outline: string; status: string };
  workflowState: string;
  isGenerating: boolean;
  generationText: string;
  progress: { current: number; total: number; message: string };
  pendingChanges: { chapterNo: number; versionId: string; changes: unknown[]; needsConfirm: boolean } | null;
  onGenerateOutline: () => void;
  onConfirmOutline: (text?: string) => void;
  onGenerateOpening: () => void;
  onGenerateBatch: () => void;
  onStop: () => void;
  onConfirmKnowledge: (all: boolean) => void;
}

function ContentTab({
  project, workflowState, isGenerating, generationText, progress,
  pendingChanges,
  onGenerateOutline, onConfirmOutline, onGenerateOpening,
  onGenerateBatch, onStop, onConfirmKnowledge,
}: ContentTabProps) {
  const [outlineEdit, setOutlineEdit] = useState("");
  const [editingOutline, setEditingOutline] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // Scroll content area to bottom during generation
  useEffect(() => {
    if (contentRef.current && isGenerating) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [generationText, isGenerating]);

  const showOutline = workflowState === "idle" || workflowState === "outline_generating" || workflowState === "outline_pending";
  const showOpening = workflowState === "outline_confirmed" || workflowState === "opening_generating" || workflowState === "opening_pending";
  const showBatch = workflowState === "opening_pending" || workflowState === "batch_generating" || workflowState === "batch_paused" || workflowState === "export_ready" || workflowState === "completed";

  return (
    <div className="space-y-4 flex-1 flex flex-col">
      {/* Progress bar */}
      {isGenerating && progress.total > 0 && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-text-muted">
            <span>{progress.message}</span>
            <span>{progress.current}/{progress.total}</span>
          </div>
          <div className="h-2 bg-bg-hover rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent-orange to-accent-cyan transition-all duration-300 rounded-full"
              style={{ width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Knowledge change notification */}
      {pendingChanges && pendingChanges.needsConfirm && (
        <Card glow="cyan" className="border-accent-cyan/30">
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2 text-accent-cyan">
              <Zap size={16} />
              <span className="text-sm font-medium">
                第{pendingChanges.chapterNo}章：检测到 {pendingChanges.changes.length} 条知识变更
              </span>
            </div>
            <div className="space-y-1.5 text-xs">
              {(pendingChanges.changes as Array<{ entity_type: string; name: string; field: string; new_value: string }>).slice(0, 5).map((c, i) => (
                <div key={i} className="flex gap-2 text-text-secondary">
                  <span className="text-text-muted">[{c.entity_type}]</span>
                  <span className="text-accent-orange">{c.name}</span>
                  <span>{c.field}: {String(c.new_value).slice(0, 50)}</span>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => onConfirmKnowledge(true)}>
                <Check size={14} />
                全部确认
              </Button>
              <Button variant="ghost" size="sm" onClick={() => onConfirmKnowledge(false)}>
                跳过
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 1: Outline */}
      {showOutline && (
        <Card glow={workflowState === "outline_pending" ? "orange" : "none"}>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                <FileText size={16} />
                第一步：生成大纲
              </h3>
              {isGenerating ? (
                <Button variant="danger" size="sm" onClick={onStop}>
                  <Square size={14} />
                  停止
                </Button>
              ) : workflowState === "idle" ? (
                <Button size="sm" onClick={onGenerateOutline}>
                  <Play size={14} />
                  生成大纲
                </Button>
              ) : null}
            </div>

            {(generationText || project.outline) && (
              <>
                {editingOutline ? (
                  <textarea
                    value={outlineEdit}
                    onChange={(e) => setOutlineEdit(e.target.value)}
                    className="w-full h-64 bg-bg-primary border border-bg-hover rounded-lg p-3 text-sm text-text-secondary resize-y focus:outline-none focus:border-accent-orange/40"
                  />
                ) : (
                  <div
                    ref={contentRef}
                    className="max-h-96 overflow-y-auto bg-bg-primary rounded-lg p-3 text-sm text-text-secondary whitespace-pre-wrap"
                  >
                    {generationText || project.outline}
                    {isGenerating && <span className="animate-pulse">▌</span>}
                  </div>
                )}

                {workflowState === "outline_pending" && !isGenerating && (
                  <div className="flex gap-2">
                    {editingOutline ? (
                      <>
                        <Button size="sm" onClick={() => { onConfirmOutline(outlineEdit); setEditingOutline(false); }}>
                          <Check size={14} />
                          保存并确认
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setEditingOutline(false)}>取消</Button>
                      </>
                    ) : (
                      <>
                        <Button size="sm" onClick={() => onConfirmOutline()}>
                          <Check size={14} />
                          确认大纲
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => {
                          setOutlineEdit(generationText || project.outline);
                          setEditingOutline(true);
                        }}>
                          修改
                        </Button>
                        <Button variant="ghost" size="sm" onClick={onGenerateOutline}>
                          <RefreshCw size={14} />
                          重新生成
                        </Button>
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 2: Opening */}
      {showOpening && (
        <Card glow={workflowState === "opening_generating" ? "cyan" : "none"}>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                <Play size={16} />
                第二步：生成开篇3章
              </h3>
              {isGenerating ? (
                <Button variant="danger" size="sm" onClick={onStop}>
                  <Square size={14} />
                  停止
                </Button>
              ) : workflowState === "outline_confirmed" ? (
                <Button size="sm" onClick={onGenerateOpening}>
                  <Play size={14} />
                  开始生成
                </Button>
              ) : null}
            </div>

            {generationText && workflowState.startsWith("opening") && (
              <div
                ref={contentRef}
                className="max-h-96 overflow-y-auto bg-bg-primary rounded-lg p-3 text-sm text-text-secondary whitespace-pre-wrap"
              >
                {generationText}
                {isGenerating && <span className="animate-pulse">▌</span>}
              </div>
            )}

            {workflowState === "opening_pending" && !isGenerating && (
              <div className="flex gap-2">
                <Button size="sm" onClick={onGenerateBatch}>
                  <Zap size={14} />
                  继续批量生成
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 3: Batch */}
      {showBatch && workflowState !== "opening_pending" && (
        <Card glow={workflowState === "batch_generating" ? "cyan" : "none"}>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                <Zap size={16} />
                第三步：批量生成
              </h3>
              {isGenerating ? (
                <Button variant="danger" size="sm" onClick={onStop}>
                  <Square size={14} />
                  停止
                </Button>
              ) : workflowState === "export_ready" || workflowState === "completed" ? (
                <Button variant="secondary" size="sm" onClick={() => onGenerateBatch()}>
                  <RefreshCw size={14} />
                  继续生成
                </Button>
              ) : null}
            </div>

            {generationText && workflowState.startsWith("batch") && (
              <div
                ref={contentRef}
                className="max-h-96 overflow-y-auto bg-bg-primary rounded-lg p-3 text-sm text-text-secondary whitespace-pre-wrap"
              >
                {generationText}
                {isGenerating && <span className="animate-pulse">▌</span>}
              </div>
            )}

            {(workflowState === "export_ready" || workflowState === "completed") && (
              <div className="text-center py-4">
                <p className="text-accent-green text-sm mb-3">全部章节生成完毕！</p>
                <Button onClick={() => {
                  const store = useGenerationStore.getState();
                  store.exportTxt().then(result => {
                    if (result) {
                      const blob = new Blob([result.content], { type: "text/plain;charset=utf-8" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = result.filename;
                      a.click();
                      URL.revokeObjectURL(url);
                      showToast("success", "导出成功");
                    }
                  });
                }}>
                  <Download size={14} />
                  导出 TXT
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}


// ─── Chapters Tab ──────────────────────────────────────

interface ChaptersTabProps {
  chapters: ChapterListItem[];
  onSelectChapter: (ch: ChapterListItem) => void;
  onRegenerate: (no: number) => void;
  isGenerating: boolean;
}

function ChaptersTab({ chapters, onSelectChapter, onRegenerate, isGenerating }: ChaptersTabProps) {
  if (chapters.length === 0) {
    return (
      <div className="text-center py-20">
        <BookOpen size={40} className="mx-auto text-text-muted/30 mb-4" />
        <p className="text-text-muted">还没有章节，请先生成大纲和开篇</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {chapters.map((ch) => (
        <div
          key={ch.id}
          className="group flex items-center gap-3 p-3 rounded-lg bg-bg-secondary hover:bg-bg-hover transition-colors cursor-pointer"
          onClick={() => onSelectChapter(ch)}
        >
          <div className="text-text-muted text-sm w-10 text-right shrink-0">
            {ch.chapter_no}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm text-text-primary truncate">
              {ch.title || `第${ch.chapter_no}章`}
            </div>
            <div className="text-xs text-text-muted mt-0.5">
              {ch.word_count > 0 ? `${ch.word_count}字` : "未生成"}
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <StatusDot status={ch.status} />
            {ch.compliance_status === "flagged" && (
              <span className="text-xs text-accent-red">合规⚠</span>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="opacity-0 group-hover:opacity-100"
              onClick={(e) => {
                e.stopPropagation();
                onRegenerate(ch.chapter_no);
              }}
              disabled={isGenerating}
              aria-label={`重新生成第${ch.chapter_no}章`}
            >
              <RefreshCw size={14} />
            </Button>
            <ChevronRight size={14} className="text-text-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-text-muted",
    generated: "bg-accent-green",
    confirmed: "bg-accent-cyan",
  };
  return (
    <span
      className={`w-2 h-2 rounded-full ${colors[status] || "bg-text-muted"}`}
      title={status}
    />
  );
}


// ─── Knowledge Tab ─────────────────────────────────────

const ENTITY_ICONS: Record<string, typeof Users> = {
  character: Users,
  item: Package,
  skill: Swords,
  faction: Eye,
  location: MapPin,
};

interface KnowledgeTabProps {
  entities: { id: string; entity_type: string; name: string; summary: string; data: string; is_important: boolean }[];
  onRefresh: () => void;
}

function KnowledgeTab({ entities, onRefresh }: KnowledgeTabProps) {
  const [filter, setFilter] = useState<string | null>(null);

  const types = [...new Set(entities.map((e) => e.entity_type))];
  const filtered = filter ? entities.filter((e) => e.entity_type === filter) : entities;

  if (entities.length === 0) {
    return (
      <div className="text-center py-20">
        <Package size={40} className="mx-auto text-text-muted/30 mb-4" />
        <p className="text-text-muted">知识库为空，生成章节后自动提取</p>
        <Button variant="ghost" size="sm" onClick={onRefresh} className="mt-3">
          <RefreshCw size={14} />
          刷新
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Type filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setFilter(null)}
          className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
            !filter ? "bg-accent-orange/10 text-accent-orange border border-accent-orange/30" : "bg-bg-secondary text-text-muted hover:text-text-secondary"
          }`}
        >
          全部 ({entities.length})
        </button>
        {types.map((t) => {
          const Icon = ENTITY_ICONS[t] || Package;
          const count = entities.filter((e) => e.entity_type === t).length;
          return (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-colors ${
                filter === t ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30" : "bg-bg-secondary text-text-muted hover:text-text-secondary"
              }`}
            >
              <Icon size={12} />
              {t} ({count})
            </button>
          );
        })}
        <Button variant="ghost" size="icon" onClick={onRefresh} aria-label="刷新知识库">
          <RefreshCw size={14} />
        </Button>
      </div>

      {/* Entity cards */}
      <div className="grid gap-3 sm:grid-cols-2">
        {filtered.map((entity) => {
          const Icon = ENTITY_ICONS[entity.entity_type] || Package;
          let parsedData: Record<string, unknown> = {};
          try { parsedData = JSON.parse(entity.data); } catch { /* ignore */ }

          return (
            <Card key={entity.id} className="group">
              <CardContent className="space-y-2">
                <div className="flex items-center gap-2">
                  <Icon size={16} className="text-accent-cyan shrink-0" />
                  <span className="font-medium text-sm text-text-primary">{entity.name}</span>
                  {entity.is_important && (
                    <span className="text-xs bg-accent-orange/10 text-accent-orange px-1.5 py-0.5 rounded">重要</span>
                  )}
                  <span className="text-xs text-text-muted ml-auto">{entity.entity_type}</span>
                </div>
                {entity.summary && (
                  <p className="text-xs text-text-secondary">{entity.summary}</p>
                )}
                {Object.keys(parsedData).length > 0 && (
                  <div className="text-xs space-y-0.5 pt-1 border-t border-bg-hover">
                    {Object.entries(parsedData).slice(0, 4).map(([k, v]) => (
                      <div key={k} className="flex gap-2">
                        <span className="text-text-muted shrink-0">{k}:</span>
                        <span className="text-text-secondary truncate">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
