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

阶段 6O 已完成。下一阶段 6P 继续基于 6K 执行分层推进覆盖，可优先选择下一个能用现有能力证明参数来源的候选，或开始为日期/月窗口类 disabled 大表制定分批回填策略。6P 完成后需要做 6N-6P 三轮复盘。

当前事实：

- 当前 enabled API 有 24 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`base_currency_query`。
- 当前已配置真实 API 有 49 个，其中 24 个已 enabled；`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`amazon_msku_page`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`traffic_analysis_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`transfer_page`、`lot_no_page`、`purchase_plan_page` 和 `procure_detail` 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 49 个，enabled 24 个。
- 6O 覆盖矩阵执行分层摘要为：`configured=49`、`needs_upstream_params=64`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 6K 为 `app.doc_catalog` 增加执行分层字段：`execution_bucket`、`execution_stage`、`execution_reason`。
- 6L 新增 `procure_detail`，文档 id 为 `1024`，路径为 `GET /purchase/srm/procure/detail`，默认保持 `enabled=false`，从 `lot_no_page.raw_json.poCode` 取参。
- 6M 新增 `storage_ledger_detail_page`，文档 id 为 `773`，路径为 `POST /purchase/inventory/storageLedgerDetail/page`，默认保持 `enabled=false`，使用 `model.beginReportDate` / `model.endReportDate`。
- 6N 新增 `storage_ledger_month_page`，文档 id 为 `2658`，路径为 `POST /fulfillment/inventory/storageLedgerMonth/page`，默认保持 `enabled=false`，使用 `monthList=["2026-06"]`。
- 6O 增加了 `param_source.fields` 的单层数组展开能力，支持 `raw_json.marketListVos[].marketId` 这类来源；当前只支持一个数组字段，不支持数组过滤、多字段同位绑定或复杂 join。
- 6O 已用真实 DB 只读确认 `amazon_shop_page.raw_json.marketListVos[].marketId` 可生成站点参数，例如 `marketId=1/10/11/12/13`。
- 6O 小范围探测 `openPrimeDiscount/query`、`openManagePromotion/query`、`coupon/query` 和 `deal/query` 时出现 400/509，因此这些广告促销接口没有作为本轮新增配置。
- 6O 新增 `traffic_sku_page`，文档 id 为 `123`，路径为 `POST /operation/sts/trafficSku/page`，默认保持 `enabled=false`。
- 6O 官方文档确认 `traffic_sku_page` 必填 `currency`、`beginDate`、`endDate`、`page`、`pagesize`、`viewType`；响应 `data.rows`，总数 `data.total`，日期字段 `recordDate`。
- 6O 不落库探测确认 `2026-07-02` 单日 `CNY/day` 返回 `total=170`，第一页 100 条。
- 6O 首次把 `traffic_sku_page.primary_key.required=true` 时，批次 `sync_20260703_174353_519246` 请求成功但写入 0 条；已确认真实响应的 `id` 不适合作为必填主键，最终配置为空主键，依靠 `data_hash` 幂等。
- 6O 最终配置使用 `currency=CNY`、`viewType=day`、`date_window.start_field=beginDate`、`date_window.end_field=endDate`、`default_start=2026-07-02`、`page.max_pages=1`、`primary_key.field=""`。
- 6O 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 24 个 enabled API。
- 6O 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已通过，同步配置数 51；数据库总配置 51 条、启用 24 条，`traffic_sku_page.enabled=0`。
- 6O 的 `traffic_sku_page` 正式单接口批次为 `sync_20260703_174553_317496`，状态 `success`，`rows=100`、`requests=1`、失败 0。
- 6O 数据库核验：同批次 `sync_batch` 成功，`sync_api_log` 成功，raw 100 条、100 个 distinct hash、100 条都有 `raw_json` 和 `data_date=2026-07-02`。
- 6O checkpoint 记录 `last_page=1`、`request_count=1`、`item_count=100`、`total_count=170`、`window_start=2026-07-02`、`window_end=2026-07-02`、`next_window_start=2026-07-03`。
- 6K-6M 三轮复盘已写入 `docs/progress.md`；下一次三轮复盘应在 6P 完成后做 6N-6P 复盘。
- 当前未配置且可直接普通探测的候选仍为 0 个；下一步不要继续按早期“未配置 direct_read_candidate 里挑一个”的策略推进。
- 当前仍不支持复杂数组 join、嵌套数组过滤或复杂过滤表达式；单层数组来源和静态 POST 数组参数已经分别通过测试或真实小窗口验证。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `purchaseSaleStorageSelf/page` 的 `dateType=DAY` 配合 `beginDate/endDate` 返回 400/50099；`trafficSkuAnalysis/page` 探测时快速触发 509；`multiTypeWarehouse/page` 响应包含联系人、手机号、邮箱和地址；`quickInbound/query` 是数组入参且请求不稳定。
- `deliveryFee/query`、`relevancePoInfo/query` 和 `traffic_analysis_page` 高频或连续分页时出现过 509；后续类似接口应减少手工扫参，优先用小窗口同步和较长等待。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、6K 执行分层、6L/6M/6N/6O 证据和当前 disabled 已验证接口清单。
2. 优先从 `needs_param_source` 中选择能用现有能力证明真实参数来源的接口；不要优先进入订单、财务敏感明细、客服文本、物流费用或销售售后。
3. 如果候选涉及依赖参数，先只读查询数据库证明参数来源真实存在，再新增默认 disabled 小样本配置。
4. 如果现有 `param_source.fields`、`param_source.filters`、`param_source.auto_advance` 或单层数组展开不够用，必须测试先行做最小扩展。
5. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
6. 对限流严格的接口，默认使用更小 `max_pages`、更长 `rate_limit.sleep_seconds` 或独立调度，不要直接加入 daily enabled。
7. 如评估已验证 disabled 接口进入 enabled，必须先把 `max_pages`、窗口或参数窗口调整到能覆盖当前目标范围，不能把接入阶段小窗口误当完整拉取。
8. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 同步 DB 配置。
9. 按本轮目标运行单接口同步、小范围 enabled 回归或完整 `--sync-enabled`；完整 enabled 当前要预留约 1.5 小时以上窗口。
10. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
11. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
12. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
13. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
14. 更新 README、三份 docs；6P 完成后写 6N-6P 三轮复盘；提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口或启用评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如新增接口，默认保持 disabled，除非已经明确完成进入日常批量的风险评估。
3. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 49 个、enabled 24 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
