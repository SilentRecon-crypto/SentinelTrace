import { useEffect, useState } from "react";
import { Target } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import { getComplaints, getLocations, getPredictions } from "@/services/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { formatDateTime } from "@/utils/format";
import { LOCATION_TYPE_LABEL } from "@/data/reference";

export function Predictions() {
  const { data: complaints } = useAsync(getComplaints, []);
  const { data: locations } = useAsync(getLocations, []);
  const [complaintId, setComplaintId] = useState("CMP-10482");

  useEffect(() => {
    if (!complaints?.some((c) => c.id === complaintId) && complaints?.[0]) setComplaintId(complaints[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [complaints]);

  const { data: prediction, loading, error, reload } = useAsync(() => getPredictions(complaintId), [complaintId]);

  const rows = prediction?.locations
    .map((p) => ({ p, loc: locations?.find((l) => l.id === p.locationId) }))
    .filter((r) => r.loc);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Predictions"
        title="Cash-Out Prediction"
        description="Ranked locations requiring investigative attention"
        actions={
          <select
            value={complaintId}
            onChange={(e) => setComplaintId(e.target.value)}
            className="h-8 rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-2.5 text-[12px] text-[color:var(--color-text-secondary)] outline-none"
          >
            {complaints?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id}
              </option>
            ))}
          </select>
        }
      />

      {error ? (
        <ErrorState onRetry={reload} />
      ) : loading || !prediction ? (
        <SkeletonBlock className="h-72" />
      ) : (
        <>
          <div className="mb-4 grid grid-cols-4 gap-3">
            <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
              <div className="text-[10.5px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">Top Prediction</div>
              <div className="mono-id mt-1.5 text-[18px] font-semibold text-[color:var(--color-text-primary)]">{prediction.topLocationId}</div>
            </div>
            <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
              <div className="text-[10.5px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">Top-5 Confidence</div>
              <div className="mono-id mt-1.5 text-[18px] font-semibold text-[color:var(--color-text-primary)]">{(prediction.top5ConfidenceAvg * 100).toFixed(1)}%</div>
            </div>
            <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
              <div className="text-[10.5px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">Candidate Locations</div>
              <div className="mono-id mt-1.5 text-[18px] font-semibold text-[color:var(--color-text-primary)]">{prediction.candidateCount}</div>
            </div>
            <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
              <div className="text-[10.5px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">Last Analysis</div>
              <div className="mt-1.5 text-[13px] font-medium text-[color:var(--color-text-primary)]">{formatDateTime(prediction.generatedAt)}</div>
            </div>
          </div>

          <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
            <div className="flex items-center gap-2 border-b border-[color:var(--color-border)] px-4 py-3">
              <Target className="h-3.5 w-3.5 text-[color:var(--color-signal)]" />
              <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Ranked Locations</h2>
            </div>
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-[color:var(--color-border)]">
                  {["Rank", "Location", "Type", "Score", "Distance", "Historical Activity", "Risk Level"].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows?.map(({ p, loc }) => (
                  <tr key={p.locationId} className="border-b border-[color:var(--color-border)] last:border-0">
                    <td className="mono-id px-4 py-2.5 text-[12px] text-[color:var(--color-text-tertiary)]">#{p.rank}</td>
                    <td className="px-4 py-2.5">
                      <div className="mono-id text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{loc!.id}</div>
                      <div className="text-[11px] text-[color:var(--color-text-tertiary)]">{loc!.city}, {loc!.state}</div>
                    </td>
                    <td className="px-4 py-2.5 text-[12px] text-[color:var(--color-text-secondary)]">{LOCATION_TYPE_LABEL[loc!.type]}</td>
                    <td className="mono-id px-4 py-2.5 text-[13px] font-semibold text-[color:var(--color-text-primary)]">{p.score.toFixed(1)}%</td>
                    <td className="px-4 py-2.5 text-[12px] text-[color:var(--color-text-secondary)]">{loc!.distanceKm.toFixed(1)} km</td>
                    <td className="px-4 py-2.5 text-[12px] text-[color:var(--color-text-secondary)]">{loc!.recentActivityCount} events</td>
                    <td className="px-4 py-2.5">
                      <RiskBadge risk={loc!.risk} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
