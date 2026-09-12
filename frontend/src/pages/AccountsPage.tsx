import { useEffect, useState } from "react";
import { Alert, Button, Empty, Input, Spin, Tag } from "antd";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { JijiaAccount } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { formatAccountDate, getAccountReadiness } from "./accountReadiness";
import { statusLabel } from "./m3Utils";

type AccountFilter = "all" | "attention" | "ready" | "inactive";

export function AccountsPage() {
  const { user } = useAuth();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const canEdit = user?.role === "admin" || user?.role === "operator";
  const accountNotice = (location.state as { accountNotice?: string } | null)?.accountNotice ?? "";
  const [accounts, setAccounts] = useState<JijiaAccount[]>([]);
  const requestedFilter = searchParams.get("filter");
  const filter: AccountFilter =
    requestedFilter === "attention" || requestedFilter === "inactive"
      ? requestedFilter
      : requestedFilter === "ready" || requestedFilter === "active"
        ? "ready"
        : "all";
  const search = searchParams.get("q") ?? "";
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .listAccounts()
      .then((rows) => {
        if (active) setAccounts(rows);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof ApiError ? caught.message : "账号数据加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reload]);

  const accountRows = accounts.map((account) => ({
    account,
    readiness: getAccountReadiness(account, canEdit),
  }));
  const counts = {
    all: accountRows.length,
    attention: accountRows.filter(({ readiness }) => readiness.tone === "attention").length,
    ready: accountRows.filter(
      ({ account, readiness }) =>
        account.status === "active" && readiness.scopeReady && readiness.tone !== "attention",
    ).length,
    inactive: accountRows.filter(({ account }) => account.status === "inactive").length,
  };
  const filteredRows = accountRows.filter(({ account, readiness }) => {
    const term = search.trim().toLowerCase();
    const matchesSearch =
      !term ||
      account.name.toLowerCase().includes(term) ||
      account.maskedAppId.toLowerCase().includes(term);
    const matchesFilter =
      filter === "all" ||
      (filter === "attention" && readiness.tone === "attention") ||
      (filter === "ready" &&
        account.status === "active" &&
        readiness.scopeReady &&
        readiness.tone !== "attention") ||
      (filter === "inactive" && account.status === "inactive");
    return matchesSearch && matchesFilter;
  });

  const filterLabels: Record<AccountFilter, string> = {
    all: "全部",
    attention: "需处理",
    ready: "可同步",
    inactive: "已停用",
  };
  const listQuery = searchParams.toString();
  const listPath = listQuery ? `/accounts?${listQuery}` : "/accounts";
  const returnNavigation = {
    from: listPath,
    backLabel: "返回账号列表",
    returnState: location.state,
  };

  function updateSearch(value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set("q", value);
    else next.delete("q");
    setSearchParams(next, { replace: true, state: location.state });
  }

  function updateFilter(nextFilter: AccountFilter) {
    const next = new URLSearchParams(searchParams);
    if (nextFilter === "all") next.delete("filter");
    else next.set("filter", nextFilter);
    setSearchParams(next, { replace: true, state: location.state });
  }

  function clearFilters() {
    setSearchParams({}, { replace: true, state: location.state });
  }

  function retryLoad() {
    setLoading(true);
    setError("");
    setReload((value) => value + 1);
  }

  return (
    <AppShell>
      <main className="accounts-page" data-node-id="38:300">
        <header className="page-heading">
          <div>
            <h1>接入管理</h1>
          </div>
          {canEdit ? (
            <Link
              className="action-link action-link--primary account-create-link"
              state={returnNavigation}
              to="/accounts/new"
            >
              ＋&nbsp;&nbsp;接入新账号
            </Link>
          ) : null}
        </header>

        <section className="account-toolbar account-toolbar--overview" aria-label="账号筛选">
          <Input.Search
            aria-label="搜索账号"
            placeholder="搜索账号名称或 appId 尾号"
            value={search}
            onChange={(event) => updateSearch(event.target.value)}
          />
          {(Object.keys(filterLabels) as AccountFilter[]).map((item) => (
            <Button
              aria-pressed={filter === item}
              className={filter === item ? "active" : ""}
              key={item}
              type={filter === item ? "primary" : "default"}
              onClick={() => updateFilter(item)}
            >
              {filterLabels[item]} {counts[item]}
            </Button>
          ))}
          <span>{canEdit ? "可管理账号" : "只读权限"}</span>
        </section>

        {accountNotice ? (
          <Alert className="page-success" role="status" title={accountNotice} type="success" />
        ) : null}
        {error ? (
          <Alert
            action={
              <Button loading={loading} onClick={retryLoad}>
                重试加载
              </Button>
            }
            className="page-alert"
            showIcon
            title={error}
            type="error"
          />
        ) : null}

        <section className="account-overview-table" aria-label="数据源账号列表">
          <header>
            <div>
              <strong>数据源账号</strong>
            </div>
            <span>共 {filteredRows.length} 个结果</span>
          </header>
          <div className="account-overview-head" aria-hidden="true">
            <span>账号</span>
            <span>当前状态</span>
            <span>同步范围</span>
            <span>最近同步</span>
            <span>下一步</span>
          </div>
          <div className="account-overview-rows">
            {loading ? (
              <div className="empty-state">
                <Spin description="正在加载账号…" />
              </div>
            ) : null}
            {!loading && !error && filteredRows.length === 0 ? (
              <Empty
                className="empty-state"
                description={accounts.length ? "没有符合条件的账号" : "尚未接入积加账号"}
              >
                {canEdit && accounts.length === 0 ? (
                  <Link
                    className="action-link action-link--primary"
                    state={returnNavigation}
                    to="/accounts/new"
                  >
                    接入第一个账号
                  </Link>
                ) : accounts.length > 0 && (search || filter !== "all") ? (
                  <Button type="link" onClick={clearFilters}>
                    清除筛选
                  </Button>
                ) : null}
              </Empty>
            ) : null}
            {filteredRows.map(({ account, readiness }) => (
              <div className="account-overview-row" key={account.id}>
                <span className="account-overview-name">
                  <Link state={returnNavigation} to={`/accounts/${account.id}`}>
                    {account.name}
                  </Link>
                  <small>appId · {account.maskedAppId}</small>
                </span>
                <span>
                  <Tag className={`readiness-badge readiness-badge--${readiness.tone}`}>
                    {readiness.label}
                  </Tag>
                  <small>{readiness.description}</small>
                </span>
                <span>
                  <strong>{account.enabledPolicyCount ?? 0} 个接口</strong>
                  <small>
                    {!readiness.scopeReady
                      ? "尚未配置"
                      : account.scheduledPolicyCount
                        ? `${account.scheduledPolicyCount} 个自动计划`
                        : "仅手动执行"}
                  </small>
                </span>
                <span>
                  <strong>
                    {account.latestJobStatus ? statusLabel(account.latestJobStatus) : "暂无记录"}
                  </strong>
                  <small>{formatAccountDate(account.latestJobAt, "尚未发起同步")}</small>
                </span>
                <span className="account-overview-action">
                  {readiness.primaryActionTarget ? (
                    <Link state={returnNavigation} to={readiness.primaryActionTarget}>
                      {readiness.primaryActionLabel}
                      <i>→</i>
                    </Link>
                  ) : (
                    <strong>{readiness.primaryActionLabel}</strong>
                  )}
                </span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </AppShell>
  );
}
