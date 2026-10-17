import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import clsx from "clsx";
import { useAsync } from "@/hooks/useAsync";
import { getAlerts } from "@/services/api";
import { timeAgo } from "@/utils/format";

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-[color:var(--color-critical)]",
  high: "bg-[color:var(--color-high)]",
  medium: "bg-[color:var(--color-medium)]",
  info: "bg-[color:var(--color-info)]",
};

export function AlertCenter() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { data: alerts } = useAsync(getAlerts, []);
  const unreadCount = alerts?.filter((a) => !a.read).length ?? 0;

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative flex h-8 w-8 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] transition-colors hover:bg-[color:var(--color-surface-hover)] hover:text-[color:var(--color-text-primary)]"
        aria-label="Alerts"
      >
        <Bell className="h-[17px] w-[17px]" strokeWidth={1.75} />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-[15px] min-w-[15px] items-center justify-center rounded-full bg-[color:var(--color-critical)] px-[3px] text-[9px] font-semibold text-white">
            {unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="animate-fade-in absolute right-0 top-10 z-40 w-[360px] overflow-hidden rounded-md border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)] shadow-2xl">
          <div className="flex items-center justify-between border-b border-[color:var(--color-border)] px-3.5 py-2.5">
            <span className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">Alert Center</span>
            <span className="text-[11px] text-[color:var(--color-text-tertiary)]">{unreadCount} unread</span>
          </div>
          <div className="max-h-[380px] overflow-y-auto">
            {alerts?.map((a) => (
              <div key={a.id} className={clsx("border-b border-[color:var(--color-border)] px-3.5 py-2.5 last:border-0", !a.read && "bg-[color:var(--color-surface-hover)]/30")}>
                <div className="flex items-start gap-2">
                  <span className={clsx("mt-1 h-1.5 w-1.5 shrink-0 rounded-full", SEVERITY_DOT[a.severity])} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[12px] font-medium leading-snug text-[color:var(--color-text-primary)]">{a.title}</p>
                      <span className="shrink-0 text-[10px] text-[color:var(--color-text-tertiary)]">{timeAgo(a.timestamp)}</span>
                    </div>
                    <p className="mt-0.5 text-[11.5px] leading-snug text-[color:var(--color-text-secondary)]">{a.detail}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
