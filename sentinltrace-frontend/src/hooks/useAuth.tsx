import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

// ============================================================
// MOCK AUTHENTICATION
//
// This is demo/mock authentication only, exactly as scoped: it exists to
// demonstrate the two separate roles (analyst vs. citizen user) and gate
// their respective portals in the UI. It does NOT implement real password
// storage, hashing, tokens, or security of any kind, and must not be
// treated as such. When the real SentinelTrace backend is integrated,
// this context's login()/logout() bodies are the only things that need
// to change — every page already consumes it through useAuth().
// ============================================================

type Role = "analyst" | "user";

interface Identity {
  name: string;
  handle: string;
}

interface AuthState {
  analyst: Identity | null;
  user: Identity | null;
}

interface AuthContextValue extends AuthState {
  loginAnalyst: (idOrEmail: string) => void;
  loginUser: (idOrEmail: string) => void;
  logoutAnalyst: () => void;
  logoutUser: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const STORAGE_KEY = "sentineltrace.mockAuth";

function loadInitial(): AuthState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* sessionStorage unavailable or corrupt — fall back to signed-out */
  }
  return { analyst: null, user: null };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(loadInitial);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* ignore persistence failures — this is a demo convenience only */
    }
  }, [state]);

  function loginAnalyst(idOrEmail: string) {
    const handle = idOrEmail.trim() || "analyst.demo";
    setState((s) => ({ ...s, analyst: { name: deriveName(handle), handle } }));
  }
  function loginUser(idOrEmail: string) {
    const handle = idOrEmail.trim() || "citizen.demo";
    setState((s) => ({ ...s, user: { name: deriveName(handle), handle } }));
  }
  function logoutAnalyst() {
    setState((s) => ({ ...s, analyst: null }));
  }
  function logoutUser() {
    setState((s) => ({ ...s, user: null }));
  }

  return (
    <AuthContext.Provider value={{ ...state, loginAnalyst, loginUser, logoutAnalyst, logoutUser }}>
      {children}
    </AuthContext.Provider>
  );
}

function deriveName(handle: string): string {
  const local = handle.split("@")[0].replace(/[._-]+/g, " ").trim();
  if (!local) return "Demo Account";
  return local
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export type { Role };
