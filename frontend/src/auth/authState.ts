import { createContext, useContext } from "react";

import type { User } from "../api/types";

export interface AuthContextValue {
  user: User | null;
  csrfToken: string | null;
  ready: boolean;
  sessionUnavailable: boolean;
  retrySession: () => void;
  login: (email: string, password: string) => Promise<User>;
  register: (token: string, displayName: string, password: string) => Promise<User>;
  clearSession: () => void;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth 必须在 AuthProvider 中使用");
  return context;
}
