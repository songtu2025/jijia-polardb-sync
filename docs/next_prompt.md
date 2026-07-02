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

阶段 4U 已完成。下一阶段 4V 评估并启用两个大库存接口的 enabled 批量同步。

当前事实：

- 当前 enabled API 有 18 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`。
- 当前已配置真实 API 有 20 个，其中 18 个已 enabled。
- `product_inventory_page` 和 `storage_inbound_page` 已单接口完整验证成功，但仍保持 `enabled=false`。
- `product_inventory_page` 文档 id 为 `15`，路径为 `POST /purchase/store/inventory/page`，响应列表字段为 `data.rows`，主键字段为 `id`，日期字段为 `updateTime`。
- `product_inventory_page` 完整成功批次：`sync_20260703_022246_265049`，`rows=118653`，`requests=1187`，checkpoint 为 `item_count=118653`、`total_count=118653`。
- `storage_inbound_page` 文档 id 为 `234`，路径为 `POST /purchase/inventory/storageInbound/page`，响应列表字段为 `data.rows`，主键字段为 `id`，日期字段为 `createdAt`。
- `storage_inbound_page` 完整成功批次：`sync_20260703_030024_100310`，`rows=174286`，`requests=1743`，checkpoint 为 `item_count=174286`、`total_count=174286`。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 22。
- 数据库已确认 `api_config.product_inventory_page.enabled=0`、`api_config.storage_inbound_page.enabled=0`，当前启用配置数仍为 18。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 20 个，enabled 18 个。
- 只读依赖型接口梳理已确认：`product_detail` 的 `id` 可来自 `product_page`；`market_inventory_query` 的 `sku` 和 `warehouseId` 可来自 `product_inventory_page`。
- 注意：两个大库存接口加入 enabled 后会新增约 2930 次请求和约 292939 条 raw 写入，`--sync-enabled` 会显著变慢，需要预留长运行窗口。

建议目标：

1. 将 `config/api_config.example.yaml` 中 `product_inventory_page.enabled` 和 `storage_inbound_page.enabled` 从 `false` 改为 `true`。
2. 运行 `.\\.venv\\Scripts\\python.exe -m app.main`，确认 dry-run enabled API 变为 20 个。
3. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`，预留长超时时间。
4. 查询数据库确认该批次 `total_api_count=20`、`success_api_count=20`、`failed_api_count=0`。
5. 查询同批次 `sync_api_log`，确认 20 个 API 均成功，尤其确认两个大库存接口 `item_count=total_count`。
6. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
7. 查询 `api_config.product_inventory_page.enabled=1`、`api_config.storage_inbound_page.enabled=1`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 20 个、enabled 20 个。
9. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。

验收：

1. dry-run enabled API 为 20 个。
2. `--sync-enabled` 同批次 20 个 API 全部成功。
3. `product_inventory_page` 和 `storage_inbound_page` 在 enabled 批次中未截断，checkpoint 里 `item_count=total_count`。
4. `api_config` 和覆盖矩阵同步到 20/20。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或任何敏感信息。
