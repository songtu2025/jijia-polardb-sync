import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, AUTH_UNAUTHORIZED_EVENT } from "../api/client";
import { AuthProvider, useAuth } from "./AuthContext";

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    api: { ...original.api, logout: vi.fn(), session: vi.fn() },
  };
});

const restoredSession = {
  user: {
    id: 1,
    email: "admin@example.com",
    displayName: "管理员",
    role: "admin" as const,
    status: "active" as const,
  },
  csrfToken: "csrf-token",
};

function AuthProbe() {
  const { csrfToken, login, logout, ready, retrySession, sessionUnavailable, user } = useAuth();
  return (
    <>
      <span>{ready ? "会话就绪" : "会话加载中"}</span>
      <span>{sessionUnavailable ? "服务不可用" : (user?.email ?? "游客")}</span>
      <span>{csrfToken ?? "无 CSRF"}</span>
      <button type="button" onClick={retrySession}>
        重试会话
      </button>
      <button type="button" onClick={() => void login("new@example.com", "new-password")}>
        重新登录
      </button>
      <button type="button" onClick={() => void logout().catch(() => undefined)}>
        退出登录
      </button>
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

describe("认证上下文", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.logout).mockReset().mockResolvedValue({ loggedOut: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("初始化会话返回 401 时进入游客态", async () => {
    vi.mocked(api.session).mockRejectedValue(new ApiError("请先登录", 401, "AUTH_REQUIRED"));
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(await screen.findByText("游客")).toBeInTheDocument();
    expect(screen.getByText("会话就绪")).toBeInTheDocument();
    expect(screen.queryByText("服务不可用")).not.toBeInTheDocument();
  });

  it.each([
    ["5xx", new ApiError("网关错误", 502, "BAD_GATEWAY")],
    ["网络", new TypeError("fetch failed")],
  ])("初始化%s故障显示不可用，重试成功后恢复会话", async (_kind, error) => {
    vi.mocked(api.session).mockRejectedValueOnce(error).mockResolvedValueOnce(restoredSession);
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(await screen.findByText("服务不可用")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "重试会话" }));

    expect(await screen.findByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByText("csrf-token")).toBeInTheDocument();
    expect(api.session).toHaveBeenCalledTimes(2);
  });

  it("运行中收到任意 API 的 401 事件后清理用户和 CSRF", async () => {
    vi.mocked(api.session).mockResolvedValue(restoredSession);
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    expect(await screen.findByText("admin@example.com")).toBeInTheDocument();

    act(() => window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT)));

    expect(screen.getByText("游客")).toBeInTheDocument();
    expect(screen.getByText("无 CSRF")).toBeInTheDocument();
  });

  it.each([
    ["5xx", new ApiError("网关错误", 502, "BAD_GATEWAY")],
    ["网络", new TypeError("fetch failed")],
  ])("退出遇到%s故障时保留当前用户和 CSRF", async (_kind, error) => {
    vi.mocked(api.session).mockResolvedValue(restoredSession);
    vi.mocked(api.logout).mockRejectedValue(error);
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    expect(await screen.findByText("admin@example.com")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "退出登录" }));
    await waitFor(() => expect(api.logout).toHaveBeenCalledWith("csrf-token"));

    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByText("csrf-token")).toBeInTheDocument();
  });

  it("退出明确返回 401 时清理本地会话", async () => {
    vi.mocked(api.session).mockResolvedValue(restoredSession);
    vi.mocked(api.logout).mockRejectedValue(new ApiError("会话已失效", 401, "SESSION_EXPIRED"));
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    expect(await screen.findByText("admin@example.com")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "退出登录" }));

    expect(await screen.findByText("游客")).toBeInTheDocument();
    expect(screen.getByText("无 CSRF")).toBeInTheDocument();
  });

  it("旧会话请求延迟返回 401 时不清理重新登录后的新会话", async () => {
    const staleResponse = deferred<Response>();
    const newSession = {
      user: {
        id: 2,
        email: "new@example.com",
        displayName: "新成员",
        role: "viewer" as const,
        status: "active" as const,
      },
      csrfToken: "new-csrf-token",
    };
    vi.mocked(api.session).mockResolvedValue(restoredSession);
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const path = String(input);
      if (path === "/api/v1/jijia-accounts") return staleResponse.promise;
      if (path === "/api/v1/auth/login") {
        return Promise.resolve(
          new Response(JSON.stringify({ data: newSession, requestId: "login-new" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      throw new Error(`未预期请求：${path}`);
    });
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    expect(await screen.findByText("admin@example.com")).toBeInTheDocument();

    const staleRequest = api.listAccounts();
    await user.click(screen.getByRole("button", { name: "重新登录" }));
    expect(await screen.findByText("new@example.com")).toBeInTheDocument();

    await act(async () => {
      staleResponse.resolve(
        new Response(
          JSON.stringify({
            error: { code: "SESSION_EXPIRED", message: "旧登录状态已过期" },
            requestId: "stale-401",
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        ),
      );
      await expect(staleRequest).rejects.toMatchObject({ status: 401 });
    });

    expect(screen.getByText("new@example.com")).toBeInTheDocument();
    expect(screen.getByText("new-csrf-token")).toBeInTheDocument();
  });
});
