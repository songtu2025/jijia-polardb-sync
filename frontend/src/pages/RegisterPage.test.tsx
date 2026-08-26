import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { RegisterPage } from "./RegisterPage";

const register = vi.fn();
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: null, register }),
}));
vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    api: { ...original.api, validateInvitation: vi.fn() },
  };
});

describe("邀请注册页", () => {
  it("展示服务端确认的邮箱和角色，并拦截不一致密码", async () => {
    vi.mocked(api.validateInvitation).mockResolvedValue({
      email: "operator@example.com",
      role: "operator",
      expiresAt: "2026-08-27T00:00:00",
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/register#token=abcdefghijklmnopqrstuvwxyz"]}>
        <RegisterPage />
      </MemoryRouter>,
    );

    await screen.findByText("operator@example.com");
    expect(api.validateInvitation).toHaveBeenCalledWith("abcdefghijklmnopqrstuvwxyz");
    expect(screen.getByText("操作员")).toBeInTheDocument();
    await user.type(screen.getByLabelText("姓名"), "周晨");
    await user.type(screen.getByLabelText("密码"), "abcdefghijkl");
    await user.type(screen.getByLabelText("确认密码"), "mnopqrstuvwx");
    await user.click(screen.getByRole("button", { name: "完成注册" }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("两次输入的密码不一致"));
    expect(register).not.toHaveBeenCalled();
  });
});
