import clsx from "clsx";

const STATUS_LABEL: Record<string, string> = {
  new: "New",
  under_investigation: "Under Investigation",
  escalated: "Escalated",
  monitoring: "Monitoring",
  resolved: "Resolved",
  operational: "Operational",
  standby: "Standby",
  degraded: "Degraded",
  offline: "Offline",
  // Real backend Case statuses (Stage 6) not covered by the mock set above —
  // additive only, "escalated"/"resolved" above are already shared with it.
  open: "Open",
  investigating: "Investigating",
  // Real backend Alert status value (Stage 5) not otherwise covered —
  // "open"/"resolved" above are already shared with it.
  acknowledged: "Acknowledged",
};

const STATUS_COLOR: Record<string, string> = {
  new: "text-[color:var(--color-info)]",
  under_investigation: "text-[color:var(--color-high)]",
  escalated: "text-[color:var(--color-critical)]",
  monitoring: "text-[color:var(--color-signal)]",
  resolved: "text-[color:var(--color-low)]",
  operational: "text-[color:var(--color-low)]",
  standby: "text-[color:var(--color-text-secondary)]",
  degraded: "text-[color:var(--color-high)]",
  offline: "text-[color:var(--color-critical)]",
  open: "text-[color:var(--color-info)]",
  investigating: "text-[color:var(--color-signal)]",
  acknowledged: "text-[color:var(--color-text-secondary)]",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-[11px] font-medium", STATUS_COLOR[status] ?? "text-[color:var(--color-text-secondary)]")}>
      <span className={clsx("h-1.5 w-1.5 rounded-full", STATUS_COLOR[status]?.replace("text-", "bg-") ?? "bg-[color:var(--color-text-secondary)]")} />
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}
