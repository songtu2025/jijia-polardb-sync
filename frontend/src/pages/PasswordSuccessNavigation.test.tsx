import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";

import { api } from "../api/client";
import { App } from "../App";
import { AuthProvider } from "../auth/AuthContext";
import { UiProvider } from "../components/UiProvider";

const signedInUser = {
  id: 1,
  email: "admin@example.com",
  displayName: "管理员",
  role: "admin" as const,
  status: "active" as const,
};

function CurrentLocation() {
  const location = useLocation();
  return (
    <div data-testid="location">
      {JSON.stringify({ pathname: location.pathname, state: location.state })}
    </div>
  );
}

function renderAuthenticatedApp(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <UiProvider>
        <AuthProvider>
          <App />
          <CurrentLocation />
        </AuthProvider>
      </UiProvider>
    </MemoryRouter>,
  );
}

describe("密码成功后的登录反馈", () => {
  beforeEach(() => {
    vi.spyOn(api, "session").mockResolvedValue({ user: signedInUser, csrfToken: "csrf-token" });
    vi.spyOn(api, "getPasswordPolicy").mockResolvedValue({ minimumLength: 12 });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("真实 AuthProvider 在修改密码后保留成功反馈", async () => {
    vi.spyOn(api, "changePassword").mockResolvedValue({ passwordChanged: true });
    const user = userEvent.setup();
    renderAuthenticatedApp("/account/security");

    await user.type(await screen.findByLabelText("当前密码"), "current-password");
    await user.type(screen.getByLabelText("新密码"), "new-password-12");
    await user.type(screen.getByLabelText("确认新密码"), "new-password-12");
    await user.click(screen.getByRole("button", { name: "修改密码" }));

    await expect
      .poll(() => screen.getByTestId("location").textContent)
      .toBe(JSON.stringify({ pathname: "/login", state: { passwordChanged: true } }));
    expect(screen.getByRole("status")).toHaveTextContent("密码已修改，请使用新密码登录");
  });

  it("已登录用户重置密码后同样保留成功反馈", async () => {
    vi.spyOn(api, "validatePasswordReset").mockResolvedValue({ valid: true });
    vi.spyOn(api, "completePasswordReset").mockResolvedValue({ passwordReset: true });
    const user = userEvent.setup();
    renderAuthenticatedApp("/reset-password#token=reset-token");

    await user.type(await screen.findByLabelText("新密码"), "reset-pass-12");
    await user.type(screen.getByLabelText("确认新密码"), "reset-pass-12");
    await user.click(screen.getByRole("button", { name: "重置密码" }));

    await expect
      .poll(() => screen.getByTestId("location").textContent)
      .toBe(JSON.stringify({ pathname: "/login", state: { passwordReset: true } }));
    expect(screen.getByRole("status")).toHaveTextContent("密码已重置，请使用新密码登录");
  });
});
