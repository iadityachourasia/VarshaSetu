"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

type Toast = { id: number; message: string };
const ToastContext = createContext<(message: string) => void>(() => undefined);

/** Brief, non-blocking confirmations ("Copied", "Download started"). One polite live region; at most three at a time; each leaves by itself. */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);
  const timers = useRef(new Set<ReturnType<typeof setTimeout>>());
  const push = useCallback((message: string) => {
    const id = ++counter.current;
    setToasts((current) => [...current.slice(-2), { id, message }]);
    const timer = setTimeout(() => { timers.current.delete(timer); setToasts((current) => current.filter((toast) => toast.id !== id)); }, 2600);
    timers.current.add(timer);
  }, []);
  useEffect(() => { const active = timers.current; return () => { active.forEach(clearTimeout); }; }, []);
  const value = useMemo(() => push, [push]);
  return <ToastContext.Provider value={value}>
    {children}
    <div className="toast-region" role="status" aria-live="polite" aria-atomic="false" data-testid="toast-region">
      {toasts.map((toast) => <div className="toast" key={toast.id}>{toast.message}</div>)}
    </div>
  </ToastContext.Provider>;
}

export function useToast() { return useContext(ToastContext); }
