import { ReactNode } from "react";

// Nhãn tiêu đề kiểu terminal — dùng chung cho mọi panel để đồng nhất giao diện.
// Thay cho <h3> thông thường, giống cách các terminal giao dịch thật gắn nhãn khung.
export default function PanelEyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="text-[11px] font-mono uppercase tracking-widest text-ghost flex items-center gap-1.5">
      <span className="text-phosphor">[</span>
      <span>{children}</span>
      <span className="text-phosphor">]</span>
    </div>
  );
}
