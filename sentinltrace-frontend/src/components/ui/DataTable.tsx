import { useMemo, useState } from "react";
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import clsx from "clsx";
import { EmptyState } from "@/components/ui/States";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => number | string;
  align?: "left" | "right" | "center";
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  searchPlaceholder?: string;
  searchFn?: (row: T, query: string) => boolean;
  pageSize?: number;
  emptyTitle?: string;
  emptyDescription?: string;
  filters?: React.ReactNode;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  searchPlaceholder = "Search...",
  searchFn,
  pageSize = 10,
  emptyTitle = "No results match your filters",
  emptyDescription = "Try adjusting the risk threshold or date range.",
  filters,
}: DataTableProps<T>) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    let out = rows;
    if (query.trim() && searchFn) out = out.filter((r) => searchFn(r, query.trim().toLowerCase()));
    if (sortKey) {
      const col = columns.find((c) => c.key === sortKey);
      if (col?.sortValue) {
        out = [...out].sort((a, b) => {
          const av = col.sortValue!(a);
          const bv = col.sortValue!(b);
          const cmp = av < bv ? -1 : av > bv ? 1 : 0;
          return sortDir === "asc" ? cmp : -cmp;
        });
      }
    }
    return out;
  }, [rows, query, sortKey, sortDir, searchFn, columns]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const pageRows = filtered.slice(currentPage * pageSize, currentPage * pageSize + pageSize);

  function toggleSort(col: Column<T>) {
    if (!col.sortValue) return;
    if (sortKey === col.key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(col.key);
      setSortDir("desc");
    }
    setPage(0);
  }

  return (
    <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
      <div className="flex flex-wrap items-center gap-2 border-b border-[color:var(--color-border)] px-4 py-3">
        {searchFn && (
          <div className="flex h-8 w-64 items-center gap-2 rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2.5">
            <Search className="h-3.5 w-3.5 text-[color:var(--color-text-tertiary)]" strokeWidth={1.75} />
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
              placeholder={searchPlaceholder}
              className="flex-1 bg-transparent text-[12px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)]"
            />
          </div>
        )}
        {filters}
        <span className="ml-auto text-[11.5px] text-[color:var(--color-text-tertiary)]">
          {filtered.length.toLocaleString("en-IN")} result{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead className="sticky top-0 z-10 bg-[color:var(--color-surface-raised)]">
                <tr className="border-b border-[color:var(--color-border)]">
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => toggleSort(col)}
                      style={{ width: col.width }}
                      className={clsx(
                        "whitespace-nowrap px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.05em] text-[color:var(--color-text-tertiary)]",
                        col.sortValue && "cursor-pointer select-none hover:text-[color:var(--color-text-secondary)]",
                        col.align === "right" && "text-right",
                        col.align === "center" && "text-center"
                      )}
                    >
                      <span className="inline-flex items-center gap-1">
                        {col.header}
                        {sortKey === col.key && (sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row) => (
                  <tr
                    key={rowKey(row)}
                    onClick={() => onRowClick?.(row)}
                    className={clsx(
                      "border-b border-[color:var(--color-border)] last:border-0",
                      onRowClick && "cursor-pointer transition-colors hover:bg-[color:var(--color-surface-hover)]"
                    )}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={clsx(
                          "whitespace-nowrap px-4 py-2.5 text-[12.5px] text-[color:var(--color-text-primary)]",
                          col.align === "right" && "text-right",
                          col.align === "center" && "text-center"
                        )}
                      >
                        {col.render(row)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t border-[color:var(--color-border)] px-4 py-2.5">
            <span className="text-[11px] text-[color:var(--color-text-tertiary)]">
              Page {currentPage + 1} of {pageCount}
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={currentPage === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="flex h-6 w-6 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] disabled:opacity-30 hover:bg-[color:var(--color-surface-hover)]"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <button
                disabled={currentPage >= pageCount - 1}
                onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                className="flex h-6 w-6 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] disabled:opacity-30 hover:bg-[color:var(--color-surface-hover)]"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
