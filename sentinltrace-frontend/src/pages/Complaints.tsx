import { useNavigate } from "react-router-dom";
import { analystPath } from "@/routes";
import { useAsync } from "@/hooks/useAsync";
import { getComplaintsPage, formatComplaintId } from "@/services/complaints";
import type { BackendComplaint } from "@/services/backendTypes";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SkeletonTable } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { formatINR, formatSyntheticDay } from "@/utils/format";

// ============================================================
// INTEGRATION STATUS (first real-backend slice): this page now fetches
// live complaints from GET /api/v1/complaints. Risk level and
// investigation status are NOT yet shown as real values here — they only
// exist per-(complaint, Model A candidate) via Stage 4/6 endpoints this
// integration slice does not call yet — so those columns show an honest
// "PENDING" placeholder rather than fabricated data, and the risk/status
// filter controls from the mock version are removed for now rather than
// filtering against data that doesn't exist. Row click-through now opens
// the real ComplaintDetail page (Slice 2), keyed by the numeric
// complaint_id rather than the mock's "CMP-xxxxx" string id.
//
// `suspiciousAccountCount` and `predictedLocationCount` (mock-only
// concepts — the latter is Model B, which does not exist yet) have no
// honest backend source at all yet, so those columns are dropped entirely
// rather than shown empty.
// ============================================================

export function Complaints() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(() => getComplaintsPage(100, 0), []);
  const complaints = data?.items ?? [];

  const columns: Column<BackendComplaint>[] = [
    { key: "id", header: "Complaint ID", render: (c) => <span className="mono-id font-medium">{formatComplaintId(c.complaint_id)}</span>, sortValue: (c) => c.complaint_id },
    { key: "day", header: "Filed", render: (c) => <span className="text-[color:var(--color-text-secondary)]">{formatSyntheticDay(c.day)}</span>, sortValue: (c) => c.day },
    { key: "amount", header: "Amount", align: "right", render: (c) => formatINR(c.fraud_amount), sortValue: (c) => c.fraud_amount },
    { key: "hops", header: "Reported Hops", align: "center", render: (c) => c.n_hops, sortValue: (c) => c.n_hops },
    { key: "risk", header: "Risk", render: () => <RiskBadge risk="pending" size="sm" /> },
    { key: "status", header: "Status", render: () => <StatusBadge status="pending" /> },
  ];

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Investigation"
        title="Complaints"
        description="Live cybercrime complaints from the SentinelTrace backend. Risk scoring, investigation status, and detail drill-down populate as later integration steps land."
      />

      {error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : loading ? (
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <SkeletonTable rows={8} />
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={complaints}
          rowKey={(c) => String(c.complaint_id)}
          onRowClick={(c) => navigate(analystPath(`/complaints/${c.complaint_id}`))}
          searchPlaceholder="Search complaint ID..."
          searchFn={(c, q) => formatComplaintId(c.complaint_id).toLowerCase().includes(q) || String(c.complaint_id).includes(q)}
        />
      )}
    </div>
  );
}
