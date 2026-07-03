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

示例文件在 `config/api_config.example.yaml`。当前只放占位接口路径和示例字段，真实字段需要登录积加开放平台文档后补充。

新增 API 的基本步骤：

1. 在 YAML 的 `apis` 下新增一项。
2. 设置唯一的 `api_code`。
3. 填写真实 `path`、分页字段、主键字段和日期字段。
4. 如果接口没有稳定业务主键，将由后续同步逻辑使用 `data_hash` 去重。

对需要滚动日期窗口的接口，`params` 支持少量日期占位符：`{{ today }}`、`{{ yesterday }}` 和 `{{ days_ago:7 }}`。程序会在发起请求前展开为 `YYYY-MM-DD`。

对需要补历史窗口的接口，可以在 YAML 中增加 `date_window`，用 `default_start`、`days`、`start_field` 和 `end_field` 生成本次请求窗口；字段可写成 `model.reportStartDate` 这类点路径。同步成功后 checkpoint 会记录 `next_window_start`，下次运行从下一窗口继续；如果下一窗口已经晚于当天，程序会跳过请求，避免严格限流接口空跑。该能力已用 `traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page` 和 `inventory_receipts_page` 做过真实单日窗口验证。

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

依赖上游参数的接口也先用 `--sync-api` 做小样本验证。例如 `product_detail` 会从已入库的 `product_page` 原始数据中取少量产品 ID 请求详情；`market_inventory_query` 会从已入库的 `product_inventory_page.raw_json` 提取 `sku` 和 `warehouseId` 请求站点库存分布；`procure_detail` 会从已入库的 `lot_no_page.raw_json` 提取少量 `poCode` 请求采购订单详情。参数来源也支持单层数组展开，例如 `raw_json.marketListVos[].marketId`。这类接口默认保持 `enabled: false`，不进入每天的 enabled 批量同步。

同步 YAML 中已启用的真实业务 API：

```bash
python -m app.main --sync-enabled
```

`--sync-enabled` 会读取 `config/api_config.example.yaml` 中 `enabled: true` 的接口，并在同一个 `sync_batch` 下逐个写入 `sync_api_log`。批次头会先提交，每个 API 使用独立事务提交 raw、log 和 checkpoint，最后再提交批次汇总状态，便于长任务运行时查看已完成接口。当前启用了 `amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page` 和 `base_currency_query`。

生成积加公开文档 API 覆盖矩阵：

```bash
python -m app.doc_catalog --output config/jijia_api_catalog.generated.json --summary
```

该命令只读取公开文档目录和详情，不读取 `.env`，不请求真实业务接口。输出文件保存公开接口元数据、分类结果、本地配置覆盖状态和下一步执行分层，例如已配置、需参数源、需敏感审查、需风险复核或暂缓写操作。

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

当前 enabled 批量属于长任务，最近一次 24 个接口完整同步耗时约 5655 秒。ECS 上的 cron 窗口应避免和其他重写入任务重叠。

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

当前已验证并启用 `amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`storage_ledger_page`、`inventory_receipts_page` 和 `base_currency_query`。

另有一批已完成小窗口、完整窗口或空结果验证但默认未启用的接口，例如 `purchase_plan_page`、`fba_inventory_page`、`inventory_event_page`、`inventory_age_page`、`traffic_analysis_page`、`shipment_data_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`purchase_sale_storage_fba_page`、`transfer_page`、`lot_no_page`、`procure_detail` 和若干库存、SKU 映射、详情类接口。其中 `shipment_data_page` 已完成 `2026-07-02` 单日完整窗口验证，但仍需评估请求量和 daily 批次耗时后再决定是否启用。这些接口需先评估数据量、限流和业务风险，再决定是否进入每天的 enabled 批量同步。

### accessToken 如何获取？

根据积加开放平台文档 `id=596`，获取 token 的文档路径是 `POST /api_token`，实际开放接口网关前缀是 `/api/open`，所以程序会请求 `/api/open/api_token`。请求体包含 `appId` 和 `appKey`，响应数据包含 `accessToken`、`expiresIn` 和 `expiresOut`。

程序会把 accessToken 缓存在 `logs/token_cache.json`，并提前 60 秒视为过期。该文件包含敏感 token，已在 `.gitignore` 中排除。

### 当前接入了哪个业务 API？

当前配置并启用了 `amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page` 和 `base_currency_query`。`amazon_shop_page` 对应文档 `id=153` 的“查询亚马逊店铺信息”；`org_manage_query` 对应文档 `id=2537` 的“查询部门列表”；`role_list` 对应文档 `id=2885` 的“查询角色列表”；`dictionary_query` 对应文档 `id=2538` 的“查询字典管理列表”；`rate_page` 对应文档 `id=139` 的“查询汇率设置”；`continent_country_tree` 对应文档 `id=4943` 的“获取大洲国家关系”；`ship_transport_list` 对应文档 `id=3059` 的“查询物流方式列表”；`country_tree` 对应文档 `id=4563` 的“获取已授权店铺区域国家”；`category_page` 对应文档 `id=54` 的“查询品类信息”；`brand_page` 对应文档 `id=1752` 的“查询品牌资料”；`product_page` 对应文档 `id=53` 的“查询产品列表”；`parent_product_page` 对应文档 `id=4835` 的“查询父产品信息”；`kb_product_page` 对应文档 `id=1956` 的“查询捆绑产品列表”；`fba_warehouse_page` 对应文档 `id=63` 的“查询仓库-FBA仓”；`store_location_page` 对应文档 `id=141` 的“查询库位信息”；`multi_shop_query` 对应文档 `id=67` 的“查询多平台店铺信息”；`platform_msku_page` 对应文档 `id=2898` 的“SKU关联多平台MSKU”；`crm_tags_page` 对应文档 `id=136` 的“查询标签管理信息”；`inventory_team_query` 对应文档 `id=5654` 的“查询团队信息”；`product_inventory_page` 对应文档 `id=15` 的“查询产品库存”；`storage_inbound_page` 对应文档 `id=234` 的“出入库记录V2”；`storage_return_page` 对应文档 `id=152` 的“查询采购退货单列表V2”；`strategy_template_page` 对应文档 `id=102` 的“分时策略NEW”；`base_currency_query` 对应文档 `id=66` 的“获取本位币币种”。

### 如何运行测试？

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 示例 API 字段是否可以直接用于生产？

不可以。`config/api_config.example.yaml` 中的路径和字段都是占位示例，需要按真实积加开放平台文档调整。

### 没有稳定业务主键怎么办？

后续同步逻辑会对原始 JSON 计算 `data_hash`，通过 `api_code + data_hash` 去重。

## 安全注意事项

- 不要提交 `.env`。
- 不要提交 `logs/token_cache.json`。
- 不要在 README、YAML 或 Python 文件中写真实密钥。
- PolarDB 账号建议使用最小权限。
- ECS 到 PolarDB 建议使用内网地址和安全组限制。
