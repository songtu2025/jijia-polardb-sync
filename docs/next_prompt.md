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

阶段 11P 已完成。下一阶段 11Q 继续推进完整拉取：`traffic_analysis_page` 已连续补齐 `2026-07-02` 和 `2026-07-03` 两个 CNY 单日完整窗口，checkpoint 当前停在 `next_window_start=2026-07-04`，仍保持 disabled。当前真实配置 API 为 50 个，enabled API 为 37 个，configured disabled 为 13 个。11N-11P 三轮复盘已完成。

当前事实：

- 当前 enabled API 有 37 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 37 个已 enabled；剩余 13 个真实配置 API 已验证但保持 disabled。
- `traffic_analysis_page` 仍为 `enabled=false`，配置为 `page_size=500`、`max_pages=8`、`rate_limit.sleep_seconds=65`、`retry.retries=1`。
- 阶段 11O 批次 `sync_20260705_134816_571790` 成功补齐 `2026-07-02`，8 次请求、3537 条 raw、`item_count=3537`、`total_count=3537`。
- 阶段 11O 紧接着运行 `2026-07-03` 的批次 `sync_20260705_135657_860017` 失败，平台返回 509，raw 写入 0，checkpoint 未推进。
- 阶段 11P 在限流冷却后运行 `sync_20260705_140151_126629`，成功补齐 `2026-07-03`，8 次请求、3548 条 raw、`item_count=3548`、`total_count=3548`、失败 0。
- `traffic_analysis_page` checkpoint 当前为 `window_start=2026-07-03`、`window_end=2026-07-03`、`next_window_start=2026-07-04`。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 37 个；执行分层摘要为 `configured=50`、`configured_enabled=37`、`configured_disabled=13`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 阶段 11P dry-run 显示 loaded 37 enabled API config(s)，确认 `traffic_analysis_page` 没有进入 enabled。
- 阶段 11P 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 阶段 11P 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，83 个测试通过。
- 11N-11P 复盘结论：`procure_detail` 已进入 enabled；`traffic_analysis_page` 已补齐两个连续单日完整窗口，但因 509 限流记录，仍需低频单接口节奏观察。

建议目标：

- 继续保持 `traffic_analysis_page.enabled=false`。
- 在平台限流冷却后运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api traffic_analysis_page`，从 checkpoint 的 `next_window_start=2026-07-04` 推进。
- 如果仍返回 509，不要连续重试；记录失败批次，并评估是否需要把该接口拆到独立低频调度。
- 如果成功，核验 `item_count == total_count`、checkpoint 推进到 `2026-07-05`、raw 写入和失败日志。
- 只有 `2026-07-04` 窗口也稳定完整且不会影响 enabled 长批次时，才评估是否进入 enabled；当前不要直接改 enabled。
- 完成后同步 `api_config`、刷新覆盖矩阵并运行编译与单测。
- 下一次三轮复盘放在 11S 完成后。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 37 个、configured disabled 13 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存和日志不提交。
