import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../api/client";
import { AccountOnboardingPage } from "./AccountOnboardingPage";
import { AccountWorkspacePage } from "./AccountWorkspacePage";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    csrfToken: "csrf-token",
    user: { id: 2, email: "operator@example.com", displayName: "操作员", role: "operator" },
    logout: vi.fn(),
  }),
}));
vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    api: {
      ...original.api,
      createAccount: vi.fn(),
      getAccount: vi.fn(),
      verifyAccount: vi.fn(),
    },
  };
});

describe("积加账号接入向导", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.createAccount).mockResolvedValue({
      id: 9,
      accountCode: "acct_new",
      name: "欧洲业务账号",
      maskedAppId: "•••• 4P7M",
      credentialSource: "encrypted",
      status: "pending_verification",
      lastVerifiedAt: null,
      lastVerifyError: null,
      createdAt: "2026-08-26T02:00:00",
      updatedAt: "2026-08-26T02:00:00",
    });
    vi.mocked(api.verifyAccount).mockResolvedValue({
      id: 9,
      accountCode: "acct_new",
      name: "欧洲业务账号",
      maskedAppId: "•••• 4P7M",
      credentialSource: "encrypted",
      status: "active",
      lastVerifiedAt: "2026-08-26T02:01:00",
      lastVerifyError: null,
      createdAt: "2026-08-26T02:00:00",
      updatedAt: "2026-08-26T02:01:00",
    });
    vi.mocked(api.getAccount).mockResolvedValue({
      id: 9,
      accountCode: "acct_new",
      name: "欧洲业务账号",
      maskedAppId: "•••• 4P7M",
      credentialSource: "encrypted",
      status: "verification_failed",
      lastVerifiedAt: null,
      lastVerifyError: "积加账号验证失败",
      createdAt: "2026-08-26T02:00:00",
      updatedAt: "2026-08-26T02:01:00",
      enabledPolicyCount: 0,
      scheduledPolicyCount: 0,
      latestJobStatus: null,
      latestJobAt: null,
      latestDataAt: null,
    });
  });

  it("默认隐藏 appKey，并支持无障碍切换显隐", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AccountOnboardingPage />
      </MemoryRouter>,
    );

    const appKeyInput = screen.getByLabelText("appKey");
    const showButton = screen.getByRole("button", { name: "显示 appKey" });
    expect(appKeyInput).toHaveAttribute("type", "password");
    expect(showButton).toHaveAttribute("aria-pressed", "false");

    await user.click(showButton);

    expect(appKeyInput).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "隐藏 appKey" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(screen.getByRole("button", { name: "隐藏 appKey" }));
    expect(appKeyInput).toHaveAttribute("type", "password");
  });

  it("按三个必填项实时更新完成度，空表单不显示准备就绪", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AccountOnboardingPage />
      </MemoryRouter>,
    );

    const submitButton = screen.getByRole("button", { name: "创建并验证账号" });
    const progress = screen.getByRole("progressbar", { name: "必填项完成度" });
    expect(screen.getByRole("status")).toHaveTextContent("待填写 3 项");
    expect(screen.getByText("仅验证访问凭证")).toBeInTheDocument();
    expect(screen.queryByText(/accessToken/i)).not.toBeInTheDocument();
    expect(screen.queryByText("准备就绪")).not.toBeInTheDocument();
    expect(progress).toHaveAttribute("aria-valuetext", "0 / 3");
    expect(submitButton).toBeDisabled();

    await user.type(screen.getByLabelText("账号名称"), "欧洲业务账号");
    expect(screen.getByRole("status")).toHaveTextContent("待填写 2 项");
    expect(progress).toHaveAttribute("aria-valuetext", "1 / 3");

    await user.type(screen.getByLabelText("appId"), "app-4P7M");
    expect(screen.getByRole("status")).toHaveTextContent("待填写 1 项");
    expect(progress).toHaveAttribute("aria-valuetext", "2 / 3");

    await user.type(screen.getByLabelText("appKey"), "secret-key");
    expect(screen.getByRole("status")).toHaveTextContent("可以创建");
    expect(progress).toHaveAttribute("aria-valuetext", "3 / 3");
    expect(submitButton).toBeEnabled();
  });

  it("创建后只验证访问凭证", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/accounts/new"]}>
        <Routes>
          <Route path="/accounts/new" element={<AccountOnboardingPage />} />
          <Route path="/accounts/:accountId/policies" element={<h1>接口策略已打开</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("账号名称"), "欧洲业务账号");
    await user.type(screen.getByLabelText("appId"), "app-4P7M");
    await user.type(screen.getByLabelText("appKey"), "secret-key");
    await user.click(screen.getByRole("button", { name: "创建并验证账号" }));

    expect(await screen.findByRole("heading", { name: "接口策略已打开" })).toBeInTheDocument();
    expect(api.createAccount).toHaveBeenCalledWith(
      "欧洲业务账号",
      "app-4P7M",
      "secret-key",
      "csrf-token",
    );
    expect(api.verifyAccount).toHaveBeenCalledWith(9, "csrf-token");
    expect(vi.mocked(api.createAccount).mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(api.verifyAccount).mock.invocationCallOrder[0],
    );
  });

  it("账号已创建但验证失败时进入该账号工作台并明确提示，避免重复创建", async () => {
    vi.mocked(api.verifyAccount).mockRejectedValue(
      new ApiError("appKey 无效", 400, "ACCOUNT_VERIFY_FAILED"),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/accounts/new"]}>
        <Routes>
          <Route path="/accounts/new" element={<AccountOnboardingPage />} />
          <Route path="/accounts/:accountId" element={<AccountWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("账号名称"), "欧洲业务账号");
    await user.type(screen.getByLabelText("appId"), "app-4P7M");
    await user.type(screen.getByLabelText("appKey"), "secret-key");
    await user.click(screen.getByRole("button", { name: "创建并验证账号" }));

    expect(await screen.findByRole("heading", { name: "欧洲业务账号" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "账号“欧洲业务账号”已创建，但验证失败：appKey 无效",
    );
    expect(api.createAccount).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "创建并验证账号" })).not.toBeInTheDocument();
  });
});
