import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { ROUTES } from "@/routes";

export function RequireAnalystAuth({ children }: { children: ReactNode }) {
  const { analyst } = useAuth();
  const location = useLocation();
  if (!analyst) return <Navigate to={ROUTES.analystLogin} replace state={{ from: location }} />;
  return <>{children}</>;
}

export function RequireUserAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to={ROUTES.userLogin} replace state={{ from: location }} />;
  return <>{children}</>;
}
