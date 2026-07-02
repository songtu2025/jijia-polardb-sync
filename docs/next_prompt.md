# Next Codex Prompt

请继续这个项目。

开始前请先阅读：

1. AGENTS.md
2. README.md
3. docs/progress.md
4. docs/decisions.md
5. config/api_config.example.yaml
6. config/jijia_api_catalog.generated.json

注意：

- 不要重建项目。
- 不要覆盖已有实现。
- 不要读取或输出 `.env` 中的真实敏感信息。
- 不要写入真实 API 凭证、数据库密码或 accessToken。
- 如果发现代码和文档状态不一致，先说明差异，再决定怎么处理。
- 完成本阶段后，请更新 `docs/progress.md`、`docs/decisions.md` 和 `docs/next_prompt.md`。
- 保持 KISS：先做最小可验证主流程，不要一次性做完整生产级同步。
- 你负责把控和审核项目结果，以真实命令、数据库状态和 Git diff 为准。
- 开发过程中继续调用 superpowers 插件。

当前阶段：

阶段 5A 已完成。下一阶段 5B 从覆盖矩阵中选择第二个依赖型接口，验证现有 `param_source` 机制能复用到另一个真实接口。

当前事实：

- 当前 enabled API 有 20 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`。
- 当前已配置真实 API 有 22 个，其中 20 个已 enabled，`product_detail` 和 `market_inventory_query` 已验证但保持 disabled。
- `market_inventory_query` 文档 id 为 `84`，路径为 `GET /purchase/inventory/marketInventory/query`。
- `market_inventory_query` 的参数来源是 `product_inventory_page.raw_json` 的 `sku` 和 `warehouseId`，小样本限制为 3。
- 阶段 4X 已完成第一批小样本，批次为 `sync_20260703_060856_408323`，`rows=2`，`requests=4`。
- 阶段 4Y 已完成第二批小样本，批次为 `sync_20260703_062446_799475`，`rows=1`，`requests=4`。
- 阶段 4Z 已完成第三批小样本，批次为 `sync_20260703_063707_425797`，`rows=0`，`requests=3`，并将 checkpoint 推进到 `next_param_offset=9`。
- 阶段 5A 未修改 YAML offset，直接复用 checkpoint 的 `next_param_offset=9`。
- offset=9 对应第四批参数对：`301 Black + 48`、`301 Black + 50`、`301 Black + 51`。
- 阶段 5A 第四批同步批次为 `sync_20260703_064619_937667`，`rows=1`，`requests=4`。
- 数据库已确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- `market_inventory_query` 同批次 `sync_api_log` 为 `request_count=4`、`success_count=1`、`failed_count=0`，`failed_request_log` 为 0 条。
- 第四批 raw 写入 1 条，有 `data_hash`，没有稳定 `source_primary_key` 和 `data_date`。
- checkpoint 已更新为 `param_offset=9`、`param_limit=3`、`next_param_offset=12`。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 24。
- 数据库已确认 `api_config.market_inventory_query.enabled=0`、`param_source.limit=3`、`offset=3`、`auto_advance=true`。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 22 个，enabled 20 个。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`，通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，通过，23 个测试。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 只读读取覆盖矩阵，筛选 `requires_upstream_params` 中尚未配置、参数可从现有 enabled raw 数据获得、且不涉及敏感字段或写操作的候选接口。
2. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
3. 只读查询数据库，证明所需参数来源真实存在，例如来自 `source_primary_key` 或 `raw_json` 顶层字段。
4. 新增一个依赖型 API 配置，默认 `enabled=false`，小样本 `limit` 控制在 3 左右。
5. 如果现有 `param_source.source_primary_key` 或 `param_source.fields` 足够，优先不改代码；如果不够，必须测试先行做最小扩展。
6. 运行新接口 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api <api_code>` 做小样本真实同步。
7. 查询数据库确认新接口批次成功，`sync_api_log`、`raw_api_data`、checkpoint 都可追踪。
8. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
9. 查询 `api_config.<api_code>.enabled=0`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 增加 1 个、enabled 仍为 20 个。
11. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
12. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
13. 提交并推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 第二个依赖型接口完成文档确认和小样本真实同步，默认保持 disabled。
2. 参数来源由数据库只读查询证明，不靠猜测字段。
3. 新接口同步批次成功，`sync_api_log` 成功数、raw 写入数和 checkpoint 可核验。
4. `api_config` 与覆盖矩阵显示真实配置 API 增加 1 个，enabled 仍为 20 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
