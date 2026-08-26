# jijia-polardb-sync

这是“积加开放平台 -> 阿里云 PolarDB MySQL”的 Python 数据同步项目。当前阶段已支持 dry-run、mock 落库验证、accessToken 获取，以及多个已验证接口的同步。

## 目录结构

```text
jijia-polardb-sync/
  app/
    main.py
    config.py
    auth.py
    api_client.py
    sync_engine.py
    db.py
    logger.py
    retry.py
    transformers/
  config/
    api_config.example.yaml
  docs/
  logs/
  sql/
    init_tables.sql
  .env.example
  requirements.txt
  README.md
```

## 环境变量

复制 `.env.example` 为 `.env`，再按真实环境填写。不要把 `.env` 提交到代码仓库。

| 变量 | 说明 |
| --- | --- |
| `APP_ENV` | 运行环境，例如 `local`、`prod` |
| `LOG_LEVEL` | 日志级别 |
| `LOG_DIR` | 日志目录 |
| `JIJIA_BASE_URL` | 积加开放平台 API 域名 |
| `JIJIA_OPEN_GATEWAY_PREFIX` | 积加开放平台开放接口网关前缀，默认 `/api/open` |
| `JIJIA_APP_ID` | 积加应用 ID |
| `JIJIA_APP_KEY` | 积加应用 Key |
| `JIJIA_TOKEN_URL` | 获取 accessToken 的接口路径 |
| `JIJIA_TOKEN_CACHE_PATH` | accessToken 本地缓存路径，默认 `logs/token_cache.json` |
| `DB_HOST` | PolarDB MySQL 地址 |
| `DB_PORT` | PolarDB MySQL 端口 |
| `DB_NAME` | 数据库名 |
| `DB_USER` | 数据库用户 |
| `DB_PASSWORD` | 数据库密码 |
| `API_CONFIG_PATH` | API YAML 配置路径 |

## PolarDB 初始化

先在 PolarDB MySQL 中创建数据库，然后执行初始化 SQL：

```bash
mysql -h <POLARDB_HOST> -P 3306 -u <DB_USER> -p <DB_NAME> < sql/init_tables.sql
```

`sql/init_tables.sql` 会创建：

- `api_config`
- `sync_batch`
- `sync_api_log`
- `raw_api_data`
- `sync_checkpoint`
- `failed_request_log`

其中 `raw_api_data.raw_json` 使用 MySQL `JSON` 类型，用来保存原始 API 返回。

## API 配置

示例文件在 `config/api_config.example.yaml`。该文件当前同时包含少量占位示例和已按积加开放平台文档验证过的真实接口配置；新增或调整接口时仍需以真实文档和单接口验证结果为准。

新增 API 的基本步骤：

1. 在 YAML 的 `apis` 下新增一项。
2. 设置唯一的 `api_code`。
3. 填写真实 `path`、分页字段、主键字段和日期字段。
4. 如果接口没有稳定业务主键，将由后续同步逻辑使用 `data_hash` 去重。

对需要滚动日期窗口的接口，`params` 支持少量日期占位符：`{{ today }}`、`{{ yesterday }}` 和 `{{ days_ago:7 }}`。程序会在发起请求前展开为 `YYYY-MM-DD`。

对需要补历史窗口的接口，可以在 YAML 中增加 `date_window`，用 `default_start`、`days`、`start_field` 和 `end_field` 生成本次请求窗口；字段可写成 `model.reportStartDate` 这类点路径。同步成功后 checkpoint 会记录 `next_window_start`，下次运行从下一窗口继续；如果下一窗口已经晚于当前可同步日期，程序会跳过请求，避免严格限流接口空跑。`lag_days` 可让报表接口只同步昨天及更早完整日，避免当天数据未稳定时提前推进 checkpoint。该能力已用 `traffic_analysis_page`、`traffic_sku_analysis_page`、`product_analyze_multi_index_page`、`store_sales_performance_page`、`market_analyze_page`、`listing_analyze_page`、`listing_analyze_multi_index_page`、`sale_profit_page`、`profit_cost_analysis_page`、`financial_profit_analysis_page`、`financial_analysis_v2_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page` 和 `inventory_receipts_page` 做过真实单日窗口验证。若官方文档明确说明 total 无效，则不配置 `total_field`，checkpoint 会如实记录 `total_count=null`，不能伪造分页完整性。

