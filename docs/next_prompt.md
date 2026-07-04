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

阶段 8B 已完成。下一阶段 8C 继续推进完整拉取：优先继续 `transfer_detail` 的 200 条窗口，或选择 `lot_no_detail` 做同等中等窗口验证。8C 完成后需要按目标模式复盘 8A-8C。

当前事实：

- 当前 enabled API 有 32 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 32 个已 enabled；剩余 18 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 32 个；执行分层摘要为 `configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 7X 已将 `purchase_plan_page.enabled` 从 `false` 改为 `true`，完整 enabled 批次 `sync_20260704_104132_951900` 为 32 个 API 全成功，请求 3075 次，写入 307946 条，耗时 4244 秒。
- 7X-7Z 复盘结论：`purchase_plan_page` 已进入 daily enabled；`transfer_detail` 仍是历史回填任务，已从 6 推进到 406 个详情，失败 0。
- 7X-7Z 复盘结论：依赖型详情接口进入 daily enabled 前需要完成足够历史回填并设计增量边界；当前不应把 `transfer_detail` 直接加入 enabled。
- 7Y 已将 `transfer_detail.param_source.limit` 从 3 改为 200，但 `transfer_detail.enabled` 仍为 `false`。
- 7Y `transfer_detail` 批次 `sync_20260704_120115_022944` 请求 200 次、写入 200 条、失败 0，checkpoint 推进到 `next_param_offset=206`。
- 7Z `transfer_detail` 批次 `sync_20260704_121501_289184` 请求 200 次、写入 200 条、失败 0，checkpoint 推进到 `next_param_offset=406`。
- 8A `transfer_detail` 批次 `sync_20260704_122721_709651` 请求 200 次、写入 200 条、失败 0，checkpoint 推进到 `next_param_offset=606`。
- 8B 不改 YAML，继续复用 `transfer_detail.param_source.limit=200`。
- 8B 起点 `transfer_detail` 已有 606 条 raw、606 个不同主键；checkpoint 为 `next_param_offset=606`。
- 8B dry-run 仍显示 loaded 32 enabled API config(s)，说明 `transfer_detail` 没有误进入 enabled。
- 8B 首次核验发现最新 `transfer_detail` 批次仍为 8A 批次，后续重新运行并以新批次为准。
- 8B 的真实单接口批次为 `sync_20260704_124032_403949`。
- 8B `transfer_detail` 批次命令输出：请求 200 次，写入 200 条。
- 8B DB 核验：该批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-04 12:40:32` 到 `2026-07-04 12:47:12`，耗时 400 秒。
- 8B 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`。
- 8B 同批次 `raw_api_data` 写入 200 条，200 个不同 `source_primary_key`，200 个不同 `data_hash`，`data_date` 范围为 `2023-02-17` 到 `2023-03-30`。
- 8B 同批次 `failed_request_log` 为 0 条；样本确认 `source_primary_key` 与 `raw_json.code` 一致。
- 8B 后 `transfer_detail` 当前累计 raw 为 806 条、806 个不同调拨单号；checkpoint 指向批次 `sync_20260704_124032_403949`，记录 `param_offset=606`、`param_limit=200`、`next_param_offset=806`、`item_count=200`、`total_count=200`。
- `transfer_detail` 上游 `storage_inbound_page` 中 `opType=TFOutbound` 的不同调拨单号为 6499 个，当前覆盖 806/6499。
- 8B 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个，真实配置 API 50 个，enabled 32 个。
- 8B 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 8B 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，78 个测试通过。
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

1. 先只读读取覆盖矩阵、7X enabled 批次证据、7Y-8B `transfer_detail` 中等窗口批次证据和当前 32 enabled 批次耗时。
2. 如果继续 `transfer_detail`，不改 YAML，直接复用 checkpoint 的 `next_param_offset=806` 跑下一批 200 条，并核验 checkpoint 推进到 1006。
3. 如果切换接口，优先选择 `lot_no_detail` 做同样的 200 条窗口验证；切换前必须说明体量、参数来源和风险。
4. 不要把 `transfer_detail` 直接加入 enabled；当前只覆盖 806/6499，daily 增量边界仍需后续设计。
5. 如果现有机制不够，必须测试先行做最小扩展。
6. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
7. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
10. 更新三份 docs；如 README 的运行说明或 API 状态变动需要同步，也一起更新。
11. 如果完成 8C，做 8A-8C 三轮复盘。
12. 提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口、参数窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用新接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实 `--sync-enabled` 批次证明成功。
3. 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
4. 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 32 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
