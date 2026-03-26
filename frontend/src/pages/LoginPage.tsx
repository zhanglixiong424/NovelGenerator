import { useState, type FormEvent } from "react";
import { Terminal } from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { showToast } from "@/components/ui/Toast";
import { ApiError } from "@/lib/api";

export function LoginPage() {
  const { login, setup } = useAuthStore();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSetup, setIsSetup] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;

    setLoading(true);
    try {
      if (isSetup) {
        await setup(username, password);
        showToast("success", "管理员账户创建成功");
      } else {
        await login(username, password);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 400 && err.message.includes("already exists")) {
          setIsSetup(false);
          showToast("info", "管理员已存在，请直接登录");
        } else if (err.status === 401) {
          showToast("error", "用户名或密码错误");
        } else {
          showToast("error", err.message);
        }
      } else {
        showToast("error", "网络连接失败");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center justify-center bg-bg-primary px-4">
      {/* Particle background placeholder */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-accent-orange/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 right-1/4 w-48 h-48 bg-accent-cyan/5 rounded-full blur-3xl" />
      </div>

      <Card className="w-full max-w-sm relative z-10" glow="orange">
        <CardContent className="pt-8 pb-8 px-6">
          {/* Logo */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <div className="p-2.5 rounded-lg bg-accent-orange/10 border border-accent-orange/20">
              <Terminal size={24} className="text-accent-orange" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-wider text-text-primary">
                NOVEL GENESIS
              </h1>
              <p className="text-xs text-text-muted tracking-widest">
                创世终端 v2.0
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              label="用户名"
              placeholder="输入用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              minLength={2}
              maxLength={50}
              required
            />

            <Input
              label="密码"
              type="password"
              placeholder="输入密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isSetup ? "new-password" : "current-password"}
              minLength={6}
              maxLength={128}
              required
            />

            <Button
              type="submit"
              className="w-full"
              size="lg"
              loading={loading}
            >
              {isSetup ? "创建管理员" : "登 录"}
            </Button>
          </form>

          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => setIsSetup(!isSetup)}
              className="text-xs text-text-muted hover:text-accent-cyan transition-colors"
            >
              {isSetup ? "已有账户？去登录" : "首次部署？创建管理员"}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