## 本地运行

安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

执行第一阶段 dry-run：

```bash
python -m app.main
```

写入一批 mock 同步数据：

```bash
python -m app.main --mock-sync
```

运行 `--mock-sync` 前，需要先在数据库执行 `sql/init_tables.sql`，并在 `.env` 中配置测试库连接。

检查数据库连接：

```bash
python -m app.main --check-db
```

测试获取积加 accessToken：

```bash
python -m app.main --test-token
```

`--test-token` 会获取真实积加 accessToken，只会输出过期时间，不会打印 accessToken。程序会优先复用本地 token 缓存，缓存失效后才重新请求接口。

调试单个业务 API 并写入原始 JSON：

```bash
python -m app.main --test-api amazon_shop_page
```

`--test-api` 会请求真实积加业务接口并写入 `sync_batch`、`sync_api_log`、`raw_api_data`，适合开发阶段验证。

同步单个真实业务 API：

```bash
python -m app.main --sync-api amazon_shop_page
```

`--sync-api` 复用分页、`sync_checkpoint`、重试、失败日志和 token 缓存能力。

依赖上游参数的接口也先用 `--sync-api` 做小样本验证。例如 `product_detail` 会从已入库的 `product_page` 原始数据中取少量产品 ID 请求详情；`market_inventory_query` 会从已入库的 `product_inventory_page.raw_json` 提取 `sku` 和 `warehouseId` 请求站点库存分布；`procure_detail` 会从已入库的 `lot_no_page.raw_json` 提取少量 `poCode` 请求采购订单详情。参数来源也支持单层数组展开，例如 `raw_json.marketListVos[].marketId`；当公开文档要求数组入参而单次只传一个来源值时，可以在字段配置中设置 `wrap_in_list: true`。这类接口在证明缺失扫描或日增量边界前默认保持 `enabled: false`，不进入每天的 enabled 批量同步。文档 1177 的店铺名称查询使用该数组形态真实请求后仍返回 HTTP 400，已登记为 `defer_runtime_rejected`，在有新官方证据前不重复探测。

同步 YAML 中已启用的真实业务 API：

分页接口在扩大首次同步范围前，可先执行只读预检：

```bash
python -m app.main --probe-api supplier_sku_quote_page
```

`--probe-api` 只请求首页并输出总数、页大小、所需页数和实际请求次数；不创建数据库引擎，不写入同步表。

官方 `detail` 明确返回有效 `total` 且没有规定总页数上限时，可以省略 `page.max_pages`；同步引擎会在每页响应后按最新 `total` 继续分页，因此后续业务增长不需要人工修改页数。已有 `max_pages` 的接口继续保留原容量保护；省略上限的接口若缺失有效 `total`，会在首页 raw 写入前失败。

```bash
python -m app.main --sync-enabled
```

