import { Alert, Button, Checkbox, Input, Radio, Select, Spin } from "antd";
import { Link } from "react-router-dom";

import type { ApiPolicy, JijiaAccount, SyncJobMarketOption } from "../api/types";

export type MarketScopeMode = "all" | "selected";

export interface SyncJobFieldErrors {
  accountId?: string;
  apiCode?: string;
  startDate?: string;
  endDate?: string;
  marketIds?: string;
}

interface SyncJobTargetSectionProps {
  accountId: string;
  accountPrefillReason: string;
  accountSetupState: "loading" | "missing" | "needs_verification" | "ready";
  activeAccounts: JijiaAccount[];
  allAccounts: JijiaAccount[];
  apiCode: string;
  apiPrefillReason: string;
  busy: boolean;
  contextAccountUnavailable: boolean;
  contextApiUnavailable: boolean;
  fieldErrors: SyncJobFieldErrors;
  loadingOptions: boolean;
  loadingPolicies: boolean;
  optionsLoadError: string;
  policies: ApiPolicy[];
  policyLoadError: string;
  policyNavigationState: unknown;
  policyTarget: string;
  onAccountChange: (accountId: string) => void;
  onApiChange: (apiCode: string) => void;
  onRetryOptions: () => void;
  onRetryPolicies: () => void;
}

