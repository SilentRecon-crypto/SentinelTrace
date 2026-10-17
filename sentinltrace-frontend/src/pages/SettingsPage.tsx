import { PageHeader } from "@/components/ui/PageHeader";

export function SettingsPage() {
  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Configuration" title="Settings" description="Analyst preferences and environment configuration." />
      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
        <h2 className="mb-3 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Environment</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2.5">
            <div className="text-[10px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Data Source</div>
            <div className="mt-1 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">Synthetic / Demo</div>
          </div>
          <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2.5">
            <div className="text-[10px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Model Version</div>
            <div className="mt-1 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">Model A</div>
          </div>
          <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2.5">
            <div className="text-[10px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Backend Connectivity</div>
            <div className="mt-1 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">Not connected</div>
          </div>
          <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2.5">
            <div className="text-[10px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Unit</div>
            <div className="mt-1 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">Cybercrime Unit — Demo</div>
          </div>
        </div>
        <p className="mt-4 text-[11.5px] text-[color:var(--color-text-tertiary)]">
          Backend API configuration will appear here once SentinelTrace's Python service is connected. No credentials or endpoints are stored in this build.
        </p>
      </div>
    </div>
  );
}