`--sync-enabled` 会读取 `config/api_config.example.yaml` 中 `enabled: true` 的接口，并在同一个 `sync_batch` 下逐个写入 `sync_api_log`。批次头会先提交，每个 API 使用独立事务提交 raw、log 和 checkpoint，最后再提交批次汇总状态，便于长任务运行时查看已完成接口。当前启用了 `amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`amazon_msku_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail` 和 `base_currency_query`。

会写数据库的入口会先获取 MySQL named lock `jijia_polardb_sync_task`，包括 `--mock-sync`、`--test-api`、`--sync-api`、`--sync-enabled` 和 `--sync-api-configs`。只读 `--probe-api` 不创建数据库连接，也不使用该互斥锁。

生成积加公开文档 API 覆盖矩阵：

```bash
python -m app.doc_catalog --review-config config/api_review_overrides.yaml --output config/jijia_api_catalog.generated.json --summary
```

该命令只读取公开文档目录和详情，不读取 `.env`，不请求真实业务接口。输出文件保存公开接口元数据、分类结果、本地配置覆盖状态和下一步执行分层，例如已配置、需参数源、需敏感审查、需风险复核或暂缓写操作。`config/api_review_overrides.yaml` 用来持久化鉴权专用、敏感凭证阻断、缺少参数源等人工审核终态；catalog 的 `summary.menu_progress` 会按板块统计已配置、终态暂缓和待审核数量，只有 `pending_review=0` 才标记 `closed=true`。

接入单个接口前，必须按 [`docs/jijia_api_document_access.md`](docs/jijia_api_document_access.md) 实时读取并核对官方 `detail` 契约。generated catalog 只用于定位和覆盖统计，不能代替完整官方文档。

基础数据文档 1177 的店铺名称查询和文档 1179 的仓库信息查询均使用已证明的真实上游站点 ID 单元素数组进行小样本验证，但首个请求都返回 HTTP 400；两者已登记为 `defer_runtime_rejected`，临时业务配置已清理，在有新官方证据前不重复探测或猜测其他数组编码。

基础数据文档 25 的用户列表已通过单次真实验证并保持 `enabled=false`。人员字段只保存到 `raw_api_data.raw_json`，日志和交接文档只记录聚合计数；13 位 `createdTime` 按 `Asia/Shanghai` 转换为 `data_date`，敏感接口失败时不保存响应正文或原始错误详情。

## ECS 部署

1. 在 ECS 安装 Python 3.11+ 和 MySQL 客户端。
2. 拉取或上传项目代码。
3. 创建虚拟环境并安装依赖。
4. 根据 `.env.example` 创建 `.env`。
5. 在 PolarDB 执行 `sql/init_tables.sql`。
6. 先运行 `python -m app.main` 确认配置文件可读取。
7. 先运行 `python -m app.main --sync-api amazon_shop_page` 验证真实单接口同步。
8. 再运行 `python -m app.main --sync-enabled` 验证启用接口批量同步。
9. 验证通过后再加入定时任务。

## cron 示例

当前启用接口同步可以用 cron 每天执行一次：

```cron
0 2 * * * cd /path/to/jijia-polardb-sync && /path/to/.venv/bin/python -m app.main --sync-enabled >> logs/cron.log 2>&1
```

当前 enabled 批量属于长任务，最近一次 45 个接口完整同步耗时 6924 秒。ECS 上的 cron 窗口应避免和其他重写入任务重叠。

## 查看日志

应用日志默认写入：

```text
logs/sync.log
```

同步完成后还会通过数据库表排查：

- `sync_batch`：每次同步批次
- `sync_api_log`：每个 API 的执行结果
- `failed_request_log`：失败请求明细

## 常见问题

### 当前支持哪些真实积加 API？

当前已验证并启用 `amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`amazon_msku_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail` 和 `base_currency_query`。
`storage_inbound_detail` 也属于当前 enabled 清单；`ship_transport_list` 已按当前官方 GET 契约完成真实验证并恢复 daily enabled，因此 enabled 总数为 46。

另有一批已完成小窗口或风险验证但默认未启用的接口，例如 `traffic_sku_analysis_page`、`product_analyze_multi_index_page`、`store_sales_performance_page`、`market_analyze_page`、`listing_analyze_page`、`listing_analyze_multi_index_page`、`sale_profit_page`、`allocation_detail_page`、`profit_cost_analysis_page`、`financial_profit_analysis_page`、`financial_analysis_v2_page`、`financial_analysis_columns_query`、`financial_analysis_month_v2_query`、`inventory_event_page`、`inventory_age_page` 和若干库存、SKU 映射、详情类接口。这些接口需先评估数据量、限流和业务风险，再决定是否进入每天的 enabled 批量同步。十三个新增统计候选均已通过 `commit_per_page` 单接口短事务验证；统计菜单 17 个文档接口已全部配置并完成真实验证，其中 3 个 enabled、14 个 disabled。`market_analyze_page`、`financial_analysis_columns_query` 和月度对象查询没有有效 total，因此 checkpoint 如实记录 `total_count=null`。短事务页写入如果被 SQLAlchemy 明确认定为失效连接，会利用幂等 upsert 换新连接重试一次；其他数据库错误仍直接失败。enabled 主链现已按配置复用该路径，但新增候选仍全部关闭，必须另行完成运行时长和业务风险评估后才能启用。

