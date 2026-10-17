import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { analystPath } from "@/routes";
import { FileWarning, ShieldAlert, MapPinned, Target, FolderSearch, ArrowRight } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import { getKpiSummary, getRiskTrend, getComplaints, getAlerts, getAccounts } from "@/services/api";
import { KPICard } from "@/components/ui/KPICard";
import { RiskTrendChart } from "@/components/charts/RiskTrendChart";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { RiskMeter } from "@/components/ui/RiskMeter";
import { SkeletonBlock, SkeletonCard } from "@/components/ui/Skeleton";
import { formatDateTime, formatINR, timeAgo } from "@/utils/format";
import { LAST_ANALYSIS_ISO } from "@/data/mockData";
import clsx from "clsx";

const RANGES = ["24H", "7D", "30D", "90D"] as const;
type Range = (typeof RANGES)[number];

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-[color:var(--color-critical)]",
  high: "bg-[color:var(--color-high)]",
  medium: "bg-[color:var(--color-medium)]",
  info: "bg-[color:var(--color-info)]",
};

export function Dashboard() {
  const navigate = useNavigate();
  const [range, setRange] = useState<Range>("7D");
  const { data: kpi } = useAsync(getKpiSummary, []);
  const { data: trend, loading: trendLoading } = useAsync(() => getRiskTrend(range), [range]);
  const { data: complaints, loading: complaintsLoading } = useAsync(getComplaints, []);
  const { data: alerts } = useAsync(getAlerts, []);
  const { data: accounts, loading: accountsLoading } = useAsync(getAccounts, []);

  const topAccounts = accounts?.slice(0, 5) ?? [];
  const criticalComplaints = complaints?.filter((c) => c.risk === "critical" || c.risk === "high").slice(0, 5) ?? [];

  return (
    <div className="animate-fade-in space-y-5">
      {/* Hero */}
      <div className="flex items-end justify-between rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-5 py-4">
        <div>
          <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)]">Cybercrime Intelligence Center</div>
          <h1 className="text-[19px] font-semibold tracking-tight text-[color:var(--color-text-primary)]">
            Predictive overview of suspicious transaction networks and potential cash-out activity
          </h1>
          <p className="mt-1 text-[12px] text-[color:var(--color-text-tertiary)]">Last analysis {formatDateTime(LAST_ANALYSIS_ISO)} IST</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={() => navigate(analystPath("/workspace"))}
            className="rounded-sm border border-[color:var(--color-border-strong)] px-3 py-1.5 text-[12px] font-medium text-[color:var(--color-text-secondary)] transition-colors hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)]"
          >
            View Investigations
          </button>
          <button
            onClick={() => navigate(analystPath("/complaints"))}
            className="rounded-sm bg-[color:var(--color-signal)] px-3 py-1.5 text-[12px] font-semibold text-[#04191c] transition-opacity hover:opacity-90"
          >
            Run Analysis
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-5 gap-3">
        {kpi ? (
          <>
            <KPICard label="Active Complaints" value={kpi.activeComplaints.toLocaleString("en-IN")} description="Complaints currently open across all units" changePct={kpi.activeComplaintsChangePct} icon={FileWarning} />
            <KPICard label="High-Risk Accounts" value={kpi.highRiskAccounts.toLocaleString("en-IN")} description="Accounts ranked above the investigation threshold" changePct={kpi.highRiskAccountsChangePct} icon={ShieldAlert} tone="critical" />
            <KPICard label="Predicted Cash-Out Locations" value={kpi.predictedCashOutLocations.toString()} description="Distinct locations flagged as likely exit points" icon={MapPinned} tone="high" />
            <KPICard label="High Confidence Predictions" value={kpi.highConfidencePredictions.toString()} description="Predictions above the 80% confidence threshold" icon={Target} />
            <KPICard label="Investigations Requiring Action" value={kpi.investigationsRequiringAction.toString()} description="Cases with unresolved escalation flags" icon={FolderSearch} tone="high" />
          </>
        ) : (
          Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
        )}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Risk overview */}
        <div className="col-span-2 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Risk Overview</h2>
              <p className="text-[11.5px] text-[color:var(--color-text-tertiary)]">Complaint risk distribution over time</p>
            </div>
            <div className="flex items-center gap-0.5 rounded-sm border border-[color:var(--color-border)] p-0.5">
              {RANGES.map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={clsx(
                    "rounded-[3px] px-2.5 py-1 text-[11px] font-medium transition-colors",
                    range === r ? "bg-[color:var(--color-surface-hover)] text-[color:var(--color-signal)]" : "text-[color:var(--color-text-tertiary)] hover:text-[color:var(--color-text-secondary)]"
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          {trendLoading || !trend ? <SkeletonBlock className="h-[240px]" /> : <RiskTrendChart data={trend} range={range} />}
          <div className="mt-1 flex items-center gap-4 border-t border-[color:var(--color-border)] pt-3">
            {[
              { label: "Critical", color: "var(--color-critical)" },
              { label: "High", color: "var(--color-high)" },
              { label: "Medium", color: "var(--color-medium)" },
              { label: "Low", color: "var(--color-low)" },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1.5 text-[11px] text-[color:var(--color-text-secondary)]">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: l.color }} />
                {l.label}
              </div>
            ))}
          </div>
        </div>

        {/* Live intelligence feed */}
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <div className="flex items-center justify-between border-b border-[color:var(--color-border)] px-4 py-3">
            <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Live Intelligence Feed</h2>
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[color:var(--color-low)]" />
          </div>
          <div className="max-h-[300px] divide-y divide-[color:var(--color-border)] overflow-y-auto">
            {alerts?.map((a) => (
              <div key={a.id} className="px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <span className={clsx("h-1.5 w-1.5 rounded-full", SEVERITY_DOT[a.severity])} />
                  <span className="mono-id text-[10.5px] text-[color:var(--color-text-tertiary)]">{timeAgo(a.timestamp)}</span>
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-[color:var(--color-text-tertiary)]">{a.severity}</span>
                </div>
                <p className="mt-1 text-[12px] leading-snug text-[color:var(--color-text-secondary)]">{a.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Top suspicious accounts */}
        <div className="col-span-2 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <div className="flex items-center justify-between border-b border-[color:var(--color-border)] px-4 py-3">
            <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Top Suspicious Accounts</h2>
            <button onClick={() => navigate(analystPath("/accounts"))} className="flex items-center gap-1 text-[11.5px] font-medium text-[color:var(--color-signal)] hover:opacity-80">
              View all <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          <div className="divide-y divide-[color:var(--color-border)]">
            {accountsLoading || topAccounts.length === 0
              ? Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton m-3 h-10 rounded-sm" />)
              : topAccounts.map((a, i) => (
                  <button
                    key={a.id}
                    onClick={() => navigate(analystPath(`/accounts/${a.id}`))}
                    className="flex w-full items-center gap-4 px-4 py-2.5 text-left transition-colors hover:bg-[color:var(--color-surface-hover)]"
                  >
                    <span className="mono-id w-5 text-[11px] text-[color:var(--color-text-tertiary)]">#{i + 1}</span>
                    <span className="mono-id w-24 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{a.id}</span>
                    <RiskMeter score={a.riskScore} risk={a.risk} compact />
                    <span className="ml-auto text-[11px] text-[color:var(--color-text-tertiary)]">{a.hopDistance} hops</span>
                    <RiskBadge risk={a.risk} size="sm" />
                  </button>
                ))}
          </div>
        </div>

        {/* High-priority complaints */}
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <div className="flex items-center justify-between border-b border-[color:var(--color-border)] px-4 py-3">
            <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">High-Priority Complaints</h2>
          </div>
          <div className="divide-y divide-[color:var(--color-border)]">
            {complaintsLoading || criticalComplaints.length === 0
              ? Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton m-3 h-10 rounded-sm" />)
              : criticalComplaints.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => navigate(analystPath(`/complaints/${c.id}`))}
                    className="flex w-full flex-col gap-1 px-4 py-2.5 text-left transition-colors hover:bg-[color:var(--color-surface-hover)]"
                  >
                    <div className="flex items-center justify-between">
                      <span className="mono-id text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{c.id}</span>
                      <RiskBadge risk={c.risk} size="sm" />
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-[color:var(--color-text-tertiary)]">
                      <span>{formatINR(c.amount)}</span>
                      <span>{c.chainDepth}-hop chain</span>
                    </div>
                  </button>
                ))}
          </div>
        </div>
      </div>
    </div>
  );
}
