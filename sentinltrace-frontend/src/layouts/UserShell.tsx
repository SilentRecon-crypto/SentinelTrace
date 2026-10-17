import { Outlet } from "react-router-dom";
import { UserSidebar } from "@/components/layout/UserSidebar";

export function UserShell() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-[color:var(--color-void)] text-[color:var(--color-text-primary)]">
      <UserSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-5">
          <div className="flex items-center gap-1.5 rounded-sm border border-[color:var(--color-border)] px-2.5 py-1.5">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[color:var(--color-low)]" />
            <span className="text-[11px] font-medium tracking-wide text-[color:var(--color-text-secondary)]">SYSTEM OPERATIONAL</span>
          </div>
          <span className="text-[11px] text-[color:var(--color-text-tertiary)]">Citizen Cybercrime Reporting</span>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
