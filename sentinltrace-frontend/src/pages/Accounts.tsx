import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { analystPath } from "@/routes";
import { useAsync } from "@/hooks/useAsync";
import { getAccounts } from "@/services/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { RiskMeter } from "@/components/ui/RiskMeter";
import { SkeletonTable } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import type { Account, RiskLevel } from "@/types";
import clsx from "clsx";

const RISK_FILTERS: (RiskLevel | "all")[] = ["all", "critical", "high", "medium", "low"];

export function Accounts() {
  const navigate = useNavigate();
  const { data: accounts, loading, error, reload } = useAsync(getAccounts, []);
  const [riskFilter, setRiskFilter] = useState<RiskLevel | "all">("all");
  const [minScore, setMinScore] = useState(0);

  const columns: Column<Account>[] = [
    { key: "rank", header: "Rank", width: "56px", render: (a) => `#${(accounts ?? []).indexOf(a) + 1}`, sortValue: (a) => -a.riskScore },
    { key: "id", header: "Account ID", render: (a) => <span className="mono-id font-medium">{a.id}</span>, sortValue: (a) => a.id },
    { key: "score", header: "Risk Score", render: (a) => <RiskMeter score={a.riskScore} risk={a.risk} />, sortValue: (a) => a.riskScore },
    { key: "hop", header: "Hop Dist.", align: "center", render: (a) => `${a.hopDistance}`, sortValue: (a) => a.hopDistance },
    { key: "ptr", header: "Pass-Through", align: "center", render: (a) => a.passThroughRatio.toFixed(2), sortValue: (a) => a.passThroughRatio },
    { key: "fanin", header: "Fan-In", align: "center", render: (a) => a.recentFanIn, sortValue: (a) => a.recentFanIn },
    { key: "outdeg", header: "Out Degree", align: "center", render: (a) => a.outDegree, sortValue: (a) => a.outDegree },
    { key: "consist", header: "Amt. Consistency", align: "center", render: (a) => a.amountConsistency.toFixed(2), sortValue: (a) => a.amountConsistency },
    { key: "centrality", header: "Centrality", align: "center", render: (a) => a.centrality.toFixed(2), sortValue: (a) => a.centrality },
    { key: "age", header: "Account Age", align: "center", render: (a) => `${a.accountAgeDays}d`, sortValue: (a) => a.accountAgeDays },
    { key: "status", header: "Status", render: (a) => <RiskBadge risk={a.status} size="sm" /> },
  ];

  const rows = (accounts ?? []).filter((a) => (riskFilter === "all" || a.risk === riskFilter) && a.riskScore >= minScore);

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Account Intelligence" title="Top Suspicious Accounts" description="Accounts ranked by Model A score across hop distance, pass-through behavior, fan-in/out, and network centrality." />

      {error ? (
        <ErrorState onRetry={reload} />
      ) : loading ? (
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <SkeletonTable rows={10} />
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(a) => a.id}
          onRowClick={(a) => navigate(analystPath(`/accounts/${a.id}`))}
          searchPlaceholder="Search account ID..."
          searchFn={(a, q) => a.id.toLowerCase().includes(q)}
          pageSize={12}
          filters={
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-0.5 rounded-sm border border-[color:var(--color-border)] p-0.5">
                {RISK_FILTERS.map((r) => (
                  <button
                    key={r}
                    onClick={() => setRiskFilter(r)}
                    className={clsx(
                      "rounded-[3px] px-2 py-1 text-[11px] font-medium capitalize transition-colors",
                      riskFilter === r ? "bg-[color:var(--color-surface-hover)] text-[color:var(--color-signal)]" : "text-[color:var(--color-text-tertiary)] hover:text-[color:var(--color-text-secondary)]"
                    )}
                  >
                    {r}
                  </button>
                ))}
              </div>
              <label className="flex items-center gap-1.5 text-[11px] text-[color:var(--color-text-tertiary)]">
                Min score
                <input type="range" min={0} max={100} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} className="accent-[var(--color-signal)]" />
                <span className="mono-id w-8 text-[color:var(--color-text-secondary)]">{minScore}</span>
              </label>
            </div>
          }
        />
      )}
    </div>
  );
}
