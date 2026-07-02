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

阶段 4W 已完成。下一阶段 4X 扩展依赖参数来源机制，先围绕 `market_inventory_query` 做小样本验证。

当前事实：

- 当前 enabled API 有 20 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`。
- 当前已配置真实 API 有 21 个，其中 20 个已 enabled，`product_detail` 已验证但保持 disabled。
- 阶段 4W 新增 `product_detail`，文档 id 为 `211`，路径为 `GET /purchase/goods/product/detail`。
- `product_detail` 的参数来源是 `product_page` 的 `raw_api_data.source_primary_key`，目标参数字段为 `id`，小样本限制为 3。
- 阶段 4W 的 `product_detail` 小样本同步批次为 `sync_20260703_060306_472537`，`rows=3`，`requests=3`。
- 数据库已确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- `product_detail` 同批次 `sync_api_log` 为 `request_count=3`、`success_count=3`、`failed_count=0`。
- `product_detail` 同批次 raw 主键为 `1`、`10`、`100`，3 条都有 `source_primary_key` 和 `data_hash`。
- 真实响应顶层字段没有 `lastDate`，因此 `product_detail.date_field=""`，`data_date` 为空符合当前事实。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 23。
- 数据库已确认 `api_config.product_detail.enabled=0`，当前启用配置数为 20。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 21 个，enabled 20 个。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`，通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，通过，19 个测试。
- 4U-4W 已完成三轮复盘：大分页直读接口已经进入 enabled；依赖型接口已打通单参数来源，但还没有支持从 `raw_json` 提取多字段参数。

建议目标：

1. 阅读现有 `SyncEngine._source_param_sets()`、`product_detail` 配置和 `product_inventory_page` raw 数据结构。
2. 只读查询 `product_inventory_page` raw JSON 的字段名和可用参数计数，不输出完整业务 JSON。
3. 为 `market_inventory_query` 增加 YAML 配置和测试，默认保持 `enabled=false`。
4. 扩展 `param_source`，支持从上游 `raw_json` 提取多个字段，生成 `sku` 和 `warehouseId` 请求参数。
5. 先取少量去重参数对做 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api market_inventory_query` 小样本验证。
6. 查询数据库确认小样本批次成功，`sync_api_log`、`raw_api_data`、checkpoint 都可追踪。
7. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
8. 查询 `api_config.market_inventory_query.enabled=0`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 变为 22 个、enabled 仍为 20 个。
10. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
11. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。

验收：

1. `market_inventory_query` 能基于 `product_inventory_page` 的真实 `sku` 和 `warehouseId` 运行小样本同步。
2. 小样本同步批次成功，`sync_api_log` 成功数、raw 写入数和 checkpoint 可核验。
3. `market_inventory_query` 默认保持 disabled，不影响现有 20 个 enabled API。
4. `api_config` 和覆盖矩阵同步到真实配置 API 22 个、enabled 20 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或任何敏感信息。
