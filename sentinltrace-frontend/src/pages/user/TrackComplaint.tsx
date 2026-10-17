import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CheckCircle2, Circle } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import { getComplaintTimeline, getUserComplaint, getUserComplaints } from "@/services/userApi";
import { PageHeader } from "@/components/ui/PageHeader";
import { UserComplaintStatusBadge } from "@/components/ui/UserComplaintStatusBadge";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/States";
import { formatDate, formatDateTime, formatINR } from "@/utils/format";
import clsx from "clsx";

export function TrackComplaint() {
  const [params] = useSearchParams();
  const { data: complaints } = useAsync(getUserComplaints, []);
  const [complaintId, setComplaintId] = useState(params.get("complaint") ?? "");

  useEffect(() => {
    if (!complaintId && complaints && complaints.length > 0) {
      setComplaintId(params.get("complaint") || complaints[0].id);
    }
  }, [complaints, complaintId, params]);

  const { data: complaint, loading: loadingComplaint } = useAsync(() => getUserComplaint(complaintId), [complaintId]);
  const { data: timeline, loading: loadingTimeline } = useAsync(() => getComplaintTimeline(complaintId), [complaintId]);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Track"
        title="Track Complaint"
        description="Select a complaint to see its current status and history."
        actions={
          <select
            value={complaintId}
            onChange={(e) => setComplaintId(e.target.value)}
            className="h-8 rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-2.5 text-[12px] text-[color:var(--color-text-secondary)] outline-none"
          >
            {complaints?.map((c) => (
              <option key={c.id} value={c.id}>{c.id} · {c.complaintType}</option>
            ))}
          </select>
        }
      />

      {!complaints || complaints.length === 0 ? (
        <EmptyState title="NO COMPLAINTS TO TRACK" description="Submit a complaint from Report Cybercrime to track its progress here." />
      ) : loadingComplaint || !complaint ? (
        <SkeletonBlock className="h-80" />
      ) : (
        <div className="space-y-4">
          <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="mono-id text-[15px] font-semibold text-[color:var(--color-text-primary)]">{complaint.id}</span>
                <span className="ml-3 text-[12.5px] text-[color:var(--color-text-secondary)]">{complaint.complaintType}</span>
              </div>
              <UserComplaintStatusBadge status={complaint.status} />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3">
              <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2">
                <div className="text-[9.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Amount</div>
                <div className="mt-0.5 text-[13px] font-medium text-[color:var(--color-text-primary)]">{formatINR(complaint.amount)}</div>
              </div>
              <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2">
                <div className="text-[9.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Submitted</div>
                <div className="mt-0.5 text-[13px] font-medium text-[color:var(--color-text-primary)]">{formatDate(complaint.dateSubmitted)}</div>
              </div>
              <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2">
                <div className="text-[9.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Last Updated</div>
                <div className="mt-0.5 text-[13px] font-medium text-[color:var(--color-text-primary)]">{formatDate(complaint.lastUpdated)}</div>
              </div>
            </div>
          </div>

          <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-5">
            <h2 className="mb-4 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Status Timeline</h2>
            {loadingTimeline || !timeline ? (
              <SkeletonBlock className="h-48" />
            ) : (
              <ol className="space-y-0">
                {timeline.map((step, i) => (
                  <li key={step.label} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      {step.complete ? (
                        <CheckCircle2 className="h-5 w-5 text-[color:var(--color-low)]" strokeWidth={1.75} />
                      ) : (
                        <Circle className="h-5 w-5 text-[color:var(--color-text-tertiary)]" strokeWidth={1.75} />
                      )}
                      {i < timeline.length - 1 && <div className={clsx("w-px flex-1 my-1", step.complete ? "bg-[color:var(--color-low)]" : "bg-[color:var(--color-border-strong)]")} style={{ minHeight: 28 }} />}
                    </div>
                    <div className="pb-6">
                      <div className={clsx("text-[13px] font-medium", step.complete ? "text-[color:var(--color-text-primary)]" : "text-[color:var(--color-text-tertiary)]")}>{step.label}</div>
                      {step.timestamp && <div className="text-[11px] text-[color:var(--color-text-tertiary)]">{formatDateTime(step.timestamp)}</div>}
                      {step.note && <p className="mt-1 max-w-md text-[11.5px] text-[color:var(--color-text-secondary)]">{step.note}</p>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
