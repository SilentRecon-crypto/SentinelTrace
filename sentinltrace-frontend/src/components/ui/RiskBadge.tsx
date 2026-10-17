import type { RiskLevel } from "@/types";
import clsx from "clsx";

// "pending" is NOT a real RiskLevel — it's a tiny additive UI state for
// cells where the backend hasn't provided a risk value yet (e.g. the
// Complaints list before Stage 4 risk data is wired in for that view).
// Distinct from "cleared", which means an analyst actively dismissed risk.
const STYLES: Record<RiskLevel | "cleared" | "pending", { bg: string; text: string; dot: string }> = {
  critical: { bg: "bg-[color:var(--color-critical-dim)]", text: "text-[color:var(--color-critical)]", dot: "bg-[color:var(--color-critical)]" },
  high: { bg: "bg-[color:var(--color-high-dim)]", text: "text-[color:var(--color-high)]", dot: "bg-[color:var(--color-high)]" },
  medium: { bg: "bg-[#2b2a12]", text: "text-[color:var(--color-medium)]", dot: "bg-[color:var(--color-medium)]" },
  low: { bg: "bg-[color:var(--color-low-dim)]", text: "text-[color:var(--color-low)]", dot: "bg-[color:var(--color-low)]" },
  cleared: { bg: "bg-[#151a22]", text: "text-[color:var(--color-text-tertiary)]", dot: "bg-[color:var(--color-text-tertiary)]" },
  pending: { bg: "bg-[#151a22]", text: "text-[color:var(--color-text-tertiary)]", dot: "bg-[color:var(--color-text-tertiary)]" },
};

export function RiskBadge({ risk, size = "md" }: { risk: RiskLevel | "cleared" | "pending"; size?: "sm" | "md" }) {
  const s = STYLES[risk];
  const label = risk === "pending" ? "PENDING" : risk.toUpperCase();
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-[3px] font-medium border border-transparent",
        s.bg,
        s.text,
        size === "sm" ? "px-1.5 py-0.5 text-[10px] tracking-wide" : "px-2 py-1 text-[11px] tracking-wide"
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full shrink-0", s.dot)} />
      {label}
    </span>
  );
}
