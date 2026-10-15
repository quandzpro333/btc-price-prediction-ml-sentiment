/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ===== Bảng màu "Trading Terminal" =====
        // Lấy cảm hứng từ terminal giao dịch thật (Bloomberg/Binance/BitVision),
        // không dùng tông "GitHub dark" chung chung như trước.
        background: "#0A0E14", // Terminal Black — đen ánh xanh
        panel: "#10151C", // Panel Ink — nền panel/card
        border: "#1E2630", // viền hairline mảnh
        bullish: "#00FF9C", // Phosphor Green — tăng/live/buy
        bearish: "#FF3B5C", // Signal Red — giảm/sell
        amber: "#FFB020", // Amber Alert — EMA, sentiment trung lập, cảnh báo
        ghost: "#6B7785", // Ghost Gray — text phụ, label
        phosphor: "#00FF9C", // alias của bullish, dùng cho hiệu ứng glow/bracket
      },
      fontFamily: {
        // Monospace cho số liệu/label (đúng chất terminal tài chính — cột số thẳng hàng)
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        // Sans cho đoạn văn dài (AI Analysis, News) — dễ đọc hơn monospace
        sans: ["var(--font-sans)", "ui-sans-serif", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 12px rgba(0, 255, 156, 0.35)",
      },
    },
    // Ghi đè toàn bộ scale border-radius về gần vuông (2px) — terminal thật không
    // dùng góc bo tròn mềm mại kiểu app hiện đại. Giữ `full` để chấm tròn (Live dot)
    // vẫn tròn như cũ.
    borderRadius: {
      none: "0px",
      sm: "2px",
      DEFAULT: "2px",
      md: "2px",
      lg: "2px",
      xl: "2px",
      "2xl": "2px",
      "3xl": "2px",
      full: "9999px",
    },
  },
  plugins: [],
};
