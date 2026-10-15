"use client";

import { useState } from "react";
import { sendChatMessage } from "@/lib/api";
import PanelEyebrow from "@/components/PanelEyebrow";
import { showToast } from "@/lib/toast";

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", text: "Xin chào! Hỏi tôi về giá BTC, RSI, Fear & Greed hoặc lý do dự đoán nhé." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages((m) => [...m, { role: "user", text: userMsg }]);
    setInput("");
    setLoading(true);
    try {
      const reply = await sendChatMessage(userMsg);
      setMessages((m) => [...m, { role: "assistant", text: reply }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "Xin lỗi, chưa thể trả lời (kiểm tra GEMINI_API_KEY ở backend)." },
      ]);
      showToast("Gemini không phản hồi được — kiểm tra quota/API key", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border border-border bg-panel p-4 flex flex-col h-96 panel-fade-in panel-hover">
      <PanelEyebrow>AI Chat</PanelEyebrow>
      <div className="flex-1 overflow-y-auto space-y-2 my-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`text-sm px-3 py-2 max-w-[85%] font-sans ${
              m.role === "user"
                ? "bg-bullish/10 border border-bullish/40 text-white ml-auto"
                : "bg-[#161b22] border border-border text-gray-200"
            }`}
          >
            {m.text}
          </div>
        ))}
        {loading && <div className="text-xs font-mono text-ghost">Đang trả lời...</div>}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !loading && send()}
          placeholder="Nhập câu hỏi..."
          disabled={loading}
          className="flex-1 bg-background border border-border px-3 py-2 text-sm text-gray-200 outline-none focus:border-bullish font-sans disabled:opacity-50"
        />
        <button
          onClick={send}
          disabled={loading}
          className="bg-bullish/10 border border-bullish text-bullish hover:bg-bullish/20 text-xs font-mono uppercase px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Gửi
        </button>
      </div>
    </div>
  );
}
