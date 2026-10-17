import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex items-start justify-between gap-4">
      <div>
        {eyebrow && <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)]">{eyebrow}</div>}
        <h1 className="text-[20px] font-semibold tracking-tight text-[color:var(--color-text-primary)]">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-[13px] leading-snug text-[color:var(--color-text-secondary)]">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
