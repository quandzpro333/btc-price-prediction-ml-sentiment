import type { Metadata } from "next";
import { JetBrains_Mono, Inter } from "next/font/google";
import "./globals.css";
import TickerTape from "@/components/TickerTape";

// Monospace cho số liệu/label (đúng chất terminal tài chính), Inter cho đoạn văn dài
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500", "700"],
});
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  // ĐỔI TIÊU ĐỀ TAB TRÌNH DUYỆT ở đây (hiện ở tab trên cùng trình duyệt)
  title: "BTC Price Prediction — Đồ án học tập",
  description:
    "Dự đoán giá Bitcoin bằng Machine Learning và phân tích Sentiment. Chỉ phục vụ mục đích học tập, không phải lời khuyên đầu tư.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className={`${jetbrainsMono.variable} ${inter.variable}`}>
      <body>
        <div className="min-h-screen bg-background">
          <header className="border-b border-border bg-panel px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* ===== LOGO =====
                  Đặt file ảnh logo của bạn vào: frontend/public/logo.png
                  (bất kỳ tên file nào cũng được, chỉ cần sửa "src" bên dưới cho khớp).
                  Nếu chưa có file, ảnh sẽ hiện icon vỡ — không ảnh hưởng gì tới việc chạy web,
                  chỉ cần thêm file vào là hiện ra ngay, không cần restart server. */}
              <img src="/logo.png" alt="Logo" className="h-7 w-7 object-contain" />

              {/* ===== TÊN + DÒNG CHỮ HEADER — sửa trực tiếp text ở đây ===== */}
              <span className="text-xl font-bold font-mono text-white">
                BTC_PREDICTOR<span className="text-bullish animate-pulse">_</span>
              </span>
              <span className="text-[10px] font-mono uppercase tracking-widest text-ghost border border-border px-1.5 py-0.5">
                Đồ án học tập — không phải lời khuyên đầu tư
              </span>
            </div>
          </header>
          <TickerTape />
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
