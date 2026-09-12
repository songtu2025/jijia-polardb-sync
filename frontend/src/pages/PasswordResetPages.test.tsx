import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../api/client";
import { ForgotPasswordPage } from "./ForgotPasswordPage";
import { ResetPasswordPage } from "./ResetPasswordPage";

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    api: {
      ...original.api,
      completePasswordReset: vi.fn(),
      getPasswordPolicy: vi.fn(),
      requestPasswordReset: vi.fn(),
      validatePasswordReset: vi.fn(),
    },
  };
});

describe("密码找回", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getPasswordPolicy).mockResolvedValue({ minimumLength: 12 });
    vi.mocked(api.requestPasswordReset).mockResolvedValue({ accepted: true });
    vi.mocked(api.validatePasswordReset).mockResolvedValue({ valid: true });
    vi.mocked(api.completePasswordReset).mockResolvedValue({ passwordReset: true });
  });

  it("申请后仅显示不会泄露邮箱是否存在的统一反馈", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText("邮箱"), "member@example.com");
    await user.click(screen.getByRole("button", { name: "发送重置邮件" }));

    expect(api.requestPasswordReset).toHaveBeenCalledWith("member@example.com");
    expect(await screen.findByRole("status")).toHaveTextContent(
      "如果该邮箱已注册，重置邮件将很快送达",
    );
    expect(screen.queryByText(/member@example.com/)).not.toBeInTheDocument();
  });

  it("从账号安全进入时自动带入当前账号邮箱", () => {
    render(
      <MemoryRouter
        initialEntries={[
          { pathname: "/forgot-password", state: { email: "operator@example.com" } },
        ]}
      >
        <ForgotPasswordPage />
      </MemoryRouter>,
    );

    expect(screen.getByLabelText("邮箱")).toHaveValue("operator@example.com");
  });

  it("从 URL fragment 读取令牌，按服务端策略重置后返回登录页", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/reset-password#token=reset-token"]}>
        <Routes>
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/login" element={<p>密码已重置，请使用新密码登录</p>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText(/密码至少 12 位/)).toBeInTheDocument();
    expect(api.validatePasswordReset).toHaveBeenCalledWith("reset-token");
    await user.type(screen.getByLabelText("新密码"), "reset-pass-12");
    await user.type(screen.getByLabelText("确认新密码"), "reset-pass-12");
    await user.click(screen.getByRole("button", { name: "重置密码" }));

    expect(api.completePasswordReset).toHaveBeenCalledWith("reset-token", "reset-pass-12");
    expect(await screen.findByText("密码已重置，请使用新密码登录")).toBeInTheDocument();
  });

  it("无效令牌不显示密码表单并提供重新申请入口", async () => {
    vi.mocked(api.validatePasswordReset).mockRejectedValue(
      new ApiError("重置链接无效或已过期", 400, "PASSWORD_RESET_TOKEN_INVALID"),
    );
    render(
      <MemoryRouter initialEntries={["/reset-password#token=expired"]}>
        <ResetPasswordPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("重置链接无效或已过期");
    expect(screen.queryByLabelText("新密码")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "重新申请重置链接" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
  });
});
