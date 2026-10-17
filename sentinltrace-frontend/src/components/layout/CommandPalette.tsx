import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, FileWarning, UserRoundSearch, MapPinned, ArrowRight, X } from "lucide-react";
import { searchAll } from "@/services/api";
import type { SearchResultItem } from "@/types";
import { RiskBadge } from "@/components/ui/RiskBadge";

import { analystPath } from "@/routes";

const TYPE_ICON = { complaint: FileWarning, account: UserRoundSearch, location: MapPinned, transaction: ArrowRight } as const;
const TYPE_LABEL = { complaint: "Complaints", account: "Accounts", location: "Locations", transaction: "Transactions" } as const;
const TYPE_ROUTE = { complaint: analystPath("/complaints"), account: analystPath("/accounts"), location: analystPath("/cashout"), transaction: analystPath("/networks") } as const;

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (open) {
      setQuery("");
      setResults([]);
      setTimeout(() => inputRef.current?.focus(), 20);
    }
  }, [open]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    let active = true;
    searchAll(query).then((r) => {
      if (active) setResults(r);
    });
    return () => {
      active = false;
    };
  }, [query]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && open) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const grouped = results.reduce<Record<string, SearchResultItem[]>>((acc, r) => {
    (acc[r.type] ??= []).push(r);
    return acc;
  }, {});

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[14vh]" onClick={onClose}>
      <div
        className="animate-fade-in w-full max-w-[560px] overflow-hidden rounded-md border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 border-b border-[color:var(--color-border)] px-4 py-3">
          <Search className="h-4 w-4 text-[color:var(--color-text-tertiary)]" strokeWidth={1.75} />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search complaint, account, transaction..."
            className="flex-1 bg-transparent text-[13.5px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)]"
          />
          <button onClick={onClose} className="text-[color:var(--color-text-tertiary)] hover:text-[color:var(--color-text-secondary)]">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[360px] overflow-y-auto p-2">
          {!query.trim() && (
            <p className="px-2 py-6 text-center text-[12px] text-[color:var(--color-text-tertiary)]">
              Search by complaint ID, account ID, transaction ID, or location ID.
            </p>
          )}
          {query.trim() && results.length === 0 && (
            <p className="px-2 py-6 text-center text-[12px] text-[color:var(--color-text-tertiary)]">No matches for &ldquo;{query}&rdquo;.</p>
          )}
          {(Object.keys(grouped) as (keyof typeof TYPE_LABEL)[]).map((type) => (
            <div key={type} className="mb-1.5">
              <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[color:var(--color-text-tertiary)]">{TYPE_LABEL[type]}</div>
              {grouped[type].map((r) => {
                const Icon = TYPE_ICON[type];
                return (
                  <button
                    key={r.id}
                    onClick={() => {
                      navigate(TYPE_ROUTE[type]);
                      onClose();
                    }}
                    className="flex w-full items-center gap-2.5 rounded-sm px-2 py-2 text-left transition-colors hover:bg-[color:var(--color-surface-hover)]"
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-tertiary)]" strokeWidth={1.75} />
                    <span className="mono-id text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{r.title}</span>
                    <span className="truncate text-[11.5px] text-[color:var(--color-text-tertiary)]">{r.subtitle}</span>
                    {r.risk && (
                      <span className="ml-auto">
                        <RiskBadge risk={r.risk} size="sm" />
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
