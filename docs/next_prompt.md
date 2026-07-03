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

阶段 6W 已完成。下一阶段 6X 继续推进完整拉取：优先从剩余已验证 disabled 的日期窗口接口中选择低风险、体量可控者推进完整窗口，或评估 `inventory_receipts_page` 是否具备进入 daily enabled 的条件；多页接口进入 enabled 前必须重新测算 cron 窗口。

当前事实：

- 当前 enabled API 有 27 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`storage_ledger_page`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 27 个已 enabled；`inventory_receipts_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`shipment_data_page`、`purchase_sale_storage_fba_page`、`traffic_analysis_page`、`transfer_page`、`lot_no_page`、`purchase_plan_page`、`procure_detail` 等已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 27 个。
- 6W 覆盖矩阵执行分层摘要为：`configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 6V 完整 enabled 批次为 `sync_20260703_214704_241675`，27 个 API 全部成功，总请求 3075 次，写入 307943 条，运行约 77 分钟。
- 6W 选择 `inventory_receipts_page` 做完整单接口窗口，未加入 enabled。
- 6W 已将 `inventory_receipts_page.page.max_pages` 从 1 调整为 10，仍保持 `enabled=false`、`page_size=100`、`params.pagesize=100`。
- 6W 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已通过，同步配置数 52；数据库总配置 52 条、启用 27 条，`inventory_receipts_page.enabled=0`。
- 6W 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 仍显示 27 个 enabled API，确认 `inventory_receipts_page` 没有误启用。
- 6W 的单接口完整窗口批次为 `sync_20260703_231344_896620`，状态 `success`，请求 2 次，写入 157 条，失败 0。
- 6W 数据库核验：该批次 157 条 raw 都有不同 `source_primary_key`，无缺失主键，`data_date=2026-07-03`。
- `inventory_receipts_page` checkpoint 已推进到 `next_window_start=2026-07-04`，并记录 `item_count=157`、`total_count=157`、`window_start=2026-07-03`、`window_end=2026-07-03`。
- `inventory_receipts_page` 历史窗口事实：`2026-07-02` 单日总量 735 条，`2026-07-03` 单日总量 157 条；当前用 `max_pages=10` 能覆盖这两个窗口。
- `traffic_analysis_page` 在 `2026-07-02` 单日 CNY 窗口总量 528 条，但限流严格，曾在第 2 页触发 509。
- `storage_ledger_detail_page` 在 `2026-07-02` 单日窗口总量 27104 条，不适合直接完整窗口。
- `storage_ledger_month_page` 在 `2026-06` 月窗口总量 6044 条，不适合直接进入 daily enabled。
- `purchase_sale_storage_fba_page` 当前 MSKU 数量维度总量 58955 条，且不是 date_window 接口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- 当前仍不支持复杂数组 join、嵌套数组过滤或复杂过滤表达式；单层数组来源和静态 POST 数组参数已经分别通过测试或真实小窗口验证。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、6K 执行分层、6W `inventory_receipts_page` 完整窗口证据、6V enabled 批次证据和 6T-6V 复盘。
2. 选择 6X 方向：可以评估 `inventory_receipts_page` 是否进入 daily enabled，也可以继续推进另一个 disabled 日期窗口的完整窗口。
3. 如果评估 enabled，必须先测算完整 enabled 批次新增请求数和耗时；当前 27 enabled 批次实测约 77 分钟。
4. 如果评估完整窗口，必须先确认总量、页大小上限、限流、预估请求数和是否可用单请求大页覆盖。
5. 如果必须连续分页，先确认失败风险；严格限流接口不要盲目增加页数和重试。
6. 如果候选涉及依赖参数，先只读查询数据库证明参数来源真实存在，再新增默认 disabled 小样本配置。
7. 如果现有机制不够，必须测试先行做最小扩展。
8. 按本轮目标运行单接口同步、小范围 enabled 回归或完整 `--sync-enabled`。
9. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
10. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`；该命令近期可能超过 120 秒，请预留 300 秒。
11. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
12. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
13. 更新 README、三份 docs；提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
3. 如推进完整单接口窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 27 个，`inventory_receipts_page` 保持 disabled 但完整窗口配置已是 `max_pages=10`。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
