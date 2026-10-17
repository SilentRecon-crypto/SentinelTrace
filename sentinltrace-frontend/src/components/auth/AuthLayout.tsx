import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { SentinelMark } from "@/components/layout/SentinelMark";
import { NetworkBackground } from "@/components/landing/NetworkBackground";
import { ROUTES } from "@/routes";

export function AuthLayout({ eyebrow, children }: { eyebrow: string; children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[color:var(--color-void)] px-4 py-10">
      <NetworkBackground className="absolute inset-0 h-full w-full opacity-40" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[color:var(--color-void)]/40 via-[color:var(--color-void)]/85 to-[color:var(--color-void)]" />

      <Link
        to={ROUTES.landing}
        className="absolute left-5 top-5 z-10 flex items-center gap-1.5 text-[12.5px] font-medium text-[color:var(--color-text-tertiary)] transition-colors hover:text-[color:var(--color-text-secondary)]"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to SentinelTrace
      </Link>

      <div className="relative z-10 w-full max-w-[400px]">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <SentinelMark className="h-9 w-9" />
          <div className="text-[15px] font-semibold tracking-tight text-[color:var(--color-text-primary)]">SentinelTrace</div>
          <div className="text-[10.5px] font-medium uppercase tracking-[0.09em] text-[color:var(--color-signal)]">{eyebrow}</div>
        </div>
        <div className="rounded-md border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)]/95 p-6 shadow-2xl backdrop-blur">
          {children}
        </div>
        <p className="mt-4 text-center text-[10.5px] text-[color:var(--color-text-tertiary)]">Synthetic / demo environment — mock authentication only.</p>
      </div>
    </div>
  );
}
