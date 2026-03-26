import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { X, CheckCircle, AlertTriangle, Info } from "lucide-react";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

let toastId = 0;
const listeners: Set<(t: Toast) => void> = new Set();

export function showToast(type: ToastType, message: string) {
  const toast: Toast = { id: ++toastId, type, message };
  listeners.forEach((fn) => fn(toast));
}

const icons: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle size={16} className="text-accent-green" />,
  error: <AlertTriangle size={16} className="text-accent-red" />,
  warning: <AlertTriangle size={16} className="text-accent-orange" />,
  info: <Info size={16} className="text-accent-cyan" />,
};

const borderColors: Record<ToastType, string> = {
  success: "border-accent-green/30",
  error: "border-accent-red/30",
  warning: "border-accent-orange/30",
  info: "border-accent-cyan/30",
};

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const handler = (t: Toast) => {
      setToasts((prev) => [...prev, t]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((x) => x.id !== t.id));
      }, 4000);
    };
    listeners.add(handler);
    return () => { listeners.delete(handler); };
  }, []);

  const remove = (id: number) => {
    setToasts((prev) => prev.filter((x) => x.id !== id));
  };

  return (
    <div
      className="fixed top-4 right-4 z-[1000] flex flex-col gap-2 max-w-sm"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "flex items-center gap-3 px-4 py-3 rounded-lg bg-bg-card border",
            "shadow-[0_4px_20px_rgba(0,0,0,0.6)]",
            "animate-[slide-in_250ms_ease-out]",
            borderColors[t.type]
          )}
        >
          {icons[t.type]}
          <span className="text-sm text-text-primary flex-1">{t.message}</span>
          <button
            onClick={() => remove(t.id)}
            className="text-text-muted hover:text-text-primary transition-colors"
            aria-label="关闭"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
