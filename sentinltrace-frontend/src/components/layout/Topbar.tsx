import { Search } from "lucide-react";
import { AlertCenter } from "@/components/layout/AlertCenter";

export function Topbar({ onOpenSearch }: { onOpenSearch: () => void }) {
  const isMac = typeof navigator !== "undefined" && /Mac/.test(navigator.platform);

  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-5">
      <button
        onClick={onOpenSearch}
        className="flex h-9 w-[340px] items-center gap-2.5 rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-3 text-left transition-colors hover:border-[color:var(--color-border-strong)]"
      >
        <Search className="h-[15px] w-[15px] text-[color:var(--color-text-tertiary)]" strokeWidth={1.75} />
        <span className="flex-1 text-[12.5px] text-[color:var(--color-text-tertiary)]">Search complaint, account, transaction...</span>
        <kbd className="rounded-[3px] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-hover)] px-1.5 py-0.5 text-[10px] font-medium text-[color:var(--color-text-tertiary)]">
          {isMac ? "⌘K" : "Ctrl K"}
        </kbd>
      </button>

      <div className="flex-1" />

      <div className="flex items-center gap-1.5 rounded-sm border border-[color:var(--color-border)] px-2.5 py-1.5">
        <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[color:var(--color-low)]" />
        <span className="text-[11px] font-medium tracking-wide text-[color:var(--color-text-secondary)]">SYSTEM OPERATIONAL</span>
      </div>

      <AlertCenter />

      <div className="flex items-center gap-2 border-l border-[color:var(--color-border)] pl-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[color:var(--color-surface-hover)] text-[10px] font-semibold text-[color:var(--color-text-secondary)]">
          RA
        </div>
        <div className="leading-tight">
          <div className="text-[11.5px] font-medium text-[color:var(--color-text-primary)]">R. Anand</div>
          <div className="text-[10px] text-[color:var(--color-text-tertiary)]">Analyst · Cyber Cell</div>
        </div>
      </div>
    </header>
  );
}