export function SyncJobTargetSection({
  accountId,
  accountPrefillReason,
  accountSetupState,
  activeAccounts,
  allAccounts,
  apiCode,
  apiPrefillReason,
  busy,
  contextAccountUnavailable,
  contextApiUnavailable,
  fieldErrors,
  loadingOptions,
  loadingPolicies,
  optionsLoadError,
  policies,
  policyLoadError,
  policyNavigationState,
  policyTarget,
  onAccountChange,
  onApiChange,
  onRetryOptions,
  onRetryPolicies,
}: SyncJobTargetSectionProps) {
  return (
    <section className="job-create-section" aria-labelledby="sync-target-heading">
      <div className="job-create-section-heading">
        <div>
          <h2 id="sync-target-heading">同步目标</h2>
        </div>
      </div>

      <div className="job-create-field">
        <label htmlFor="sync-account-id">积加账号</label>
        <Select
          aria-describedby={
            fieldErrors.accountId
              ? "sync-account-status sync-account-id-error"
              : "sync-account-status"
          }
          aria-label="积加账号"
          aria-invalid={Boolean(fieldErrors.accountId)}
          disabled={
            busy || loadingOptions || Boolean(optionsLoadError) || activeAccounts.length === 0
          }
          id="sync-account-id"
          loading={loadingOptions}
          options={[
            ...activeAccounts.map((account) => ({
              label: account.name,
              value: String(account.id),
            })),
            ...(contextAccountUnavailable
              ? [
                  {
                    label: `${allAccounts.find((account) => String(account.id) === accountId)?.name ?? `账号 ${accountId}`}（不可用）`,
                    value: accountId,
                    disabled: true,
                  },
                ]
              : []),
          ]}
          placeholder={loadingOptions ? "正在加载可用账号…" : "请选择可用账号"}
          value={accountId || undefined}
          virtual={false}
          onChange={onAccountChange}
        />
        <small className="field-hint" id="sync-account-status">
          {loadingOptions
            ? "加载中"
            : optionsLoadError
              ? "加载失败"
              : accountPrefillReason ||
                (activeAccounts.length > 1 ? "请选择本次同步目标" : "已自动选择")}
        </small>
        {fieldErrors.accountId ? (
          <small className="field-error" id="sync-account-id-error" role="alert">
            {fieldErrors.accountId}
          </small>
        ) : null}
      </div>

      <div className="job-create-field">
        <label htmlFor="sync-api-code">已启用接口</label>
        <Select
          aria-describedby={
            fieldErrors.apiCode ? "sync-api-status sync-api-code-error" : "sync-api-status"
          }
          aria-label="已启用接口"
          aria-invalid={Boolean(fieldErrors.apiCode)}
          disabled={
            busy ||
            loadingOptions ||
            Boolean(optionsLoadError) ||
            !accountId ||
            loadingPolicies ||
            Boolean(policyLoadError)
          }
          id="sync-api-code"
          loading={loadingPolicies}
          options={[
            ...policies.map((policy) => ({
              label: `${policy.name} · ${policy.apiCode}`,
              value: policy.apiCode,
            })),
            ...(contextApiUnavailable
              ? [{ label: `${apiCode}（不可用）`, value: apiCode, disabled: true }]
              : []),
          ]}
          placeholder={
            loadingPolicies
              ? "正在加载已启用接口…"
              : accountId
                ? "请选择已启用接口"
                : "请先选择账号"
          }
          value={apiCode || undefined}
          virtual={false}
          onChange={onApiChange}
        />
        <small className="field-hint" id="sync-api-status">
          {loadingPolicies
            ? "加载中"
            : policyLoadError
              ? "加载失败"
              : apiPrefillReason ||
                (!accountId
                  ? "先选择账号"
                  : policies.length > 1
                    ? "请选择本次同步目标"
                    : "已自动选择")}
        </small>
        {fieldErrors.apiCode ? (
          <small className="field-error" id="sync-api-code-error" role="alert">
            {fieldErrors.apiCode}
          </small>
        ) : null}
      </div>

      {optionsLoadError ? (
        <Alert
          action={
            <Button disabled={loadingOptions} onClick={onRetryOptions}>
              重新加载账号和接口
            </Button>
          }
          aria-label="账号和接口加载失败"
          className="setup-guidance"
          description="未能确认账号和接口目录，请重新加载后再配置任务。"
          showIcon
          title={optionsLoadError}
          type="error"
        />
      ) : accountSetupState === "missing" || accountSetupState === "needs_verification" ? (
        <RecoveryGuidance state={accountSetupState} />
      ) : null}
      {contextAccountUnavailable ? (
        <section className="setup-guidance" aria-label="账号上下文不可用">
          <strong>链接中的账号当前不可用</strong>
          <p>请选择其他可用账号，或到账号列表检查验证和启用状态。</p>
          <Link className="action-link action-link--neutral" to="/accounts">
            检查账号状态
          </Link>
        </section>
      ) : null}
      {policyLoadError && accountId ? (
        <Alert
          action={
            <Button disabled={loadingPolicies} onClick={onRetryPolicies}>
              重新加载接口策略
            </Button>
          }
          aria-label="接口策略加载失败"
          className="setup-guidance"
          description="未能确认该账号的接口策略，请重新加载后再继续。"
          showIcon
          title={policyLoadError}
          type="error"
        />
      ) : !loadingPolicies && accountId && policies.length === 0 ? (
        <section className="setup-guidance" aria-label="接口策略准备指引">
          <strong>先启用一个接口策略</strong>
          <p>该账号没有可手动运行的已启用接口，请先完成策略配置。</p>
          <Link
            className="action-link action-link--neutral"
            to={policyTarget}
            state={policyNavigationState}
          >
            配置接口策略
          </Link>
        </section>
      ) : null}
      {contextApiUnavailable && policies.length > 0 ? (
        <section className="setup-guidance" aria-label="接口上下文不可用">
          <strong>链接中的接口当前不可用</strong>
          <p>请选择其他已启用接口，或检查该账号的同步策略。</p>
          <Link
            className="action-link action-link--neutral"
            to={policyTarget}
            state={policyNavigationState}
          >
            检查接口策略
          </Link>
        </section>
      ) : null}
    </section>
  );
}

