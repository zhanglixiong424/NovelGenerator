import { useEffect, useState } from "react";
import {
  Terminal, Settings, Database, Plus, BookOpen,
  Trash2, ChevronRight, LogOut, Loader2,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { projectApi, type Project } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { showToast } from "@/components/ui/Toast";

interface DashboardPageProps {
  onNavigate: (page: string) => void;
  onOpenProject: (id: string) => void;
}

export function DashboardPage({ onNavigate, onOpenProject }: DashboardPageProps) {
  const { user, logout } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const fetchProjects = async () => {
    try {
      const data = await projectApi.list();
      setProjects(data);
    } catch {
      showToast("error", "加载项目失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProjects(); }, []);

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`确定删除小说《${title}》及其所有章节？此操作不可撤销。`)) return;
    try {
      await projectApi.delete(id);
      setProjects((p) => p.filter((x) => x.id !== id));
      showToast("success", "已删除");
    } catch {
      showToast("error", "删除失败");
    }
  };

  return (
    <div className="min-h-dvh bg-bg-primary">
      {/* Top Bar */}
      <header className="sticky top-0 z-40 bg-bg-primary/80 backdrop-blur-md border-b border-bg-hover">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Terminal size={20} className="text-accent-orange" />
            <span className="text-sm font-bold tracking-wider text-text-primary hidden sm:inline">
              NOVEL GENESIS
            </span>
            <span className="text-xs text-text-muted hidden sm:inline">v2.0</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate("ai-config")}
              aria-label="AI 配置"
            >
              <Settings size={16} />
              <span className="hidden sm:inline">AI 配置</span>
            </Button>
            <Button variant="ghost" size="sm" onClick={logout} aria-label="退出">
              <LogOut size={16} />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Welcome */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-text-primary">
            欢迎回来，{user?.username}
          </h1>
          <p className="text-sm text-text-muted mt-1">管理你的小说生成项目</p>
        </div>

        {/* Project list */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-text-muted" />
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((p) => (
              <Card key={p.id} glow="orange" className="group hover:bg-bg-hover/50 transition-colors cursor-pointer" onClick={() => onOpenProject(p.id)}>
                <CardContent className="flex items-center gap-4">
                  <div className="p-2 rounded-lg bg-accent-orange/10 shrink-0">
                    <BookOpen size={20} className="text-accent-orange" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-text-primary truncate">《{p.title}》</h3>
                    <p className="text-xs text-text-muted mt-0.5">
                      {p.genre} · {p.chapter_count} 章 · {p.target_platform || "未设平台"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <span className={`text-xs px-2 py-1 rounded ${
                      p.status === "completed" ? "bg-accent-green/10 text-accent-green"
                      : p.status === "idle" ? "bg-bg-hover text-text-muted"
                      : "bg-accent-orange/10 text-accent-orange"
                    }`}>
                      {p.status === "idle" ? "空闲" : p.status === "completed" ? "已完成" : p.status}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => { e.stopPropagation(); handleDelete(p.id, p.title); }}
                      className="opacity-0 group-hover:opacity-100 hover:text-accent-red"
                      aria-label={`删除 ${p.title}`}
                    >
                      <Trash2 size={16} />
                    </Button>
                    <ChevronRight size={16} className="text-text-muted" />
                  </div>
                </CardContent>
              </Card>
            ))}

            {projects.length === 0 && (
              <div className="text-center py-20">
                <Database size={40} className="mx-auto text-text-muted/30 mb-4" />
                <p className="text-text-muted mb-4">还没有小说项目</p>
              </div>
            )}

            <Button
              variant="secondary"
              onClick={() => setShowCreate(true)}
              className="w-full"
            >
              <Plus size={16} />
              创建新项目
            </Button>
          </div>
        )}
      </main>

      {showCreate && (
        <CreateProjectModal
          onClose={() => setShowCreate(false)}
          onCreated={(p) => {
            setProjects((prev) => [p, ...prev]);
            setShowCreate(false);
            showToast("success", `《${p.title}》创建成功`);
          }}
        />
      )}
    </div>
  );
}

// ─── Create Project Modal ──────────────────────────────

interface CreateModalProps {
  onClose: () => void;
  onCreated: (p: Project) => void;
}

function CreateProjectModal({ onClose, onCreated }: CreateModalProps) {
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("玄幻");
  const [platform, setPlatform] = useState("");
  const [wordCount, setWordCount] = useState(100000);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!title.trim()) {
      showToast("warning", "请输入书名");
      return;
    }
    setSaving(true);
    try {
      const project = await projectApi.create({
        title: title.trim(),
        genre,
        target_platform: platform,
        target_word_count: wordCount,
      });
      onCreated(project);
    } catch {
      showToast("error", "创建失败");
    } finally {
      setSaving(false);
    }
  };

  const genres = ["玄幻", "奇幻", "末世", "都市", "科幻", "仙侠", "灵异", "历史", "游戏"];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <Card className="relative z-10 w-full max-w-md mx-4" glow="cyan">
        <CardContent className="space-y-4 pt-6">
          <h2 className="text-lg font-bold text-text-primary">创建新项目</h2>

          <Input label="书名" placeholder="输入你的小说名" value={title} onChange={(e) => setTitle(e.target.value)} required />

          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-text-secondary">类型</label>
            <div className="flex flex-wrap gap-2">
              {genres.map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setGenre(g)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-all duration-200 ${
                    genre === g
                      ? "bg-accent-orange/10 border border-accent-orange/40 text-accent-orange"
                      : "bg-bg-secondary border border-bg-hover text-text-muted hover:text-text-secondary"
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>

          <Input label="目标平台" placeholder="如 番茄小说、起点中文网" value={platform} onChange={(e) => setPlatform(e.target.value)} />

          <Input label="目标字数" type="number" value={String(wordCount)} onChange={(e) => setWordCount(parseInt(e.target.value) || 100000)} />

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={onClose}>取消</Button>
            <Button loading={saving} onClick={handleSubmit}>创建</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
