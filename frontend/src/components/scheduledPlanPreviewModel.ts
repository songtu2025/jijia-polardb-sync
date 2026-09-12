import type { ScheduledPlan, ScheduledPlanWindowPreview } from "../api/types";

const phaseLabels: Record<ScheduledPlanWindowPreview["phase"], string> = {
  history_backfill: "历史回填",
  update_incremental: "增量同步",
  no_date_window: "无日期窗口",
};

export function scheduledPlanPhaseText(preview: ScheduledPlanWindowPreview): string {
  return phaseLabels[preview.phase];
}

export function nextWindowRangeText(preview: ScheduledPlanWindowPreview): string {
  if (preview.phase === "no_date_window") {
    return "当前可用数据";
  }
  if (preview.predictionStatus === "caught_up") return "历史数据已追平，等待新数据";
  if (preview.predictionStatus === "unavailable") return "暂无法预测数据范围";
  if (preview.predictionStatus === "dynamic") {
    return preview.nextStartDate
      ? `从 ${preview.nextStartDate} 开始，结束日期将在执行前确定`
      : "数据范围将在执行前确定";
  }
  if (preview.nextStartDate && preview.nextEndDate) {
    return preview.nextStartDate === preview.nextEndDate
      ? `${preview.nextStartDate}（全天）`
      : `${preview.nextStartDate} 至 ${preview.nextEndDate}`;
  }
  return preview.nextStartDate ? `从 ${preview.nextStartDate} 开始` : "暂无法预测数据范围";
}

export function nextWindowBasisText(preview: ScheduledPlanWindowPreview): string {
  if (preview.phase === "no_date_window") return "不限定日期范围";
  return preview.basisLabel;
}

export function syncProgressText(preview: ScheduledPlanWindowPreview): [string, string] {
  if (preview.phase === "no_date_window") {
    return ["不适用", "每次执行获取当前数据"];
  }
  const completeText = preview.completeThrough
    ? `已同步至 ${preview.completeThrough}`
    : "尚无同步水位";
  if (preview.nextStartDate) return [completeText, `下次从 ${preview.nextStartDate}`];
  if (preview.predictionStatus === "caught_up") return [completeText, "当前已追平，等待新数据"];
  return [completeText, "下一起点暂不可用"];
}

export function blockedResumeText(plan: ScheduledPlan): string | null {
  if (plan.status !== "blocked") return null;
  return plan.nextWindowPreview.nextStartDate
    ? `活动任务结束后从 ${plan.nextWindowPreview.nextStartDate} 继续，不会跳过数据。`
    : "活动任务结束后继续同步，不会跳过数据。";
}

export function scheduledPlanNextStartText(preview: ScheduledPlanWindowPreview): string {
  if (preview.phase === "no_date_window") return "每次读取当前可用数据";
  if (preview.nextStartDate) return preview.nextStartDate;
  if (preview.predictionStatus === "caught_up") return "等待新数据";
  return "暂不可用";
}