全平台当前 YAML 与 DB 均为 74 个配置、46 个 enabled；catalog 的 187 个公开文档接口中已配置 66 个，尚未配置 121 个。基础数据板块当前为 10 个已配置、5 个终态暂缓、1 个待审，仍未收口；新增的 `monthly_statement_amount_query` 和 `all_user_list` 均保持 disabled，没有扩大每日批量范围。
当前状态更新：全平台 YAML 与 DB 均为 75 个配置、46 个 enabled；catalog 的 187 个公开文档接口中已配置 67 个，尚未配置 120 个。基础数据板块为 11 个已配置、5 个终态暂缓、0 个待审，已按审核终态收口；这不表示该板块的全部接口都已配置。新增的 `monthly_statement_amount_query`、`all_user_list` 和 `file_file_url_query` 均保持 disabled，没有扩大每日批量范围。其中附件链接接口只使用已证明的真实附件 ID 小样本做 raw-only 备份，审核和日志不输出附件 ID 或链接。

产品板块已按审核终态收口：8 个接口已配置且 enabled，10 个接口有明确终态，待审为 0。文档 5070「查询变体属性」因没有真实 `attributeName` 参数来源登记为 `defer_no_param_source`，没有新增业务配置或发起真实请求；这同样不表示产品板块 18 个接口均已配置。

### accessToken 如何获取？

根据积加开放平台文档 `id=596`，获取 token 的文档路径是 `POST /api_token`，实际开放接口网关前缀是 `/api/open`，所以程序会请求 `/api/open/api_token`。请求体包含 `appId` 和 `appKey`，响应数据包含 `accessToken`、`expiresIn` 和 `expiresOut`。

程序会把 accessToken 缓存在 `logs/token_cache.json`，并提前 60 秒视为过期。该文件包含敏感 token，已在 `.gitignore` 中排除。

### 当前接入了哪个业务 API？

当前 enabled 清单与“当前支持哪些真实积加 API？”一致，共 46 个。各接口的文档 id、路径、分页和执行分层以 `config/api_config.example.yaml` 与 `config/jijia_api_catalog.generated.json` 为准。

### 如何运行测试？

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 示例 API 字段是否可以直接用于生产？

不能一概直接使用。`config/api_config.example.yaml` 中已有一批真实验证过的接口配置，也保留了少量占位示例；生产启用前应确认对应 `api_code` 已通过真实文档、单接口同步和数据库核验。

### 没有稳定业务主键怎么办？

后续同步逻辑会对原始 JSON 计算 `data_hash`，通过 `api_code + data_hash` 去重。

## 安全注意事项

- 不要提交 `.env`。
- 不要提交 `logs/token_cache.json`。
- 不要在 README、YAML 或 Python 文件中写真实密钥。
- PolarDB 账号建议使用最小权限。
- ECS 到 PolarDB 建议使用内网地址和安全组限制。

## 仓库板块进度

仓库板块已接入并真实验证供应商仓接口 `supplier_warehouse_page`（文档 64），保持 `enabled=false`。该接口无业务参数来源、使用 `id` 幂等和 `createDate` 业务日期，敏感失败详情会脱敏；本次账号返回空列表，已如实记录为成功的 1 次请求、0 条数据，不扩大每日批量范围。当前全平台 YAML/DB 为 76 个配置、46 个 enabled；catalog 为 68 个已配置，仓库板块尚有 3 个待审接口。

自营仓接口 `self_warehouse_page`（文档 212）也已真实验证并保持 `enabled=false`：1 次请求、27 条数据、0 失败；联系人类字段仅 raw 备份，`data_date` 如实为空。全平台当前为 77 个配置、46 个 enabled，仓库板块尚有 2 个待审接口。

仓库板块现已完成审核终态收口：文档 1035 因公开响应含服务商凭证字段暂缓，文档 1449 因必填 `rnType` 缺少可证明的真实参数来源暂缓。当前仓库板块为 4 个已配置、2 个 enabled、2 个终态暂缓、0 个待审；这表示审核收口，不表示 6 个接口都已配置。

## 库存板块进度

库存板块现已完成审核终态收口：9 个接口已配置（其中 8 个 enabled），4 个写操作继续暂缓；文档 1022 的日窗口真实请求已有 400/50099 证据，登记为 `defer_runtime_rejected`。当前库存板块为 5 个终态暂缓、0 个待审；这表示审核收口，不表示 14 个接口都已配置。
## 采购板块进度

