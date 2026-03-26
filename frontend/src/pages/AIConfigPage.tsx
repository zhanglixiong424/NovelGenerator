import { useEffect, useState } from "react";
import {
  Plus, PlayCircle, Pencil, Trash2, Zap, Bot, Sparkles,
  CheckCircle, XCircle, Clock, Eye, EyeOff, ChevronLeft,
} from "lucide-react";
import { useAIConfigStore } from "@/stores/aiConfig";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { showToast } from "@/components/ui/Toast";
import type { AIProviderCreate } from "@/lib/api";

const providerIcons: Record<string, React.ReactNode> = {
  kimi: <Zap size={18} className="text-accent-orange" />,
  openai: <Bot size={18} className="text-accent-cyan" />,
  deepseek: <Sparkles size={18} className="text-accent-purple" />,
  custom: <Sparkles size={18} className="text-accent-green" />,
};

const statusIcons: Record<string, React.ReactNode> = {
  success: <CheckCircle size={14} className="text-accent-green" />,
  failed: <XCircle size={14} className="text-accent-red" />,
  untested: <Clock size={14} className="text-text-muted" />,
};

interface AIConfigPageProps {
  onBack: () => void;
}

export function AIConfigPage({ onBack }: AIConfigPageProps) {
  const { providers, loading, fetch, add, update, remove, test } = useAIConfigStore();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  useEffect(() => { fetch(); }, [fetch]);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确定删除 "${name}" 配置？`)) return;
    try {
      await remove(id);
      showToast("success", "已删除");
    } catch {
      showToast("error", "删除失败");
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const result = await test(id);
      if (result.success) {
        showToast("success", `连通成功 (${result.latency_ms}ms)`);
      } else {
        showToast("error", result.message);
      }
    } catch {
      showToast("error", "测试失败");
    } finally {
      setTestingId(null);
    }
  };

  return (
    <div className="min-h-dvh bg-bg-primary">
      <header className="sticky top-0 z-40 bg-bg-primary/80 backdrop-blur-md border-b border-bg-hover">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 -ml-2 text-text-muted hover:text-text-primary transition-colors rounded-lg hover:bg-bg-hover"
            aria-label="返回"
          >
            <ChevronLeft size={20} />
          </button>
          <Zap size={18} className="text-accent-orange" />
          <h1 className="text-sm font-bold tracking-wider text-text-primary">
            AI PROVIDER CONFIGURATION
          </h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {loading && providers.length === 0 ? (
          <div className="text-center py-20 text-text-muted">加载中...</div>
        ) : (
          <>
            {providers.map((p) => (
              <Card key={p.id} glow={p.is_enabled ? "orange" : "none"}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {providerIcons[p.provider_type] || providerIcons.custom}
                      <span className="font-medium text-text-primary">{p.name}</span>
                      <span className="text-xs text-text-muted px-2 py-0.5 rounded bg-bg-hover">
                        {p.model_name}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-muted">优先级: {p.priority}</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          p.is_enabled
                            ? "bg-accent-green/10 text-accent-green"
                            : "bg-bg-hover text-text-muted"
                        }`}
                      >
                        {p.is_enabled ? "ON" : "OFF"}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-text-muted">API Key: </span>
                      <span className="text-text-secondary font-mono">
                        {showKeys[p.id] ? p.api_key_masked : "sk-***...***"}
                      </span>
                      <button
                        onClick={() => setShowKeys((k) => ({ ...k, [p.id]: !k[p.id] }))}
                        className="ml-2 text-text-muted hover:text-text-primary transition-colors"
                        aria-label={showKeys[p.id] ? "隐藏" : "显示"}
                      >
                        {showKeys[p.id] ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                    <div>
                      <span className="text-text-muted">Base URL: </span>
                      <span className="text-text-secondary font-mono text-xs break-all">{p.base_url}</span>
                    </div>
                    <div>
                      <span className="text-text-muted">Temperature: </span>
                      <span className="text-text-secondary">{p.temperature}</span>
                    </div>
                    <div>
                      <span className="text-text-muted">Max Tokens: </span>
                      <span className="text-text-secondary">{p.max_tokens}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-bg-hover">
                    <div className="flex items-center gap-2 text-xs">
                      {statusIcons[p.last_test_status]}
                      <span className="text-text-muted">
                        {p.last_test_status === "success" && "连通"}
                        {p.last_test_status === "failed" && "失败"}
                        {p.last_test_status === "untested" && "未测试"}
                        {p.last_test_at && ` (${new Date(p.last_test_at).toLocaleString("zh-CN")})`}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        loading={testingId === p.id}
                        onClick={() => handleTest(p.id)}
                      >
                        <PlayCircle size={14} />
                        测试
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => { setEditingId(p.id); setShowForm(true); }}
                      >
                        <Pencil size={14} />
                        编辑
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(p.id, p.name)}
                        className="hover:text-accent-red"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {providers.length === 0 && !loading && (
              <div className="text-center py-20">
                <Zap size={40} className="mx-auto text-text-muted/30 mb-4" />
                <p className="text-text-muted mb-4">尚未配置 AI 提供商</p>
                <Button onClick={() => { setEditingId(null); setShowForm(true); }}>
                  <Plus size={16} />
                  添加第一个配置
                </Button>
              </div>
            )}

            {providers.length > 0 && (
              <Button
                variant="secondary"
                onClick={() => { setEditingId(null); setShowForm(true); }}
                className="w-full"
              >
                <Plus size={16} />
                添加新配置
              </Button>
            )}

            {/* Fallback strategy info */}
            <Card glow="none">
              <CardContent>
                <p className="text-sm text-text-muted">
                  <span className="text-text-secondary font-medium">Fallback 策略：</span>
                  当前模型不可用时自动切换到下一优先级模型。最大重试次数 3 次，指数退避间隔。
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </main>

      {/* Add/Edit Form Modal */}
      {showForm && (
        <ProviderForm
          editingId={editingId}
          onClose={() => { setShowForm(false); setEditingId(null); }}
          onSave={async (data) => {
            try {
              if (editingId) {
                await update(editingId, data);
                showToast("success", "配置已更新");
              } else {
                await add(data as AIProviderCreate);
                showToast("success", "配置已添加");
              }
              setShowForm(false);
              setEditingId(null);
            } catch {
              showToast("error", "保存失败");
            }
          }}
        />
      )}
    </div>
  );
}

