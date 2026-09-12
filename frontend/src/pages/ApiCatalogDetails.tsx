import { Alert, Collapse, Descriptions, Tag } from "antd";
import type { DescriptionsProps } from "antd";
import type { ApiCatalogItem, OfficialApiCatalogItem } from "../api/types";
import { formatDate, statusLabel } from "./m3Utils";

function CatalogTechnicalDetails({
  item,
  fields,
}: {
  item: Pick<ApiCatalogItem, "method" | "path">;
  fields: DescriptionsProps["items"];
}) {
  return (
    <Collapse
      items={[
        {
          key: "technical",
          label: "技术详情",
          children: (
            <Descriptions
              column={1}
              size="small"
              items={[
                {
                  key: "request",
                  label: "请求",
                  children: (
                    <code>
                      {item.method} {item.path}
                    </code>
                  ),
                },
                ...(fields ?? []),
              ]}
            />
          ),
        },
      ]}
    />
  );
}

export function ConnectedCatalogDetail({
  item,
  accountSelected,
}: {
  item: ApiCatalogItem;
  accountSelected: boolean;
}) {
  const fieldLabel = (value?: string) => value?.trim() || "未配置，使用整条 JSON / 哈希";
  return (
    <div className="catalog-detail">
      <p className="muted-copy">
        {item.apiCode} · 配置版本 v{item.configVersion ?? "—"}
      </p>
      <section>
        <h3>可获取的数据</h3>
        <p>{item.dataSummary ?? item.name}</p>
      </section>
      <section>
        <h3>{accountSelected ? "当前账号同步情况" : "全部账号汇总"}</h3>
        <Descriptions
          column={1}
          size="small"
          items={[
            {
              key: "platform",
              label: "平台状态",
              children: (
                <Tag color={item.platformEnabled ? "success" : "default"}>
                  {item.platformEnabled ? "平台启用" : "平台停用"}
                </Tag>
              ),
            },
            {
              key: "account",
              label: "账号状态",
              children: accountSelected
                ? item.accountEnabled
                  ? "已启用"
                  : "未启用"
                : "选择账号后查看",
            },
            {
              key: "run",
              label: "最近运行",
              children: item.recentRunStatus
                ? `${statusLabel(item.recentRunStatus)} · ${formatDate(item.recentRunAt)}`
                : "尚未运行",
            },
            {
              key: "records",
              label: "原始记录",
              children: `${(item.rawRecordCount ?? 0).toLocaleString()} 条`,
            },
          ]}
        />
      </section>
      {!item.platformEnabled && (
        <Alert showIcon type="warning" title="平台已停用此接口，账号配置不能恢复平台运行权限。" />
      )}
      {(item.canRunDirectly === false || item.upstreamApiCode) && (
        <Alert
          showIcon
          type="info"
          title={`需要上游接口 ${item.upstreamApiCode ?? "提供参数"}，请先完成依赖配置。`}
        />
      )}
      <CatalogTechnicalDetails
        item={item}
        fields={[
          {
            key: "official",
            label: "官方目录",
            children: item.officialExists ? `已关联文档 #${item.officialDocId ?? "—"}` : "未关联",
          },
          { key: "list", label: "列表字段", children: fieldLabel(item.listField) },
          { key: "pk", label: "业务主键", children: fieldLabel(item.primaryKeyField) },
          { key: "date", label: "数据日期", children: fieldLabel(item.dateField) },
          {
            key: "storage",
            label: "保存方式",
            children:
              item.storageMode === "history_on_change"
                ? "最新快照 + 变更历史"
                : "最新原始 JSON 快照",
          },
          {
            key: "window",
            label: "日期窗口",
            children: item.supportsDateWindow ? "支持" : "不支持",
          },
          {
            key: "upstream",
            label: "上游接口",
            children: item.upstreamApiCode || "无，可直接运行",
          },
          {
            key: "sensitive",
            label: "敏感响应",
            children: item.sensitive ? "是，详情访问受审计" : "未标记",
          },
        ]}
      />
    </div>
  );
}

export function OfficialCatalogDetail({
  item,
  classification,
  onSelectConfiguredApi,
}: {
  item: OfficialApiCatalogItem;
  classification: string;
  onSelectConfiguredApi: (apiCode: string) => void;
}) {
  return (
    <div className="catalog-detail">
      <p className="muted-copy">
        {item.menuPath} · 官方文档 #{item.docId ?? "—"}
      </p>
      <Tag className="catalog-detail-status" color={item.systemConfigured ? "success" : "default"}>
        {item.systemConfigured ? "已接入" : "待接入"}
      </Tag>
      <section className="catalog-condition-panel">
        <h3>接入条件</h3>
        <dl>
          <div>
            <dt>条件分类</dt>
            <dd>{classification}</dd>
          </div>
          <div>
            <dt>当前评估</dt>
            <dd>{item.executionReason}</dd>
          </div>
        </dl>
      </section>
      {item.methodMismatch && (
        <Alert
          showIcon
          type="warning"
          title="已发布配置与官方目录的请求方法不一致，需要人工复核后再调整。"
        />
      )}
      <CatalogTechnicalDetails
        item={item}
        fields={[
          {
            key: "fields",
            label: "业务必填参数",
            children: item.businessRequiredFields.join("、") || "无",
          },
          {
            key: "shape",
            label: "响应形态",
            children: item.hasPageResponse
              ? "分页"
              : item.hasListResponse
                ? "列表"
                : "单对象或待确认",
          },
          {
            key: "sensitive",
            label: "敏感字段",
            children: item.sensitive ? "存在，接入前需审核" : "未识别",
          },
        ]}
      />
      {item.configuredApiCodes.length > 0 && (
        <section className="catalog-configured-apis">
          <div className="catalog-detail-section-heading">
            <div>
              <h3>已接入接口</h3>
              <p>选择接口后查看系统配置与运行状态。</p>
            </div>
            <span>{item.configuredApiCodes.length} 个</span>
          </div>
          <div className="catalog-configured-api-list">
            {item.configuredApiCodes.map((code) => (
              <button
                key={code}
                type="button"
                aria-label={`查看已接入接口：${code}`}
                onClick={() => onSelectConfiguredApi(code)}
              >
                <code>{code}</code>
                <span aria-hidden="true">查看</span>
              </button>
            ))}
          </div>
        </section>
      )}
      {!item.systemConfigured && (
        <section>
          <h3>如何接入</h3>
          <p>
            由维护人员核对官方文档和接入条件，完成适配、验证与受控发布后，再配置账号接口。官方目录存在不代表当前可运行。
          </p>
        </section>
      )}
    </div>
  );
}
