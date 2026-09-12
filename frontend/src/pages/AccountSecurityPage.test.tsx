import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../api/client";
import { AccountSecurityPage } from "./AccountSecurityPage";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    csrfToken: "csrf-token",
    user: {
      id: 2,
      email: "operator@example.com",
      displayName: "操作员",
      role: "operator",
      status: "enabled",
    },
  }),
}));
vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    api: {
      ...original.api,
      changePassword: vi.fn(),
      getPasswordPolicy: vi.fn(),
    },
  };
});

describe("账号安全", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getPasswordPolicy).mockResolvedValue({ minimumLength: 14 });
    vi.mocked(api.changePassword).mockResolvedValue({ passwordChanged: true });
  });

  it("按服务端策略校验并修改自己的密码，成功后回到登录页", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/account/security"]}>
        <Routes>
          <Route path="/account/security" element={<AccountSecurityPage />} />
          <Route path="/login" element={<p>密码已修改，请使用新密码登录</p>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(
      await screen.findByText("密码至少 14 位；请勿使用与其他系统相同的密码。"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "忘记当前密码？" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
    expect(screen.queryByText("修改当前账号的登录密码。")).not.toBeInTheDocument();
    expect(screen.queryByText("修改成功后，所有设备需要重新登录。")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("当前密码"), "current-password");
    await user.type(screen.getByLabelText("新密码"), "short");
    await user.type(screen.getByLabelText("确认新密码"), "short");
    await user.click(screen.getByRole("button", { name: "修改密码" }));
    expect(await screen.findByText("密码至少需要 14 位")).toBeInTheDocument();
    expect(api.changePassword).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("新密码"));
    await user.clear(screen.getByLabelText("确认新密码"));
    await user.type(screen.getByLabelText("新密码"), "new-password-14");
    await user.type(screen.getByLabelText("确认新密码"), "new-password-14");
    await user.click(screen.getByRole("button", { name: "修改密码" }));

    expect(api.changePassword).toHaveBeenCalledWith(
      "current-password",
      "new-password-14",
      "csrf-token",
    );
    expect(await screen.findByText("密码已修改，请使用新密码登录")).toBeInTheDocument();
  });

  it("当前密码错误时保留表单并允许重试", async () => {
    vi.mocked(api.changePassword).mockRejectedValue(
      new ApiError("当前密码不正确", 400, "CURRENT_PASSWORD_INVALID"),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AccountSecurityPage />
      </MemoryRouter>,
    );
    await screen.findByText(/密码至少 14 位/);
    await user.type(screen.getByLabelText("当前密码"), "wrong-password");
    await user.type(screen.getByLabelText("新密码"), "new-password-14");
    await user.type(screen.getByLabelText("确认新密码"), "new-password-14");
    await user.click(screen.getByRole("button", { name: "修改密码" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("当前密码不正确");
    await waitFor(() => expect(screen.getByLabelText("当前密码")).toBeEnabled());
    expect(screen.getByLabelText("当前密码")).toHaveValue("wrong-password");
  });

  it("密码要求加载失败时保留说明和禁用表单，并可重新加载", async () => {
    vi.mocked(api.getPasswordPolicy)
      .mockRejectedValueOnce(new Error("network error"))
      .mockResolvedValueOnce({ minimumLength: 14 });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AccountSecurityPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("密码服务暂不可用")).toBeInTheDocument();
    expect(screen.getByLabelText("当前密码")).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "重新加载" }));

    expect(await screen.findByText(/密码至少 14 位/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("当前密码")).toBeEnabled());
  });
});
