import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Empty, Spin, Tag } from "antd";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { FailedRequest, SyncRunLog } from "../api/types";
import { getApiErrorMessage, statusLabel } from "../pages/m3Utils";

export function JobRunDiagnostics({
  runId,
  batchNo,
}: {
  runId: number | string;
  batchNo?: string | null;
}) {
  const logsRequestRef = useRef(0);
  const failedRequestsRequestRef = useRef(0);
  const [logs, setLogs] = useState<SyncRunLog[]>([]);
  const [failedRequests, setFailedRequests] = useState<FailedRequest[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);
  const [failedRequestsLoading, setFailedRequestsLoading] = useState(true);
  const [logsError, setLogsError] = useState("");
  const [failedRequestsError, setFailedRequestsError] = useState("");

  const loadLogs = useCallback(async () => {
    const requestId = ++logsRequestRef.current;
    setLogsLoading(true);
    setLogsError("");
    try {
      const page = await api.listSyncRunLogs(runId);
      if (logsRequestRef.current === requestId) setLogs(page.items);
    } catch (caught) {
      if (logsRequestRef.current === requestId) {
        setLogsError(getApiErrorMessage(caught, "接口日志加载失败，请稍后重试"));
      }
    } finally {
      if (logsRequestRef.current === requestId) setLogsLoading(false);
    }
  }, [runId]);

  const loadFailedRequests = useCallback(async () => {
    const requestId = ++failedRequestsRequestRef.current;
    setFailedRequestsLoading(true);
    setFailedRequestsError("");
    try {
      const page = await api.listFailedRequests(runId);
      if (failedRequestsRequestRef.current === requestId) setFailedRequests(page.items);
    } catch (caught) {
      if (failedRequestsRequestRef.current === requestId) {
        setFailedRequestsError(getApiErrorMessage(caught, "失败请求加载失败，请稍后重试"));
      }
    } finally {
      if (failedRequestsRequestRef.current === requestId) setFailedRequestsLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    setLogs([]);
    setFailedRequests([]);
    void loadLogs();
    void loadFailedRequests();
    return () => {
      logsRequestRef.current += 1;
      failedRequestsRequestRef.current += 1;
    };
  }, [loadFailedRequests, loadLogs]);

  return (
    <section
      className="m3-card job-diagnostics"
      id="job-diagnostics"
      aria-labelledby="job-diagnostics-title"
    >
      <div className="m3-card-heading">
        <div>
          <h2 id="job-diagnostics-title">批次诊断</h2>
          <p className="muted-copy">
            当前查看{batchNo ? `批次 ${batchNo}` : "所选批次"} 的接口日志和失败请求。
          </p>
        </div>
        <Link className="m3-link" to={`/runs/${runId}`}>
          查看完整技术日志
        </Link>
      </div>
      <div className="job-diagnostics-grid">
        <div>
          <h3>接口日志</h3>
          {logsLoading ? <Spin description="正在加载接口日志…" size="small" /> : null}
          {logsError ? (
            <Alert
              action={<Button onClick={() => void loadLogs()}>重试接口日志</Button>}
              title={logsError}
              type="error"
            />
          ) : null}
          {!logsLoading && !logsError ? (
            logs.length ? (
              <ul>
                {logs.slice(0, 5).map((log) => (
                  <li key={String(log.id)}>
                    <strong>{log.apiCode}</strong>
                    <span>
                      <Tag>{statusLabel(log.status)}</Tag>
                      {log.message ? ` · ${log.message}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty description="暂无接口日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )
          ) : null}
        </div>
        <div>
          <h3>失败请求</h3>
          {failedRequestsLoading ? <Spin description="正在加载失败请求…" size="small" /> : null}
          {failedRequestsError ? (
            <Alert
              action={<Button onClick={() => void loadFailedRequests()}>重试失败请求</Button>}
              title={failedRequestsError}
              type="error"
            />
          ) : null}
          {!failedRequestsLoading && !failedRequestsError ? (
            failedRequests.length ? (
              <ul>
                {failedRequests.slice(0, 5).map((item) => (
                  <li key={String(item.id)}>
                    <strong>{item.apiCode}</strong>
                    <span>{item.errorMessage ?? item.errorCode ?? "请求失败"}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty description="本次运行没有失败请求" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )
          ) : null}
        </div>
      </div>
    </section>
  );
}
