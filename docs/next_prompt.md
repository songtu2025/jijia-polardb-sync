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

阶段 6Z 已完成。下一阶段 7A 继续推进完整拉取：优先从剩余已验证 disabled 的日期窗口或低风险参数接口中选择一个候选推进完整窗口或小样本验证。

当前事实：

- 当前 enabled API 有 29 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 29 个已 enabled；`storage_ledger_detail_page`、`storage_ledger_month_page`、`purchase_sale_storage_fba_page`、`traffic_analysis_page`、`transfer_page`、`lot_no_page`、`purchase_plan_page`、`procure_detail` 等已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 29 个。
- 6Z 覆盖矩阵执行分层摘要为：`configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 6Z 已将 `shipment_data_page` 从 disabled 提升到 enabled；配置为 `enabled=true`、`page_size=100`、`page.max_pages=12`、空主键。
- 6Z 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已通过，同步配置数 52；数据库总配置 52 条、启用 29 条，`shipment_data_page.enabled=1`。
- 6Z 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 29 个 enabled API，并包含 `shipment_data_page`。
- 6Z 完整 enabled 批次为 `sync_20260704_012039_532253`，29 个 API 全部成功，失败 0；总请求 3077 次，写入 308187 条，运行 4959 秒。
- 6Z 数据库核验：同批次 `sync_api_log` 共 29 条，29 条成功、0 条失败；`request_count=3077`、`success_count=308187`、`failed_count=0`。
- `shipment_data_page` 在 6Z enabled 批次内请求 3 次，`2026-07-03` 窗口返回 241 条，checkpoint 记录 `last_page=3`、`item_count=241`、`total_count=241`、`window_start=2026-07-03`、`window_end=2026-07-03`、`next_window_start=2026-07-04`。
- 6Y 已新增日期窗口分页截断保护：当 `item_count < total_count` 时，该 API 记为 failed，不更新 checkpoint。
- 6W-6Y 复盘结论：完整窗口验收必须看 `item_count == total_count`，不能只看批次 success；进入 daily enabled 前必须跑完整 enabled 批次；日期窗口接口必须防止分页截断后推进 checkpoint。
- 6Z 是新一组三轮的第 1 轮；7A 不需要做三轮复盘，7B 完成后再复盘 6Z-7B。
- `traffic_analysis_page` 在 `2026-07-02` 单日 CNY 窗口总量 528 条，但限流严格，曾在第 2 页触发 509。
- `storage_ledger_detail_page` 在 `2026-07-02` 单日窗口总量 27104 条，不适合直接完整窗口。
- `storage_ledger_month_page` 在 `2026-06` 月窗口总量 6044 条，不适合直接进入 daily enabled。
- `purchase_sale_storage_fba_page` 当前 MSKU 数量维度总量 58955 条，且不是 date_window 接口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- `app.doc_catalog` 近期可能超过 120 秒，请预留 300 秒。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、6K 执行分层、6Z `shipment_data_page` enabled 批次证据、6W-6Y 复盘和当前 29 enabled 批次耗时。
2. 优先评估一个剩余 disabled 日期窗口接口是否可以推进完整窗口；候选应避开订单、财务敏感明细、客服文本、物流费用和超大慢接口。
3. 如果选择依赖参数接口，先只读查询数据库证明参数来源真实存在，再做默认 disabled 小样本配置和单接口验证。
4. 如果评估 enabled，必须先测算完整 enabled 批次新增请求数和耗时；当前 29 enabled 批次实测 4959 秒。
5. 任何日期窗口完整验证都必须证明 `item_count == total_count`；如触发 `date window page truncated`，先修正分页上限后重跑。
6. 如果现有机制不够，必须测试先行做最小扩展。
7. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
8. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
11. 更新 README、三份 docs；提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
3. 如推进完整单接口窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 29 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