interface SyncJobScopeSectionProps {
  busy: boolean;
  checkpointRangeDisabled: boolean;
  customRangeDisabled: boolean;
  endDate: string;
  fieldErrors: SyncJobFieldErrors;
  loadingMarketOptions: boolean;
  marketOptions: SyncJobMarketOption[];
  marketOptionsError: string;
  marketScopeMode: MarketScopeMode;
  rangeMode: "checkpoint" | "custom";
  selectedMarketIds: number[];
  selectedPolicy: ApiPolicy | undefined;
  startDate: string;
  supportsMarketScope: boolean;
  onEndDateChange: (value: string) => void;
  onMarketScopeModeChange: (mode: MarketScopeMode) => void;
  onRangeModeChange: (mode: "checkpoint" | "custom") => void;
  onRetryMarketOptions: () => void;
  onStartDateChange: (value: string) => void;
  onToggleMarket: (marketId: number, selected: boolean) => void;
}

export function SyncJobScopeSection({
  busy,
  checkpointRangeDisabled,
  customRangeDisabled,
  endDate,
  fieldErrors,
  loadingMarketOptions,
  marketOptions,
  marketOptionsError,
  marketScopeMode,
  rangeMode,
  selectedMarketIds,
  selectedPolicy,
  startDate,
  supportsMarketScope,
  onEndDateChange,
  onMarketScopeModeChange,
  onRangeModeChange,
  onRetryMarketOptions,
  onStartDateChange,
  onToggleMarket,
}: SyncJobScopeSectionProps) {
  return (
    <section className="job-create-section" aria-labelledby="sync-range-heading">
      <div className="job-create-section-heading">
        <div>
          <h2 id="sync-range-heading">数据范围</h2>
        </div>
      </div>
      {selectedPolicy && !selectedPolicy.supportsDateWindow ? (
        <div className="range-static-summary" aria-label="数据范围方式">
          <strong>同步当前完整结果</strong>
          <small>此接口不使用日期窗口，每次同步当前可返回的完整结果。</small>
        </div>
      ) : (
        <fieldset className="range-mode-fieldset" disabled={checkpointRangeDisabled}>
          <legend className="sr-only">同步方式</legend>
          <Radio
            aria-disabled={checkpointRangeDisabled}
            className={`range-mode-option${checkpointRangeDisabled ? " range-mode-option--disabled" : ""}`}
            checked={rangeMode === "checkpoint"}
            name="range-mode"
            onChange={() => onRangeModeChange("checkpoint")}
          >
            <span>
              <strong>补齐历史至今（推荐）</strong>
              <small>
                首次从接口允许的最早日期开始；以后从成功检查点接续，终点由服务端按最新完整数据日计算。
              </small>
            </span>
          </Radio>
          <Radio
            aria-disabled={customRangeDisabled}
            className={`range-mode-option${customRangeDisabled ? " range-mode-option--disabled" : ""}`}
            checked={rangeMode === "custom"}
            disabled={customRangeDisabled}
            name="range-mode"
            onChange={() => onRangeModeChange("custom")}
          >
            <span>
              <strong>重跑指定日期</strong>
              <small>只重跑所选日期，不推进主检查点。</small>
            </span>
          </Radio>
        </fieldset>
      )}
      {rangeMode === "custom" ? (
        <div className="date-range-grid">
          <div className="job-create-field">
            <label htmlFor="sync-start-date">开始日期</label>
            <Input
              aria-describedby={
                fieldErrors.startDate
                  ? "sync-date-constraints sync-start-date-error"
                  : "sync-date-constraints"
              }
              aria-invalid={Boolean(fieldErrors.startDate)}
              aria-required="true"
              disabled={busy}
              id="sync-start-date"
              max={endDate || undefined}
              type="date"
              value={startDate}
              onInput={(event) => onStartDateChange(event.currentTarget.value)}
            />
            {fieldErrors.startDate ? (
              <small className="field-error" id="sync-start-date-error" role="alert">
                {fieldErrors.startDate}
              </small>
            ) : null}
          </div>
          <div className="job-create-field">
            <label htmlFor="sync-end-date">结束日期</label>
            <Input
              aria-describedby={
                fieldErrors.endDate
                  ? "sync-date-constraints sync-end-date-error"
                  : "sync-date-constraints"
              }
              aria-invalid={Boolean(fieldErrors.endDate)}
              aria-required="true"
              disabled={busy}
              id="sync-end-date"
              min={startDate || undefined}
              type="date"
              value={endDate}
              onInput={(event) => onEndDateChange(event.currentTarget.value)}
            />
            {fieldErrors.endDate ? (
              <small className="field-error" id="sync-end-date-error" role="alert">
                {fieldErrors.endDate}
              </small>
            ) : null}
          </div>
          <p className="field-hint date-range-hint" id="sync-date-constraints">
            开始 ≤ 结束
          </p>
        </div>
      ) : null}
      <div className="job-store-scope">
        <strong id="sync-market-scope-heading">店铺范围</strong>
        {supportsMarketScope ? (
          <fieldset
            aria-describedby={fieldErrors.marketIds ? "sync-market-scope-error" : undefined}
            aria-invalid={Boolean(fieldErrors.marketIds)}
            className="market-scope-fieldset"
            disabled={busy}
          >
            <legend className="sr-only">选择店铺范围</legend>
            <Radio
              checked={marketScopeMode === "all"}
              className="market-scope-option"
              id="sync-market-scope-all"
              name="market-scope-mode"
              onChange={() => onMarketScopeModeChange("all")}
            >
              <span>
                <b>全部店铺</b>
                <small>账号可访问范围</small>
              </span>
            </Radio>
            <Radio
              checked={marketScopeMode === "selected"}
              className="market-scope-option"
              disabled={loadingMarketOptions || marketOptions.length === 0}
              name="market-scope-mode"
              onChange={() => onMarketScopeModeChange("selected")}
            >
              <span>
                <b>指定店铺站点</b>
                <small>选择一个或多个站点</small>
              </span>
            </Radio>
            {marketScopeMode === "selected" ? (
              <div className="market-option-list" aria-label="可选店铺站点">
                {marketOptions.map((option) => (
                  <Checkbox
                    checked={selectedMarketIds.includes(option.marketId)}
                    key={option.marketId}
                    onChange={(event) => onToggleMarket(option.marketId, event.target.checked)}
                  >
                    <span>{option.label}</span>
                  </Checkbox>
                ))}
              </div>
            ) : null}
            {loadingMarketOptions ? <Spin description="正在加载店铺站点…" size="small" /> : null}
            {!loadingMarketOptions && marketOptions.length === 0 && !marketOptionsError ? (
              <small>暂无可选站点，仍可按全部店铺同步。</small>
            ) : null}
            {marketOptionsError ? (
              <Alert
                action={
                  <Button className="text-button" type="text" onClick={onRetryMarketOptions}>
                    重新加载
                  </Button>
                }
                className="field-error"
                title={`${marketOptionsError}。仍可按全部店铺同步。`}
                type="error"
              />
            ) : null}
            {fieldErrors.marketIds ? (
              <small className="field-error" id="sync-market-scope-error">
                {fieldErrors.marketIds}
              </small>
            ) : null}
          </fieldset>
        ) : (
          <>
            <p>全部店铺</p>
            <small>此接口不支持店铺筛选</small>
          </>
        )}
      </div>
    </section>
  );
}

function RecoveryGuidance({ state }: { state: "missing" | "needs_verification" }) {
  const missing = state === "missing";
  return (
    <section className="setup-guidance" aria-label="账号准备指引">
      <strong>{missing ? "先接入积加账号" : "先完成账号验证"}</strong>
      <p>
        {missing
          ? "创建并验证账号后，才能选择接口发起同步。"
          : "当前账号均不可用于同步，请在账号管理中完成验证或恢复启用。"}
      </p>
      <Link
        className="action-link action-link--neutral"
        to={missing ? "/accounts/new" : "/accounts"}
      >
        {missing ? "接入账号" : "检查账号状态"}
      </Link>
    </section>
  );
}