采购订单列表接口 `procure_page`（文档 86，`POST /purchase/srm/procure/page`）已完成真实单接口验证，保持 `enabled=false`。分页字段在 `pageInfo.page`/`pageInfo.pagesize`，同步引擎现支持用点路径写入嵌套分页参数；本次只请求第 1 页，100 条数据均使用 `id` 主键和 `data_hash` 幂等，`updateTime` 生成 `data_date`。

供应商信息列表接口 `supplier_page`（文档 43，`POST /purchase/srm/supplier/page`）也已完成真实单接口验证，保持 `enabled=false`。成功批次 `sync_20260720_182049_479213` 为 1 次请求、27 条成功、0 失败；联系人、电话、邮箱和地址仅保存在 raw JSON，审核不输出其值，按 `data_hash` 幂等，`createdAt` 生成 `data_date`。当前 YAML/DB 均为 79 个配置、46 个 enabled，catalog 保留 187 个有效公开文档详情并离线重分类为 71 个已配置、46 个 enabled；采购板块为 7 个已配置、5 个 enabled、13 个终态暂缓、3 个待审，尚未收口。

供应商产品列表接口 `supplier_sku_quote_page`（文档 91，`POST /purchase/srm/supplierSkuQuote/page`）已配置为 `enabled=false`，使用 `id` 幂等、`createdAt` 生成 `data_date`，人员标识只做 raw 备份。首次一页验证批次 `sync_20260729_120154_588297` 已安全写入 100 条，但因配置的单页上限低于上游有效总量，被分页完整性保护标记为失败，未写 checkpoint；这不是上游拒绝，也不应表述为已验证成功。当前 YAML/DB 为 80 个配置、46 个 enabled，catalog 为 72 个已配置、46 个 enabled；采购板块为 8 个已配置、5 个 enabled、13 个终态暂缓、2 个待审，尚未收口。

经确认提高到两页后，批次 `sync_20260729_121333_642328` 仍由同一保护机制停止：2 次请求已安全写入 200 条，说明上游有效总量仍超过两页；没有 checkpoint 或失败请求记录。接口继续保持默认关闭，后续必须先确认新的受限页数，不能直接扩大到未知范围。

阶段 16AH 已完成实时 `total` 驱动配置和真实单接口验证：YAML/DB 均不再设置固定 `max_pages`，并启用 `commit_per_page=true`，接口仍保持 `enabled=false`。成功批次 `sync_20260729_151815_934165` 按运行时 `total` 自动请求 98 页，写入 9,727 条 raw；主键和 hash 均为 9,727 个，`data_date` 无空值，checkpoint 为第 98 页、98 次请求和 9,727 条，失败请求为 0。后续运行仍按当次最新 `total` 计算，不固定沿用 98 页。

阶段 16AI 已完成采购快捷入库查询接口的真实终态审核。官方文档 1080 规定 `POST /purchase/srm/quickInbound/query` 使用可选的字符串数组 `data`，最多 100 个采购单号；本次从已验证的 `procure_page.raw_json.code` 取得真实采购单号，只按官方单元素数组格式发出 1 次请求。批次 `sync_20260730_100043_263810` 收到 HTTP 400 后立即停止，没有重试或尝试其他数组编码，raw 和 checkpoint 均为 0；失败日志未保存请求参数、响应正文或敏感值。

该候选已登记为 `defer_runtime_rejected`，临时 YAML/DB 配置已清理，失败 batch/API log 保留。同步引擎保留显式 `wrap_in_list=true` 的顶层字段数组包装能力，未启用时仍保持原标量行为。当前 YAML/DB 均为 80 个配置、46 个 enabled，配置差异为 0；实时官方 catalog 已刷新为 189 个有效详情、72 个已配置、46 个 enabled，采购板块为 8 个已配置、5 个 enabled、14 个终态暂缓、1 个待审，尚未收口。

阶段 16AJ 已完成采购主体查询接口的敏感终态收口。官方文档 5262 规定 `POST /purchase/srm/purchaseSubject/list` 为无请求体、非分页的读取接口，但响应包含联系人、邮箱、电话、税号、地址、银行账户和公章图片链接等高敏感字段，因此登记为 `defer_sensitive_credentials`，未新增业务配置、未调用真实业务 API。

采购板块当前为 23 个文档接口、8 个已配置、5 个 enabled、15 个终态暂缓、0 个待审，`closed=true`。这表示采购板块审核终态已收口，不表示 23 个接口均已配置；全平台仍为 80 个 YAML/DB 配置、46 个 enabled，catalog 为 189 个有效详情、72 个已配置、46 个 enabled。

