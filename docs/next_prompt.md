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

阶段 6X 已完成。下一阶段 6Y 继续推进完整拉取：优先从剩余已验证 disabled 的日期窗口接口中选择低风险、体量可控者推进完整窗口；本阶段完成后需要对 6W-6Y 做三轮复盘。

当前事实：

- 当前 enabled API 有 28 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`storage_ledger_page`、`inventory_receipts_page`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 28 个已 enabled；`storage_ledger_detail_page`、`storage_ledger_month_page`、`shipment_data_page`、`purchase_sale_storage_fba_page`、`traffic_analysis_page`、`transfer_page`、`lot_no_page`、`purchase_plan_page`、`procure_detail` 等已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 28 个。
- 6X 覆盖矩阵执行分层摘要为：`configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 6W 已将 `inventory_receipts_page` 推进到完整单日窗口：批次 `sync_20260703_231344_896620`，请求 2 次，写入 157 条，`item_count=total_count=157`，窗口为 `2026-07-03`。
- 6X 已将 `inventory_receipts_page` 从 disabled 提升到 enabled；配置为 `enabled=true`、`page_size=100`、`page.max_pages=10`。
- 6X 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已通过，同步配置数 52；数据库总配置 52 条、启用 28 条，`inventory_receipts_page.enabled=1`。
- 6X 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 28 个 enabled API，并包含 `inventory_receipts_page`。
- 6X 完整 enabled 批次为 `sync_20260703_232214_043129`，28 个 API 全部成功，失败 0；总请求 3078 次，写入 307943 条，运行约 83 分钟。
- 6X 数据库核验：同批次 `sync_api_log` 共 28 条，28 条成功、0 条失败；`request_count=3078`、`success_count=307943`、`failed_count=0`。
- 6X 批次从 `2026-07-03 23:22:14` 运行到 `2026-07-04 00:45:01`，因此后段 date_window 接口按 `2026-07-04` 窗口推进。
- `inventory_receipts_page` 在 6X enabled 批次内请求 1 次，`2026-07-04` 窗口返回 0 条，checkpoint 记录 `item_count=0`、`total_count=0`、`window_start=2026-07-04`、`window_end=2026-07-04`、`next_window_start=2026-07-05`。
- `traffic_page`、`traffic_sku_page`、`storage_ledger_page` 在 6X 批次内也按 `2026-07-04` 窗口请求 1 次并返回 0 条，属于跨日批次的预期行为。
- `traffic_analysis_page` 在 `2026-07-02` 单日 CNY 窗口总量 528 条，但限流严格，曾在第 2 页触发 509。
- `shipment_data_page` 在 `2026-07-02` 单日窗口总量 943 条，在 `2026-07-03` 单日窗口总量 58 条，当前 checkpoint 已到 `2026-07-04`。
- `storage_ledger_detail_page` 在 `2026-07-02` 单日窗口总量 27104 条，不适合直接完整窗口。
- `storage_ledger_month_page` 在 `2026-06` 月窗口总量 6044 条，不适合直接进入 daily enabled。
- `purchase_sale_storage_fba_page` 当前 MSKU 数量维度总量 58955 条，且不是 date_window 接口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- 当前仍不支持复杂数组 join、嵌套数组过滤或复杂过滤表达式；单层数组来源和静态 POST 数组参数已经分别通过测试或真实小窗口验证。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、6K 执行分层、6X `inventory_receipts_page` enabled 批次证据、6W `inventory_receipts_page` 完整窗口证据和 6T-6V 复盘。
2. 选择 6Y 方向：优先推进一个剩余 disabled 日期窗口接口的完整窗口；候选应避开订单、财务敏感明细、客服文本、物流费用和超大慢接口。
3. 完成 6Y 后必须对 6W-6Y 做三轮复盘。
4. 如果评估 enabled，必须先测算完整 enabled 批次新增请求数和耗时；当前 28 enabled 批次实测约 83 分钟。
5. 如果评估完整窗口，必须先确认总量、页大小上限、限流、预估请求数和是否可用单请求大页覆盖。
6. 如果必须连续分页，先确认失败风险；严格限流接口不要盲目增加页数和重试。
7. 如果候选涉及依赖参数，先只读查询数据库证明参数来源真实存在，再新增默认 disabled 小样本配置。
8. 如果现有机制不够，必须测试先行做最小扩展。
9. 按本轮目标运行单接口同步、小范围 enabled 回归或完整 `--sync-enabled`。
10. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
11. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`；该命令近期可能超过 120 秒，请预留 300 秒。
12. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
13. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
14. 更新 README、三份 docs；提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
3. 如推进完整单接口窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 28 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
