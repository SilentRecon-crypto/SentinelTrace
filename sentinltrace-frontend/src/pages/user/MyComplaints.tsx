import { useNavigate } from "react-router-dom";
import { useAsync } from "@/hooks/useAsync";
import { getUserComplaints } from "@/services/userApi";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { UserComplaintStatusBadge } from "@/components/ui/UserComplaintStatusBadge";
import { SkeletonTable } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { formatDate, formatINR } from "@/utils/format";
import { userPath } from "@/routes";
import type { UserComplaint } from "@/types";

export function MyComplaints() {
  const navigate = useNavigate();
  const { data: complaints, loading, error, reload } = useAsync(getUserComplaints, []);

  const columns: Column<UserComplaint>[] = [
    { key: "id", header: "Complaint ID", render: (c) => <span className="mono-id font-medium">{c.id}</span>, sortValue: (c) => c.id },
    { key: "date", header: "Date Submitted", render: (c) => formatDate(c.dateSubmitted), sortValue: (c) => c.dateSubmitted },
    { key: "type", header: "Complaint Type", render: (c) => c.complaintType, sortValue: (c) => c.complaintType },
    { key: "amount", header: "Amount", align: "right", render: (c) => formatINR(c.amount), sortValue: (c) => c.amount },
    { key: "status", header: "Status", render: (c) => <UserComplaintStatusBadge status={c.status} /> },
    { key: "updated", header: "Last Updated", render: (c) => formatDate(c.lastUpdated), sortValue: (c) => c.lastUpdated },
  ];

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="User Portal" title="My Complaints" description="All complaints you've submitted, with their current status." />
      {error ? (
        <ErrorState onRetry={reload} />
      ) : loading ? (
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <SkeletonTable rows={4} />
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={complaints ?? []}
          rowKey={(c) => c.id}
          onRowClick={(c) => navigate(userPath(`/track?complaint=${c.id}`))}
          searchPlaceholder="Search complaint ID..."
          searchFn={(c, q) => c.id.toLowerCase().includes(q) || c.complaintType.toLowerCase().includes(q)}
          emptyTitle="NO COMPLAINTS YET"
          emptyDescription="Complaints you submit will appear here."
        />
      )}
    </div>
  );
}
