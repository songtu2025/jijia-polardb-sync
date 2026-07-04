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

阶段 8T 已完成。下一阶段 8U 继续推进完整拉取：优先继续 `transfer_detail` 的 200 条窗口，或选择 `lot_no_detail` 做同等中等窗口验证。

当前事实：

- 当前 enabled API 有 32 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 32 个已 enabled；剩余 18 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 32 个；执行分层摘要为 `configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 7X 已将 `purchase_plan_page.enabled` 从 `false` 改为 `true`，完整 enabled 批次 `sync_20260704_104132_951900` 为 32 个 API 全成功，请求 3075 次，写入 307946 条，耗时 4244 秒。
- 7X-7Z 复盘结论：`purchase_plan_page` 已进入 daily enabled；`transfer_detail` 仍是历史回填任务，已从 6 推进到 406 个详情，失败 0。
- 8A-8C 复盘结论：三轮连续复用 `transfer_detail.param_source.limit=200`，从 406 推进到 1006，累计新增 600 个调拨单详情，失败 0。
- 8D-8F 复盘结论：三轮连续复用 `transfer_detail.param_source.limit=200`，从 1006 推进到 1606，累计新增 600 个调拨单详情，失败 0。
- 8G-8I 复盘结论：三轮连续复用 `transfer_detail.param_source.limit=200`，从 1606 推进到 2206，累计新增 600 个调拨单详情，失败 0。
- 8K-8M 复盘结论：三轮连续复用 `transfer_detail.param_source.limit=200`，从 2406 推进到 3006，累计新增 600 个调拨单详情，失败 0。
- 8N-8P 复盘结论：三轮连续复用 `transfer_detail.param_source.limit=200`，从 3006 推进到 3606，累计新增 600 个调拨单详情，失败 0。
- 8P 不改 YAML，继续复用 `transfer_detail.param_source.limit=200`，从 3406 推进到 3606，失败 0。
- 8Q 不改 YAML，继续复用 `transfer_detail.param_source.limit=200`，从 3606 推进到 3806，失败 0。
- 8R 不改 YAML，继续复用 `transfer_detail.param_source.limit=200`，从 3806 推进到 4006，失败 0。
- 8S 不改 YAML，继续复用 `transfer_detail.param_source.limit=200`。
- 8S dry-run 仍显示 loaded 32 enabled API config(s)，说明 `transfer_detail` 没有误进入 enabled。
- 8S 的真实单接口批次为 `sync_20260704_163241_732118`。
- 8S `transfer_detail` 批次命令输出：请求 200 次，写入 200 条。
- 8S DB 核验：该批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-04 16:32:42` 到 `2026-07-04 16:40:10`，耗时 448 秒。
- 8S 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`。
- 8S 同批次 `raw_api_data` 写入 200 条，200 个不同 `source_primary_key`，200 个不同 `data_hash`，`data_date` 范围为 `2025-03-14` 到 `2025-04-27`。
- 8S 同批次 `failed_request_log` 为 0 条；样本确认 `source_primary_key` 与 `raw_json.code` 一致。
- 8S 后 `transfer_detail` 当前累计 raw 为 4206 条、4206 个不同调拨单号；checkpoint 指向批次 `sync_20260704_163241_732118`，记录 `param_offset=4006`、`param_limit=200`、`next_param_offset=4206`、`item_count=200`、`total_count=200`。
- `transfer_detail` 上游 `storage_inbound_page` 中 `opType=TFOutbound` 的不同调拨单号为 6499 个，当前覆盖 4206/6499，约 64.7%。
- 8S 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 8S 覆盖矩阵刷新为公开文档 API 185 个，真实配置 API 50 个，enabled 32 个。
- 8S 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 8S 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，78 个测试通过。
- 8Q-8S 复盘结论：三轮连续复用 `transfer_detail.param_source.limit=200`，从 3606 推进到 4206，累计新增 600 个调拨单详情，失败 0；窗口耗时约 442 到 458 秒，仍适合继续分批回填，但尚不应进入 enabled。
- 8T 不改 YAML，继续复用 `transfer_detail.param_source.limit=200`。
- 8T dry-run 仍显示 loaded 32 enabled API config(s)，说明 `transfer_detail` 没有误进入 enabled。
- 8T 的真实单接口批次为 `sync_20260704_164600_551797`。
- 8T `transfer_detail` 批次命令输出：请求 200 次，写入 200 条。
- 8T DB 核验：该批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-04 16:46:01` 到 `2026-07-04 16:52:45`，耗时 404 秒。
- 8T 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`。
- 8T 同批次 `raw_api_data` 写入 200 条，200 个不同 `source_primary_key`，200 个不同 `data_hash`，`data_date` 范围为 `2025-04-27` 到 `2025-06-09`。
- 8T 同批次 `failed_request_log` 为 0 条；样本确认 `source_primary_key` 与 `raw_json.code` 一致。
- 8T 后 `transfer_detail` 当前累计 raw 为 4406 条、4406 个不同调拨单号；checkpoint 指向批次 `sync_20260704_164600_551797`，记录 `param_offset=4206`、`param_limit=200`、`next_param_offset=4406`、`item_count=200`、`total_count=200`。
- `transfer_detail` 上游 `storage_inbound_page` 中 `opType=TFOutbound` 的不同调拨单号为 6499 个，当前覆盖 4406/6499，约 67.8%。
- 8T 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 8T 覆盖矩阵刷新为公开文档 API 185 个，真实配置 API 50 个，enabled 32 个。
- 8T 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 8T 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，78 个测试通过。
- `product_detail` 已在 7W 进入 daily enabled，使用 `exclude_existing_target=true` 按目标表缺失主键做增量拾取；当前缺失详情数为 0。
- `purchase_plan_page` 当前总量为 0 是业务数据现状，已在 7X 进入 daily enabled。
- `traffic_analysis_page` 在 `2026-07-02` 单日 CNY 窗口总量 528 条，但限流严格，曾在第 2 页触发 509。
- `storage_ledger_detail_page` 在 `2026-07-02` 单日窗口总量 27104 条，不适合直接完整窗口。
- `storage_ledger_month_page` 在 `2026-06` 月窗口总量 6044 条，不适合直接进入 daily enabled。
- `purchase_sale_storage_fba_page` 当前 MSKU 数量维度总量 58955 条，且不是 date_window 接口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- `app.doc_catalog` 近期可能超过 120 秒，请预留 300 秒。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、7X enabled 批次证据、7Y-8T `transfer_detail` 中等窗口批次证据、8A-8C、8D-8F、8G-8I、8K-8M、8N-8P、8Q-8S 复盘和当前 32 enabled 批次耗时。
2. 如果继续 `transfer_detail`，不改 YAML，直接复用 checkpoint 的 `next_param_offset=4406` 跑下一批 200 条，并核验 checkpoint 推进到 4606。
3. 如果切换接口，优先选择 `lot_no_detail` 做同样的 200 条窗口验证；切换前必须说明体量、参数来源和风险。
4. 不要把 `transfer_detail` 直接加入 enabled；当前只覆盖 4406/6499，daily 增量边界仍需后续设计。
5. 如果现有机制不够，必须测试先行做最小扩展。
6. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
7. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
10. 8T-8V 三轮完成后再做下一次全面复盘。
11. 更新三份 docs；如 README 的运行说明或 API 状态变动需要同步，也一起更新。
12. 提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口、参数窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用新接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实 `--sync-enabled` 批次证明成功。
3. 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
4. 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 32 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
