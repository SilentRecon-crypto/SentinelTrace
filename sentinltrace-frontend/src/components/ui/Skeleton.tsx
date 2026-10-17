export function SkeletonCard() {
  return <div className="skeleton h-[120px] rounded-md border border-[color:var(--color-border)]" />;
}

export function SkeletonRow() {
  return <div className="skeleton h-9 w-full rounded-sm" />;
}

export function SkeletonTable({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  );
}

export function SkeletonBlock({ className = "h-48" }: { className?: string }) {
  return <div className={`skeleton rounded-md border border-[color:var(--color-border)] ${className}`} />;
}
