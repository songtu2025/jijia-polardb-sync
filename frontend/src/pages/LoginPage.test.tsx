import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { LoginPage } from "./LoginPage";

const login = vi.fn();
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: null, login }),
}));

describe("登录页", () => {
  it("提交邮箱和密码并进入管理员成员页", async () => {
    login.mockResolvedValue({ role: "admin" });
    const user = userEvent.setup();
    render(<MemoryRouter><LoginPage /></MemoryRouter>);

    await user.type(screen.getByLabelText("邮箱"), "admin@example.com");
    await user.type(screen.getByLabelText("密码"), "safe-password");
    await user.click(screen.getByRole("button", { name: "登录" }));

    expect(login).toHaveBeenCalledWith("admin@example.com", "safe-password");
  });
});
