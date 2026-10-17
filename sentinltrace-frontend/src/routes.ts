// ============================================================
// SENTINELTRACE ROUTE CONSTANTS
//
// The existing analyst application originally lived at the site root
// (e.g. "/complaints", "/accounts/:id"). To make room for the new public
// landing page at "/", the analyst app was moved under the "/analyst"
// prefix and the user portal lives under "/user". These helpers are the
// single source of truth for that prefixing so every navigate()/NavLink
// call stays consistent.
// ============================================================

export const ANALYST_BASE = "/analyst";
export const USER_BASE = "/user";

export const analystPath = (path: string = "") => `${ANALYST_BASE}${path}`;
export const userPath = (path: string = "") => `${USER_BASE}${path}`;

export const ROUTES = {
  landing: "/",
  analystLogin: "/analyst/login",
  analystHome: analystPath(),
  userLogin: "/user/login",
  userHome: userPath(),
} as const;
