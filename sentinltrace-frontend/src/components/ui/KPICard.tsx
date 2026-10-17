import type { LucideIcon } from "lucide-react";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import clsx from "clsx";

interface KPICardProps {
  label: string;
  value: string;
  description: string;
  changePct?: number;
  icon: LucideIcon;
  tone?: "default" | "critical" | "high";
}

export function KPICard({ label, value, description, changePct, icon: Icon, tone = "default" }: KPICardProps) {
  const positive = (changePct ?? 0) >= 0;
  return (
    <div className="group relative rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4 transition-colors hover:border-[color:var(--color-border-strong)]">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-[color:var(--color-text-tertiary)]">{label}</span>
        <Icon
          className={clsx(
            "h-4 w-4",
            tone === "critical" ? "text-[color:var(--color-critical)]" : tone === "high" ? "text-[color:var(--color-high)]" : "text-[color:var(--color-signal)]"
          )}
          strokeWidth={1.75}
        />
      </div>
      <div className="mt-2.5 text-[28px] font-semibold leading-none text-[color:var(--color-text-primary)] mono-id">{value}</div>
      <p className="mt-2 text-[12px] leading-snug text-[color:var(--color-text-secondary)]">{description}</p>
      {changePct !== undefined && (
        <div className={clsx("mt-2.5 inline-flex items-center gap-1 text-[11px] font-medium", positive ? "text-[color:var(--color-low)]" : "text-[color:var(--color-critical)]")}>
          {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
          {Math.abs(changePct).toFixed(1)}% this period
        </div>
      )}
    </div>
  );
}
