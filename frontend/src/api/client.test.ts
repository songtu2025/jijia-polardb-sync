import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./client";

describe("API 客户端", () => {
  afterEach(() => vi.restoreAllMocks());

  it("登录请求携带 Cookie 凭据", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ data: { user: {}, csrfToken: "csrf" }, requestId: "r1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await api.login("admin@example.com", "password");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({ credentials: "include", method: "POST" }),
    );
  });

  it("成员写请求携带 CSRF 头", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ data: {}, requestId: "r2" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await api.updateUser(8, { role: "viewer" }, "csrf-token");

    const request = fetchMock.mock.calls[0][1];
    expect(new Headers(request?.headers).get("X-CSRF-Token")).toBe("csrf-token");
  });
});
