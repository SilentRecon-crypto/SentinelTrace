import { createContext, useContext, useState, type ReactNode } from "react";
import type { InvestigationPin, RiskLevel } from "@/types";

interface WorkspaceContextValue {
  pins: InvestigationPin[];
  isPinned: (entityType: InvestigationPin["entityType"], entityId: string) => boolean;
  togglePin: (entityType: InvestigationPin["entityType"], entityId: string, label: string, risk?: RiskLevel) => void;
  removePin: (id: string) => void;
  clearPins: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [pins, setPins] = useState<InvestigationPin[]>([
    { id: "pin-seed-1", entityType: "complaint", entityId: "CMP-10482", label: "CMP-10482", risk: "high", pinnedAt: new Date().toISOString(), note: "Primary case for demo walkthrough" },
    { id: "pin-seed-2", entityType: "account", entityId: "ACC-10482", label: "ACC-10482", risk: "critical", pinnedAt: new Date().toISOString() },
  ]);

  function isPinned(entityType: InvestigationPin["entityType"], entityId: string) {
    return pins.some((p) => p.entityType === entityType && p.entityId === entityId);
  }

  function togglePin(entityType: InvestigationPin["entityType"], entityId: string, label: string, risk?: RiskLevel) {
    setPins((prev) => {
      const existing = prev.find((p) => p.entityType === entityType && p.entityId === entityId);
      if (existing) return prev.filter((p) => p.id !== existing.id);
      return [...prev, { id: `pin-${Date.now()}`, entityType, entityId, label, risk, pinnedAt: new Date().toISOString() }];
    });
  }

  function removePin(id: string) {
    setPins((prev) => prev.filter((p) => p.id !== id));
  }

  function clearPins() {
    setPins([]);
  }

  return <WorkspaceContext.Provider value={{ pins, isPinned, togglePin, removePin, clearPins }}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
