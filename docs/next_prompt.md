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

阶段 4V 已完成。下一阶段 4W 启动依赖型接口的最小参数来源机制，先围绕 `product_detail` 做小样本验证。

当前事实：

- 当前 enabled API 有 20 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`。
- 当前已配置真实 API 有 20 个，20 个均已 enabled。
- 阶段 4V 的 `--sync-enabled` 批次为 `sync_20260703_040353_819845`，`apis=20`，`rows=306174`，`requests=3052`。
- 数据库已确认该批次 `total_api_count=20`、`success_api_count=20`、`failed_api_count=0`。
- `product_inventory_page` 在该批次中请求 1187 次，写入 118653 条，checkpoint 为 `item_count=118653`、`total_count=118653`。
- `storage_inbound_page` 在该批次中请求 1743 次，写入 174286 条，checkpoint 为 `item_count=174286`、`total_count=174286`。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 22。
- 数据库已确认 `api_config.product_inventory_page.enabled=1`、`api_config.storage_inbound_page.enabled=1`，当前启用配置数为 20。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 20 个，enabled 20 个。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`，通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，通过，15 个测试。
- 只读依赖型接口梳理已确认：`product_detail` 的 `id` 可来自 `product_page`；`market_inventory_query` 的 `sku` 和 `warehouseId` 可来自 `product_inventory_page`。

建议目标：

1. 阅读现有 `app/sync_engine.py`、`app/api_client.py`、`app/main.py` 和相关测试，确认最小改动点。
2. 为 `product_detail` 增加 YAML 配置和测试，默认保持 `enabled=false`。
3. 实现或复用一个最小参数来源机制，从已同步的 `product_page` raw 数据中提取少量产品 `id`。
4. 先运行小样本 `product_detail` 同步，不要加入 20 个 enabled 生产批量同步。
5. 查询数据库确认小样本批次成功，`sync_api_log`、`raw_api_data`、checkpoint 都可追踪。
6. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
7. 查询 `api_config.product_detail.enabled=0`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 变为 21 个、enabled 仍为 20 个。
9. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
11. 完成 4W 后做 4U-4W 三轮复盘。

验收：

1. `product_detail` 能基于 `product_page` 的真实产品 `id` 运行小样本同步。
2. 小样本同步批次成功，`sync_api_log` 成功数、raw 写入数和 checkpoint 可核验。
3. `product_detail` 默认保持 disabled，不影响现有 20 个 enabled API。
4. `api_config` 和覆盖矩阵同步到真实配置 API 21 个、enabled 20 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或任何敏感信息。
