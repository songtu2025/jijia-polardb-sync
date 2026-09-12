import type { ApiPolicy, ApiPolicyUpdateInput } from "./api/types";

export const MAX_BATCH_POLICIES = 100;

export function buildPolicyUpdate(
  policy: ApiPolicy,
  changes: Partial<Pick<ApiPolicyUpdateInput, "enabled" | "scheduleMode" | "scheduleExpr">>,
): ApiPolicyUpdateInput {
  return {
    enabled: policy.enabled,
    scheduleMode: policy.scheduleMode,
    scheduleExpr: policy.scheduleExpr,
    timezone: "Asia/Shanghai",
    windowMode: policy.supportsDateWindow ? "checkpoint" : null,
    lookbackDays: null,
    startDate: null,
    ...changes,
  };
}
