import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { MembersPage } from "./MembersPage";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    csrfToken: "csrf-token",
    user: { id: 1, email: "admin@example.com", displayName: "管理员", role: "admin" },
    logout: vi.fn(),
  }),
}));
vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    api: {
      ...original.api,
      listUsers: vi.fn(),
      listInvitations: vi.fn(),
      createInvitation: vi.fn(),
    },
  };
});

describe("成员与权限页", () => {
  beforeEach(() => {
    vi.mocked(api.listUsers).mockResolvedValue([
      { id: 1, email: "admin@example.com", displayName: "管理员", role: "admin", status: "active" },
    ]);
    vi.mocked(api.listInvitations).mockResolvedValue([]);
    vi.mocked(api.createInvitation).mockResolvedValue({
      id: 2,
      email: "viewer@example.com",
      role: "viewer",
      expiresAt: "2026-08-27T00:00:00",
      usedAt: null,
      revokedAt: null,
    });
  });

  it("管理员可按固定角色发送邀请", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><MembersPage /></MemoryRouter>);
    expect((await screen.findAllByText("admin@example.com")).length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /邀请成员/ }));
    await user.type(screen.getByLabelText("邮箱"), "viewer@example.com");
    await user.selectOptions(screen.getByLabelText("角色"), "viewer");
    await user.click(screen.getByRole("button", { name: "发送邀请" }));

    expect(api.createInvitation).toHaveBeenCalledWith(
      "viewer@example.com",
      "viewer",
      "csrf-token",
    );
  });
});
