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

阶段 9F 已完成。下一阶段 9G 继续推进完整拉取：评估是否将 `transfer_detail` 从 disabled 加入 daily enabled；如启用，必须用完整 `--sync-enabled` 批次证明 33 个 enabled API 同批次成功。

当前事实：

- 当前 enabled API 有 32 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 32 个已 enabled；剩余 18 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 32 个；执行分层摘要为 `configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 7X 已将 `purchase_plan_page.enabled` 从 `false` 改为 `true`，完整 enabled 批次 `sync_20260704_104132_951900` 为 32 个 API 全成功，请求 3075 次，写入 307946 条，耗时 4244 秒。
- `product_detail` 已在 7W 进入 daily enabled，使用 `exclude_existing_target=true` 按目标表缺失主键做增量拾取；当前缺失详情数为 0。
- `purchase_plan_page` 当前总量为 0 是业务数据现状，已在 7X 进入 daily enabled。
- `transfer_detail` 已完成当前历史回填，当前覆盖 6499/6499，剩余缺口 0。
- 9F 为 `raw_json.fields` 参数来源补充了 `exclude_existing_target=true` 支持：从上游 raw_json 字段取候选参数，再反连接目标 API 的 `raw_api_data.source_primary_key`，只同步目标表缺失的主键。
- 9F 已将 `transfer_detail.param_source.exclude_existing_target` 设为 `true`，但 `transfer_detail.enabled` 仍为 `false`。
- 9F 已运行 `.\\.venv\\Scripts\\python.exe -m unittest tests.test_transfer_detail_param_source tests.test_product_detail_param_source`，10 个测试通过。
- 9F 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 9F dry-run 显示 loaded 32 enabled API config(s)，说明 `transfer_detail` 没有误进入 enabled。
- 9F 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api transfer_detail`，批次 `sync_20260704_193447_716759`，请求 0 次，写入 0 条，失败 0。
- 9F DB 核验显示批次 `sync_20260704_193447_716759` 为 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- 9F 同批次 `sync_api_log` 为 `status=success`、`request_count=0`、`success_count=0`、`failed_count=0`；同批次 raw 为 0 条，`failed_request_log` 为 0 条。
- 9F 后 `transfer_detail` checkpoint 指向批次 `sync_20260704_193447_716759`，记录 `param_offset=0`、`param_limit=200`、`next_param_offset=0`、`item_count=0`、`total_count=0`；这是缺失扫描语义，不再使用历史 offset 推进。
- 9F DB 配置确认 `transfer_detail.enabled=0`、`config_json.enabled=false`、`param_source.exclude_existing_target=true`。
- 9F 覆盖矩阵刷新为公开文档 API 185 个，真实配置 API 50 个，enabled 32 个。
- 9F 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 9F 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 9F 全面复盘结论：`transfer_detail` 已具备进入 daily enabled 的技术前提，但是否启用第 33 个 API 需要结合 32 个 enabled 批次约 4244 秒的运行成本评估，并用完整 `--sync-enabled` 批次证明。
- 8Y 暴露当前客户端不会在业务接口 401 时自动刷新 token；如再次遇到 401，应先核验失败批次是否推进 checkpoint 或留下 raw，再按需清缓存重跑同一窗口。
- `traffic_analysis_page` 在 `2026-07-02` 单日 CNY 窗口总量 528 条，但限流严格，曾在第 2 页触发 509。
- `storage_ledger_detail_page` 在 `2026-07-02` 单日窗口总量 27104 条，不适合直接完整窗口。
- `storage_ledger_month_page` 在 `2026-06` 月窗口总量 6044 条，不适合直接进入 daily enabled。
- `purchase_sale_storage_fba_page` 当前 MSKU 数量维度总量 58955 条，且不是 date_window 接口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- `app.doc_catalog` 近期可能超过 120 秒，请预留 300 秒。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、7X enabled 批次证据、9F `transfer_detail` 空缺口批次证据、本轮全面复盘和当前 32 enabled 批次耗时。
2. 如果决定启用 `transfer_detail`，将 `transfer_detail.enabled` 改为 `true`，同步 `api_config`，dry-run 应显示 33 个 enabled API。
3. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`，查询数据库确认 33 个 API 同批次成功，且 `transfer_detail` 在空缺口时请求 0 次、失败 0。
4. 如果不启用 `transfer_detail`，优先选择下一个 disabled 真实接口或高价值参数型接口；切换前必须说明体量、参数来源和风险。
5. 如果再次遇到业务接口 401，先核验失败批次是否推进 checkpoint 或留下 raw；必要时清理 token 缓存后重跑同一窗口。
6. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data`、`failed_request_log` 和 checkpoint 都可追踪。
7. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
10. 更新三份 docs；如 README 的运行说明或 API 状态变动需要同步，也一起更新。
11. 提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口、参数窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用 `transfer_detail`，必须证明 `api_config.enabled=1`、dry-run enabled 数量为 33，并用真实 `--sync-enabled` 批次证明 33 个 API 同批次成功。
3. 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进；如果是缺失扫描语义，应明确请求 0 或新增缺失数。
4. 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 32 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