## 物流板块进度

阶段 16AK-A 已按实时官方文档修正 `ship_transport_list`（文档 3059）的本地配置：请求方法为 `GET`、每页最大 100、按 `data.total` 动态分页、限流间隔 1 秒，并在重新验证前保持 `enabled=false`。旧的固定 `max_pages=10` 已删除，不再把猜测页数作为长期上限。

唯一一次只读首页预检返回 `total_count=292`、`page_size=100`、`required_pages=3`、`request_count=1`，耗时 1.613 秒；本阶段没有运行 `--sync-api-configs`、`--sync-api` 或完整 `--sync-enabled`。因此本地 YAML/catalog 为 80 个配置、45 个 enabled，数据库仍保留上一快照 80/46，等待下一次写操作确认后再同步配置。

阶段 16AK-B 已完成 GET 单接口真实验证：`--sync-api-configs` 后 YAML/DB 均为 80 个配置、45 个 enabled，目标接口保持 `enabled=false`；批次 `sync_20260730_112541_515611` 按运行时 `total=292` 请求 3 页，292 条成功、0 失败。当前批次主键和 hash 均为 292 个，checkpoint 为第 3 页、3 次请求和 292 条，失败请求为 0。

`raw_api_data` 当前共保留 293 条：本批次覆盖 292 条，另有 1 条历史记录本次上游未返回。原始备份不主动删除历史对象；后续是否恢复该接口的 daily enabled，需单独确认。

阶段 16AK-C 已将验证通过的 `ship_transport_list` 恢复为 daily enabled：YAML、catalog 与 DB 均为 80 个配置、46 个 enabled，目标仍使用 GET、每页 100、实时 `data.total` 分页和 1 秒限流。本阶段只执行配置同步，没有调用业务接口或运行完整 `--sync-enabled`；latest batch、raw 和 checkpoint 均保持 16AK-B 的成功证据。

## 物流发货单预检

阶段 16AL-A 已按官方文档 1027 为 `delivery_page` 增加默认关闭的本地配置：`POST /fulfillment/ship/delivery/page`，每页 100、按 `data.total` 动态分页，不设置固定总页数；`id` 缺失时回退到 `data_hash` 幂等，`updateTime` 生成 `data_date`，人员、金额、单号和备注等业务敏感字段只保存在 raw JSON。唯一一次首页预检返回实时 `total=18162`，对应当前 182 页、1 次请求，耗时 5.065 秒。

本阶段未同步配置或写数据库，因此本地 YAML 为 81/46，DB 仍为 80/46，唯一差异是 `delivery_page`。下一阶段须单独确认后增加 `commit_per_page=true`、同步配置并只运行该接口；182 页只是本次 total 的计算结果，后续仍按运行时 total 自动适应业务增长。

阶段 16AL-B 已完成发货单列表的真实单接口验证。配置同步后 YAML/DB 均为 81 个配置、46 个 enabled；`delivery_page` 保持关闭、无固定 `max_pages`，使用 `commit_per_page=true` 按页短事务。批次 `sync_20260730_143314_977605` 按运行时 `total=18168` 自动请求 182 页，18168 条成功、0 失败，数据库批次耗时 1110 秒。

本批次 raw 的业务主键和 data hash 均为 18168 个，无空主键、空日期或主键/日期映射错误；checkpoint 为第 182 页、182 次请求、18168 条和 total 18168，失败请求为 0。预检时 total 为 18162，真实同步增长 6 条仍被自动覆盖，证明没有把 182 页固化成长期上限。

接口继续保持 `enabled=false`。是否加入 daily enabled 必须单独确认；按本次数据量会为每日主链增加约 182 次请求和 18.5 分钟运行时间，但后续实际请求数仍以当次最新 total 为准。

阶段 16AL-C 已将真实验证通过的 `delivery_page` 加入 daily enabled。YAML、catalog 与 DB 均为 81 个配置、47 个 enabled；目标继续使用 POST、实时 total 动态分页、每页 100、`commit_per_page=true`、`id`/hash 幂等、`updateTime` 日期和敏感 raw-only。本阶段只同步配置，没有调用业务 API，16AL-B 的 batch、18168 条 raw、API log、checkpoint 和失败记录均未变化。