// ─── Provider Form Modal ───────────────────────────────

interface ProviderFormProps {
  editingId: string | null;
  onClose: () => void;
  onSave: (data: Partial<AIProviderCreate>) => Promise<void>;
}

function ProviderForm({ editingId, onClose, onSave }: ProviderFormProps) {
  const { providers } = useAIConfigStore();
  const existing = editingId ? providers.find((p) => p.id === editingId) : null;

  const [form, setForm] = useState({
    name: existing?.name || "",
    provider_type: existing?.provider_type || "kimi",
    api_key: "",
    base_url: existing?.base_url || "https://api.moonshot.cn/v1",
    model_name: existing?.model_name || "moonshot-v1-128k",
    priority: existing?.priority || 1,
    is_enabled: existing?.is_enabled ?? true,
    max_tokens: existing?.max_tokens || 4096,
    temperature: existing?.temperature || 0.7,
  });
  const [saving, setSaving] = useState(false);

  const set = (field: string, value: string | number | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  const urlDefaults: Record<string, { base_url: string; model_name: string }> = {
    kimi: { base_url: "https://api.moonshot.cn/v1", model_name: "moonshot-v1-128k" },
    openai: { base_url: "https://api.openai.com/v1", model_name: "gpt-4-turbo" },
    deepseek: { base_url: "https://api.deepseek.com/v1", model_name: "deepseek-chat" },
    custom: { base_url: "", model_name: "" },
  };

  const handleTypeChange = (type: string) => {
    set("provider_type", type);
    if (!editingId && urlDefaults[type]) {
      set("base_url", urlDefaults[type].base_url);
      set("model_name", urlDefaults[type].model_name);
    }
  };

  const handleSubmit = async () => {
    if (!form.name || (!editingId && !form.api_key) || !form.base_url || !form.model_name) {
      showToast("warning", "请填写必填字段");
      return;
    }
    setSaving(true);
    const data: Partial<AIProviderCreate> = { ...form };
    if (editingId && !form.api_key) {
      delete data.api_key;
    }
    await onSave(data);
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <Card className="relative z-10 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" glow="cyan">
        <CardHeader>
          <h2 className="font-bold text-text-primary">
            {editingId ? "编辑配置" : "添加 AI 配置"}
          </h2>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input label="显示名称" placeholder="如 Kimi Pro" value={form.name} onChange={(e) => set("name", e.target.value)} required />

          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-text-secondary">提供商类型</label>
            <div className="grid grid-cols-4 gap-2">
              {["kimi", "openai", "deepseek", "custom"].map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleTypeChange(type)}
                  className={`h-10 rounded-lg text-sm font-medium transition-all duration-200 ${
                    form.provider_type === type
                      ? "bg-accent-orange/10 border border-accent-orange/40 text-accent-orange"
                      : "bg-bg-secondary border border-bg-hover text-text-muted hover:border-bg-hover hover:text-text-secondary"
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          <Input
            label={editingId ? "API Key（留空保持不变）" : "API Key"}
            type="password"
            placeholder="sk-..."
            value={form.api_key}
            onChange={(e) => set("api_key", e.target.value)}
            required={!editingId}
          />

          <Input label="Base URL" placeholder="https://api.example.com/v1" value={form.base_url} onChange={(e) => set("base_url", e.target.value)} required />

          <Input label="模型名称" placeholder="model-name" value={form.model_name} onChange={(e) => set("model_name", e.target.value)} required />

          <div className="grid grid-cols-3 gap-3">
            <Input label="优先级" type="number" value={String(form.priority)} onChange={(e) => set("priority", parseInt(e.target.value) || 1)} />
            <Input label="Temperature" type="number" value={String(form.temperature)} onChange={(e) => set("temperature", parseFloat(e.target.value) || 0.7)} />
            <Input label="Max Tokens" type="number" value={String(form.max_tokens)} onChange={(e) => set("max_tokens", parseInt(e.target.value) || 4096)} />
          </div>

          <div className="flex items-center gap-3">
            <label className="text-sm text-text-secondary">启用</label>
            <button
              type="button"
              className={`w-11 h-6 rounded-full transition-colors duration-200 ${
                form.is_enabled ? "bg-accent-green" : "bg-bg-hover"
              }`}
              onClick={() => set("is_enabled", !form.is_enabled)}
              role="switch"
              aria-checked={form.is_enabled}
            >
              <div className={`w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${
                form.is_enabled ? "translate-x-[22px]" : "translate-x-[2px]"
              }`} />
            </button>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={onClose}>取消</Button>
            <Button loading={saving} onClick={handleSubmit}>
              {editingId ? "保存更改" : "添加"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
