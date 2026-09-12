import { StrictMode } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AUTH_UNAUTHORIZED_EVENT } from "../api/client";
import { AuthProvider, useAuth } from "./AuthContext";

function SessionProbe() {
  const { csrfToken, ready, user } = useAuth();
  return (
    <>
      <span>{ready ? "会话就绪" : "会话加载中"}</span>
      <span>{user?.email ?? "游客"}</span>
      <span>{csrfToken ?? "无 CSRF"}</span>
    </>
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

describe("StrictMode 会话恢复", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("第二次恢复成功后忽略第一次恢复延迟返回的真实 401 事件", async () => {
    const firstSession = deferred<Response>();
    const secondSession = deferred<Response>();
    const unauthorizedListener = vi.fn();
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorizedListener);
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockReturnValueOnce(firstSession.promise)
      .mockReturnValueOnce(secondSession.promise);

    render(
      <StrictMode>
        <AuthProvider>
          <SessionProbe />
        </AuthProvider>
      </StrictMode>,
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    secondSession.resolve(
      new Response(
        JSON.stringify({
          data: {
            user: {
              id: 2,
              email: "new@example.com",
              displayName: "新成员",
              role: "viewer",
              status: "active",
            },
            csrfToken: "new-csrf-token",
          },
          requestId: "session-new",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    expect(await screen.findByText("new@example.com")).toBeInTheDocument();
    expect(screen.getByText("new-csrf-token")).toBeInTheDocument();

    await act(async () => {
      firstSession.resolve(
        new Response(
          JSON.stringify({
            error: { code: "SESSION_EXPIRED", message: "旧会话已过期" },
            requestId: "session-old",
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        ),
      );
    });
    await waitFor(() => expect(unauthorizedListener).toHaveBeenCalledTimes(1));

    expect(screen.getByText("new@example.com")).toBeInTheDocument();
    expect(screen.getByText("new-csrf-token")).toBeInTheDocument();
    expect(screen.queryByText("游客")).not.toBeInTheDocument();
    window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorizedListener);
  });
});
