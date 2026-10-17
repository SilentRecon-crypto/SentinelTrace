import { Pin, PinOff } from "lucide-react";
import clsx from "clsx";
import { useWorkspace } from "@/hooks/useWorkspace";
import type { InvestigationPin, RiskLevel } from "@/types";

export function PinButton({
  entityType,
  entityId,
  label,
  risk,
}: {
  entityType: InvestigationPin["entityType"];
  entityId: string;
  label: string;
  risk?: RiskLevel;
}) {
  const { isPinned, togglePin } = useWorkspace();
  const pinned = isPinned(entityType, entityId);

  return (
    <button
      onClick={() => togglePin(entityType, entityId, label, risk)}
      className={clsx(
        "flex items-center gap-1.5 rounded-sm border px-3 py-1.5 text-[12px] font-medium transition-colors",
        pinned
          ? "border-[color:var(--color-signal)] bg-[color:var(--color-signal-dim)] text-[color:var(--color-signal)]"
          : "border-[color:var(--color-border-strong)] text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)]"
      )}
    >
      {pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
      {pinned ? "Pinned to Workspace" : "Pin to Workspace"}
    </button>
  );
}
