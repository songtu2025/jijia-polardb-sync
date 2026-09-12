import { Input, Select } from "antd";
import type { InputRef } from "antd";
import type { Ref } from "react";
import type { ScheduleMode } from "../api/types";

export function PolicyScheduleFields({
  mode,
  expression,
  disabled,
  bulk = false,
  expressionError,
  expressionRef,
  onModeChange,
  onExpressionChange,
}: {
  mode: ScheduleMode;
  expression: string;
  disabled: boolean;
  bulk?: boolean;
  expressionError?: string;
  expressionRef?: Ref<InputRef>;
  onModeChange: (mode: ScheduleMode) => void;
  onExpressionChange: (expression: string) => void;
}) {
  const fieldKey = bulk ? "bulk-schedule" : "schedule";
  const expressionId = `${fieldKey}-expression`;
  const hintId = `${fieldKey}-hint`;
  const errorId = `${fieldKey}-error`;

  return (
    <>
      <label className="job-create-field">
        {bulk ? "执行周期" : "同步方式"}
        <Select
          aria-label={bulk ? "批量运行方式" : "同步方式"}
          disabled={disabled}
          options={[
            { label: "每日", value: "daily" },
            { label: "高级：Cron", value: "cron" },
          ]}
          value={mode}
          virtual={false}
          onChange={(value) => {
            onModeChange(value);
            onExpressionChange("");
          }}
        />
      </label>
      {mode !== "manual_only" ? (
        <>
          <label className="job-create-field" htmlFor={expressionId}>
            {mode === "daily" ? "执行时间" : "Cron 表达式"}
            <Input
              id={expressionId}
              ref={expressionRef}
              aria-label={
                bulk
                  ? mode === "daily"
                    ? "批量每日执行时间"
                    : "批量 Cron 表达式"
                  : mode === "daily"
                    ? "执行时间"
                    : "Cron 表达式"
              }
              aria-describedby={`${hintId}${expressionError ? ` ${errorId}` : ""}`}
              aria-invalid={Boolean(expressionError)}
              type={mode === "daily" ? "time" : "text"}
              required
              disabled={disabled}
              value={expression}
              onChange={(event) => onExpressionChange(event.target.value)}
            />
            {expressionError ? (
              <small className="field-error" id={errorId} role="alert">
                {expressionError}
              </small>
            ) : null}
          </label>
          <small className="field-hint" id={hintId}>
            北京时间 UTC+08:00
            {mode === "cron"
              ? "；五段表达式：分 时 日 月 星期，例如 0 */6 * * *，最短执行间隔为 15 分钟。保存时由服务端校验。"
              : ""}
          </small>
        </>
      ) : null}
    </>
  );
}
