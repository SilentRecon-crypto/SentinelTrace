import clsx from "clsx";
import type { UserComplaintStatus } from "@/types";

const LABEL: Record<UserComplaintStatus, string> = {
  submitted: "Submitted",
  under_review: "Under Review",
  investigation_in_progress: "Investigation in Progress",
  resolved: "Resolved",
};

const COLOR: Record<UserComplaintStatus, string> = {
  submitted: "text-[color:var(--color-info)]",
  under_review: "text-[color:var(--color-high)]",
  investigation_in_progress: "text-[color:var(--color-signal)]",
  resolved: "text-[color:var(--color-low)]",
};

export function UserComplaintStatusBadge({ status }: { status: UserComplaintStatus }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-[11px] font-medium", COLOR[status])}>
      <span className={clsx("h-1.5 w-1.5 rounded-full", COLOR[status].replace("text-", "bg-"))} />
      {LABEL[status]}
    </span>
  );
}
