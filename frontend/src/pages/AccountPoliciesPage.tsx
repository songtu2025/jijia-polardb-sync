import { useEffect, useRef, useState } from "react";
import { Alert, Button, Empty, Input, Select, Spin } from "antd";
import { Link, Navigate, useLocation, useParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { ApiPolicy, ApiPolicyUpdateInput, JijiaAccountStatus } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { buildPolicyUpdate, MAX_BATCH_POLICIES } from "../policyUtils";
import { businessDomainLabel } from "../businessDomains";
import { getReturnNavigation } from "./m3Utils";
import { PolicyDomainGroup } from "../components/PolicyDomainGroup";

type PolicyFilter = "all" | "enabled" | "scheduled" | "pending" | "blocked";

export function AccountPoliciesPage() {
  const { accountId } = useParams();
  const location = useLocation();
  const query = new URLSearchParams(location.search);
  if (query.get("intent") === "schedule") {
    const apiCode = query.get("apiCode");
    return (
      <Navigate
        replace
        state={location.state}
        to={
          apiCode
            ? `/jobs/plans/${accountId}/${encodeURIComponent(apiCode)}`
            : `/jobs/plans/new?accountId=${accountId}`
        }
      />
    );
  }
  return <AccountPoliciesContent />;
}

function AccountPoliciesContent() {
  const accountId = Number(useParams().accountId);
  const location = useLocation();
  const { csrfToken, user } = useAuth();
  const canEdit = user?.role === "admin" || user?.role === "operator";
  const routeState = location.state as { policyNotice?: string; returnTo?: string } | null;
  const routeNotice = routeState?.policyNotice ?? "";
  const requestedApiCode = new URLSearchParams(location.search).get("apiCode") ?? "";
  const returnNavigation = getReturnNavigation(
    location.state,
    `/accounts/${accountId}`,
    "返回账号概览",
    ["/jobs", "/accounts", "/api-catalog"],
  );
  const [accountName, setAccountName] = useState("");
  const [accountStatus, setAccountStatus] = useState<JijiaAccountStatus | null>(null);
  const [policies, setPolicies] = useState<ApiPolicy[]>([]);
  const [stateAccountId, setStateAccountId] = useState(accountId);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [domain, setDomain] = useState("");
  const [filter, setFilter] = useState<PolicyFilter>("enabled");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(routeNotice);
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(() => new Set());
  const [reload, setReload] = useState(0);
  const [bulkBusy, setBulkBusy] = useState(false);
  const routeAccountIdRef = useRef(accountId);
  const requestGenerationRef = useRef(0);
  routeAccountIdRef.current = accountId;

  useEffect(() => {
    const generation = ++requestGenerationRef.current;
    setStateAccountId(accountId);
    setAccountName("");
    setAccountStatus(null);
    setPolicies([]);
    setSelectedCode(null);
    setLoading(true);
    setError("");
    setNotice(routeNotice);
    setSelectedCodes(new Set());
    setSearch("");
    setDomain("");
    setBulkBusy(false);
    Promise.all([api.getAccount(accountId), api.listPolicies(accountId)])
      .then(([account, rows]) => {
        if (requestGenerationRef.current !== generation || routeAccountIdRef.current !== accountId)
          return;
        const initialFilter =
          !requestedApiCode && rows.some((policy) => policy.enabled) ? "enabled" : "all";
        setAccountName(account.name);
        setAccountStatus(account.status);
        setPolicies(rows);
        setFilter(initialFilter);
        setSearch(requestedApiCode);
        setSelectedCode(
          requestedApiCode || (rows.find((policy) => policy.enabled) ?? rows[0])?.apiCode || null,
        );
      })
      .catch((caught) => {
        if (requestGenerationRef.current === generation && routeAccountIdRef.current === accountId)
          setError(caught instanceof ApiError ? caught.message : "接口策略加载失败");
      })
      .finally(() => {
        if (requestGenerationRef.current === generation && routeAccountIdRef.current === accountId)
          setLoading(false);
      });
    return () => {
      if (requestGenerationRef.current === generation) {
        requestGenerationRef.current += 1;
      }
    };
  }, [accountId, routeNotice, reload, requestedApiCode]);

  const stateMatchesRoute = stateAccountId === accountId;
  const currentPolicies = stateMatchesRoute ? policies : [];
  const enabledCount = currentPolicies.filter((policy) => policy.enabled).length;
  const scheduledCount = currentPolicies.filter(
    (policy) => policy.enabled && policy.scheduleMode !== "manual_only",
  ).length;
  const pendingCount = currentPolicies.length - enabledCount;
  const blockedCount =
    accountStatus === "active" ? 0 : currentPolicies.filter((policy) => policy.enabled).length;
  const filtered = currentPolicies.filter((policy) => {
    const term = search.trim().toLowerCase();
    const matchesSearch =
      !term ||
      policy.name.toLowerCase().includes(term) ||
      policy.apiCode.toLowerCase().includes(term);
    const matchesFilter =
      filter === "all" ||
      (filter === "enabled" && policy.enabled) ||
      (filter === "scheduled" && policy.enabled && policy.scheduleMode !== "manual_only") ||
      (filter === "pending" && !policy.enabled) ||
      (filter === "blocked" && accountStatus !== "active" && policy.enabled);
    const matchesDomain = !domain || policy.domain === domain;
    return matchesSearch && matchesFilter && matchesDomain;
  });
  const selected =
    filtered.find((policy) => policy.apiCode === selectedCode) ?? filtered[0] ?? null;
  const domains = Array.from(new Set(currentPolicies.map((policy) => policy.domain))).sort();
  const groupedPolicies = Array.from(
    filtered.reduce((groups, policy) => {
      const rows = groups.get(policy.domain) ?? [];
      rows.push(policy);
      groups.set(policy.domain, rows);
      return groups;
    }, new Map<string, ApiPolicy[]>()),
  );
  const summaryItems: Array<{ count: number; filter: PolicyFilter; label: string }> = [
    { count: enabledCount, filter: "enabled", label: "已启用" },
    { count: currentPolicies.length, filter: "all", label: "全部接口" },
    { count: scheduledCount, filter: "scheduled", label: "自动计划" },
    { count: pendingCount, filter: "pending", label: "未启用" },
    { count: blockedCount, filter: "blocked", label: "运行受阻" },
  ];

  const selectedPolicies = currentPolicies.filter((policy) => selectedCodes.has(policy.apiCode));
  const hiddenSelectionCount = selectedPolicies.filter(
    (policy) => !filtered.includes(policy),
  ).length;

  async function applyBulk(enabled: boolean) {
    if (!csrfToken || !canEdit || bulkBusy || selectedCodes.size === 0) return;
    if (selectedCodes.size > MAX_BATCH_POLICIES) {
      setError("一次最多设置 100 个接口，请减少选择后保存。");
      return;
    }
    if (enabled && selectedPolicies.some((policy) => !policy.catalogEnabled)) {
      setError("所选接口包含平台停用项，请取消选择后保存。");
      return;
    }
    const generation = requestGenerationRef.current;
    const isCurrent = () =>
      requestGenerationRef.current === generation && routeAccountIdRef.current === accountId;
    setBulkBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await api.batchUpdatePolicies(
        accountId,
        selectedPolicies.map((policy) => ({
          apiCode: policy.apiCode,
          ...buildPolicyUpdate(policy, { enabled }),
        })),
        csrfToken,
      );
      if (!isCurrent()) return;
      const updates = new Map(updated.map((policy) => [policy.apiCode, policy]));
      setPolicies((current) => current.map((policy) => updates.get(policy.apiCode) ?? policy));
      setSelectedCodes(new Set());
      setNotice(`${updated.length} 个接口策略已批量保存。`);
    } catch (caught) {
      if (isCurrent()) setError(caught instanceof ApiError ? caught.message : "批量策略保存失败");
    } finally {
      if (isCurrent()) setBulkBusy(false);
    }
  }

  async function savePolicy(input: ApiPolicyUpdateInput) {
    if (!selected || !csrfToken) return;
    const targetAccountId = accountId;
    const targetApiCode = selected.apiCode;
    const generation = requestGenerationRef.current;
    setError("");
    setNotice("");
    try {
      const updated = await api.updatePolicy(targetAccountId, targetApiCode, input, csrfToken);
      if (
        requestGenerationRef.current !== generation ||
        routeAccountIdRef.current !== targetAccountId
      )
        return;
      setPolicies((current) =>
        current.map((item) => (item.apiCode === updated.apiCode ? updated : item)),
      );
      setNotice(`“${updated.name}”策略已保存。`);
    } catch (caught) {
      if (
        requestGenerationRef.current !== generation ||
        routeAccountIdRef.current !== targetAccountId
      )
        return;
      setError(caught instanceof ApiError ? caught.message : "策略保存失败");
    }
  }

  return (
    <AppShell>
      <main className="policy-page" data-node-id="3:2">
        <header className="page-heading policy-heading">
          <div>
            <small>接入管理 / {stateMatchesRoute && accountName ? accountName : "账号概览"}</small>
            <h1>同步接口</h1>
          </div>
          <Link
            className="action-link action-link--neutral"
            to={returnNavigation.path}
            state={returnNavigation.state}
          >
            {returnNavigation.label}
          </Link>
        </header>
        <nav aria-label="账号管理导航" className="account-workspace-nav">
          <Link to={`/accounts/${accountId}`}>账号概览</Link>
          <Link aria-current="page" className="active" to={`/accounts/${accountId}/policies`}>
            同步接口
          </Link>
        </nav>
        <p>
          管理接口可用范围。执行周期统一在同步任务中配置。{" "}
          <Link to={`/jobs/plans?account=${accountId}`}>查看定时计划</Link>
        </p>
        <section aria-label="同步接口筛选" className="policy-summary">
          {summaryItems.map((item) => (
            <Button
              disabled={bulkBusy}
              aria-label={`${item.label} ${item.count}`}
              aria-pressed={filter === item.filter}
              className={filter === item.filter ? "active" : ""}
              key={item.filter}
              type={filter === item.filter ? "primary" : "default"}
              onClick={() => setFilter(item.filter)}
            >
              <span>{item.label}</span>
              <strong>{item.count}</strong>
            </Button>
          ))}
        </section>
        <section className="policy-toolbar">
          <Input.Search
            disabled={bulkBusy}
            aria-label="搜索同步接口"
            placeholder="搜索接口名称或 API code"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <Select
            disabled={bulkBusy}
            aria-label="按业务域筛选"
            options={[
              { label: "全部业务域", value: "" },
              ...domains.map((item) => ({ label: businessDomainLabel(item), value: item })),
            ]}
            value={domain}
            virtual={false}
            onChange={setDomain}
          />
          <span className="policy-result-count">
            当前显示 {filtered.length} / {currentPolicies.length}
          </span>
          {canEdit && filtered.length ? (
            <Button
              className="text-button"
              type="text"
              disabled={bulkBusy}
              onClick={() =>
                setSelectedCodes(
                  (current) =>
                    new Set([
                      ...current,
                      ...filtered
                        .filter((policy) => policy.catalogEnabled)
                        .map((policy) => policy.apiCode),
                    ]),
                )
              }
            >
              全选当前结果
            </Button>
          ) : null}
          <span>{canEdit ? "选择接口后可批量设置" : "只读权限"}</span>
        </section>
        {canEdit && selectedCodes.size > 0 && !loading ? (
          <section className="policy-bulk-bar policy-schedule-bar" aria-label="批量策略操作">
            <strong>
              已选择 {selectedCodes.size} 个接口（每次最多 {MAX_BATCH_POLICIES} 个）
            </strong>
            {hiddenSelectionCount > 0 ? (
              <span>其中 {hiddenSelectionCount} 个被当前筛选隐藏</span>
            ) : null}
            <Button
              disabled={bulkBusy}
              className="text-button"
              type="text"
              onClick={() => setSelectedCodes(new Set())}
            >
              清空选择
            </Button>
            {selectedPolicies.some(
              (policy) => !policy.enabled && policy.scheduleMode !== "manual_only",
            ) ? (
              <p>启用后将恢复所选接口原有的定时设置。</p>
            ) : null}
            <p>
              仅修改接口启停状态，保留原周期和时间。停用后不再创建新任务，正在执行的任务不受影响。
            </p>
            <Button
              disabled={
                bulkBusy || selectedCodes.size === 0 || selectedCodes.size > MAX_BATCH_POLICIES
              }
              loading={bulkBusy}
              type="primary"
              onClick={() => void applyBulk(true)}
            >
              批量启用
            </Button>
            <Button
              disabled={
                bulkBusy || selectedCodes.size === 0 || selectedCodes.size > MAX_BATCH_POLICIES
              }
              onClick={() => void applyBulk(false)}
            >
              批量停用
            </Button>
          </section>
        ) : null}
        {notice ? (
          <Alert className="page-success" role="status" title={notice} type="success" />
        ) : null}
        {error ? (
          <Alert
            className="page-alert"
            showIcon
            title={error}
            type="error"
            action={
              currentPolicies.length === 0 ? (
                <Button onClick={() => setReload((current) => current + 1)}>重新加载</Button>
              ) : undefined
            }
          />
        ) : null}
        {canEdit &&
        !loading &&
        stateMatchesRoute &&
        accountStatus === "active" &&
        enabledCount > 0 &&
        returnNavigation.path.indexOf("/jobs/new") !== 0 ? (
          <section className="policy-next-step" aria-label="同步接口状态">
            <div>
              <span>配置可用</span>
              <strong>{enabledCount} 个接口已启用</strong>
              <p>需要立即执行时，进入任务预览确认日期范围。</p>
            </div>
            <Link
              className="action-link action-link--primary"
              to={`/jobs/new?accountId=${accountId}`}
              state={{
                from: `${location.pathname}${location.search}`,
                backLabel: "返回同步接口",
                returnState: location.state,
              }}
            >
              预览并发起同步
            </Link>
          </section>
        ) : null}
        <section className="policy-workspace">
          <div className="policy-list">
            <div className="policy-table-head">
              <span>接口</span>
              <span>业务域</span>
              <span>状态</span>
              <span>同步策略</span>
            </div>
            {loading || !stateMatchesRoute ? (
              <div className="empty-state">
                <Spin description="正在加载接口策略…" />
              </div>
            ) : null}
            {!loading && !error && stateMatchesRoute && filtered.length === 0 ? (
              <Empty
                className="empty-state"
                description={
                  currentPolicies.length === 0
                    ? "暂无可配置接口，请在接口中心查看平台接入状态。"
                    : "没有符合条件的接口，可清除搜索或选择全部接口。"
                }
              />
            ) : null}
            {groupedPolicies.map(([domainName, rows]) => (
              <PolicyDomainGroup
                accountId={accountId}
                accountStatus={accountStatus}
                canEdit={canEdit}
                busy={bulkBusy}
                domainName={domainName}
                initiallyOpen={
                  filter !== "all" || Boolean(search || domain) || rows.some((row) => row.enabled)
                }
                key={`${accountId}-${filter}-${domainName}`}
                policies={rows}
                selectedCode={selected?.apiCode ?? null}
                selectedCodes={selectedCodes}
                onSave={savePolicy}
                onSelect={setSelectedCode}
                onToggleSelected={(apiCode, checked) =>
                  setSelectedCodes((current) => {
                    const next = new Set(current);
                    if (checked) {
                      next.add(apiCode);
                    } else {
                      next.delete(apiCode);
                    }
                    return next;
                  })
                }
              />
            ))}
          </div>
        </section>
      </main>
    </AppShell>
  );
}
