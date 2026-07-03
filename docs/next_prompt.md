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

阶段 7B 已完成。下一阶段 7C 继续推进完整拉取：优先从剩余 disabled 中选择一个低风险参数型接口继续扩大窗口，或评估一个低成本已验证接口是否适合进入 daily enabled。

当前事实：

- 当前 enabled API 有 30 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`country_province_query`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 30 个已 enabled；剩余 20 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 30 个。
- 7B 选择 `product_detail`，原因是它属于产品主数据详情，依赖已同步的 `product_page.source_primary_key`，风险低于订单、财务敏感明细、客服文本、物流费用和库存超大表。
- 7B 已将 `product_detail.param_source.limit` 从 3 提升到 10，仍保持 `enabled=false`。
- 7B 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已通过，同步配置数 52；数据库确认 `product_detail.enabled=0`、`param_source.limit=10`、`param_source.auto_advance=true`。
- 7B 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 30 个 enabled API，说明 `product_detail` 没有误进入 daily enabled。
- 7B 的真实单接口批次为 `sync_20260704_042403_551628`，`product_detail` 请求 10 次、写入 10 条、失败 0。
- 7B 数据库核验：该批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`；同批次 `sync_api_log.status=success`、`request_count=10`、`success_count=10`、`failed_count=0`。
- 7B 同批次 `raw_api_data` 写入 10 条 `product_detail`，10 个不同 `source_primary_key`，无缺失主键。
- 7B 后 `product_detail` checkpoint 记录 `param_offset=9`、`param_limit=10`、`next_param_offset=19`、`item_count=10`、`total_count=10`。
- 7B 后覆盖矩阵执行分层摘要仍为：`configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 6Z-7B 三轮复盘已完成：6Z 证明完整窗口接口可以稳定进入 enabled；7A 证明追平参数接口进入 enabled 后请求数为 0 也可追踪；7B 证明剩余大参数源详情接口需要用小窗口持续推进覆盖面。
- `traffic_analysis_page` 在 `2026-07-02` 单日 CNY 窗口总量 528 条，但限流严格，曾在第 2 页触发 509。
- `storage_ledger_detail_page` 在 `2026-07-02` 单日窗口总量 27104 条，不适合直接完整窗口。
- `storage_ledger_month_page` 在 `2026-06` 月窗口总量 6044 条，不适合直接进入 daily enabled。
- `purchase_sale_storage_fba_page` 当前 MSKU 数量维度总量 58955 条，且不是 date_window 接口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- `app.doc_catalog` 近期可能超过 120 秒，请预留 300 秒。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、7B `product_detail` 批次证据、7A `country_province_query` enabled 批次证据、6Z `shipment_data_page` enabled 批次证据和当前 30 enabled 批次耗时。
2. 优先评估 `product_detail` 是否继续扩大参数窗口，或选择 `storage_inbound_detail`、`transfer_detail`、`lot_no_detail`、`market_inventory_query` 等参数型接口做下一段小窗口。
3. 如选择 `purchase_plan_page` 进入 enabled，必须说明它当前总量为 0 的业务意义，并用完整 enabled 批次证明不会影响日常同步。
4. 如果评估 enabled，必须先测算完整 enabled 批次新增请求数和耗时；当前 30 enabled 批次实测约 4825 秒。
5. 任何日期窗口完整验证都必须证明 `item_count == total_count`；如触发 `date window page truncated`，先修正分页上限后重跑。
6. 如果现有机制不够，必须测试先行做最小扩展。
7. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
8. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
11. 更新三份 docs；如 README 的运行说明或 API 状态变动需要同步，也一起更新。
12. 提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口、参数窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
3. 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
4. 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 30 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
