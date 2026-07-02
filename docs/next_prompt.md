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

阶段 4Q 已完成。4O-4Q 三轮复盘已写入 `docs/progress.md`。下一阶段 4R 将已单接口验证通过的两个低风险接口加入 enabled 批量同步。

当前事实：

- 当前 enabled API 有 14 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`。
- 当前已配置真实 API 有 16 个，其中 `store_location_page` 和 `multi_shop_query` 仍为 `enabled=false`。
- 阶段 4Q 中 `store_location_page` 单接口验证成功，批次 `sync_20260703_013043_934150`，`rows=1116`，`requests=12`。
- 数据库确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，1116 条 raw 数据都有 `source_primary_key` 和 `data_date`，checkpoint 记录 `item_count=1116`、`total_count=1116`。
- 阶段 4Q 中 `multi_shop_query` 单接口验证成功，批次 `sync_20260703_013128_451336`，`rows=6`，`requests=1`。
- 数据库确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，6 条 raw 数据都有 `source_primary_key`；该接口无日期字段，`data_date` 为空。
- `api_config` 已同步到 18 条，enabled 仍为 14。
- `api_config.store_location_page.enabled=0`、`api_config.multi_shop_query.enabled=0`。
- 覆盖矩阵仍显示公开文档 API 185 个，真实配置 API 16 个，enabled 14 个。

4O-4Q 复盘结论：

- `kb_product_page` 当前账号返回 0 条，但请求、日志和 checkpoint 链路正常。
- `store_location_page` 当前总量为 1116 条，请求 12 页；加入 enabled 后会增加批量同步耗时。
- `multi_shop_query` 是多平台店铺基础维度，可为后续多平台依赖型接口提供参数来源。
- 依赖上游参数接口仍需要单独设计参数来源和批次粒度。

建议目标：

1. 将 `store_location_page.enabled` 和 `multi_shop_query.enabled` 从 `false` 改为 `true`。
2. 运行 `.\\.venv\\Scripts\\python.exe -m app.main`，确认 enabled API 变为 16 个。
3. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`。
4. 查询数据库确认 16 个 API 同批次成功，`failed_api_count=0`。
5. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
6. 查询 `api_config.store_location_page.enabled=1` 和 `api_config.multi_shop_query.enabled=1`。
7. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 为 16 个、enabled 为 16 个。
8. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。

验收：

1. 16 个 enabled API 同批次同步成功。
2. `store_location_page` 和 `multi_shop_query` 的批量同步日志与单接口验证口径一致。
3. 数据库 `api_config` 中两个新接口均为 enabled。
4. 覆盖矩阵、测试和文档同步更新。
5. 不提交 `.env`、token 缓存、日志或任何敏感信息。
