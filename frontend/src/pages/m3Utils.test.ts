import { describe, expect, it } from "vitest";

import { formatDate, getReturnNavigation } from "./m3Utils";

describe("formatDate", () => {
  it("按显式计划时区展示 UTC 时间", () => {
    expect(formatDate("2026-08-28T18:30:00Z", "Asia/Shanghai")).toBe("2026年8月29日 02:30");
    expect(formatDate("2026-08-28T18:30:00Z", "UTC")).toBe("2026年8月28日 18:30");
  });
});

describe("返回导航", () => {
  it("保留筛选、锚点和原页面状态，兼容旧返回文案", () => {
    const state = { pageIndex: 2 };
    expect(
      getReturnNavigation(
        { from: "/data/stores?keyword=test#rows", label: "返回店铺", returnState: state },
        "/raw-data",
        "返回原始数据",
        ["/data", "/raw-data"],
      ),
    ).toEqual({ path: "/data/stores?keyword=test#rows", label: "返回店铺", state });
    expect(getReturnNavigation({ from: "/jobs#worker-status" }, "/", "返回", ["/jobs"]).path).toBe(
      "/jobs#worker-status",
    );
  });

  it.each([
    "https://example.com",
    "//example.com",
    "/\\example.com",
    "/jobs-other",
    "/jobs/../members",
  ])("拒绝不属于允许模块的返回地址 %s", (from) => {
    expect(
      getReturnNavigation({ from, returnState: { draft: true } }, "/jobs", "返回任务", ["/jobs"]),
    ).toEqual({ path: "/jobs", label: "返回任务" });
  });

  it("允许概览作为精确来源，但不因此放开其他模块", () => {
    expect(getReturnNavigation({ from: "/" }, "/jobs", "返回", ["/"]).path).toBe("/");
    expect(getReturnNavigation({ from: "/members" }, "/jobs", "返回", ["/"]).path).toBe("/jobs");
  });
});
