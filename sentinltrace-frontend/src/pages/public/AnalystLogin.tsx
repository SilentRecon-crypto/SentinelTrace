import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { useAuth } from "@/hooks/useAuth";
import { ROUTES } from "@/routes";

export function AnalystLogin() {
  const { loginAnalyst } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [analystId, setAnalystId] = useState("");
  const [password, setPassword] = useState("");

  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? ROUTES.analystHome;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    // Mock/demo authentication — any non-empty credentials are accepted.
    // No password is stored, checked against a database, or transmitted
    // anywhere. This exists only to demonstrate the analyst-vs-user role
    // split; real authentication arrives with the backend integration.
    loginAnalyst(analystId || "analyst.demo");
    navigate(from, { replace: true });
  }

  return (
    <AuthLayout eyebrow="Analyst Portal">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Analyst ID / Email</label>
          <input
            value={analystId}
            onChange={(e) => setAnalystId(e.target.value)}
            placeholder="analyst@cybercell.gov.in"
            className="h-10 w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 text-[13px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)] focus:border-[color:var(--color-signal)]"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="h-10 w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 text-[13px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)] focus:border-[color:var(--color-signal)]"
          />
        </div>

        <button
          type="submit"
          className="flex w-full items-center justify-center gap-2 rounded-sm bg-[color:var(--color-signal)] py-2.5 text-[13px] font-semibold text-[#04191c] transition-opacity hover:opacity-90"
        >
          <ShieldCheck className="h-4 w-4" strokeWidth={1.75} /> Secure Access
        </button>

        <div className="flex items-center justify-center gap-1.5 border-t border-[color:var(--color-border)] pt-3.5">
          <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[color:var(--color-low)]" />
          <span className="text-[10.5px] font-medium tracking-wide text-[color:var(--color-text-tertiary)]">SYSTEM OPERATIONAL</span>
        </div>
      </form>
    </AuthLayout>
  );
}
