import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { WorkerStatusPanel } from "./WorkerStatusPanel";

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    api: {
      ...original.api,
      getWorkerRuntime: vi.fn(),
    },
  };
});

describe("Worker 状态面板", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("后台刷新间隔最短为 15 秒", async () => {
    vi.useFakeTimers();
    const runtime = {
      availability: "online",
      heartbeatAt: "2026-08-27T08:00:00Z",
      currentJobId: null,
      queueDepth: 0,
      oldestQueuedAt: null,
      pollIntervalSeconds: 3,
      offlineAfterSeconds: 90,
    } as const;
    const backgroundRefresh = deferred<typeof runtime>();
    vi.mocked(api.getWorkerRuntime)
      .mockResolvedValueOnce(runtime)
      .mockReturnValueOnce(backgroundRefresh.promise);

    render(<WorkerStatusPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText("执行服务在线")).toBeInTheDocument();
    expect(api.getWorkerRuntime).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(14_999);
    });
    expect(api.getWorkerRuntime).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(api.getWorkerRuntime).toHaveBeenCalledTimes(2);
    expect(screen.getByText("执行服务在线")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "刷新状态" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "正在刷新状态" })).not.toBeInTheDocument();
    await act(async () => backgroundRefresh.resolve(runtime));
  });
  it("离线时只展示影响、关键状态和重新检查操作", async () => {
    vi.mocked(api.getWorkerRuntime).mockResolvedValue({
      availability: "offline",
      heartbeatAt: null,
      currentJobId: 31,
      queueDepth: 3,
      oldestQueuedAt: null,
      pollIntervalSeconds: 3,
      offlineAfterSeconds: 90,
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <WorkerStatusPanel />
      </MemoryRouter>,
    );
    expect(await screen.findByText("执行服务离线")).toBeInTheDocument();
    expect(screen.getByText(/任务将继续排队，服务恢复后自动执行/)).toBeInTheDocument();
    expect(screen.queryByText("离线判定阈值")).not.toBeInTheDocument();
    expect(screen.queryByText(/ECS|systemd|数据库连接/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看任务 31" })).toHaveAttribute("href", "/jobs/31");
    expect(document.getElementById("worker-status")).toBeInTheDocument();
    const calls = vi.mocked(api.getWorkerRuntime).mock.calls.length;
    await user.click(screen.getByRole("button", { name: "刷新状态" }));
    expect(api.getWorkerRuntime).toHaveBeenCalledTimes(calls + 1);
  });

  it("重新检查期间只保留一个请求并展示局部加载状态", async () => {
    const runtime = {
      availability: "online" as const,
      heartbeatAt: "2026-08-27T08:00:00Z",
      currentJobId: null,
      queueDepth: 0,
      oldestQueuedAt: null,
      pollIntervalSeconds: 30,
      offlineAfterSeconds: 90,
    };
    const refresh = deferred<typeof runtime>();
    vi.mocked(api.getWorkerRuntime)
      .mockResolvedValueOnce(runtime)
      .mockReturnValueOnce(refresh.promise);
    const user = userEvent.setup();
    render(<WorkerStatusPanel />);

    await screen.findByText("执行服务在线");
    await user.click(screen.getByRole("button", { name: "刷新状态" }));
    const checkingButton = screen.getByRole("button", { name: "正在刷新状态" });
    expect(checkingButton).toBeDisabled();
    expect(api.getWorkerRuntime).toHaveBeenCalledTimes(2);
    await user.click(checkingButton);
    expect(api.getWorkerRuntime).toHaveBeenCalledTimes(2);

    await act(async () => refresh.resolve(runtime));
    expect(screen.getByRole("button", { name: "刷新状态" })).toBeEnabled();
  });

  it("紧凑模式识别执行服务正在处理当前详情任务", async () => {
    vi.mocked(api.getWorkerRuntime).mockResolvedValue({
      availability: "busy",
      heartbeatAt: "2026-08-27T08:00:00Z",
      currentJobId: 8,
      queueDepth: 3,
      oldestQueuedAt: "2026-08-27T07:59:00Z",
      pollIntervalSeconds: 30,
      offlineAfterSeconds: 90,
    });

    render(<WorkerStatusPanel compact currentExecutionId="8" />);

    const panel = await screen.findByLabelText("任务执行服务状态");
    expect(panel).toHaveClass("worker-status--compact");
    expect(screen.getByText("执行服务正在处理本任务")).toBeInTheDocument();
    expect(screen.getByText("当前任务正在正常执行。")).toBeInTheDocument();
    expect(screen.queryByText("执行服务忙碌")).not.toBeInTheDocument();
    expect(screen.getByText(/最近心跳/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "刷新状态" })).toBeEnabled();
    expect(screen.queryByText("排队任务")).not.toBeInTheDocument();
    expect(screen.queryByText("离线判定阈值")).not.toBeInTheDocument();
  });

  it("紧凑模式明确提示执行服务正在处理其他任务", async () => {
    vi.mocked(api.getWorkerRuntime).mockResolvedValue({
      availability: "busy",
      heartbeatAt: "2026-08-27T08:00:00Z",
      currentJobId: 8,
      queueDepth: 3,
      oldestQueuedAt: "2026-08-27T07:59:00Z",
      pollIntervalSeconds: 30,
      offlineAfterSeconds: 90,
    });

    render(<WorkerStatusPanel compact currentExecutionId={9} />);

    expect(await screen.findByText("执行服务正在处理其他任务")).toBeInTheDocument();
    expect(screen.getByText("当前任务正在等待，正在处理任务 8。")).toBeInTheDocument();
    expect(screen.queryByText("执行服务正在处理本任务")).not.toBeInTheDocument();
    expect(screen.queryByText("执行服务忙碌")).not.toBeInTheDocument();
  });

  it.each([
    ["普通", false],
    ["紧凑", true],
  ] as const)("%s模式后台刷新失败时保留上次结果", async (_label, compact) => {
    vi.useFakeTimers();
    const runtime = {
      availability: "online" as const,
      heartbeatAt: "2026-08-27T08:00:00Z",
      currentJobId: null,
      queueDepth: 0,
      oldestQueuedAt: null,
      pollIntervalSeconds: 3,
      offlineAfterSeconds: 90,
    };
    vi.mocked(api.getWorkerRuntime)
      .mockResolvedValueOnce(runtime)
      .mockRejectedValueOnce(new Error("暂时失败"));

    render(<WorkerStatusPanel compact={compact} />);
    await act(async () => {
      await Promise.resolve();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });

    expect(screen.getByText("执行服务在线")).toBeInTheDocument();
    expect(screen.getByText(/状态刷新失败/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "刷新状态" })).toBeEnabled();
  });
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}
