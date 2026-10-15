export type ToastType = "success" | "error" | "info";

export interface ToastPayload {
  message: string;
  type?: ToastType;
}

const TOAST_EVENT = "app:toast";

// Gọi hàm này ở BẤT KỲ ĐÂU trong app (component nào cũng được) để hiện 1 toast —
// không cần bọc Context Provider, không cần prop drilling. ToastContainer.tsx
// (mount 1 lần trong layout.tsx) sẽ lắng nghe CustomEvent này và tự hiển thị.
export function showToast(message: string, type: ToastType = "info") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<ToastPayload>(TOAST_EVENT, { detail: { message, type } }));
}

export const TOAST_EVENT_NAME = TOAST_EVENT;
