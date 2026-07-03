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

阶段 6T 已完成。下一阶段 6U 继续推进完整拉取：可以继续做下一个低风险完整窗口，也可以评估 `traffic_page` 是否具备进入 daily enabled 的条件；多页且需要长等待的接口进入 enabled 前必须重新测算 cron 窗口。

当前事实：

- 当前 enabled API 有 25 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_sku_page`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 25 个已 enabled；`traffic_page`、`storage_ledger_page`、`shipment_data_page`、`inventory_receipts_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`purchase_sale_storage_fba_page`、`transfer_page`、`lot_no_page`、`purchase_plan_page`、`procure_detail` 等已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 25 个。
- 6T 覆盖矩阵执行分层摘要为：`configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 6Q 已将 `traffic_sku_page` 推进到 `2026-07-02` 单日完整窗口：批次 `sync_20260703_180803_993141`，`rows=170`、`requests=1`、`item_count=total_count=170`。
- 6R 已将 `traffic_page` 推进到 `2026-07-02` 单日完整窗口：批次 `sync_20260703_182130_693272`，`rows=583`、`requests=2`、`item_count=total_count=583`，仍保持 disabled。
- 6S 已将 `storage_ledger_page` 推进到 `2026-07-02` 单日完整窗口：批次 `sync_20260703_183551_315212`，`rows=1163`、`requests=3`、`item_count=total_count=1163`，仍保持 disabled。
- 6T 选择将 `traffic_sku_page` 从 disabled 提升到 enabled；原因是它完整窗口只需 1 次请求，体量和耗时风险低于 `traffic_page` 与 `storage_ledger_page`。
- 6T 已用 TDD 约束 `traffic_sku_page.enabled=true`，并将 enabled 基线测试从 24 调整为 25。
- 6T 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已通过，同步配置数 52；数据库总配置 52 条、启用 25 条，`traffic_sku_page.enabled=1`。
- 6T 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 25 个 enabled API，并包含 `traffic_sku_page`。
- 6T 的完整 `--sync-enabled` 批次为 `sync_20260703_184641_020339`，状态 `success`，25 个 API 全部成功，失败 0；总请求 3074 次，写入 307943 条，运行约 76 分钟。
- 6T 数据库核验：同批次 `sync_api_log` 共 25 条，25 条成功、0 条失败；`request_count=3074`、`success_count=307943`、`failed_count=0`。
- `traffic_sku_page` 在 6T enabled 批次内请求 1 次，`2026-07-03` 窗口返回 0 条，checkpoint 记录 `item_count=0`、`total_count=0`、`window_start=2026-07-03`、`window_end=2026-07-03`、`next_window_start=2026-07-04`。
- `traffic_page` 和 `storage_ledger_page` 已完成完整窗口，但仍保持 disabled；它们需要多页和较长页间等待，进入 daily enabled 前必须重新评估批量耗时。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- 当前仍不支持复杂数组 join、嵌套数组过滤或复杂过滤表达式；单层数组来源和静态 POST 数组参数已经分别通过测试或真实小窗口验证。
- `deliveryFee/query`、`relevancePoInfo/query`、`traffic_analysis_page`、`traffic_page` 和 `traffic_sku_page` 这类统计或费用接口后续应减少手工扫参；如必须连续分页，先确认页大小上限和限流间隔。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、6K 执行分层、6T `traffic_sku_page` enabled 批次证据、6Q-6S 完整窗口证据和 6Q-6S 复盘。
2. 选择 6U 方向：继续推进一个已验证 disabled 接口的完整窗口，或评估 `traffic_page` 是否具备进入 daily enabled 的条件。
3. 如果评估 enabled，必须先测算完整 enabled 批次新增请求数和耗时；当前 25 enabled 批次实测约 76 分钟。
4. 如果评估完整窗口，必须先确认总量、页大小上限、限流、预估请求数和是否可用单请求大页覆盖。
5. 如果必须连续分页，先确认失败风险；`traffic_page` 证明页大小上限可能低于目标总量，`storage_ledger_page` 证明旧 checkpoint 总量可能低于当前真实总量。
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
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 25 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
