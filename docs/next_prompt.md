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

阶段 6S 已完成。下一阶段 6T 进入新一组三轮：可以继续从已验证 disabled 接口中选择体量可控者推进完整单接口窗口，也可以评估已完成完整窗口的接口是否具备进入 daily enabled 的条件。

当前事实：

- 当前 enabled API 有 24 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 24 个已 enabled；`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`amazon_msku_page`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`transfer_page`、`lot_no_page`、`purchase_plan_page` 和 `procure_detail` 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 24 个。
- 6S 覆盖矩阵执行分层摘要仍为：`configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 6Q 已将 `traffic_sku_page` 推进到 `2026-07-02` 单日完整窗口：批次 `sync_20260703_180803_993141`，`rows=170`、`requests=1`、`item_count=total_count=170`，仍保持 disabled。
- 6R 已将 `traffic_page` 推进到 `2026-07-02` 单日完整窗口：批次 `sync_20260703_182130_693272`，`rows=583`、`requests=2`、`item_count=total_count=583`，仍保持 disabled。
- 6S 已将 `storage_ledger_page` 推进到 `2026-07-02` 单日完整窗口：批次 `sync_20260703_183551_315212`，`rows=1163`、`requests=3`、`item_count=total_count=1163`，仍保持 disabled。
- 6S 起点的旧 checkpoint 记录 `storage_ledger_page.total_count=710`；本轮真实同步发现当前 `2026-07-02` 总量已变为 1163。因此后续完整窗口判断必须以最新 checkpoint 为准。
- 6S 第一次 `storage_ledger_page` 完整窗口尝试批次 `sync_20260703_183130_464206` 写入 1000 条、请求 2 次，但 checkpoint 显示 `total_count=1163`，不算完整窗口。
- 6S 最终采用 `storage_ledger_page.page.page_size=500`、`params.pagesize=500`、`page.max_pages=3`、`rate_limit.sleep_seconds=65`、`retry.retries=1`。
- 6S 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 24 个 enabled API。
- 6S 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已通过，同步配置数 52；数据库总配置 52 条、启用 24 条，`storage_ledger_page.enabled=0`。
- 6S 数据库核验：同批次 `sync_batch` 成功，`sync_api_log` 成功，raw 1163 条、1163 个 distinct hash、1163 条都有 `raw_json` 和 `data_date=2026-07-02`。
- 6S checkpoint 记录 `last_page=3`、`request_count=3`、`item_count=1163`、`total_count=1163`、`window_start=2026-07-02`、`window_end=2026-07-02`、`next_window_start=2026-07-03`。
- 6Q-6S 复盘结论：完整窗口标准必须以 checkpoint 的 `item_count == total_count` 为准，不能用早期小窗口总量或命令输出的成功状态替代。
- 6Q-6S 复盘结论：严格限流或分页上限不明的接口，优先减少无效重试、确认页大小上限、按较长页间等待推进；`traffic_sku_page` 适合单页放大，`traffic_page` 和 `storage_ledger_page` 需要少量分页。
- 6Q-6S 复盘结论：这些接口仍保持 disabled，进入 daily enabled 前还要评估每天窗口、历史回填节奏、完整 enabled 批次耗时和 cron 窗口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- 当前仍不支持复杂数组 join、嵌套数组过滤或复杂过滤表达式；单层数组来源和静态 POST 数组参数已经分别通过测试或真实小窗口验证。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `purchaseSaleStorageSelf/page` 的 `dateType=DAY` 配合 `beginDate/endDate` 返回 400/50099；`trafficSkuAnalysis/page` 探测时快速触发 509；`multiTypeWarehouse/page` 响应包含联系人、手机号、邮箱和地址；`quickInbound/query` 是数组入参且请求不稳定。
- `deliveryFee/query`、`relevancePoInfo/query`、`traffic_analysis_page`、`traffic_page` 和 `traffic_sku_page` 这类统计或费用接口后续应减少手工扫参；如必须连续分页，先确认页大小上限和限流间隔。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、6K 执行分层、6Q-6S 完整窗口证据、6Q-6S 复盘、6N-6P 复盘和 `platform_msku_page` enabled 批次证据。
2. 选择 6T 方向：继续推进一个已验证 disabled 接口的完整窗口，或评估已完成完整窗口的 `traffic_sku_page`、`traffic_page`、`storage_ledger_page` 是否具备进入 daily enabled 的条件。
3. 如果评估 enabled，必须先测算完整 enabled 批次新增请求数和耗时；完整 enabled 当前要预留约 1.5 小时以上窗口，不能直接把新接口加入 daily。
4. 如果评估完整窗口，必须先确认总量、页大小上限、限流、预估请求数和是否可用单请求大页覆盖，不能把接入阶段小窗口误当完整拉取。
5. 如果必须连续分页，先确认失败风险；`traffic_page` 证明页大小上限可能低于目标总量，`traffic_sku_page` 证明连续翻页可能触发 509，`storage_ledger_page` 证明旧 checkpoint 总量可能低于当前真实总量。
6. 如果继续新增 API，仍优先从 `needs_param_source` 中选择能用现有能力证明真实参数来源的接口。
7. 如果候选涉及依赖参数，先只读查询数据库证明参数来源真实存在，再新增默认 disabled 小样本配置。
8. 如果现有 `param_source.fields`、`param_source.filters`、`param_source.auto_advance`、单层数组展开或 `date_window` 不够用，必须测试先行做最小扩展。
9. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
10. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 同步 DB 配置。
11. 按本轮目标运行单接口同步、小范围 enabled 回归或完整 `--sync-enabled`。
12. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
13. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
14. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
15. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
16. 更新 README、三份 docs；提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如新增接口，默认保持 disabled，除非它已经完成进入日常批量的风险评估。
3. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
4. 如推进完整单接口窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0；不能只跑接入小窗口。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 24 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
