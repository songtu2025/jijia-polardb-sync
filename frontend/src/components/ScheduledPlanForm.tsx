import { useEffect, useRef, useState } from "react";
import { Alert, Button, Empty, Input, Modal, Select, Spin } from "antd";
import type { InputRef } from "antd";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { ApiPolicy, JijiaAccount, ScheduledPlan, ScheduleMode } from "../api/types";
import { buildPolicyUpdate, MAX_BATCH_POLICIES } from "../policyUtils";
import { businessDomainLabel } from "../businessDomains";
import { PolicyDomainGroup } from "./PolicyDomainGroup";
import { PolicyScheduleFields } from "./PolicyScheduleFields";
import { formatDate } from "../pages/m3Utils";
import { ScheduledPlanRangeRules } from "./ScheduledPlanWindowPreview";

export function ScheduledPlanForm({
  accountId,
  refreshToken,
  apiCode,
  canEdit,
  csrfToken,
  returnTo,
  returnLabel,
  returnState,
  onDirtyChange,
  onBusyChange,
}: {
  accountId: number;
  refreshToken: number;
  apiCode?: string;
  canEdit: boolean;
  csrfToken: string | null;
  returnTo: string;
  returnLabel: string;
  returnState?: unknown;
  onDirtyChange: (dirty: boolean) => void;
  onBusyChange: (busy: boolean) => void;
}) {
  const [account, setAccount] = useState<JijiaAccount | null>(null);
  const [policies, setPolicies] = useState<ApiPolicy[]>([]);
  const [scheduledPlan, setScheduledPlan] = useState<ScheduledPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [expressionError, setExpressionError] = useState("");
  const [reload, setReload] = useState(0);
  const [search, setSearch] = useState("");
  const [domain, setDomain] = useState("");
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(() => new Set());
  const [mode, setMode] = useState<ScheduleMode>("daily");
  const [expression, setExpression] = useState("");
  const [busy, setBusy] = useState(false);
  const [savedPlans, setSavedPlans] = useState<ApiPolicy[]>([]);
  const [closed, setClosed] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);
  const generationRef = useRef(0);
  const initializedRef = useRef(false);
  const expressionRef = useRef<InputRef>(null);

  useEffect(() => {
    const generation = ++generationRef.current;
    setLoading(true);
    setLoadError("");
    Promise.all([
      api.getAccount(accountId),
      api.listPolicies(accountId),
      apiCode ? api.listScheduledPlans() : Promise.resolve([]),
    ])
      .then(([loadedAccount, rows, scheduledPlans]) => {
        if (generationRef.current !== generation) return;
        setAccount(loadedAccount);
        setPolicies(rows);
        setScheduledPlan(
          scheduledPlans.find(
            (plan) => plan.jijiaAccountId === accountId && plan.apiCode === apiCode,
          ) ?? null,
        );
        const target = rows.find((policy) => policy.apiCode === apiCode);
        if (apiCode && !target) setLoadError("找不到指定接口，请返回定时计划重新选择。");
        if (target && !initializedRef.current) {
          initializedRef.current = true;
          setSelectedCodes(new Set([target.apiCode]));
          setMode(target.scheduleMode === "manual_only" ? "daily" : target.scheduleMode);
          setExpression(target.scheduleExpr ?? "");
        }
      })
      .catch((caught) => {
        if (generationRef.current === generation)
          setLoadError(caught instanceof ApiError ? caught.message : "计划配置加载失败");
      })
      .finally(() => {
        if (generationRef.current === generation) setLoading(false);
      });
    return () => {
      generationRef.current += 1;
    };
  }, [accountId, apiCode, reload, refreshToken]);

  const target = policies.find((policy) => policy.apiCode === apiCode);
  const selected = policies.filter((policy) => selectedCodes.has(policy.apiCode));
  const filtered = policies.filter(
    (policy) =>
      (!domain || policy.domain === domain) &&
      `${policy.name} ${policy.apiCode}`.toLowerCase().includes(search.trim().toLowerCase()),
  );
  const groups = Array.from(
    filtered.reduce((result, policy) => {
      result.set(policy.domain, [...(result.get(policy.domain) ?? []), policy]);
      return result;
    }, new Map<string, ApiPolicy[]>()),
  );
  const hiddenCount = selected.filter((policy) => !filtered.includes(policy)).length;
  const selectableFiltered = filtered.filter(
    (policy) => policy.catalogEnabled && !selectedCodes.has(policy.apiCode),
  );
  const newPlanCount = selected.filter((policy) => !policy.enabled).length;
  const updatedPlanCount = selected.length - newPlanCount;
  const blocked = account?.status !== "active" || selected.some((policy) => !policy.catalogEnabled);

  const closeBlocked =
    account?.status !== "active" || Boolean(target?.enabled && !target.catalogEnabled);

  async function save(close = false) {
    if (!canEdit || !csrfToken || busy || !selected.length || (close ? closeBlocked : blocked))
      return;
    if (!close && !expression.trim()) {
      setExpressionError(mode === "daily" ? "请输入每日执行时间" : "请输入 Cron 表达式");
      expressionRef.current?.focus();
      return;
    }
    if (selected.length > MAX_BATCH_POLICIES) {
      setActionError("一次最多设置 100 个接口，请减少选择后保存。");
      return;
    }
    const generation = generationRef.current;
    setBusy(true);
    onBusyChange(true);
    setActionError("");
    setExpressionError("");
    setSavedPlans([]);
    setClosed(false);
    const inputs = selected.map((policy) =>
      buildPolicyUpdate(policy, {
        enabled: close ? policy.enabled : true,
        scheduleMode: close ? "manual_only" : mode,
        scheduleExpr: close ? null : expression.trim(),
      }),
    );
    try {
      const updated = apiCode
        ? [await api.updatePolicy(accountId, apiCode, inputs[0], csrfToken)]
        : await api.batchUpdatePolicies(
            accountId,
            selected.map((policy, index) => ({ ...inputs[index], apiCode: policy.apiCode })),
            csrfToken,
          );
      if (generationRef.current !== generation) return;
      const updates = new Map(updated.map((policy) => [policy.apiCode, policy]));
      setPolicies((current) => current.map((policy) => updates.get(policy.apiCode) ?? policy));
      setSavedPlans(close ? [] : updated);
      setClosed(close);
      onDirtyChange(false);
      if (apiCode) {
        try {
          const scheduledPlans = await api.listScheduledPlans();
          if (generationRef.current !== generation) return;
          setScheduledPlan(
            scheduledPlans.find(
              (plan) => plan.jijiaAccountId === accountId && plan.apiCode === apiCode,
            ) ?? null,
          );
        } catch {
          if (generationRef.current === generation) setScheduledPlan(null);
        }
      }
      if (close) {
        setMode("daily");
        setExpression("");
      }
    } catch (caught) {
      if (generationRef.current === generation)
        setActionError(caught instanceof ApiError ? caught.message : "定时计划保存失败");
    } finally {
      if (generationRef.current === generation) {
        setBusy(false);
        onBusyChange(false);
      }
    }
  }

  function toggle(apiCode: string, checked: boolean) {
    if (selectedCodes.has(apiCode) === checked) return;
    setActionError("");
    setSelectedCodes((current) => {
      const next = new Set(current);
      if (checked) next.add(apiCode);
      else next.delete(apiCode);
      return next;
    });
    onDirtyChange(true);
  }

  if (loading && !account) return <Spin description="正在加载计划配置…" />;
  if (!loading && loadError && (!account || (apiCode && !target))) {
    return (
      <Alert
        type="error"
        title={loadError}
        action={<Button onClick={() => setReload((value) => value + 1)}>重新加载</Button>}
      />
    );
  }
  return (
    <div className="scheduled-plan-form">
      <p className="scheduled-plan-current-account">
        当前账号：{account?.name ?? "未加载"}。每个接口独立生成任务。
      </p>
      {account?.status !== "active" ? (
        <Alert
          type="warning"
          title="账号尚未验证或已停用，恢复有效状态后才能保存计划。"
          action={
            <>
              <Link to={`/accounts/${accountId}`} target="_blank" rel="noopener noreferrer">
                管理账号
              </Link>
              <Button disabled={busy} onClick={() => setReload((value) => value + 1)}>
                重新检查
              </Button>
            </>
          }
        />
      ) : null}
      {loadError ? (
        <Alert
          type="error"
          title={loadError}
          action={<Button onClick={() => setReload((value) => value + 1)}>重新加载</Button>}
        />
      ) : null}
      <div className="scheduled-plan-workspace">
        <section
          className="job-create-section scheduled-plan-interface-section"
          aria-labelledby="scheduled-plan-interface-heading"
        >
          <div className="job-create-section-heading">
            <div>
              <h2 id="scheduled-plan-interface-heading">2. 同步接口</h2>
              <p>
                {apiCode ? "确认需要调整的接口及当前计划。" : "选择需要按同一周期自动执行的接口。"}
              </p>
            </div>
          </div>
          {apiCode ? (
            target ? (
              <section className="policy-next-step" aria-label="当前定时计划">
                <div>
                  <strong>{target.name}</strong>
                  <p>{target.apiCode}</p>
                  <p>
                    当前周期：
                    {target.scheduleMode === "manual_only"
                      ? "仅手动"
                      : `${target.scheduleMode === "daily" ? "每天" : "Cron"} ${target.scheduleExpr}`}{" "}
                    · 北京时间
                  </p>
                  <p>下次计划时间：{formatDate(target.nextRunAt, target.timezone)}</p>
                  {!target.catalogEnabled ? (
                    <Alert type="warning" title="平台已停用该接口，不能启用定时计划。" />
                  ) : null}
                </div>
              </section>
            ) : null
          ) : (
            <>
              <section className="policy-toolbar scheduled-plan-filter-toolbar">
                <Input
                  allowClear
                  aria-label="搜索同步接口"
                  placeholder="搜索接口名称或 API code"
                  value={search}
                  disabled={busy}
                  onChange={(event) => setSearch(event.target.value)}
                />
                <Select
                  aria-label="按业务域筛选"
                  value={domain}
                  disabled={busy}
                  virtual={false}
                  options={[
                    { label: "全部业务域", value: "" },
                    ...Array.from(new Set(policies.map((policy) => policy.domain))).map(
                      (value) => ({
                        label: businessDomainLabel(value),
                        value,
                      }),
                    ),
                  ]}
                  onChange={setDomain}
                />
                <span className="policy-result-count" aria-live="polite">
                  当前结果 {filtered.length} / 共 {policies.length} · 已选 {selected.length}
                </span>
                <Button
                  disabled={busy || selectableFiltered.length === 0}
                  onClick={() => {
                    setActionError("");
                    setSelectedCodes(
                      (current) =>
                        new Set([
                          ...current,
                          ...selectableFiltered.map((policy) => policy.apiCode),
                        ]),
                    );
                    onDirtyChange(true);
                  }}
                >
                  全选当前结果
                </Button>
                <Button
                  disabled={busy || selected.length === 0}
                  onClick={() => {
                    setActionError("");
                    setSelectedCodes(new Set());
                    onDirtyChange(true);
                  }}
                >
                  清空选择
                </Button>
              </section>
              {selected.length > MAX_BATCH_POLICIES ? (
                <Alert type="warning" title="一次最多设置 100 个接口，请减少选择后保存。" />
              ) : null}
              {filtered.length ? (
                <div
                  className="scheduled-plan-interface-list"
                  role="region"
                  aria-label="可选同步接口"
                  tabIndex={0}
                >
                  {groups.map(([name, rows]) => (
                    <PolicyDomainGroup
                      key={name}
                      accountId={accountId}
                      accountStatus={account?.status ?? null}
                      canEdit={canEdit}
                      busy={busy}
                      selectionOnly
                      domainName={name}
                      initiallyOpen={Boolean(
                        search.trim() ||
                        domain ||
                        rows.some((policy) => selectedCodes.has(policy.apiCode)),
                      )}
                      policies={rows}
                      selectedCode={null}
                      selectedCodes={selectedCodes}
                      onToggleSelected={toggle}
                    />
                  ))}
                </div>
              ) : (
                <Empty
                  description={
                    <div className="scheduled-plan-empty-filter">
                      <span>
                        {policies.length
                          ? "没有符合条件的接口。"
                          : "暂无可配置接口，请在接口中心查看平台接入状态。"}
                      </span>
                      {policies.length && (search.trim() || domain) ? (
                        <Button
                          onClick={() => {
                            setSearch("");
                            setDomain("");
                          }}
                        >
                          清除搜索和筛选
                        </Button>
                      ) : null}
                    </div>
                  }
                />
              )}
              <p className="scheduled-plan-selection-note">
                已选择 {selected.length} 个接口（每次最多 {MAX_BATCH_POLICIES} 个）
                {hiddenCount ? `，其中 ${hiddenCount} 个被当前筛选隐藏` : ""}
              </p>
            </>
          )}
        </section>
        {canEdit && (!apiCode || target) ? (
          <aside className="scheduled-plan-execution-column" aria-label="执行计划与保存">
            <section
              className="job-create-section scheduled-plan-execution-section"
              aria-labelledby="scheduled-plan-execution-heading"
            >
              <div className="job-create-section-heading">
                <div>
                  <h2 id="scheduled-plan-execution-heading">3. 执行计划</h2>
                  <p>所有所选接口使用同一周期和时间，计划时区固定为北京时间。</p>
                </div>
              </div>
              <div className="scheduled-plan-fields">
                <PolicyScheduleFields
                  mode={mode}
                  expression={expression}
                  expressionError={expressionError}
                  expressionRef={expressionRef}
                  disabled={busy || blocked}
                  bulk={!apiCode}
                  onModeChange={(value) => {
                    setMode(value);
                    setExpressionError("");
                    setActionError("");
                    onDirtyChange(true);
                  }}
                  onExpressionChange={(value) => {
                    setExpression(value);
                    setExpressionError("");
                    setActionError("");
                    onDirtyChange(true);
                  }}
                />
              </div>
              <div className="scheduled-plan-impact-summary" aria-live="polite">
                <span>
                  新启用 <strong>{newPlanCount}</strong>
                </span>
                <span>
                  更新 <strong>{updatedPlanCount}</strong>
                </span>
                <p>
                  {updatedPlanCount
                    ? `更新的 ${updatedPlanCount} 个接口将覆盖原周期和时间。`
                    : "当前不会覆盖已有接口的周期和时间。"}
                  支持日期窗口的接口按已保存的同步进度继续；其他接口按自身规则同步。
                </p>
              </div>
            </section>
            <footer className="job-create-action-bar scheduled-plan-action-bar">
              {actionError ? (
                <Alert className="scheduled-plan-action-error" type="error" title={actionError} />
              ) : null}
              <dl className="job-create-compact-summary" aria-label="当前定时计划配置">
                <div>
                  <dt>同步范围</dt>
                  <dd>{selected.length ? `${selected.length} 个接口` : "尚未选择接口"}</dd>
                </div>
                <div>
                  <dt>执行周期</dt>
                  <dd>{mode === "daily" ? "每日" : "Cron"}</dd>
                </div>
                <div>
                  <dt>执行时间</dt>
                  <dd>{expression || "尚未设置"}</dd>
                </div>
              </dl>
              <div className="job-create-actions">
                <Button
                  type="primary"
                  loading={busy}
                  disabled={
                    busy || blocked || !selected.length || selected.length > MAX_BATCH_POLICIES
                  }
                  onClick={() => void save()}
                >
                  {apiCode ? "保存修改" : `保存 ${selected.length} 个定时计划`}
                </Button>
                {target && target.scheduleMode !== "manual_only" ? (
                  <Button disabled={busy || closeBlocked} onClick={() => setConfirmClose(true)}>
                    关闭定时执行
                  </Button>
                ) : null}
              </div>
            </footer>
          </aside>
        ) : !canEdit ? (
          <p>当前为只读权限，可查看接口的周期和运行状态。</p>
        ) : null}
      </div>
      {apiCode && target ? (
        scheduledPlan ? (
          <ScheduledPlanRangeRules preview={scheduledPlan.nextWindowPreview} />
        ) : (
          <section
            className="job-create-section"
            aria-labelledby="scheduled-plan-range-rules-heading"
          >
            <div className="job-create-section-heading">
              <div>
                <h2 id="scheduled-plan-range-rules-heading">数据范围规则</h2>
                <p>当前计划暂未返回数据范围预测，请刷新后重试。</p>
              </div>
            </div>
          </section>
        )
      ) : null}
      {target?.enabled && !target.catalogEnabled && target.scheduleMode !== "manual_only" ? (
        <Alert
          type="warning"
          title="平台停用期间无法在保持接口启用状态的同时关闭定时执行，请先在接入管理处理接口状态。"
        />
      ) : null}
      {closed ? (
        <Alert
          type="success"
          title="定时执行已关闭。接口启用状态保持不变，已排队和正在执行的任务不受影响。重新开启需要设置执行周期。"
        />
      ) : null}
      {savedPlans.length ? (
        <section className="policy-next-step" aria-label="定时计划保存结果">
          <div>
            <strong>已保存 {savedPlans.length} 个接口的定时计划</strong>
            <p>以下为上次成功保存的计划；新修改需保存后生效。</p>
            <ul>
              {savedPlans.map((plan) => (
                <li key={plan.apiCode}>
                  {plan.name}：{plan.scheduleMode === "daily" ? "每天" : "Cron"} {plan.scheduleExpr}{" "}
                  · 北京时间 ·{" "}
                  {plan.nextRunAt
                    ? `下次计划时间：${formatDate(plan.nextRunAt, plan.timezone)}`
                    : "下次计划时间未返回，请查看计划状态"}
                </li>
              ))}
            </ul>
            <p>执行服务运行时会按计划生成任务，实际开始时间受队列和当前任务影响。</p>
          </div>
          <Link className="action-link action-link--primary" to={returnTo} state={returnState}>
            {returnLabel}
          </Link>
        </section>
      ) : null}
      <Modal
        open={confirmClose}
        title={`关闭“${target?.name ?? ""}”的定时执行`}
        okText="关闭定时执行"
        cancelText="保留计划"
        onCancel={() => setConfirmClose(false)}
        onOk={() => {
          setConfirmClose(false);
          void save(true);
        }}
      >
        <p>
          将不再按周期生成新任务，接口启用状态、已排队和正在执行的任务不变。重新开启需要重新设置周期。
        </p>
      </Modal>
    </div>
  );
}
