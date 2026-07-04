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

阶段 7U 已完成。下一阶段 7V 继续推进完整拉取：优先验证 `product_detail` 新增产品 ID 的增量拾取方式和完整 enabled 批次新增成本；如果当前机制不适合 enabled，再转向下一个低风险参数型接口。

当前事实：

- 当前 enabled API 有 30 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`country_province_query`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 30 个已 enabled；剩余 20 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 30 个；执行分层摘要为 `configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 7U 继续选择 `product_detail`，未改 YAML，仍保持 `enabled=false`。
- 7U 起点 DB 确认 `product_detail` checkpoint 来自 7T 批次 `sync_20260704_085210_504745`，记录 `param_offset=8119`、`param_limit=500`、`next_param_offset=8258`。
- 7U 起点覆盖量为 `product_detail` 8258 个不同产品主键，`product_page` 8258 个不同产品主键，剩余 0。
- 7U 的真实单接口空窗口批次为 `sync_20260704_090119_560431`，`product_detail` 请求 0 次、写入 0 条、失败 0。
- 7U 数据库核验：该批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-04 09:01:20` 到 `2026-07-04 09:01:24`。
- 7U 同批次 `sync_api_log.status=success`、`request_count=0`、`success_count=0`、`failed_count=0`、`error_message=NULL`。
- 7U 同批次 `raw_api_data` 写入 0 条 `product_detail`；同批次 `failed_request_log` 为 0 条。
- 7U 后 `product_detail` checkpoint 指向批次 `sync_20260704_090119_560431`，记录 `param_offset=8258`、`param_limit=500`、`next_param_offset=8258`、`item_count=0`、`total_count=0`。
- 7U 后 `product_detail` 累计 raw 覆盖仍为 8258 条，8258 个不同产品主键；上游 `product_page` 当前仍为 8258 个不同产品主键。
- 7U 后 dry-run 仍显示 30 个 enabled API，说明 `product_detail` 没有误进入 enabled。
- 7U 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary` 并通过。
- 7U 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 7U 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，76 个测试通过。
- 7U 结论：`product_detail` 追平后的空窗口行为已验证；没有新上游产品时不会请求外部 API、不会写入空数据，并会留下成功批次、接口日志和 checkpoint。
- 7U 结论：这还不能证明 `product_detail` 可进入 daily enabled，因为新增产品 ID 出现在上游 `product_page` 后，是否能被 `next_param_offset=8258` 正确拾取仍未验证。
- `product_detail` 的当前瓶颈不再是历史覆盖量，而是新增产品增量拾取、enabled 批次新增耗时和日常调度边界。
- `traffic_analysis_page` 在 `2026-07-02` 单日 CNY 窗口总量 528 条，但限流严格，曾在第 2 页触发 509。
- `storage_ledger_detail_page` 在 `2026-07-02` 单日窗口总量 27104 条，不适合直接完整窗口。
- `storage_ledger_month_page` 在 `2026-06` 月窗口总量 6044 条，不适合直接进入 daily enabled。
- `purchase_sale_storage_fba_page` 当前 MSKU 数量维度总量 58955 条，且不是 date_window 接口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- `app.doc_catalog` 近期可能超过 120 秒，请预留 300 秒。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、7U `product_detail` 空窗口批次证据和当前 30 enabled 批次耗时。
2. 如果评估 `product_detail` 进入 daily enabled，先验证 `next_param_offset=8258` 下新增产品 ID 的增量拾取方式和完整 enabled 批次新增耗时，不要只凭空窗口成功直接启用。
3. 如果现有 `param_source` 的 offset 机制无法安全处理新增产品插入排序问题，先提出最小改法和测试，不要直接改生产调度。
4. 如果切换接口，优先选择 `storage_inbound_detail`、`transfer_detail`、`lot_no_detail`、`market_inventory_query` 等参数型接口，但应避免回到 3 条样本的低效节奏。
5. 如选择 `purchase_plan_page` 进入 enabled，必须说明它当前总量为 0 的业务意义，并用完整 enabled 批次证明不会影响日常同步。
6. 如果评估 enabled，必须先测算完整 enabled 批次新增请求数和耗时；当前 30 enabled 批次实测约 4825 秒。
7. 任何日期窗口完整验证都必须证明 `item_count == total_count`；如触发 `date window page truncated`，先修正分页上限后重跑。
8. 如果现有机制不够，必须测试先行做最小扩展。
9. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
10. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
11. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
12. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
13. 更新三份 docs；如 README 的运行说明或 API 状态变动需要同步，也一起更新。
14. 提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口、参数窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
3. 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
4. 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 30 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
