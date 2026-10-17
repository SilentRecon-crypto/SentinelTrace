import { lazy, Suspense, useState } from "react";
import { useAsync } from "@/hooks/useAsync";
import { getLocations } from "@/services/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { LOCATION_TYPE_LABEL } from "@/data/reference";
import { PinButton } from "@/components/ui/PinButton";

// The Leaflet map (and its ~150KB of map-library JS) is only needed on this
// page, so it's code-split out of the main bundle and loaded on demand.
const IndiaMap = lazy(() => import("@/components/map/IndiaMap").then((m) => ({ default: m.IndiaMap })));

export function CashOutIntelligence() {
  const { data: locations, loading, error, reload } = useAsync(getLocations, []);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = locations?.find((l) => l.id === selectedId) ?? locations?.[0] ?? null;

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Cash-Out Intelligence" title="Predicted Cash-Out Locations" description="Location intelligence for likely physical cash-withdrawal points, ranked by aggregated risk signal." />

      {error ? (
        <ErrorState onRetry={reload} />
      ) : loading || !locations ? (
        <SkeletonBlock className="h-[460px]" />
      ) : (
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2">
            <Suspense fallback={<SkeletonBlock className="h-[460px]" />}>
              <IndiaMap locations={locations} selectedId={selected?.id ?? null} onSelect={setSelectedId} />
            </Suspense>
          </div>

          <div className="flex flex-col gap-4">
            {/* Location detail panel */}
            {selected && (
              <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[color:var(--color-signal)]">Location Intelligence</span>
                  <PinButton entityType="location" entityId={selected.id} label={selected.id} risk={selected.risk} />
                </div>
                <div className="flex items-center gap-2">
                  <span className="mono-id text-[16px] font-semibold text-[color:var(--color-text-primary)]">{selected.id}</span>
                  <RiskBadge risk={selected.risk} size="sm" />
                </div>
                <p className="mt-0.5 text-[12px] text-[color:var(--color-text-secondary)]">
                  {LOCATION_TYPE_LABEL[selected.type]} · {selected.city}, {selected.state}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2.5">
                  {[
                    ["Prediction Score", `${selected.predictionScore.toFixed(1)}%`],
                    ["Rank", `#${selected.rank}`],
                    ["Distance", `${selected.distanceKm.toFixed(1)} km`],
                    ["Historical Fraud", selected.historicalFraudCount.toString()],
                    ["Recent Activity", selected.recentActivityCount.toString()],
                    ["Agg. Top-K Score", selected.aggregatedTopKScore.toFixed(2)],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2.5 py-2">
                      <div className="text-[9.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">{label}</div>
                      <div className="mono-id mt-0.5 text-[13px] font-semibold text-[color:var(--color-text-primary)]">{value}</div>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[10.5px] italic text-[color:var(--color-text-tertiary)]">Demo values — real-time location scoring requires Model B, not yet integrated.</p>
              </div>
            )}

            {/* Ranked list */}
            <div className="flex-1 overflow-hidden rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
              <div className="border-b border-[color:var(--color-border)] px-4 py-2.5">
                <h2 className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">Top Predicted Locations</h2>
              </div>
              <div className="max-h-[280px] divide-y divide-[color:var(--color-border)] overflow-y-auto">
                {locations.slice(0, 10).map((l) => (
                  <button
                    key={l.id}
                    onClick={() => setSelectedId(l.id)}
                    className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-[color:var(--color-surface-hover)] ${selected?.id === l.id ? "bg-[color:var(--color-surface-hover)]" : ""}`}
                  >
                    <span className="mono-id w-5 text-[11px] text-[color:var(--color-text-tertiary)]">#{l.rank}</span>
                    <div className="min-w-0 flex-1">
                      <div className="mono-id text-[12px] font-medium text-[color:var(--color-text-primary)]">{l.id}</div>
                      <div className="text-[10.5px] text-[color:var(--color-text-tertiary)]">{l.city}</div>
                    </div>
                    <span className="mono-id text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">{l.predictionScore.toFixed(1)}%</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
