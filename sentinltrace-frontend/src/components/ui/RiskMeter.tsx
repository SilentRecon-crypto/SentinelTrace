import clsx from "clsx";
import type { RiskLevel } from "@/types";

const COLOR: Record<RiskLevel, string> = {
  critical: "var(--color-critical)",
  high: "var(--color-high)",
  medium: "var(--color-medium)",
  low: "var(--color-low)",
};

export function RiskMeter({ score, risk, compact = false }: { score: number; risk: RiskLevel; compact?: boolean }) {
  return (
    <div className={clsx("flex items-center gap-2", compact ? "w-24" : "w-32")}>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[color:var(--color-border)]">
        <div
          className="h-full rounded-full transition-[width]"
          style={{ width: `${Math.min(100, Math.max(2, score))}%`, background: COLOR[risk] }}
        />
      </div>
      <span className="mono-id text-[12px] font-medium tabular-nums text-[color:var(--color-text-primary)]">{score.toFixed(1)}%</span>
    </div>
  );
}
