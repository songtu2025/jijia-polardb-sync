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

当前阶段：

阶段 4S 已完成。下一阶段 4T 将 `crm_tags_page` 和 `inventory_team_query` 加入 enabled 批量同步。

当前事实：

- 当前 enabled API 有 16 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`。
- 当前已配置真实 API 有 18 个，其中 16 个已 enabled。
- `crm_tags_page` 和 `inventory_team_query` 已单接口验证成功，但仍保持 `enabled=false`。
- `crm_tags_page` 文档 id 为 `136`，路径为 `GET /operation/crm/tags/page`，响应列表字段为 `data`，主键字段为 `id`，日期字段为 `updateTime`。
- `crm_tags_page` 成功批次：`sync_20260703_015227_219654`，`rows=7`，`requests=1`，7 条 raw 数据都有 `source_primary_key` 和 `data_date`。
- `inventory_team_query` 文档 id 为 `5654`，路径为 `POST /fulfillment/inventory/teamManagement/query`，响应列表字段为 `data`，主键字段为 `teamId`，无日期字段。
- `inventory_team_query` 成功批次：`sync_20260703_015302_084824`，`rows=1`，`requests=1`，1 条 raw 数据有 `source_primary_key`，`data_date` 为空符合配置。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 20。
- 数据库已确认 `api_config.crm_tags_page.enabled=0`、`api_config.inventory_team_query.enabled=0`，当前启用配置数仍为 16。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 18 个，enabled 16 个。

建议目标：

1. 将 `config/api_config.example.yaml` 中 `crm_tags_page.enabled` 和 `inventory_team_query.enabled` 从 `false` 改为 `true`。
2. 运行 `.\\.venv\\Scripts\\python.exe -m app.main`，确认 dry-run enabled API 变为 18 个。
3. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`。
4. 查询数据库确认该批次 `total_api_count=18`、`success_api_count=18`、`failed_api_count=0`。
5. 查询同批次 `sync_api_log`，确认 18 个 API 均成功，尤其确认 `crm_tags_page` 和 `inventory_team_query`。
6. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
7. 查询 `api_config.crm_tags_page.enabled=1`、`api_config.inventory_team_query.enabled=1`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 18 个、enabled 18 个。
9. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。

验收：

1. dry-run enabled API 为 18 个。
2. `--sync-enabled` 同批次 18 个 API 全部成功。
3. `api_config` 和覆盖矩阵同步到 18/18。
4. `compileall` 和 `unittest discover` 通过。
5. 不提交 `.env`、token 缓存、日志或任何敏感信息。
