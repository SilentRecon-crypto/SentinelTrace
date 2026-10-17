import { NavLink, useNavigate } from "react-router-dom";
import { startTransition } from "react";
import { LayoutDashboard, FilePlus2, ListChecks, Search, Bell, UserRound, LogOut } from "lucide-react";
import clsx from "clsx";
import { SentinelMark } from "@/components/layout/SentinelMark";
import { useAuth } from "@/hooks/useAuth";
import { userPath, ROUTES } from "@/routes";

const NAV_ITEMS = [
  { to: userPath(), label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: userPath("/report"), label: "Report Cybercrime", icon: FilePlus2 },
  { to: userPath("/complaints"), label: "My Complaints", icon: ListChecks },
  { to: userPath("/track"), label: "Track Complaint", icon: Search },
  { to: userPath("/notifications"), label: "Notifications", icon: Bell },
  { to: userPath("/profile"), label: "Profile", icon: UserRound },
];

export function UserSidebar() {
  const { user, logoutUser } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    navigate(ROUTES.landing, { replace: true });
    startTransition(() => {
      logoutUser();
    });
  }

  return (
    <aside className="flex h-full w-[224px] shrink-0 flex-col border-r border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <div className="flex h-14 items-center gap-2.5 border-b border-[color:var(--color-border)] px-4">
        <SentinelMark className="h-6 w-6 shrink-0" />
        <div className="leading-none">
          <div className="text-[13px] font-semibold tracking-tight text-[color:var(--color-text-primary)]">SentinelTrace</div>
          <div className="text-[9.5px] font-medium uppercase tracking-[0.09em] text-[color:var(--color-text-tertiary)]">User Portal</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2.5 py-3">
        <ul className="space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-2.5 rounded-sm px-2.5 py-[7px] text-[12.5px] font-medium transition-colors",
                    isActive
                      ? "bg-[color:var(--color-surface-hover)] text-[color:var(--color-signal)]"
                      : "text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)] hover:text-[color:var(--color-text-primary)]"
                  )
                }
              >
                <item.icon className="h-[15px] w-[15px] shrink-0" strokeWidth={1.75} />
                <span className="truncate">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-[color:var(--color-border)] p-2.5">
        <div className="flex items-center gap-2 px-1">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[color:var(--color-surface-hover)] text-[10px] font-semibold text-[color:var(--color-text-secondary)]">
            {(user?.name ?? "U")[0]?.toUpperCase()}
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <div className="truncate text-[11.5px] font-medium text-[color:var(--color-text-primary)]">{user?.name ?? "Citizen"}</div>
            <div className="truncate text-[10px] text-[color:var(--color-text-tertiary)]">User Portal</div>
          </div>
          <button
            onClick={handleLogout}
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-sm text-[color:var(--color-text-tertiary)] hover:bg-[color:var(--color-surface-hover)] hover:text-[color:var(--color-critical)]"
            aria-label="Log out"
            title="Log out"
          >
            <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </aside>
  );
}
