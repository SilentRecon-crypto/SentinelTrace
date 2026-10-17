import { useAsync } from "@/hooks/useAsync";
import { getUserNotifications } from "@/services/userApi";
import { PageHeader } from "@/components/ui/PageHeader";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/States";
import { timeAgo } from "@/utils/format";
import clsx from "clsx";

export function Notifications() {
  const { data: notifications, loading } = useAsync(getUserNotifications, []);

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Updates" title="Notifications" description="Updates about your submitted complaints." />
      {loading || !notifications ? (
        <SkeletonBlock className="h-64" />
      ) : notifications.length === 0 ? (
        <EmptyState title="NO NOTIFICATIONS" description="You'll see updates here as your complaints progress." />
      ) : (
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <div className="divide-y divide-[color:var(--color-border)]">
            {notifications.map((n) => (
              <div key={n.id} className={clsx("flex items-start gap-3 px-4 py-3.5", !n.read && "bg-[color:var(--color-surface-hover)]/30")}>
                <span className={clsx("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", n.read ? "bg-[color:var(--color-text-tertiary)]" : "bg-[color:var(--color-signal)]")} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{n.title}</p>
                    <span className="shrink-0 text-[10.5px] text-[color:var(--color-text-tertiary)]">{timeAgo(n.timestamp)}</span>
                  </div>
                  <p className="mt-0.5 text-[12px] leading-snug text-[color:var(--color-text-secondary)]">{n.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
