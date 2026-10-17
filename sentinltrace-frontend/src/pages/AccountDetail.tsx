import { useNavigate, useParams } from "react-router-dom";
import { analystPath } from "@/routes";
import { ArrowLeft, Network as NetworkIcon } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import { getAccount } from "@/services/api";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { formatINR, timeAgo } from "@/utils/format";
import { MODEL_A_FEATURES } from "@/data/reference";
import { PinButton } from "@/components/ui/PinButton";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2.5">
      <div className="text-[10px] font-medium uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]">{label}</div>
      <div className="mono-id mt-1 text-[14px] font-semibold text-[color:var(--color-text-primary)]">{value}</div>
    </div>
  );
}

export function AccountDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: account, loading, error, reload } = useAsync(() => getAccount(id!), [id]);

  if (error) return <ErrorState onRetry={reload} />;
  if (loading || !account) {
    return (
      <div className="space-y-4">
        <SkeletonBlock className="h-24" />
        <SkeletonBlock className="h-64" />
      </div>
    );
  }

  const contributing = MODEL_A_FEATURES.map((f) => ({
    ...f,
    value:
      f.key === "hopDistance" ? `${account.hopDistance} hops` :
      f.key === "passThroughRatio" ? account.passThroughRatio.toFixed(2) :
      f.key === "recentFanIn" ? account.recentFanIn.toString() :
      f.key === "outDegree" ? account.outDegree.toString() :
      f.key === "amountConsistency" ? account.amountConsistency.toFixed(2) :
      f.key === "centrality" ? account.centrality.toFixed(2) :
      `${account.accountAgeDays} days`,
  }));

  return (
    <div className="animate-fade-in space-y-4">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-[12px] font-medium text-[color:var(--color-text-tertiary)] hover:text-[color:var(--color-text-secondary)]">
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </button>

      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)]">Account Intelligence</div>
            <div className="flex items-center gap-3">
              <h1 className="mono-id text-[22px] font-semibold text-[color:var(--color-text-primary)]">{account.id}</h1>
              <RiskBadge risk={account.risk} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <PinButton entityType="account" entityId={account.id} label={account.id} risk={account.risk} />
            <button
              onClick={() => navigate(analystPath(`/networks?complaint=${account.linkedComplaintIds[0] ?? ""}`))}
              className="flex items-center gap-1.5 rounded-sm border border-[color:var(--color-border-strong)] px-3 py-1.5 text-[12px] font-medium text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)]"
            >
              <NetworkIcon className="h-3.5 w-3.5" /> View in Network
            </button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-4 gap-3">
          <Stat label="Risk Score" value={`${account.riskScore.toFixed(1)}%`} />
          <Stat label="Model" value="Model A" />
          <Stat label="Last Activity" value={timeAgo(account.lastActivity)} />
          <Stat label="Account Age" value={`${account.accountAgeDays} days`} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
          <h2 className="mb-3 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Account Characteristics</h2>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Transaction Count" value={account.transactionCount.toString()} />
            <Stat label="Incoming Volume" value={formatINR(account.incomingVolume)} />
            <Stat label="Outgoing Volume" value={formatINR(account.outgoingVolume)} />
            <Stat label="Fan-In" value={account.fanIn.toString()} />
            <Stat label="Fan-Out" value={account.fanOut.toString()} />
            <Stat label="Pass-Through Ratio" value={account.passThroughRatio.toFixed(2)} />
            <Stat label="Graph Centrality" value={account.centrality.toFixed(2)} />
            <Stat label="Hop Distance" value={`${account.hopDistance} hops`} />
            <Stat label="Amount Consistency" value={account.amountConsistency.toFixed(2)} />
          </div>

          <h2 className="mb-3 mt-5 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Risk Factors</h2>
          <ul className="space-y-1.5">
            {account.riskFactors.map((f) => (
              <li key={f} className="flex items-start gap-2 text-[12.5px] text-[color:var(--color-text-secondary)]">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-[color:var(--color-critical)]" />
                {f}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
          <h2 className="mb-1 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Contributing Signals</h2>
          <p className="mb-3 text-[11.5px] text-[color:var(--color-text-tertiary)]">Model A features that contributed to this account's ranking. Demo values shown.</p>
          <div className="space-y-2.5">
            {contributing.map((f) => (
              <div key={f.key} className="flex items-center justify-between border-b border-[color:var(--color-border)] pb-2 last:border-0">
                <span className="text-[11.5px] text-[color:var(--color-text-secondary)]">{f.label}</span>
                <span className="mono-id text-[12px] font-medium text-[color:var(--color-text-primary)]">{f.value}</span>
              </div>
            ))}
          </div>

          {account.linkedComplaintIds.length > 0 && (
            <>
              <h2 className="mb-2 mt-5 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Linked Complaints</h2>
              <div className="space-y-1.5">
                {account.linkedComplaintIds.map((cid) => (
                  <button
                    key={cid}
                    onClick={() => navigate(analystPath(`/complaints/${cid}`))}
                    className="mono-id block w-full rounded-sm border border-[color:var(--color-border)] px-2.5 py-1.5 text-left text-[12px] text-[color:var(--color-signal)] hover:border-[color:var(--color-signal)]"
                  >
                    {cid}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
