import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAsync } from "@/hooks/useAsync";
import { getComplaints, getNetwork } from "@/services/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { NetworkGraphView } from "@/components/network/NetworkGraphView";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { formatINR } from "@/utils/format";

export function Networks() {
  const [params] = useSearchParams();
  const { data: complaints } = useAsync(getComplaints, []);
  const [complaintId, setComplaintId] = useState<string>(params.get("complaint") ?? "");

  useEffect(() => {
    if (!complaintId && complaints && complaints.length > 0) {
      setComplaintId(params.get("complaint") || "CMP-10482");
    }
  }, [complaints, complaintId, params]);

  const { data: graph, loading, error, reload } = useAsync(() => getNetwork(complaintId), [complaintId]);
  const complaint = complaints?.find((c) => c.id === complaintId);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Transaction Networks"
        title="Money Movement Graph"
        description="Interactive transaction-network visualization from victim report through intermediary accounts to predicted cash-out."
        actions={
          <select
            value={complaintId}
            onChange={(e) => setComplaintId(e.target.value)}
            className="h-8 rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-2.5 text-[12px] text-[color:var(--color-text-secondary)] outline-none"
          >
            {complaints?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} · {c.risk.toUpperCase()}
              </option>
            ))}
          </select>
        }
      />

      {complaint && (
        <div className="mb-3 flex items-center gap-4 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-4 py-2.5">
          <span className="mono-id text-[13px] font-semibold text-[color:var(--color-text-primary)]">{complaint.id}</span>
          <RiskBadge risk={complaint.risk} size="sm" />
          <span className="text-[12px] text-[color:var(--color-text-secondary)]">{formatINR(complaint.amount)}</span>
          <span className="text-[12px] text-[color:var(--color-text-tertiary)]">{complaint.chainDepth}-hop chain</span>
          <span className="text-[12px] text-[color:var(--color-text-tertiary)]">Top account {complaint.topAccountId}</span>
        </div>
      )}

      {error ? <ErrorState onRetry={reload} /> : loading || !graph ? <SkeletonBlock className="h-[400px]" /> : <NetworkGraphView graph={graph} />}

      <p className="mt-2 text-[11.5px] text-[color:var(--color-text-tertiary)]">
        Drag to pan, use the zoom controls to scale, select a node for details, or toggle Trace Path to highlight the suspicious chain.
      </p>
    </div>
  );
}
