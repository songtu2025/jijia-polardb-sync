import type { Invitation } from "../api/types";

const INVITATION_EXPIRING_WINDOW_MS = 24 * 60 * 60 * 1000;
const TIMEZONE_SUFFIX_PATTERN = /(Z|[+-]\d{2}:\d{2})$/i;

export type InvitationStatus = "pending" | "expiring" | "expired" | "accepted" | "revoked";

export function parseApiDate(value: string): Date {
  // 后端 MySQL DATETIME 以 UTC 返回且不带后缀，浏览器端统一按 UTC 解释。
  return new Date(TIMEZONE_SUFFIX_PATTERN.test(value) ? value : `${value}Z`);
}

export function getInvitationStatus(invitation: Invitation, now = Date.now()): InvitationStatus {
  if (invitation.usedAt) return "accepted";
  if (invitation.revokedAt) return "revoked";
  const remaining = parseApiDate(invitation.expiresAt).getTime() - now;
  if (remaining <= 0) return "expired";
  if (remaining <= INVITATION_EXPIRING_WINDOW_MS) return "expiring";
  return "pending";
}
