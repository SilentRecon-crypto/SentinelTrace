import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { LogIn, UserPlus } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { useAuth } from "@/hooks/useAuth";
import { ROUTES } from "@/routes";

export function UserLogin() {
  const { loginUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<"signin" | "create">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? ROUTES.userHome;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    // Mock/demo authentication — any non-empty credentials are accepted,
    // and "Create account" simply signs the demo user in immediately.
    // Nothing is persisted beyond this browser session.
    loginUser(email || "citizen.demo");
    navigate(from, { replace: true });
  }

  return (
    <AuthLayout eyebrow="User Portal">
      <div className="mb-4 flex rounded-sm border border-[color:var(--color-border)] p-0.5">
        <button
          onClick={() => setMode("signin")}
          className={`flex-1 rounded-[3px] py-1.5 text-[12px] font-medium transition-colors ${mode === "signin" ? "bg-[color:var(--color-surface-hover)] text-[color:var(--color-signal)]" : "text-[color:var(--color-text-tertiary)]"}`}
        >
          Sign In
        </button>
        <button
          onClick={() => setMode("create")}
          className={`flex-1 rounded-[3px] py-1.5 text-[12px] font-medium transition-colors ${mode === "create" ? "bg-[color:var(--color-surface-hover)] text-[color:var(--color-signal)]" : "text-[color:var(--color-text-tertiary)]"}`}
        >
          Create Account
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Email / Username</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
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

        {mode === "signin" && (
          <div className="flex items-center justify-between text-[11.5px]">
            <label className="flex items-center gap-1.5 text-[color:var(--color-text-secondary)]">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="accent-[var(--color-signal)]" />
              Remember me
            </label>
            <button
              type="button"
              onClick={() => setNotice("Password reset isn't available in this demo environment.")}
              className="font-medium text-[color:var(--color-signal)] hover:underline"
            >
              Forgot password?
            </button>
          </div>
        )}

        {notice && <p className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2.5 py-2 text-[11px] text-[color:var(--color-text-tertiary)]">{notice}</p>}

        <button
          type="submit"
          className="flex w-full items-center justify-center gap-2 rounded-sm bg-[color:var(--color-signal)] py-2.5 text-[13px] font-semibold text-[#04191c] transition-opacity hover:opacity-90"
        >
          {mode === "signin" ? (
            <>
              <LogIn className="h-4 w-4" strokeWidth={1.75} /> Sign In
            </>
          ) : (
            <>
              <UserPlus className="h-4 w-4" strokeWidth={1.75} /> Create Account
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