文档 1778 `POST /fulfillment/ship/cost/page` 是公开读取分页接口，但实时官方说明明确要求“发货单集合、时间必传一项”。各筛选字段的 `must=false` 不能解释为允许无筛选请求；单页最大 100、响应为 `data.rows/data.total`、默认每秒 2 次。

阶段 16AM-A 增加的本地 `logistics_cost_page` 配置继续保持默认关闭。此前只传分页字段的唯一一次预检返回 `ApiRequestError` 且没有取得 total；16AM-B 重新读取完整官方说明后确认该请求缺少官方要求的业务条件，因此不再复检，也不把旧异常猜测为 HTTP 拒绝或网络问题。

probe 现已安全记录包装内的原始异常类型和 HTTP 状态码；异常消息、URL、请求参数和响应正文不会进入日志。172 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过。

16AM-B 没有调用业务 API、没有同步配置或写数据库。本地 YAML 为 82/47，DB 为 81/47，唯一差异仍是目标 disabled 配置；下一阶段只读审核 `codes` 或时间条件的真实来源，确认前不得探测或同步。

## 物流发货单明细

阶段 16AN-A 已按官方文档 1028 接入 delivery_detail_query：POST /fulfillment/ship/delivery/query，从已验证的 delivery_page.raw_json.code 生成单元素 deliveryCodes，固定请求 needItem=true，非分页读取 data 数组。接口保持 enabled=false，人员、金额、物流跟踪和备注等字段只作敏感 raw 备份。

唯一单接口批次 sync_20260731_105320_767996 为 success：1 次请求、1 条成功、0 失败。响应 deliveryCode 是空字符串，因此没有写业务主键，按完整对象 data_hash 幂等；updateTime 已正确生成 data_date，checkpoint 记录 1 次请求、1 条结果和下一个参数偏移。

当前 YAML/DB 均为 83 个配置、47 个 enabled，配置差异为 0；logistics_cost_page 只随配置同步写入 DB 且继续 disabled，没有产生业务日志、raw、checkpoint 或失败记录。文档 1028 不进入 daily enabled，也不在本阶段扩大到 18,168 个来源。

## 销售退货订单运行终态

阶段 16AO-A 按实时官方文档 9 审核 `POST /operation/sale/returnOrder/page`：只使用必填 `page/pagesize=1/100`，响应约定为 `data.rows/data.total`，官方单页上限 100、默认每秒 5 次；订单号、退货原因、买家备注和商品字段按敏感 raw-only 边界审核。

唯一一次无数据库首页预检在 1.154 秒后返回 HTTP 400，没有取得 `total` 或所需页数。没有重试、猜测筛选条件、改换请求编码或输出响应内容，因此不进入真实同步阶段。

文档 9 已登记为 `defer_runtime_rejected`，临时业务配置已清理。YAML/DB 均保持 83 个配置、47 个 enabled，catalog 为 189/75/47；销售板块为 0 个已配置、2 个终态暂缓、13 个待审。latest batch 仍为 `sync_20260731_105320_767996` success，目标五张表均为 0。

## Web 服务：阶段 0 + M1

Web 管理服务独立位于 `backend/` 和 `frontend/`，不会启动或改写现有同步任务。当前支持受邀注册、邮箱密码登录、服务端 Session Cookie、CSRF、退出、Admin/Operator/Viewer 固定角色、成员管理，以及 SMTP/Console/Fake 邮件适配器。

Windows PowerShell 本地启动：

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m backend.app.cli bootstrap-admin --email admin@example.com
.\scripts\dev-api.ps1
# 另开一个 PowerShell
.\scripts\dev-web.ps1
```

本地 `MAIL_PROVIDER=console` 时，邀请地址只输出到 API 进程终端；生产环境必须配置 SMTP、HTTPS、`SESSION_COOKIE_SECURE=true` 和带 `__Host-` 前缀的 Cookie 名。`0001` 只创建 `app_user`、`auth_action_token`、`user_session`，生产迁移必须由部署负责人执行。

完整检查：

```powershell
.\scripts\check.ps1
```

本阶段不包含密码重置、积加账号管理、同步策略、Worker、Redis、Celery 或第三方登录。
