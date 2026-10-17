import { useAsync } from "@/hooks/useAsync";
import { getModelMetrics } from "@/services/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";

function MetricComparisonRow({ label, modelValue, baselineValue, suffix = "%" }: { label: string; modelValue: number; baselineValue: number; suffix?: string }) {
  const max = Math.max(modelValue, baselineValue, 1) * 1.15;
  const improvement = modelValue - baselineValue;
  return (
    <div className="border-b border-[color:var(--color-border)] py-3.5 last:border-0">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{label}</span>
        <span className="mono-id text-[11px] font-medium text-[color:var(--color-low)]">
          {improvement >= 0 ? "+" : ""}
          {improvement.toFixed(1)} pts vs baseline
        </span>
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center gap-2.5">
          <span className="w-16 shrink-0 text-[10.5px] text-[color:var(--color-text-tertiary)]">Model A</span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-[color:var(--color-border)]">
            <div className="h-full rounded-full bg-[color:var(--color-signal)]" style={{ width: `${(modelValue / max) * 100}%` }} />
          </div>
          <span className="mono-id w-14 shrink-0 text-right text-[12px] font-semibold text-[color:var(--color-text-primary)]">
            {modelValue.toFixed(1)}
            {suffix}
          </span>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="w-16 shrink-0 text-[10.5px] text-[color:var(--color-text-tertiary)]">Baseline</span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-[color:var(--color-border)]">
            <div className="h-full rounded-full bg-[color:var(--color-text-tertiary)]" style={{ width: `${(baselineValue / max) * 100}%` }} />
          </div>
          <span className="mono-id w-14 shrink-0 text-right text-[12px] font-medium text-[color:var(--color-text-secondary)]">
            {baselineValue.toFixed(1)}
            {suffix}
          </span>
        </div>
      </div>
    </div>
  );
}

export function ModelEvaluation() {
  const { data: metrics, loading, error, reload } = useAsync(getModelMetrics, []);

  if (error) return <ErrorState onRetry={reload} />;
  if (loading || !metrics) {
    return (
      <div className="space-y-4">
        <SkeletonBlock className="h-24" />
        <SkeletonBlock className="h-96" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-4">
      <PageHeader eyebrow="Model Evaluation" title="Model A — Suspicious Account Ranking" description="Performance of the currently implemented ranking model, evaluated against a fixed baseline heuristic." />

      <div className="grid grid-cols-4 gap-3">
        {[
          ["Precision@1", metrics.precisionAt1],
          ["Precision@5", metrics.precisionAt5],
          ["Recall@5", metrics.recallAt5],
          ["MRR", metrics.mrr],
        ].map(([label, value]) => (
          <div key={label as string} className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
            <div className="text-[10.5px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">{label}</div>
            <div className="mono-id mt-1.5 text-[26px] font-semibold text-[color:var(--color-text-primary)]">{(value as number).toFixed(1)}%</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
          <div className="mb-1 flex items-center justify-between">
            <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Baseline Comparison</h2>
            <span className="rounded-[3px] bg-[color:var(--color-signal-dim)] px-2 py-0.5 text-[10px] font-medium text-[color:var(--color-signal)]">Model Version: Model A</span>
          </div>
          <p className="mb-1 text-[12px] text-[color:var(--color-text-secondary)]">Model A consistently improves ranking quality over the baseline across the evaluated metrics.</p>
          <div className="mt-2">
            <MetricComparisonRow label="Precision@1" modelValue={metrics.precisionAt1} baselineValue={metrics.baseline.precisionAt1} />
            <MetricComparisonRow label="Precision@5" modelValue={metrics.precisionAt5} baselineValue={metrics.baseline.precisionAt5} />
            <MetricComparisonRow label="Recall@5" modelValue={metrics.recallAt5} baselineValue={metrics.baseline.recallAt5} />
            <MetricComparisonRow label="MRR" modelValue={metrics.mrr} baselineValue={metrics.baseline.mrr} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
            <h2 className="mb-3 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Evaluation Context</h2>
            <div className="space-y-2.5">
              {[
                ["Evaluation set", `${metrics.evaluation.complaintCount} complaints`],
                ["Candidate accounts", metrics.evaluation.candidateAccountCount.toLocaleString("en-IN")],
                ["Positive targets", metrics.evaluation.positiveTargetCount.toString()],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between border-b border-[color:var(--color-border)] pb-2 last:border-0">
                  <span className="text-[11.5px] text-[color:var(--color-text-tertiary)]">{label}</span>
                  <span className="mono-id text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">{value}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[10.5px] leading-snug text-[color:var(--color-text-tertiary)]">
              Methodology: Model A ranks candidate accounts within each complaint's transaction subgraph; metrics compare the rank of the true suspicious account against a heuristic
              baseline over the evaluation set above.
            </p>
          </div>
        </div>
      </div>

      {/* Model transparency */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
        <h2 className="mb-1 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Model Transparency — Feature Set</h2>
        <p className="mb-3 text-[12px] text-[color:var(--color-text-secondary)]">The signals Model A uses to rank suspicious accounts, explained in investigator-friendly terms.</p>
        <div className="grid grid-cols-2 gap-3">
          {metrics.features.map((f) => (
            <div key={f.key} className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3.5 py-3">
              <div className="text-[12px] font-semibold text-[color:var(--color-text-primary)]">{f.label}</div>
              <p className="mt-1 text-[11.5px] leading-snug text-[color:var(--color-text-secondary)]">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
