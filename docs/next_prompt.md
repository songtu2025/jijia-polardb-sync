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

阶段 4Y 已完成。下一阶段 4Z 为依赖参数接口增加 checkpoint 驱动的自动窗口推进，先围绕 `market_inventory_query` 做第三批小样本验证。

当前事实：

- 当前 enabled API 有 20 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`。
- 当前已配置真实 API 有 22 个，其中 20 个已 enabled，`product_detail` 和 `market_inventory_query` 已验证但保持 disabled。
- `market_inventory_query` 文档 id 为 `84`，路径为 `GET /purchase/inventory/marketInventory/query`。
- `market_inventory_query` 的参数来源是 `product_inventory_page.raw_json` 的 `sku` 和 `warehouseId`，小样本限制为 3。
- 阶段 4X 已完成第一批小样本，批次为 `sync_20260703_060856_408323`，`rows=2`，`requests=4`。
- 阶段 4Y 已增加 `param_source.offset`，并将 `market_inventory_query.param_source.offset=3`。
- offset=3 对应第二批参数对：`301 Black + 23`、`301 Black + 43`、`301 Black + 44`。
- 阶段 4Y 的第二批小样本同步批次为 `sync_20260703_062446_799475`，`rows=1`，`requests=4`。
- 数据库已确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- `market_inventory_query` 同批次 `sync_api_log` 为 `request_count=4`、`success_count=1`、`failed_count=0`，`failed_request_log` 为 0 条。
- `market_inventory_query` 同批次 raw 写入 1 条，有 `data_hash`，没有稳定 `source_primary_key` 和 `data_date`。
- checkpoint 记录 `item_count=1`、`total_count=3`；这里的 `total_count=3` 表示本次参数对数量，不是响应行总数。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 24。
- 数据库已确认 `api_config.market_inventory_query.enabled=0`、`param_source.limit=3`、`param_source.offset=3`，当前启用配置数为 20。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 22 个，enabled 20 个。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`，通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，通过，21 个测试。
- 目前 offset 仍是手动 YAML 窗口；还没有从 checkpoint 自动推进下一批参数。
- 本地 Git 可能仍领先远端，因为之前 GitHub 凭据阻塞过 `git push`。开始前请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 阅读现有 `SyncEngine._source_param_sets()`、`_update_checkpoint()`、`market_inventory_query` 配置和相关测试。
2. 为 `param_source` 增加最小 checkpoint 自动推进能力，优先让下一批 offset 从上次 checkpoint 计算。
3. 用测试约束：上次 offset=3、limit=3 后，下一批 offset 应推进到 6。
4. 保持 `market_inventory_query.enabled=false`，不要加入 20 个 enabled 生产批量同步。
5. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api market_inventory_query` 做第三批小样本真实同步。
6. 查询数据库确认第三批批次成功，`sync_api_log`、`raw_api_data`、checkpoint 都可追踪。
7. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
8. 查询 `api_config.market_inventory_query.enabled=0`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 仍为 22 个、enabled 仍为 20 个。
10. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
11. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
12. 提交并尝试推送；如果 GitHub 凭据仍阻塞，保留本地提交并明确说明本地 ahead 数和远端提交号。

验收：

1. `market_inventory_query` 能从 checkpoint 自动推进到第三批小样本。
2. 第三批参数对不重复前两批参数对。
3. 第三批同步批次成功，`sync_api_log` 成功数、raw 写入数和 checkpoint 可核验。
4. `market_inventory_query` 默认保持 disabled，不影响现有 20 个 enabled API。
5. `api_config` 和覆盖矩阵保持真实配置 API 22 个、enabled 20 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或任何敏感信息。
