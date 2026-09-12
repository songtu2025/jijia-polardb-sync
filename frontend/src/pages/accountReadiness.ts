import type { JijiaAccount, JijiaAccountStatus, SyncJobStatus } from "../api/types";

type AccountPrimaryAction =
  | "verify"
  | "reverify"
  | "configure_scope"
  | "start_sync"
  | "view_job"
  | "view_data"
  | "view_status"
  | "none";

export interface AccountReadiness {
  connectionReady: boolean;
  description: string;
  label: string;
  primaryAction: AccountPrimaryAction;
  primaryActionLabel: string;
  primaryActionTarget: string | null;
  scopeReady: boolean;
  tone: "ready" | "attention" | "progress" | "inactive";
}

export const accountStatusNames: Record<JijiaAccountStatus, string> = {
  pending_verification: "待验证",
  active: "连接正常",
  verification_failed: "验证失败",
  inactive: "已停用",
};

const activeJobStatuses = new Set<SyncJobStatus>([
  "queued",
  "running",
  "pause_requested",
  "paused",
]);
const failedJobStatuses = new Set<SyncJobStatus>(["partial_failed", "failed"]);

export function formatAccountDate(value: string | null | undefined, fallback = "暂无") {
  if (!value) return fallback;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function getAccountReadiness(account: JijiaAccount, canEdit: boolean): AccountReadiness {
  const connectionReady = account.status === "active";
  const scopeReady = (account.enabledPolicyCount ?? 0) > 0;
  const jobActive = account.latestJobStatus
    ? activeJobStatuses.has(account.latestJobStatus)
    : false;
  const jobFailed = account.latestJobStatus
    ? failedJobStatuses.has(account.latestJobStatus)
    : false;

  if (account.status === "inactive") {
    return {
      connectionReady,
      description: "账号已停用，不会再生成新的同步任务。",
      label: "已停用",
      primaryAction: canEdit ? "none" : "view_status",
      primaryActionLabel: canEdit ? "账号已停用" : "查看账号",
      primaryActionTarget: canEdit ? null : `/accounts/${account.id}`,
      scopeReady,
      tone: "inactive",
    };
  }

  if (!canEdit) {
    return {
      connectionReady,
      description:
        account.status !== "active"
          ? (account.lastVerifyError ?? "账号连接尚未验证。")
          : !scopeReady
            ? "尚未配置同步范围。"
            : jobFailed
              ? "最近一次同步未成功完成。"
              : "账号连接与同步范围可用。",
      label:
        account.status !== "active"
          ? "连接需处理"
          : !scopeReady
            ? "待配置"
            : jobFailed
              ? "同步异常"
              : "可同步",
      primaryAction: "view_status",
      primaryActionLabel: "查看账号",
      primaryActionTarget: `/accounts/${account.id}`,
      scopeReady,
      tone: account.status !== "active" || !scopeReady || jobFailed ? "attention" : "ready",
    };
  }

  if (account.status === "pending_verification") {
    return {
      connectionReady,
      description: "验证凭证后才能配置同步范围。",
      label: "待验证",
      primaryAction: "verify",
      primaryActionLabel: "验证连接",
      primaryActionTarget: null,
      scopeReady,
      tone: "attention",
    };
  }

  if (account.status === "verification_failed") {
    return {
      connectionReady,
      description: account.lastVerifyError ?? "最近一次连接验证失败。",
      label: "连接异常",
      primaryAction: "reverify",
      primaryActionLabel: "重新验证",
      primaryActionTarget: null,
      scopeReady,
      tone: "attention",
    };
  }

  if (!scopeReady) {
    return {
      connectionReady,
      description: "选择需要同步的数据接口，并启用同步接口。",
      label: "待配置",
      primaryAction: "configure_scope",
      primaryActionLabel: "配置同步范围",
      primaryActionTarget: `/accounts/${account.id}/policies`,
      scopeReady,
      tone: "attention",
    };
  }

  if (jobActive) {
    return {
      connectionReady,
      description: "同步任务正在执行，可以查看实时进度。",
      label: "同步中",
      primaryAction: "view_job",
      primaryActionLabel: "查看任务进度",
      primaryActionTarget: `/jobs?account=${account.id}`,
      scopeReady,
      tone: "progress",
    };
  }

  if (jobFailed) {
    return {
      connectionReady,
      description: "最近一次同步未成功完成，需要查看失败原因。",
      label: "同步异常",
      primaryAction: "view_job",
      primaryActionLabel: "处理同步异常",
      primaryActionTarget: `/jobs?account=${account.id}`,
      scopeReady,
      tone: "attention",
    };
  }

  if (account.latestDataAt) {
    return {
      connectionReady,
      description: `最近数据更新于 ${formatAccountDate(account.latestDataAt)}。`,
      label: "正常运行",
      primaryAction: "view_data",
      primaryActionLabel: "查看最新数据",
      primaryActionTarget: `/raw-data?jijiaAccountId=${account.id}`,
      scopeReady,
      tone: "ready",
    };
  }

  if (account.latestJobAt) {
    return {
      connectionReady,
      description: "已有执行记录，但尚无可验证的数据。",
      label: "等待数据",
      primaryAction: "view_job",
      primaryActionLabel: "查看最近任务",
      primaryActionTarget: `/jobs?account=${account.id}`,
      scopeReady,
      tone: "progress",
    };
  }

  return {
    connectionReady,
    description: "连接和同步范围均已就绪，可以发起首次同步。",
    label: "可开始同步",
    primaryAction: "start_sync",
    primaryActionLabel: "发起首次同步",
    primaryActionTarget: `/jobs/new?accountId=${account.id}`,
    scopeReady,
    tone: "progress",
  };
}
