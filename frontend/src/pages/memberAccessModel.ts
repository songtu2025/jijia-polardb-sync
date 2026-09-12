import type { Invitation, User, UserRole, UserStatus } from "../api/types";
import { getInvitationStatus, parseApiDate, type InvitationStatus } from "./memberInvitationStatus";

export const roleNames: Record<UserRole, string> = {
  admin: "管理员",
  operator: "操作员",
  viewer: "只读成员",
};

export const statusNames: Record<UserStatus, string> = {
  invited: "待接受",
  active: "已启用",
  disabled: "已停用",
};

export const permissions: Record<UserRole, string[]> = {
  admin: ["查看接口、任务与日志", "管理成员与角色", "发送、重发和撤销邀请"],
  operator: ["查看接口、任务与日志", "执行获授权的日常操作"],
  viewer: ["查看获授权的只读数据"],
};

export const invitationStatusNames: Record<InvitationStatus, string> = {
  pending: "待接受",
  expiring: "即将过期",
  expired: "已过期",
  accepted: "已接受",
  revoked: "已撤销",
};

export type MembersView = "members" | "invitations";

export type PendingConfirmation =
  | { kind: "disable"; user: User }
  | { kind: "demote"; role: UserRole; user: User }
  | { invitation: Invitation; kind: "revoke" };

export type InvitationRow = {
  invitation: Invitation;
  status: InvitationStatus;
};

type MemberDirectoryInput = {
  invitations: Invitation[];
  search: string;
  selectedId: number | null;
  selectedInvitationId: number | null;
  users: User[];
};

export function formatDate(value?: string | null) {
  if (!value) return "尚未登录";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parseApiDate(value));
}

export function invitationTimeline(invitation: Invitation, status: InvitationStatus): string {
  if (status === "accepted") return `已于 ${formatDate(invitation.usedAt)} 接受`;
  if (status === "revoked") return `已于 ${formatDate(invitation.revokedAt)} 撤销`;
  if (status === "expired") return `已于 ${formatDate(invitation.expiresAt)} 过期`;
  if (status === "expiring") return `将在 ${formatDate(invitation.expiresAt)} 过期`;
  return `有效期至 ${formatDate(invitation.expiresAt)}`;
}

export function canResendInvitation(status: InvitationStatus): boolean {
  return status === "pending" || status === "expiring" || status === "expired";
}

export function canRevokeInvitation(status: InvitationStatus): boolean {
  return status === "pending" || status === "expiring";
}

export function deriveMemberDirectory({
  invitations,
  search,
  selectedId,
  selectedInvitationId,
  users,
}: MemberDirectoryInput) {
  const searchTerm = search.trim().toLowerCase();
  const members = users.filter((user) => user.status !== "invited");
  const filteredUsers = members.filter(
    (user) =>
      !searchTerm ||
      user.email.toLowerCase().includes(searchTerm) ||
      (user.displayName ?? "").toLowerCase().includes(searchTerm),
  );
  const invitationRows = invitations.map((invitation) => ({
    invitation,
    status: getInvitationStatus(invitation),
  }));
  const filteredInvitations = invitationRows.filter(
    ({ invitation }) => !searchTerm || invitation.email.toLowerCase().includes(searchTerm),
  );
  const selectedUser =
    filteredUsers.find((user) => user.id === selectedId) ?? filteredUsers[0] ?? null;
  const selectedInvitationRow =
    filteredInvitations.find(({ invitation }) => invitation.id === selectedInvitationId) ??
    filteredInvitations[0] ??
    null;
  const activeAdminCount = users.filter(
    (user) => user.role === "admin" && user.status === "active",
  ).length;
  const protectsLastAdmin = Boolean(
    selectedUser?.role === "admin" && selectedUser.status === "active" && activeAdminCount <= 1,
  );

  return {
    filteredInvitations,
    filteredUsers,
    members,
    protectsLastAdmin,
    selectedInvitationRow,
    selectedUser,
  };
}
