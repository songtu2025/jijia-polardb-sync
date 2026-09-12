import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Form, Tag } from "antd";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { ApiPolicy, JijiaAccount, SyncJobMarketOption, SyncJobPreview } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import {
  SyncJobScopeSection,
  SyncJobTargetSection,
  type MarketScopeMode,
  type SyncJobFieldErrors,
} from "../components/SyncJobConfigurationSections";
import { buildPolicyRecovery, readSyncJobDraft } from "./syncJobDraft";
import { JobReview, ErrorSummary, CompactSummary } from "../components/SyncJobPreviewSummary";
import { getApiErrorMessage, getReturnNavigation } from "./m3Utils";

type CreatePageState = "config" | "review";

export function SyncJobCreatePage() {
  const { csrfToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [restoredDraft] = useState(() => readSyncJobDraft(location.state, searchParams));
  const returnNavigation = getReturnNavigation(location.state, "/jobs", "返回任务列表", [
    "/",
    "/jobs",
    "/accounts",
    "/api-catalog",
    "/data",
    "/raw-data",
    "/sale-returns",
    "/audit",
  ]);
  const initialAccountId = searchParams.get("accountId")?.trim() ?? restoredDraft?.accountId ?? "";
  const initialApiCode = searchParams.get("apiCode")?.trim() ?? restoredDraft?.apiCode ?? "";
  const [pageState, setPageState] = useState<CreatePageState>("config");
  const [allAccounts, setAllAccounts] = useState<JijiaAccount[]>([]);
  const [catalogCodes, setCatalogCodes] = useState<Set<string>>(() => new Set());
  const [accountId, setAccountId] = useState("");
  const [accountPrefillReason, setAccountPrefillReason] = useState("");
  const [apiCode, setApiCode] = useState("");
  const [apiPrefillReason, setApiPrefillReason] = useState("");
  const [policies, setPolicies] = useState<ApiPolicy[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [loadingPolicies, setLoadingPolicies] = useState(false);
  const [optionsLoadError, setOptionsLoadError] = useState("");
  const [policyLoadError, setPolicyLoadError] = useState("");
  const [optionsRetryVersion, setOptionsRetryVersion] = useState(0);
  const [policyRetryVersion, setPolicyRetryVersion] = useState(0);
  const [rangeMode, setRangeMode] = useState<"checkpoint" | "custom">(
    restoredDraft?.rangeMode ?? "checkpoint",
  );
  const [startDate, setStartDate] = useState(restoredDraft?.startDate ?? "");
  const [endDate, setEndDate] = useState(restoredDraft?.endDate ?? "");
  const [marketScopeMode, setMarketScopeMode] = useState<MarketScopeMode>("all");
  const [marketOptions, setMarketOptions] = useState<SyncJobMarketOption[]>([]);
  const [selectedMarketIds, setSelectedMarketIds] = useState<number[]>([]);
  const [loadingMarketOptions, setLoadingMarketOptions] = useState(false);
  const [marketOptionsError, setMarketOptionsError] = useState("");
  const [marketOptionsRetryVersion, setMarketOptionsRetryVersion] = useState(0);
  const [preview, setPreview] = useState<SyncJobPreview | null>(null);
  const [caughtUp, setCaughtUp] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<SyncJobFieldErrors>({});
  const [contextAccountUnavailable, setContextAccountUnavailable] = useState(false);
  const [contextApiUnavailable, setContextApiUnavailable] = useState(false);
  const [liveMessage, setLiveMessage] = useState("正在加载可用账号和接口目录");
  const operationGenerationRef = useRef(0);
  const routeKeyRef = useRef(location.key);
  const previousRouteKeyRef = useRef(location.key);
  routeKeyRef.current = location.key;
  const marketDraftRestoredRef = useRef(false);
  useEffect(() => {
    if (previousRouteKeyRef.current !== location.key) {
      setRangeMode("checkpoint");
      setStartDate("");
      setEndDate("");
      marketDraftRestoredRef.current = true;
    }
    previousRouteKeyRef.current = location.key;
    operationGenerationRef.current += 1;
    setBusy(false);
    setPreview(null);
    setCaughtUp(false);
    setPageState("config");
    setFormError("");
    return () => {
      operationGenerationRef.current += 1;
    };
  }, [location.key]);
  const policyRequestIdRef = useRef(0);
  const marketRequestIdRef = useRef(0);
  const eligibleApiCodesRef = useRef<Set<string>>(new Set());
  const reviewHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const errorSummaryRef = useRef<HTMLDivElement | null>(null);

  const activeAccounts = useMemo(
    () => allAccounts.filter((account) => account.status === "active"),
    [allAccounts],
  );
  const selectedAccount = activeAccounts.find((account) => String(account.id) === accountId);
  const selectedPolicy = policies.find((policy) => policy.apiCode === apiCode);
  const supportsMarketScope = Boolean(selectedPolicy?.supportsMarketScope);
  const accountSetupState = loadingOptions
    ? "loading"
    : allAccounts.length === 0
      ? "missing"
      : activeAccounts.length === 0
        ? "needs_verification"
        : "ready";

  useEffect(() => {
    let active = true;
    setLoadingOptions(true);
    setOptionsLoadError("");
    setFormError("");
    setContextAccountUnavailable(false);
    Promise.all([api.listAccounts(), api.getApiCatalog()])
      .then(([accountRows, catalog]) => {
        if (!active) return;
        const availableAccounts = accountRows.filter((account) => account.status === "active");
        const requestedAccount = availableAccounts.find(
          (account) => String(account.id) === initialAccountId,
        );
        setAllAccounts(accountRows);
        setCatalogCodes(
          new Set(
            catalog
              .filter((item) => item.platformEnabled ?? item.catalogEnabled)
              .map((item) => item.apiCode),
          ),
        );
        if (requestedAccount) {
          setAccountId(String(requestedAccount.id));

          setAccountPrefillReason("来自链接");
        } else if (initialAccountId) {
          setAccountId(initialAccountId);

          setAccountPrefillReason("链接中的账号不可用");
        } else if (availableAccounts.length === 1) {
          setAccountId(String(availableAccounts[0].id));

          setAccountPrefillReason("已自动选择");
        } else {
          setAccountId("");

          setAccountPrefillReason("");
        }
        setContextAccountUnavailable(Boolean(initialAccountId && !requestedAccount));
        setLiveMessage("账号和接口目录加载完成");
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setOptionsLoadError(getApiErrorMessage(caught, "账号与接口选项加载失败"));
        setLiveMessage("账号与接口选项加载失败");
      })
      .finally(() => {
        if (active) setLoadingOptions(false);
      });
    return () => {
      active = false;
    };
  }, [initialAccountId, optionsRetryVersion]);

  useEffect(() => {
    const requestId = ++policyRequestIdRef.current;
    eligibleApiCodesRef.current = new Set();
    setPolicies([]);
    setApiCode("");
    setApiPrefillReason("");
    setContextApiUnavailable(false);
    setPolicyLoadError("");
    setPreview(null);
    setPageState("config");
    if (!accountId || loadingOptions || optionsLoadError || contextAccountUnavailable) {
      setLoadingPolicies(false);
      return undefined;
    }

    setLoadingPolicies(true);
    setLiveMessage("正在加载该账号的已启用接口");
    api
      .listPolicies(Number(accountId))
      .then((rows) => {
        if (policyRequestIdRef.current !== requestId) return;
        const eligible = rows.filter(
          (policy) => policy.enabled && catalogCodes.has(policy.apiCode),
        );
        const canUseInitialApi = Boolean(initialApiCode);
        const requestedPolicy = canUseInitialApi
          ? eligible.find((policy) => policy.apiCode === initialApiCode)
          : undefined;
        eligibleApiCodesRef.current = new Set(eligible.map((policy) => policy.apiCode));
        setPolicies(eligible);
        const nextPolicy =
          requestedPolicy ?? (!canUseInitialApi && eligible.length === 1 ? eligible[0] : undefined);
        if (requestedPolicy) {
          setApiCode(requestedPolicy.apiCode);
          setApiPrefillReason("来自链接");
        } else if (canUseInitialApi) {
          setApiCode(initialApiCode);
          setApiPrefillReason("链接中的接口不可用");
        } else if (eligible.length === 1) {
          setApiCode(eligible[0].apiCode);
          setApiPrefillReason("已自动选择");
        } else {
          setApiCode("");
          setApiPrefillReason("");
        }
        if (nextPolicy && !nextPolicy.supportsDateWindow) setRangeMode("checkpoint");
        setContextApiUnavailable(Boolean(canUseInitialApi && !requestedPolicy));
        setLiveMessage(eligible.length > 0 ? "已启用接口加载完成" : "该账号没有已启用接口");
      })
      .catch((caught: unknown) => {
        if (policyRequestIdRef.current !== requestId) return;
        eligibleApiCodesRef.current = new Set();
        setPolicies([]);
        setPolicyLoadError(getApiErrorMessage(caught, "账号策略加载失败"));
        setLiveMessage("账号策略加载失败");
      })
      .finally(() => {
        if (policyRequestIdRef.current === requestId) setLoadingPolicies(false);
      });
    return () => {
      if (policyRequestIdRef.current === requestId) {
        policyRequestIdRef.current += 1;
      }
    };
  }, [
    accountId,
    catalogCodes,
    contextAccountUnavailable,
    initialAccountId,
    initialApiCode,
    loadingOptions,
    optionsLoadError,
    policyRetryVersion,
  ]);

  useEffect(() => {
    const requestId = ++marketRequestIdRef.current;
    setMarketOptions([]);
    setSelectedMarketIds([]);
    setMarketScopeMode("all");
    setMarketOptionsError("");
    setFieldErrors((current) => ({ ...current, marketIds: undefined }));
    if (!accountId || !apiCode || !supportsMarketScope) {
      setLoadingMarketOptions(false);
      return undefined;
    }
    setLoadingMarketOptions(true);
    api
      .listSyncJobMarketOptions(Number(accountId), apiCode)
      .then((rows) => {
        if (marketRequestIdRef.current !== requestId) return;
        setMarketOptions(rows);
        if (
          !marketDraftRestoredRef.current &&
          restoredDraft?.accountId === accountId &&
          restoredDraft.apiCode === apiCode
        ) {
          setMarketScopeMode(restoredDraft.marketScopeMode);
          setSelectedMarketIds(restoredDraft.selectedMarketIds);
          marketDraftRestoredRef.current = true;
        }
      })
      .catch((caught: unknown) => {
        if (marketRequestIdRef.current !== requestId) return;
        setMarketOptionsError(getApiErrorMessage(caught, "店铺站点加载失败"));
      })
      .finally(() => {
        if (marketRequestIdRef.current === requestId) setLoadingMarketOptions(false);
      });
    return () => {
      if (marketRequestIdRef.current === requestId) marketRequestIdRef.current += 1;
    };
  }, [accountId, apiCode, marketOptionsRetryVersion, supportsMarketScope, restoredDraft]);

  useEffect(() => {
    if (pageState !== "review") return;
    const frame = window.requestAnimationFrame(() => reviewHeadingRef.current?.focus());
    return () => window.cancelAnimationFrame(frame);
  }, [pageState]);

  useEffect(() => {
    if (!formError && !Object.values(fieldErrors).some(Boolean)) return;
    const frame = window.requestAnimationFrame(() => errorSummaryRef.current?.focus());
    return () => window.cancelAnimationFrame(frame);
  }, [fieldErrors, formError]);

  function invalidatePreview() {
    setPreview(null);
    setCaughtUp(false);
    setPageState("config");
    setFormError("");
  }

  function handleRangeModeChange(nextRangeMode: "checkpoint" | "custom") {
    setRangeMode(nextRangeMode);
    setFieldErrors({});
    invalidatePreview();
  }

  function handleStartDateChange(value: string) {
    setStartDate(value);
    setFieldErrors((current) => ({ ...current, startDate: undefined }));
    invalidatePreview();
  }

  function handleEndDateChange(value: string) {
    setEndDate(value);
    setFieldErrors((current) => ({ ...current, endDate: undefined }));
    invalidatePreview();
  }

  function handleMarketScopeModeChange(nextMode: MarketScopeMode) {
    setMarketScopeMode(nextMode);
    if (nextMode === "all") {
      setFieldErrors((current) => ({ ...current, marketIds: undefined }));
    }
    invalidatePreview();
  }

  function handleMarketToggle(marketId: number, selected: boolean) {
    const nextIds = selected
      ? [...selectedMarketIds, marketId]
      : selectedMarketIds.filter((value) => value !== marketId);
    setSelectedMarketIds([...new Set(nextIds)].sort((left, right) => left - right));
    setFieldErrors((current) => ({ ...current, marketIds: undefined }));
    invalidatePreview();
  }

  function handleAccountChange(nextAccountId: string) {
    marketDraftRestoredRef.current = true;
    policyRequestIdRef.current += 1;
    eligibleApiCodesRef.current = new Set();
    setAccountId(nextAccountId);

    setAccountPrefillReason("");
    setApiCode("");
    setPolicies([]);
    setLoadingPolicies(Boolean(nextAccountId));
    setContextAccountUnavailable(false);
    setContextApiUnavailable(false);
    setPolicyLoadError("");
    setFieldErrors({});
    invalidatePreview();
  }

  function handleApiChange(nextApiCode: string) {
    marketDraftRestoredRef.current = true;
    const nextPolicy = policies.find((policy) => policy.apiCode === nextApiCode);
    setApiCode(nextApiCode);
    setApiPrefillReason("");
    setContextApiUnavailable(false);
    setFieldErrors((current) => ({ ...current, apiCode: undefined }));
    if (nextPolicy && !nextPolicy.supportsDateWindow) setRangeMode("checkpoint");
    invalidatePreview();
  }

  function validateFields(): boolean {
    const errors: SyncJobFieldErrors = {};
    const parsedAccountId = Number(accountId);
    if (
      !Number.isInteger(parsedAccountId) ||
      parsedAccountId <= 0 ||
      !activeAccounts.some((account) => account.id === parsedAccountId)
    ) {
      errors.accountId = "请选择可用账号";
    }
    if (!apiCode || !eligibleApiCodesRef.current.has(apiCode)) {
      errors.apiCode = "请选择该账号的已启用接口";
    }
    if (rangeMode === "custom") {
      if (!startDate) errors.startDate = "请选择开始日期";
      if (!endDate) errors.endDate = "请选择结束日期";
      if (startDate && endDate && startDate > endDate) {
        errors.startDate = "开始日期不能晚于结束日期";
      }
    }
    if (
      marketScopeMode === "selected" &&
      (selectedMarketIds.length === 0 ||
        selectedMarketIds.some((id) => !marketOptions.some((option) => option.marketId === id)))
    ) {
      errors.marketIds = "请选择当前可用的店铺站点";
    }
    setFieldErrors(errors);
    if (Object.values(errors).some(Boolean)) {
      setFormError("请修正以下内容后再预览执行计划");
      return false;
    }
    setFormError("");
    return true;
  }

  async function previewPlan() {
    if (!validateFields()) return;
    const generation = ++operationGenerationRef.current;
    const routeKey = location.key;
    const isCurrent = () =>
      generation === operationGenerationRef.current && routeKey === routeKeyRef.current;
    setBusy(true);
    setFormError("");
    setCaughtUp(false);
    try {
      const nextPreview = await api.previewSyncJob({
        jijiaAccountId: Number(accountId),
        apiCode,
        rangeMode,
        startDate: rangeMode === "custom" ? startDate : null,
        endDate: rangeMode === "custom" ? endDate : null,
        marketIds: marketScopeMode === "selected" ? selectedMarketIds : null,
        previewToken: null,
      });
      if (!isCurrent()) return;
      setPreview(nextPreview);
      setPageState("review");
      setLiveMessage("执行计划已生成，请检查后创建任务");
    } catch (caught) {
      if (!isCurrent()) return;
      if (caught instanceof ApiError && caught.code === "INCREMENTAL_CAUGHT_UP") {
        setCaughtUp(true);
        setFormError("");
        setLiveMessage("已同步至最新完整数据日，不需要创建任务");
      } else {
        setFormError(getApiErrorMessage(caught, "执行计划预览失败，请稍后重试"));
        setLiveMessage("执行计划预览失败");
      }
    } finally {
      if (isCurrent()) setBusy(false);
    }
  }

  async function createJob() {
    if (!preview || preview.activeTask || busy) return;
    if (!csrfToken) {
      setFormError("登录状态已失效，请重新登录");
      setLiveMessage("登录状态已失效，任务未创建");
      return;
    }
    const generation = ++operationGenerationRef.current;
    const routeKey = location.key;
    const isCurrent = () =>
      generation === operationGenerationRef.current && routeKey === routeKeyRef.current;
    setBusy(true);
    setFormError("");
    try {
      const accepted = await api.createSyncJob(
        {
          jijiaAccountId: Number(accountId),
          apiCode,
          rangeMode,
          startDate: rangeMode === "custom" ? startDate : null,
          endDate: rangeMode === "custom" ? endDate : null,
          marketIds: marketScopeMode === "selected" ? selectedMarketIds : null,
          previewToken: preview.previewToken,
        },
        csrfToken,
      );
      if (!isCurrent()) return;
      navigate(
        accepted.taskNo
          ? `/jobs/tasks/${encodeURIComponent(accepted.taskNo)}`
          : `/jobs/${accepted.jobId}`,
        {
          replace: true,
          state: {
            backLabel: returnNavigation.label,
            returnState: returnNavigation.state,
            createdJobId: String(accepted.jobId),
            createdTaskNo: accepted.taskNo ?? undefined,
            from: returnNavigation.path,
            jobCreatedNotice: "任务已加入队列",
          },
        },
      );
    } catch (caught) {
      if (!isCurrent()) return;
      if (caught instanceof ApiError && caught.code === "SYNC_WINDOW_CHANGED") {
        setPreview(null);
        setPageState("config");
        setFormError("系统检查点或可用日期已变化，请重新预览执行计划");
      } else {
        setFormError(getApiErrorMessage(caught, "任务创建失败，请稍后重试"));
      }
      setLiveMessage("任务未创建，请检查页面提示");
    } finally {
      if (isCurrent()) setBusy(false);
    }
  }

  function returnToConfig(targetId: string) {
    setPageState("config");
    setFormError("");
    setLiveMessage("已返回配置任务，当前填写内容保持不变");
    window.requestAnimationFrame(() => document.getElementById(targetId)?.focus());
  }

  const downstreamDisabled = busy || loadingOptions || loadingPolicies || !apiCode;
  const checkpointRangeDisabled = downstreamDisabled;
  const customRangeDisabled = downstreamDisabled || !selectedPolicy?.supportsDateWindow;
  const canPreview =
    !busy &&
    !loadingOptions &&
    !loadingPolicies &&
    !contextAccountUnavailable &&
    !contextApiUnavailable &&
    Boolean(accountId && apiCode);
  const selectedApiLabel = selectedPolicy
    ? `${selectedPolicy.name} · ${selectedPolicy.apiCode}`
    : "待选择";
  const rangeSummary =
    selectedPolicy && !selectedPolicy.supportsDateWindow
      ? "同步当前完整结果"
      : rangeMode === "checkpoint"
        ? "补齐历史至今"
        : startDate && endDate
          ? `${startDate} 至 ${endDate}`
          : "待选择日期";
  const storeSummary =
    supportsMarketScope && marketScopeMode === "selected"
      ? `已选 ${selectedMarketIds.length} 个店铺`
      : "全部店铺";
  const { policyTarget, policyNavigationState } = buildPolicyRecovery(
    {
      accountId,
      apiCode,
      rangeMode,
      startDate,
      endDate,
      marketScopeMode,
      selectedMarketIds,
    },
    returnNavigation,
  );
  const fieldErrorEntries = Object.entries(fieldErrors).filter((entry) => entry[1]);

  return (
    <AppShell>
      <main className="m3-page job-create-page">
        <p className="sr-only" aria-live="polite" role="status">
          {liveMessage}
        </p>
        <header className="page-heading job-create-heading">
          <div>
            <Link className="m3-link" to={returnNavigation.path} state={returnNavigation.state}>
              ← {returnNavigation.label}
            </Link>
            <h1>创建同步任务</h1>
          </div>
          <Tag className="job-create-state">
            {pageState === "config" ? "配置任务" : "检查并创建"}
          </Tag>
        </header>

        {pageState === "config" ? (
          <div className="job-create-layout">
            <Form className="job-create-form" noValidate onFinish={previewPlan}>
              <SyncJobTargetSection
                accountId={accountId}
                accountPrefillReason={accountPrefillReason}
                accountSetupState={accountSetupState}
                activeAccounts={activeAccounts}
                allAccounts={allAccounts}
                apiCode={apiCode}
                apiPrefillReason={apiPrefillReason}
                busy={busy}
                contextAccountUnavailable={contextAccountUnavailable}
                contextApiUnavailable={contextApiUnavailable}
                fieldErrors={fieldErrors}
                loadingOptions={loadingOptions}
                loadingPolicies={loadingPolicies}
                optionsLoadError={optionsLoadError}
                policies={policies}
                policyLoadError={policyLoadError}
                policyNavigationState={policyNavigationState}
                policyTarget={policyTarget}
                onAccountChange={handleAccountChange}
                onApiChange={handleApiChange}
                onRetryOptions={() => setOptionsRetryVersion((current) => current + 1)}
                onRetryPolicies={() => setPolicyRetryVersion((current) => current + 1)}
              />
              <SyncJobScopeSection
                busy={busy}
                checkpointRangeDisabled={checkpointRangeDisabled}
                customRangeDisabled={customRangeDisabled}
                endDate={endDate}
                fieldErrors={fieldErrors}
                loadingMarketOptions={loadingMarketOptions}
                marketOptions={marketOptions}
                marketOptionsError={marketOptionsError}
                marketScopeMode={marketScopeMode}
                rangeMode={rangeMode}
                selectedMarketIds={selectedMarketIds}
                selectedPolicy={selectedPolicy}
                startDate={startDate}
                supportsMarketScope={supportsMarketScope}
                onEndDateChange={handleEndDateChange}
                onMarketScopeModeChange={handleMarketScopeModeChange}
                onRangeModeChange={handleRangeModeChange}
                onRetryMarketOptions={() => setMarketOptionsRetryVersion((current) => current + 1)}
                onStartDateChange={handleStartDateChange}
                onToggleMarket={handleMarketToggle}
              />

              {caughtUp ? (
                <Alert
                  aria-label="同步进度已追平"
                  description="当前检查点已追平服务端可用的最新完整数据，不需要创建同步任务。"
                  role="status"
                  showIcon
                  title="已同步至最新完整数据日"
                  type="success"
                />
              ) : null}

              <ErrorSummary
                entries={fieldErrorEntries}
                formError={formError}
                summaryRef={errorSummaryRef}
              />
              <footer className="job-create-action-bar">
                <CompactSummary
                  apiName={selectedApiLabel}
                  range={rangeSummary}
                  storeScope={storeSummary}
                />
                <div className="job-create-actions">
                  <Link
                    className="action-link action-link--neutral"
                    to={returnNavigation.path}
                    state={returnNavigation.state}
                  >
                    取消
                  </Link>
                  <Button disabled={!canPreview} htmlType="submit" loading={busy} type="primary">
                    {busy ? "正在生成执行计划…" : "预览执行计划"}
                  </Button>
                </div>
              </footer>
            </Form>
          </div>
        ) : preview ? (
          <JobReview
            preview={preview}
            accountName={selectedAccount?.name ?? `账号 ${accountId}`}
            apiName={
              selectedPolicy ? `${selectedPolicy.name} · ${selectedPolicy.apiCode}` : apiCode
            }
            rangeMode={rangeMode}
            busy={busy}
            formError={formError}
            headingRef={reviewHeadingRef}
            errorRef={errorSummaryRef}
            returnNavigation={returnNavigation}
            onReturnToConfig={returnToConfig}
            onCreate={createJob}
            taskReturnState={policyNavigationState}
          />
        ) : null}
      </main>
    </AppShell>
  );
}
