import { ApiError } from "../api/client";
import type { ChangeCatchupStatus } from "../api/types";

export const browserTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

export function formatDate(value?: string | null, timeZone = browserTimeZone): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone,
  }).format(date);
}

export function timeZoneNote(): string {
  return `时间按浏览器时区 ${browserTimeZone} 展示`;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export const detailReturnPaths = [
  "/",
  "/jobs",
  "/runs",
  "/audit",
  "/raw-data",
  "/sale-returns",
  "/data",
  "/accounts",
  "/api-catalog",
] as const;

export function getReturnNavigation(
  state: unknown,
  fallbackPath: string,
  fallbackLabel: string,
  allowedPrefixes: readonly string[],
): { path: string; label: string; state?: unknown } {
  if (!state || typeof state !== "object") {
    return { path: fallbackPath, label: fallbackLabel };
  }
  const candidate = state as {
    from?: unknown;
    backLabel?: unknown;
    label?: unknown;
    returnState?: unknown;
  };
  const from = typeof candidate.from === "string" ? candidate.from : "";
  if (!from.startsWith("/") || from.startsWith("//") || /[\\\r\n\t]/.test(from)) {
    return { path: fallbackPath, label: fallbackLabel };
  }
  const pathname = new URL(from, "https://navigation.invalid").pathname;
  const allowed = allowedPrefixes.some(
    (prefix) => pathname === prefix || (prefix !== "/" && pathname.startsWith(`${prefix}/`)),
  );
  if (!allowed) return { path: fallbackPath, label: fallbackLabel };
  const requestedLabel = candidate.backLabel ?? candidate.label;
  return {
    path: from,
    label: typeof requestedLabel === "string" && requestedLabel ? requestedLabel : fallbackLabel,
    ...(candidate.returnState === undefined ? {} : { state: candidate.returnState }),
  };
}

const statusNames: Record<string, string> = {
  queued: "排队中",
  running: "运行中",
  pause_requested: "正在暂停",
  paused: "已暂停",
  success: "已完成",
  partial_failed: "部分失败",
  failed: "失败",
  cancelled: "已取消",
  stopped: "已停止",
  blocked: "已阻塞",
  pending: "待开始",
  complete: "变更追赶完成",
};

export function statusLabel(status: string): string {
  return statusNames[status] ?? status;
}

const changeCatchupNames: Record<ChangeCatchupStatus, string> = {
  pending: "待开始",
  running: "变更追赶进行中",
  complete: "变更追赶完成",
  incremental_ready: "增量同步已追平",
  blocked: "等待恢复",
  failed: "追赶失败",
};

export function changeCatchupLabel(status: ChangeCatchupStatus): string {
  return changeCatchupNames[status];
}
