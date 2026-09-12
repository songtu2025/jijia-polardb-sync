import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import {
  advanceAuthSessionGeneration,
  api,
  ApiError,
  AUTH_UNAUTHORIZED_EVENT,
  isCurrentAuthUnauthorizedEvent,
} from "../api/client";
import type { User } from "../api/types";
import { AuthContext, type AuthContextValue } from "./authState";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [sessionUnavailable, setSessionUnavailable] = useState(false);
  const [sessionAttempt, setSessionAttempt] = useState(0);

  const clearSession = useCallback(() => {
    advanceAuthSessionGeneration();
    setUser(null);
    setCsrfToken(null);
    setSessionUnavailable(false);
  }, []);

  useEffect(() => {
    const clearSession = (event: Event) => {
      if (!isCurrentAuthUnauthorizedEvent(event)) return;
      setUser(null);
      setCsrfToken(null);
      setSessionUnavailable(false);
    };
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, clearSession);
    return () => window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, clearSession);
  }, []);

  useEffect(() => {
    let active = true;
    setReady(false);
    setSessionUnavailable(false);
    advanceAuthSessionGeneration();
    api
      .session()
      .then((result) => {
        if (!active) return;
        setUser(result.user);
        setCsrfToken(result.csrfToken);
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          setUser(null);
          setCsrfToken(null);
          return;
        }
        setSessionUnavailable(true);
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, [sessionAttempt]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      csrfToken,
      ready,
      sessionUnavailable,
      retrySession() {
        setSessionAttempt((current) => current + 1);
      },
      clearSession,
      async login(email, password) {
        const result = await api.login(email, password);
        advanceAuthSessionGeneration();
        setUser(result.user);
        setCsrfToken(result.csrfToken);
        return result.user;
      },
      async register(token, displayName, password) {
        const result = await api.register(token, displayName, password);
        advanceAuthSessionGeneration();
        setUser(result.user);
        setCsrfToken(result.csrfToken);
        return result.user;
      },
      async logout() {
        if (csrfToken) {
          try {
            await api.logout(csrfToken);
          } catch (error) {
            if (!(error instanceof ApiError && error.status === 401)) throw error;
          }
        }
        clearSession();
      },
    }),
    [clearSession, csrfToken, ready, sessionUnavailable, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
