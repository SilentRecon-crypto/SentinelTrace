import { NavLink, useNavigate } from "react-router-dom";
import { startTransition } from "react";
import {
  LayoutDashboard,
  FileWarning,
  UserRoundSearch,
  Network,
  MapPinned,
  Target,
  ChartNoAxesCombined,
  FolderSearch,
  Activity,
  Settings,
  LogOut,
} from "lucide-react";
import clsx from "clsx";
import { SentinelMark } from "@/components/layout/SentinelMark";
import { useAuth } from "@/hooks/useAuth";
import { analystPath, ROUTES } from "@/routes";

const NAV_ITEMS = [
  { to: analystPath(), label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: analystPath("/complaints"), label: "Complaints", icon: FileWarning },
  { to: analystPath("/accounts"), label: "Account Intelligence", icon: UserRoundSearch },
  { to: analystPath("/networks"), label: "Transaction Networks", icon: Network },
  { to: analystPath("/cashout"), label: "Cash-Out Intelligence", icon: MapPinned },
  { to: analystPath("/predictions"), label: "Predictions", icon: Target },
  { to: analystPath("/analytics"), label: "Model Evaluation", icon: ChartNoAxesCombined },
  { to: analystPath("/workspace"), label: "Investigation Workspace", icon: FolderSearch },
  { to: analystPath("/system"), label: "System Status", icon: Activity },
];

export function Sidebar() {
  const { analyst, logoutAnalyst } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    navigate(ROUTES.landing, { replace: true });
    startTransition(() => {
      logoutAnalyst();
    });
  }

  return (
    <aside className="flex h-full w-[228px] shrink-0 flex-col border-r border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <div className="flex h-14 items-center gap-2.5 border-b border-[color:var(--color-border)] px-4">
        <SentinelMark className="h-6 w-6 shrink-0" />
        <div className="leading-none">
          <div className="text-[13px] font-semibold tracking-tight text-[color:var(--color-text-primary)]">SentinelTrace</div>
          <div className="text-[9.5px] font-medium uppercase tracking-[0.09em] text-[color:var(--color-text-tertiary)]">Cybercrime Intelligence</div>
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
        <NavLink
          to={analystPath("/settings")}
          className={({ isActive }) =>
            clsx(
              "mb-2 flex items-center gap-2.5 rounded-sm px-2.5 py-[7px] text-[12.5px] font-medium transition-colors",
              isActive ? "bg-[color:var(--color-surface-hover)] text-[color:var(--color-signal)]" : "text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)] hover:text-[color:var(--color-text-primary)]"
            )
          }
        >
          <Settings className="h-[15px] w-[15px]" strokeWidth={1.75} />
          Settings
        </NavLink>
        <div className="flex items-center justify-between rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-2.5 py-2">
          <div className="flex items-center gap-1.5">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[color:var(--color-low)]" />
            <span className="text-[10.5px] font-medium text-[color:var(--color-text-secondary)]">Demo Environment</span>
          </div>
        </div>
        <div className="mt-2 flex items-center gap-2 px-1">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[color:var(--color-surface-hover)] text-[10px] font-semibold text-[color:var(--color-text-secondary)]">
            {(analyst?.name ?? "R A")
              .split(" ")
              .map((w) => w[0])
              .slice(0, 2)
              .join("")
              .toUpperCase()}
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <div className="truncate text-[11.5px] font-medium text-[color:var(--color-text-primary)]">{analyst?.name ?? "Analyst"}</div>
            <div className="truncate text-[10px] text-[color:var(--color-text-tertiary)]">Cybercrime Unit · Analyst</div>
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
