import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Empty, Input, Select, Spin, Table, type TableColumnsType } from "antd";
import { Link, useLocation, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { RawDataDetail, RawDataVersion } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { SourceBackLink } from "../components/SourceBackLink";
import { formatDate, getApiErrorMessage, timeZoneNote } from "./m3Utils";

function flattenJson(value: unknown, path = "$", result: Record<string, string> = {}) {
  if (value !== null && typeof value === "object") {
    const entries = Array.isArray(value)
      ? value.map((item, index) => [String(index), item] as const)
      : Object.entries(value);
    if (entries.length === 0) result[path] = Array.isArray(value) ? "[]" : "{}";
    entries.forEach(([key, item]) => flattenJson(item, `${path}.${key}`, result));
  } else {
    result[path] = JSON.stringify(value);
  }
  return result;
}

export function RawDataDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const { user } = useAuth();
  const [data, setData] = useState<RawDataDetail | null>(null);
  const [versions, setVersions] = useState<RawDataVersion[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [versionsLoading, setVersionsLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [versionsError, setVersionsError] = useState("");
  const [jsonSearch, setJsonSearch] = useState("");
  const [copyMessage, setCopyMessage] = useState("");
  const [compareLeft, setCompareLeft] = useState("current");
  const [compareRight, setCompareRight] = useState("");
  const [stateId, setStateId] = useState(id);
  const requestGenerationRef = useRef(0);
  const canViewRaw = user?.role === "admin" || user?.role === "operator";
  const stateMatchesRoute = stateId === id;
  const currentData = stateMatchesRoute && data && String(data.id) === id ? data : null;
  const currentVersions = useMemo(
    () => (stateMatchesRoute ? versions : []),
    [stateMatchesRoute, versions],
  );
  const currentNextCursor = stateMatchesRoute ? nextCursor : null;
  const currentError = stateMatchesRoute ? error : "";
  const currentVersionsError = stateMatchesRoute ? versionsError : "";
  const pageLoading = !stateMatchesRoute || loading || (data !== null && currentData === null);
  const currentVersionsLoading = !stateMatchesRoute || versionsLoading;
  const verificationTaskId = new URLSearchParams(location.search).get("taskId") ?? "";
  const verificationRunId = new URLSearchParams(location.search).get("runId") ?? "";
  const verificationBatchNo = new URLSearchParams(location.search).get("observedBatchNo") ?? "";
  const verificationTaskPath = verificationTaskId
    ? `/jobs/${encodeURIComponent(verificationTaskId)}${
        verificationRunId ? `?runId=${encodeURIComponent(verificationRunId)}#job-diagnostics` : ""
      }`
    : "/jobs";
  const verificationRunPath = verificationRunId
    ? `/runs/${encodeURIComponent(verificationRunId)}`
    : "/runs";
  const rawDataReturnPath = `/raw-data${location.search}`;

  const sourceState = {
    from: `${location.pathname}${location.search}`,
    backLabel: "返回原始记录",
    returnState: location.state,
  };
  const searchResults = useMemo(() => {
    if (!currentData?.rawJson || !jsonSearch.trim()) return [];
    const term = jsonSearch.trim().toLowerCase();
    return Object.entries(flattenJson(currentData.rawJson))
      .filter(([path, value]) => `${path} ${value}`.toLowerCase().includes(term))
      .slice(0, 100);
  }, [currentData?.rawJson, jsonSearch]);
  const compareRows = useMemo(() => {
    const payload = (key: string) =>
      key === "current"
        ? currentData?.rawJson
        : currentVersions.find((version) => String(version.id) === key)?.rawJson;
    if (!compareLeft || !compareRight) return [];
    const left = flattenJson(payload(compareLeft));
    const right = flattenJson(payload(compareRight));
    return [...new Set([...Object.keys(left), ...Object.keys(right)])]
      .filter((path) => left[path] !== right[path])
      .sort()
      .map((path) => ({ path, left: left[path] ?? "—", right: right[path] ?? "—" }));
  }, [compareLeft, compareRight, currentData?.rawJson, currentVersions]);

  useEffect(() => {
    if (!id) return undefined;
    const generation = ++requestGenerationRef.current;
    setStateId(id);
    setData(null);
    setVersions([]);
    setNextCursor(null);
    setLoading(true);
    setVersionsLoading(true);
    setLoadingMore(false);
    setError("");
    setVersionsError("");
    setJsonSearch("");
    setCopyMessage("");
    setCompareLeft("current");
    setCompareRight("");

    void api
      .getRawData(id)
      .then((detail) => {
        if (requestGenerationRef.current !== generation) return;
        setData(detail);
      })
      .catch((caught: unknown) => {
        if (requestGenerationRef.current !== generation) return;
        setError(getApiErrorMessage(caught, "原始数据详情加载失败，请稍后重试"));
      })
      .finally(() => {
        if (requestGenerationRef.current === generation) setLoading(false);
      });

    void api
      .listRawDataVersions(id)
      .then((history) => {
        if (requestGenerationRef.current !== generation) return;
        setVersions(history.items);
        setNextCursor(history.nextCursor ?? null);
      })
      .catch((caught: unknown) => {
        if (requestGenerationRef.current !== generation) return;
        setVersionsError(getApiErrorMessage(caught, "版本历史加载失败，请稍后重试"));
      })
      .finally(() => {
        if (requestGenerationRef.current === generation) setVersionsLoading(false);
      });

    return () => {
      if (requestGenerationRef.current === generation) {
        requestGenerationRef.current += 1;
      }
    };
  }, [id]);

  async function loadMoreVersions() {
    if (!id || !nextCursor) return;
    const targetId = id;
    const cursor = nextCursor;
    const generation = requestGenerationRef.current;
    setLoadingMore(true);
    setVersionsError("");
    try {
      const history = await api.listRawDataVersions(targetId, cursor);
      if (requestGenerationRef.current !== generation) return;
      setVersions((current) => [...current, ...history.items]);
      setNextCursor(history.nextCursor ?? null);
    } catch (caught) {
      if (requestGenerationRef.current !== generation) return;
      setVersionsError(getApiErrorMessage(caught, "版本历史加载失败"));
    } finally {
      if (requestGenerationRef.current === generation) setLoadingMore(false);
    }
  }

  async function copyCurrentJson() {
    if (currentData?.rawJson == null) return;
    setCopyMessage("");
    try {
      await navigator.clipboard.writeText(JSON.stringify(currentData.rawJson, null, 2));
      setCopyMessage("JSON 已复制");
    } catch {
      setCopyMessage("复制失败，请手动选择内容");
    }
  }

  const compareColumns: TableColumnsType<(typeof compareRows)[number]> = [
    {
      title: "字段路径",
      dataIndex: "path",
      key: "path",
      width: 280,
      render: (value: string) => <code>{value}</code>,
    },
    { title: "版本 A", dataIndex: "left", key: "left", width: 320 },
    { title: "版本 B", dataIndex: "right", key: "right", width: 320 },
  ];

  return (
    <AppShell>
      <main className="m3-page">
        <SourceBackLink
          fallbackPath={rawDataReturnPath}
          fallbackLabel={verificationBatchNo ? "返回批次数据" : "返回原始数据"}
        />
        {pageLoading ? (
          <div className="empty-state">
            <Spin description="正在加载原始数据详情…" />
          </div>
        ) : null}
        {currentError ? (
          <Alert className="page-alert" role="alert" title={currentError} showIcon type="error" />
        ) : null}
        {currentVersionsError ? (
          <Alert
            className="page-alert"
            role="alert"
            title={currentVersionsError}
            showIcon
            type="error"
          />
        ) : null}
        {!pageLoading && currentData ? (
          <>
            <header className="page-heading">
              <div>
                <h1>{currentData.apiCode}</h1>
                <p>
                  {currentData.accountName ??
                    (currentData.jijiaAccountId
                      ? `账号 ${currentData.jijiaAccountId}`
                      : "legacy 账号")}
                  {" · 主键 "}
                  {currentData.sourcePrimaryKey ?? "—"}
                </p>
              </div>
              {verificationTaskId || verificationRunId ? (
                <div className="heading-actions">
                  {verificationTaskId ? (
                    <Link
                      className="action-link action-link--neutral"
                      to={verificationTaskPath}
                      state={sourceState}
                    >
                      返回任务
                    </Link>
                  ) : null}
                  {verificationRunId ? (
                    <Link className="m3-link" to={verificationRunPath}>
                      查看技术日志
                    </Link>
                  ) : null}
                </div>
              ) : null}
            </header>
            <section className="m3-card m3-summary-grid" aria-label="原始数据摘要">
              <div>
                <span>数据日期</span>
                <strong>{currentData.dataDate ?? "—"}</strong>
              </div>
              <div>
                <span>数据哈希</span>
                <strong>{currentData.dataHash ?? "—"}</strong>
              </div>
              <div>
                <span>最后观察</span>
                <strong>{formatDate(currentData.lastObservedAt ?? currentData.updatedAt)}</strong>
              </div>
              <div>
                <span>历史版本</span>
                <strong>{currentData.versionCount ?? currentVersions.length}</strong>
              </div>
              <div>
                <span>观察次数</span>
                <strong>{currentData.observationCount ?? "—"}</strong>
              </div>
              <div>
                <span>最后批次</span>
                <strong>
                  <code>{currentData.batchNo ?? "—"}</code>
                </strong>
              </div>
            </section>
            <nav className="raw-lineage" aria-label="数据来源链路">
              {currentData.jijiaAccountId ? (
                <Link to={`/accounts/${currentData.jijiaAccountId}`} state={sourceState}>
                  {currentData.accountName ?? `账号 ${currentData.jijiaAccountId}`}
                </Link>
              ) : (
                <span>{currentData.accountName ?? "历史账号"}</span>
              )}
              <span>→</span>
              <span>{currentData.apiCode}</span>
              <span>→</span>
              <Link to={verificationTaskPath} state={sourceState}>
                {verificationTaskId ? `任务 #${verificationTaskId}` : "同步任务"}
              </Link>
              <span>→</span>
              {verificationRunId ? (
                <Link to={verificationRunPath} state={sourceState}>
                  批次 {verificationBatchNo || currentData.batchNo || "—"}
                </Link>
              ) : (
                <>
                  <span>批次 {currentData.batchNo || "—"}</span>
                  <Link to="/runs" state={sourceState}>
                    浏览执行记录
                  </Link>
                </>
              )}
              <span>→</span>
              <strong>记录 #{currentData.id}</strong>
            </nav>
            <p className="timezone-note">{timeZoneNote()}</p>
            {canViewRaw && currentData.rawJson != null ? (
              <section className="m3-card">
                <div className="m3-card-heading">
                  <h2>原始 JSON</h2>
                  <Button onClick={() => void copyCurrentJson()}>复制 JSON</Button>
                </div>
                {copyMessage ? (
                  <Alert
                    role="status"
                    title={copyMessage}
                    type={copyMessage.startsWith("复制失败") ? "error" : "success"}
                  />
                ) : null}
                <label className="raw-json-search" htmlFor="raw-json-search">
                  搜索字段或值
                  <Input
                    id="raw-json-search"
                    type="search"
                    value={jsonSearch}
                    onChange={(event) => setJsonSearch(event.target.value)}
                  />
                </label>
                {jsonSearch.trim() ? (
                  <div className="raw-search-results" aria-live="polite">
                    <strong>找到 {searchResults.length} 个匹配字段</strong>
                    {searchResults.length ? (
                      <ul>
                        {searchResults.map(([path, value]) => (
                          <li key={path}>
                            <code>{path}</code>
                            <span>{value}</span>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
                <details className="raw-json-disclosure" open>
                  <summary>当前版本 · 点击收起</summary>
                  <pre className="raw-json" aria-label="原始 JSON">
                    {JSON.stringify(currentData.rawJson, null, 2)}
                  </pre>
                </details>
              </section>
            ) : (
              <section className="m3-card">
                <h2>原始 JSON</h2>
                <p className="muted-copy">当前角色仅可查看元数据，完整原始 JSON 不可见。</p>
              </section>
            )}
          </>
        ) : null}
        <section className="m3-card">
          <h2>版本历史</h2>
          {canViewRaw && currentVersions.some((version) => version.rawJson != null) ? (
            <div className="raw-compare">
              <h3>字段级差异</h3>
              <div className="raw-compare-selectors">
                <label>
                  版本 A
                  <Select
                    aria-label="版本 A"
                    options={[
                      { label: "当前快照", value: "current" },
                      ...currentVersions.map((version) => ({
                        label: `版本 ${version.id} · ${version.batchNo ?? "—"}`,
                        value: String(version.id),
                      })),
                    ]}
                    value={compareLeft}
                    onChange={setCompareLeft}
                  />
                </label>
                <label>
                  版本 B
                  <Select
                    aria-label="版本 B"
                    options={[
                      { label: "选择版本", value: "" },
                      ...currentVersions.map((version) => ({
                        label: `版本 ${version.id} · ${version.batchNo ?? "—"}`,
                        value: String(version.id),
                      })),
                    ]}
                    value={compareRight}
                    onChange={setCompareRight}
                  />
                </label>
              </div>
              {compareRight ? (
                <p className="muted-copy">
                  {compareRows.length
                    ? `共 ${compareRows.length} 个字段发生变化`
                    : "所选版本没有字段差异"}
                </p>
              ) : null}
              {compareRows.length ? (
                <Table
                  aria-label="字段级差异"
                  columns={compareColumns}
                  dataSource={compareRows}
                  pagination={false}
                  rowKey="path"
                  scroll={{ x: 920 }}
                />
              ) : null}
            </div>
          ) : null}
          {currentVersionsLoading ? (
            <div className="empty-state">
              <Spin description="正在加载版本历史…" />
            </div>
          ) : !currentVersionsError && currentVersions.length === 0 ? (
            <Empty description="暂无版本历史" />
          ) : currentVersions.length > 0 ? (
            <ul className="m3-list raw-version-list">
              {currentVersions.map((version) => (
                <li key={String(version.id)}>
                  <details>
                    <summary>
                      <span>
                        <strong>{version.dataDate ?? "未标注日期"}</strong>
                        <small>批次 {version.batchNo ?? "—"}</small>
                      </span>
                      <span>
                        <small>{formatDate(version.observedAt)}</small>
                        <code>{version.dataHash ?? "—"}</code>
                      </span>
                    </summary>
                    {canViewRaw && version.rawJson != null ? (
                      <pre
                        className="raw-json raw-version-json"
                        aria-label={`版本 ${version.id} 原始 JSON`}
                      >
                        {JSON.stringify(version.rawJson, null, 2)}
                      </pre>
                    ) : (
                      <p className="muted-copy">当前角色不可查看该版本原文。</p>
                    )}
                  </details>
                </li>
              ))}
            </ul>
          ) : null}
          {currentNextCursor ? (
            <div className="load-more-row">
              <Button loading={loadingMore} onClick={() => void loadMoreVersions()}>
                {loadingMore ? "加载中…" : "加载更多版本"}
              </Button>
            </div>
          ) : null}
        </section>
      </main>
    </AppShell>
  );
}
