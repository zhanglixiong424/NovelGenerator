import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/auth";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { AIConfigPage } from "@/pages/AIConfigPage";
import { ProjectDetailPage } from "@/pages/ProjectDetailPage";
import { ToastContainer } from "@/components/ui/Toast";

type Page = { name: "dashboard" } | { name: "ai-config" } | { name: "project"; projectId: string };

export default function App() {
  const { token, loading, init } = useAuthStore();
  const [page, setPage] = useState<Page>({ name: "dashboard" });

  useEffect(() => { init(); }, [init]);

  if (loading) {
    return (
      <div className="min-h-dvh bg-bg-primary flex items-center justify-center">
        <div className="text-text-muted animate-pulse text-sm tracking-wider">INITIALIZING...</div>
      </div>
    );
  }

  return (
    <>
      <ToastContainer />
      {!token ? (
        <LoginPage />
      ) : page.name === "ai-config" ? (
        <AIConfigPage onBack={() => setPage({ name: "dashboard" })} />
      ) : page.name === "project" ? (
        <ProjectDetailPage
          projectId={page.projectId}
          onBack={() => setPage({ name: "dashboard" })}
        />
      ) : (
        <DashboardPage
          onNavigate={(p) => setPage({ name: p as "dashboard" | "ai-config" })}
          onOpenProject={(id) => setPage({ name: "project", projectId: id })}
        />
      )}
    </>
  );
}
