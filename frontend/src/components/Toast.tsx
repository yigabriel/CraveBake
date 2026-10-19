import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { Icon } from "./ui";

type Tone = "success" | "error" | "info";
interface Toast {
  id: number;
  message: string;
  tone: Tone;
}

const ToastContext = createContext<(message: string, tone?: Tone) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const show = useCallback((message: string, tone: Tone = "success") => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message, tone }]);
    setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 3500);
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-28 z-[70] flex flex-col items-center gap-sm px-margin-mobile lg:bottom-md">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="flex items-center gap-sm rounded-full bg-inverse-surface px-md py-sm text-label-md text-inverse-on-surface shadow-lift"
          >
            <Icon
              name={toast.tone === "error" ? "error" : toast.tone === "info" ? "info" : "check_circle"}
              className={`text-[20px] ${toast.tone === "error" ? "text-primary-fixed" : "text-tertiary-fixed"}`}
            />
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
