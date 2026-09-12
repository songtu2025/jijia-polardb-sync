import { describe, expect, it } from "vitest";

import type { JijiaAccount } from "../api/types";
import { getAccountReadiness } from "./accountReadiness";

const account: JijiaAccount = {
  id: 8,
  accountCode: "acct_demo",
  name: "测试账号",
  maskedAppId: "•••• demo",
  credentialSource: "encrypted",
  status: "active",
  lastVerifiedAt: "2026-08-26T02:42:00",
  lastVerifyError: null,
  createdAt: "2026-08-26T02:00:00",
  updatedAt: "2026-08-26T02:42:00",
  enabledPolicyCount: 0,
  scheduledPolicyCount: 0,
  latestJobStatus: null,
  latestJobAt: null,
  latestDataAt: null,
};

describe("账号接入就绪状态", () => {
  it("按连接、范围、任务和数据顺序生成唯一主要操作", () => {
    expect(
      getAccountReadiness({ ...account, status: "pending_verification" }, true).primaryAction,
    ).toBe("verify");
    expect(getAccountReadiness(account, true).primaryAction).toBe("configure_scope");
    const ready = getAccountReadiness({ ...account, enabledPolicyCount: 2 }, true);
    expect(ready.primaryAction).toBe("start_sync");
    expect(ready.primaryActionTarget).toBe("/jobs/new?accountId=8");
    expect(
      getAccountReadiness(
        {
          ...account,
          enabledPolicyCount: 2,
          latestJobStatus: "failed",
        },
        true,
      ).primaryAction,
    ).toBe("view_job");
    expect(
      getAccountReadiness(
        {
          ...account,
          enabledPolicyCount: 2,
          latestJobStatus: "success",
          latestDataAt: "2026-08-27T03:00:00",
        },
        true,
      ).primaryAction,
    ).toBe("view_data");
  });

  it("Viewer 始终只得到查看状态操作", () => {
    const readiness = getAccountReadiness(
      {
        ...account,
        status: "verification_failed",
        lastVerifyError: "连接失败",
      },
      false,
    );

    expect(readiness.primaryAction).toBe("view_status");
    expect(readiness.primaryActionTarget).toBe("/accounts/8");
  });
});
