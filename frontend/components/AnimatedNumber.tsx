"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  value: number | null | undefined; // cho phép null/undefined (model classification không có predicted_price)
  decimals?: number;
  prefix?: string;
  suffix?: string;
  durationMs?: number;
  className?: string;
  fallback?: string; // hiện khi value là null/undefined, mặc định "—"
}

// Số "lăn" mượt từ giá trị cũ sang giá trị mới (kiểu đồng hồ công-tơ-mét), thay vì
// nhảy số cứng mỗi lần dữ liệu cập nhật — dùng requestAnimationFrame, không cần thư viện.
export default function AnimatedNumber({
  value,
  decimals = 2,
  prefix = "",
  suffix = "",
  durationMs = 500,
  className = "",
  fallback = "—",
}: Props) {
  const [display, setDisplay] = useState(value ?? 0);
  const fromRef = useRef(value ?? 0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    // value null/undefined (vd model classification không có predicted_price)
    // -> không chạy animation, chỉ hiện fallback ("—") ở phần render bên dưới.
    if (value === null || value === undefined) return;

    const from = fromRef.current;
    const to = value;
    const startTime = performance.now();

    if (rafRef.current) cancelAnimationFrame(rafRef.current);

    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / durationMs);
      // easeOutCubic — chậm dần về cuối, tự nhiên hơn tuyến tính
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = from + (to - from) * eased;
      setDisplay(current);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        fromRef.current = to;
      }
    };

    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  if (value === null || value === undefined) {
    return <span className={className}>{fallback}</span>;
  }

  return (
    <span className={className}>
      {prefix}
      {display.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </span>
  );
}
