import { CheckCircle2, CircleDashed, AlertTriangle, XCircle } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import { getSystemStatus } from "@/services/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { LAST_ANALYSIS_ISO } from "@/data/mockData";
import { formatDateTime } from "@/utils/format";

const STATUS_ICON = {
  operational: { icon: CheckCircle2, color: "var(--color-low)" },
  standby: { icon: CircleDashed, color: "var(--color-text-tertiary)" },
  degraded: { icon: AlertTriangle, color: "var(--color-high)" },
  offline: { icon: XCircle, color: "var(--color-critical)" },
} as const;

export function SystemStatus() {
  const { data: components, loading, error, reload } = useAsync(getSystemStatus, []);

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="System" title="System Status" description="Operational status of SentinelTrace platform components." />

      <div className="mb-4 flex items-center gap-2 rounded-md border border-[color:var(--color-high)]/40 bg-[color:var(--color-high-dim)]/40 px-4 py-3">
        <AlertTriangle className="h-4 w-4 shrink-0 text-[color:var(--color-high)]" />
        <div>
          <p className="text-[12.5px] font-medium text-[color:var(--color-text-primary)]">Demo Environment</p>
          <p className="text-[11.5px] text-[color:var(--color-text-secondary)]">
            This frontend is running entirely on synthetic mock data. The Python/FastAPI backend is not yet connected — API status reflects planned integration, not a live service.
          </p>
        </div>
      </div>

      {error ? (
        <ErrorState onRetry={reload} />
      ) : loading || !components ? (
        <SkeletonBlock className="h-72" />
      ) : (
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <div className="divide-y divide-[color:var(--color-border)]">
            {components.map((c) => {
              const cfg = STATUS_ICON[c.status];
              const Icon = cfg.icon;
              return (
                <div key={c.name} className="flex items-center gap-4 px-4 py-3.5">
                  <Icon className="h-4 w-4 shrink-0" style={{ color: cfg.color }} strokeWidth={1.75} />
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px] font-medium text-[color:var(--color-text-primary)]">{c.name}</div>
                    <div className="text-[11.5px] text-[color:var(--color-text-tertiary)]">{c.detail}</div>
                  </div>
                  <span className="rounded-[3px] px-2 py-1 text-[10.5px] font-semibold uppercase tracking-wide" style={{ color: cfg.color, background: `color-mix(in srgb, ${cfg.color} 14%, transparent)` }}>
                    {c.status}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="border-t border-[color:var(--color-border)] px-4 py-3">
            <p className="text-[11px] text-[color:var(--color-text-tertiary)]">Last synthetic analysis run: {formatDateTime(LAST_ANALYSIS_ISO)} IST</p>
          </div>
        </div>
      )}
    </div>
  );
}
