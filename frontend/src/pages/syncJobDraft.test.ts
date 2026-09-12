import { describe, expect, it } from "vitest";
import { buildPolicyRecovery, readSyncJobDraft } from "./syncJobDraft";

const draft = {
  accountId: "8",
  apiCode: "sale_return_order_page",
  rangeMode: "custom" as const,
  startDate: "2026-01-01",
  endDate: "2026-01-02",
  marketScopeMode: "selected" as const,
  selectedMarketIds: [101],
};

describe("任务草稿恢复", () => {
  it("URL目标和草稿不一致时丢弃草稿", () => {
    expect(
      readSyncJobDraft({ syncJobDraft: draft }, new URLSearchParams("accountId=9")),
    ).toBeUndefined();
    expect(
      readSyncJobDraft({ syncJobDraft: draft }, new URLSearchParams("apiCode=other")),
    ).toBeUndefined();
    expect(readSyncJobDraft({ syncJobDraft: draft }, new URLSearchParams("accountId=8"))).toEqual(
      draft,
    );
  });
  it("接口支线携带完整草稿和原始来源，不复用预览", () => {
    const recovery = buildPolicyRecovery(draft, {
      path: "/jobs?account=8",
      label: "返回任务列表",
      state: { page: 2 },
    });
    expect(recovery.policyTarget).toBe("/accounts/8/policies?apiCode=sale_return_order_page");
    expect(recovery.policyNavigationState.returnState).toEqual({
      from: "/jobs?account=8",
      backLabel: "返回任务列表",
      returnState: { page: 2 },
      syncJobDraft: draft,
    });
  });
});
