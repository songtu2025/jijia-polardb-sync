import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { api, ApiError } from "../api/client";
import type { User } from "../api/types";

interface AuthContextValue {
  user: User | null;
  csrfToken: string | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (
    token: string,
    displayName: string,
    password: string,
  ) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .session()
      .then((result) => {
        if (!active) return;
        setUser(result.user);
        setCsrfToken(result.csrfToken);
      })
      .catch((error: unknown) => {
        // 未登录或本地 API 尚未启动时都保持游客态，不污染浏览器控制台。
        if (!(error instanceof ApiError)) {
          console.error("恢复登录状态失败", error);
        }
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      csrfToken,
      ready,
      async login(email, password) {
        const result = await api.login(email, password);
        setUser(result.user);
        setCsrfToken(result.csrfToken);
        return result.user;
      },
      async register(token, displayName, password) {
        const result = await api.register(token, displayName, password);
        setUser(result.user);
        setCsrfToken(result.csrfToken);
        return result.user;
      },
      async logout() {
        try {
          if (csrfToken) await api.logout(csrfToken);
        } finally {
          setUser(null);
          setCsrfToken(null);
        }
      },
    }),
    [csrfToken, ready, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth 必须在 AuthProvider 中使用");
  return context;
}
