import { Descriptions } from "antd";

import type { ScheduledPlanWindowPreview } from "../api/types";
import { scheduledPlanNextStartText, scheduledPlanPhaseText } from "./scheduledPlanPreviewModel";

export function ScheduledPlanRangeRules({ preview }: { preview: ScheduledPlanWindowPreview }) {
  return (
    <section className="job-create-section" aria-labelledby="scheduled-plan-range-rules-heading">
      <div className="job-create-section-heading">
        <div>
          <h2 id="scheduled-plan-range-rules-heading">数据范围规则</h2>
          <p>{preview.basisLabel}</p>
        </div>
      </div>
      <Descriptions
        column={{ xs: 1, sm: 2, lg: 3 }}
        items={[
          { key: "phase", label: "同步阶段", children: scheduledPlanPhaseText(preview) },
          {
            key: "complete-through",
            label: "已同步至",
            children:
              preview.phase === "no_date_window"
                ? "不适用"
                : (preview.completeThrough ?? "尚无同步水位"),
          },
          {
            key: "next-start",
            label: "下一起点",
            children: scheduledPlanNextStartText(preview),
          },
          {
            key: "lag-days",
            label: "数据延迟",
            children:
              preview.phase === "no_date_window" || preview.lagDays == null
                ? "不适用"
                : `${preview.lagDays} 天`,
          },
          {
            key: "max-window-days",
            label: "单窗口上限",
            children: preview.maxWindowDays == null ? "不适用" : `${preview.maxWindowDays} 天`,
          },
          {
            key: "advance-condition",
            label: "推进条件",
            children: preview.advancesOnSuccess ? "仅当前窗口成功后推进同步水位" : "不推进日期水位",
          },
        ]}
        size="small"
      />
    </section>
  );
}
