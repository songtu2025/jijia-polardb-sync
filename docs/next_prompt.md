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

阶段 5C 已完成。下一阶段 5D 为 `product_detail` 开启 checkpoint 自动窗口推进，并验证第二批产品 ID 小样本。

当前事实：

- 当前 enabled API 有 20 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`。
- 当前已配置真实 API 有 23 个，其中 20 个已 enabled，`product_detail`、`market_inventory_query` 和 `storage_inbound_detail` 已验证但保持 disabled。
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
- `storage_inbound_detail` 文档 id 为 `235`，路径为 `GET /purchase/inventory/storageInbound/detail`。
- `storage_inbound_detail` 的必填参数是 `code`，参数来源是 `storage_inbound_page.raw_json.code`，小样本限制为 3。
- 已只读确认 `storage_inbound_page` 有 174286 条 raw 均有 `code`，去重 `code` 也是 174286 个。
- 阶段 5B 已完成 `storage_inbound_detail` 第一批小样本，批次为 `sync_20260703_065554_541779`，`rows=3`，`requests=3`。
- 数据库已确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- `storage_inbound_detail` 同批次 `sync_api_log` 为 `request_count=3`、`success_count=3`、`failed_count=0`，`failed_request_log` 为 0 条。
- 第一批 raw 写入 3 条，均有 `source_primary_key`、`data_hash` 和 `data_date`。
- `storage_inbound_detail` checkpoint 已更新为 `param_offset=0`、`param_limit=3`、`next_param_offset=3`。
- 阶段 5C 已将 `storage_inbound_detail.param_source.auto_advance=true`，同时保持 `enabled=false` 和 `limit=3`。
- 阶段 5C 已按程序真实排序确认 offset=3 的第二批 code 为 `GIB00922092100000004`、`GIB00922093000000005`、`GIB00922093000000006`。
- 阶段 5C 第二批同步批次为 `sync_20260703_071322_698205`，`rows=3`，`requests=3`。
- 数据库已确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- `storage_inbound_detail` 同批次 `sync_api_log` 为 `request_count=3`、`success_count=3`、`failed_count=0`，`failed_request_log` 为 0 条。
- 第二批 raw 写入 3 条，均有 `source_primary_key`、`data_hash` 和 `data_date`。
- `storage_inbound_detail` checkpoint 已更新为 `param_offset=3`、`param_limit=3`、`next_param_offset=6`。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 25。
- 数据库已确认 `api_config.market_inventory_query.enabled=0`、`param_source.limit=3`、`offset=3`、`auto_advance=true`。
- 数据库已确认 `api_config.storage_inbound_detail.enabled=0`、`param_source.source_api_code=storage_inbound_page`、`param_source.limit=3`、`param_source.auto_advance=true`。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 23 个，enabled 20 个。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`，通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，通过，25 个测试。
- 5A-5C 三轮复盘已写入 `docs/progress.md`。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 将 `product_detail.param_source.auto_advance` 设置为 `true`，继续保持 `enabled=false`。
2. 不修改 `limit=3`，用 `product_detail` 既有 checkpoint 推进到第二批产品 ID。
3. 先只读查询第二批 `product_page.source_primary_key`，确认不重复第一批 `1`、`10`、`100`。
4. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api product_detail`，验证第二批小样本真实同步。
5. 查询数据库确认新批次成功，`sync_api_log`、`raw_api_data`、checkpoint 都可追踪。
6. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
7. 查询 `api_config.product_detail.enabled=0` 且 `param_source.auto_advance=true`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 仍为 23 个、enabled 仍为 20 个。
9. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
11. 更新三份 docs，并提交推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. `product_detail` 能从 checkpoint 自动推进到第二批产品 ID 小样本。
2. 第二批产品 ID 不重复第一批，且同步批次成功。
3. `product_detail` 默认保持 disabled，不影响现有 20 个 enabled API。
4. `api_config` 与覆盖矩阵保持真实配置 API 23 个、enabled 20 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
