import { useNavigate } from "react-router-dom";
import { FilePlus2, ListChecks, Search, ArrowRight } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import { getUserComplaints } from "@/services/userApi";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/ui/PageHeader";
import { UserComplaintStatusBadge } from "@/components/ui/UserComplaintStatusBadge";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { formatDate, formatINR } from "@/utils/format";
import { userPath } from "@/routes";

export function UserDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: complaints, loading } = useAsync(getUserComplaints, []);

  const total = complaints?.length ?? 0;
  const inProgress = complaints?.filter((c) => c.status === "under_review" || c.status === "investigation_in_progress").length ?? 0;
  const resolved = complaints?.filter((c) => c.status === "resolved").length ?? 0;

  return (
    <div className="animate-fade-in space-y-5">
      <PageHeader eyebrow="User Portal" title={`Welcome back${user?.name ? `, ${user.name}` : ""}`} description="Report a cybercrime incident or track the status of your existing complaints." />

      <div className="grid grid-cols-3 gap-3">
        {loading || !complaints ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
              <div className="text-[10.5px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">Total Complaints</div>
              <div className="mono-id mt-1.5 text-[24px] font-semibold text-[color:var(--color-text-primary)]">{total}</div>
            </div>
            <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
              <div className="text-[10.5px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">In Progress</div>
              <div className="mono-id mt-1.5 text-[24px] font-semibold text-[color:var(--color-high)]">{inProgress}</div>
            </div>
            <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
              <div className="text-[10.5px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">Resolved</div>
              <div className="mono-id mt-1.5 text-[24px] font-semibold text-[color:var(--color-low)]">{resolved}</div>
            </div>
          </>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <button
          onClick={() => navigate(userPath("/report"))}
          className="flex flex-col items-start gap-2 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4 text-left transition-colors hover:border-[color:var(--color-signal)]"
        >
          <FilePlus2 className="h-4 w-4 text-[color:var(--color-signal)]" strokeWidth={1.75} />
          <span className="text-[13px] font-medium text-[color:var(--color-text-primary)]">Report Cybercrime</span>
          <span className="text-[11.5px] text-[color:var(--color-text-tertiary)]">Submit a new complaint</span>
        </button>
        <button
          onClick={() => navigate(userPath("/complaints"))}
          className="flex flex-col items-start gap-2 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4 text-left transition-colors hover:border-[color:var(--color-signal)]"
        >
          <ListChecks className="h-4 w-4 text-[color:var(--color-signal)]" strokeWidth={1.75} />
          <span className="text-[13px] font-medium text-[color:var(--color-text-primary)]">My Complaints</span>
          <span className="text-[11.5px] text-[color:var(--color-text-tertiary)]">View all your submissions</span>
        </button>
        <button
          onClick={() => navigate(userPath("/track"))}
          className="flex flex-col items-start gap-2 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4 text-left transition-colors hover:border-[color:var(--color-signal)]"
        >
          <Search className="h-4 w-4 text-[color:var(--color-signal)]" strokeWidth={1.75} />
          <span className="text-[13px] font-medium text-[color:var(--color-text-primary)]">Track Complaint</span>
          <span className="text-[11.5px] text-[color:var(--color-text-tertiary)]">See a status timeline</span>
        </button>
      </div>

      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
        <div className="flex items-center justify-between border-b border-[color:var(--color-border)] px-4 py-3">
          <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Recent Complaints</h2>
          <button onClick={() => navigate(userPath("/complaints"))} className="flex items-center gap-1 text-[11.5px] font-medium text-[color:var(--color-signal)] hover:opacity-80">
            View all <ArrowRight className="h-3 w-3" />
          </button>
        </div>
        <div className="divide-y divide-[color:var(--color-border)]">
          {loading || !complaints
            ? Array.from({ length: 3 }).map((_, i) => <div key={i} className="skeleton m-3 h-10 rounded-sm" />)
            : complaints.slice(0, 4).map((c) => (
                <button
                  key={c.id}
                  onClick={() => navigate(userPath(`/track?complaint=${c.id}`))}
                  className="flex w-full items-center gap-4 px-4 py-2.5 text-left transition-colors hover:bg-[color:var(--color-surface-hover)]"
                >
                  <span className="mono-id w-24 text-[12px] font-medium text-[color:var(--color-text-primary)]">{c.id}</span>
                  <span className="flex-1 truncate text-[12px] text-[color:var(--color-text-secondary)]">{c.complaintType}</span>
                  <span className="text-[11.5px] text-[color:var(--color-text-tertiary)]">{formatDate(c.dateSubmitted)}</span>
                  <span className="text-[12px] font-medium text-[color:var(--color-text-primary)]">{formatINR(c.amount)}</span>
                  <UserComplaintStatusBadge status={c.status} />
                </button>
              ))}
        </div>
      </div>
    </div>
  );
}
