import { SearchX, AlertTriangle } from "lucide-react";

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <SearchX className="h-7 w-7 text-[color:var(--color-text-tertiary)]" strokeWidth={1.5} />
      <p className="text-[13px] font-medium tracking-wide text-[color:var(--color-text-secondary)]">{title}</p>
      <p className="max-w-sm text-[12px] text-[color:var(--color-text-tertiary)]">{description}</p>
    </div>
  );
}

export function ErrorState({ message = "The requested data could not be loaded.", onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <AlertTriangle className="h-7 w-7 text-[color:var(--color-critical)]" strokeWidth={1.5} />
      <p className="text-[13px] font-medium tracking-wide text-[color:var(--color-text-primary)]">Intelligence data unavailable</p>
      <p className="max-w-sm text-[12px] text-[color:var(--color-text-tertiary)]">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 rounded-sm border border-[color:var(--color-border-strong)] px-3 py-1.5 text-[12px] font-medium text-[color:var(--color-text-secondary)] transition-colors hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)]"
        >
          Retry
        </button>
      )}
    </div>
  );
}
