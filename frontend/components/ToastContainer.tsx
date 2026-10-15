"use client";

import { useEffect, useState } from "react";
import { TOAST_EVENT_NAME, ToastPayload, ToastType } from "@/lib/toast";

interface ToastEntry {
  id: number;
  message: string;
  type: ToastType;
  exiting: boolean;
}

const TYPE_STYLES: Record<ToastType, string> = {
  success: "border-bullish text-bullish",
  error: "border-bearish text-bearish",
  info: "border-border text-gray-200",
};

const TYPE_ICON: Record<ToastType, string> = {
  success: "✓",
  error: "✗",
  info: "·",
};

let nextId = 1;

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<ToastPayload>).detail;
      const id = nextId++;
      setToasts((prev) => [...prev, { id, message: detail.message, type: detail.type || "info", exiting: false }]);

      // Tự động ẩn sau 3.5s: đánh dấu "exiting" để chạy animation rồi mới xoá khỏi DOM
      setTimeout(() => {
        setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 200);
      }, 3500);
    };

    window.addEventListener(TOAST_EVENT_NAME, handler);
    return () => window.removeEventListener(TOAST_EVENT_NAME, handler);
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto ${t.exiting ? "toast-exit" : "toast-enter"} bg-panel border ${TYPE_STYLES[t.type]} px-3 py-2 text-xs font-mono flex items-center gap-2 shadow-lg max-w-xs`}
        >
          <span>{TYPE_ICON[t.type]}</span>
          <span className="text-gray-200">{t.message}</span>
        </div>
      ))}
    </div>
  );
}
