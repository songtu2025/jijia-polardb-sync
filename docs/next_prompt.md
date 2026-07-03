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

阶段 6L 已完成。下一阶段 6M 继续基于 6K 执行分层推进覆盖，优先在 `needs_param_source` 中选择第二个能证明真实参数来源的接口，或为已验证 disabled 接口设计更明确的历史回填策略。

当前事实：

- 当前 enabled API 有 24 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`base_currency_query`。
- 当前已配置真实 API 有 46 个，其中 24 个已 enabled；`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`amazon_msku_page`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`traffic_analysis_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`transfer_page`、`lot_no_page`、`purchase_plan_page` 和 `procure_detail` 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 46 个，enabled 24 个。
- 6K 为 `app.doc_catalog` 增加执行分层字段：`execution_bucket`、`execution_stage`、`execution_reason`。
- 6K 覆盖矩阵执行分层摘要为：`configured=45`、`needs_upstream_params=68`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 6L 新增 `procure_detail`，文档 id 为 `1024`，路径为 `GET /purchase/srm/procure/detail`，默认保持 `enabled=false`。
- 6L 先排除 `attribute/detail` 和 `multiShopWarehouse/query`：当前数据库证据无法证明 `attributeName` 和 `platformCode` 来源，不要靠猜测字段接入。
- 6L 已只读确认 `lot_no_page` 有 300 条 raw，其中 300 条都有 `poCode`，去重后 168 个采购单号。
- 6L 的 `procure_detail` 配置从 `lot_no_page.raw_json.poCode` 取参，`limit=3`，`auto_advance=true`，`response.item_field=data`。
- `procure_detail` 公开文档响应 `data` 没有稳定顶层 `code` 或日期字段，因此当前 `primary_key.field=""`、`date_field=""`，依赖 `data_hash` 幂等。
- 6L 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 24 个 enabled API。
- 6L 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已通过，同步配置数 48；数据库总配置 48 条、启用 24 条，`procure_detail.enabled=0`。
- 6L 的 `procure_detail` 单接口批次为 `sync_20260703_170038_518908`，状态 `success`，`rows=3`、`requests=3`、失败 0。
- 6L 数据库核验：同批次 `sync_api_log` 成功，raw 3 条都有 `data_hash`，checkpoint 记录 `param_offset=0`、`param_limit=3`、`next_param_offset=3`。
- 6L 的 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary` 已通过，公开文档 185 个，真实配置 46 个，enabled 24 个。
- 6L 覆盖矩阵执行分层摘要为：`configured=46`、`needs_upstream_params=67`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 当前未配置且可直接普通探测的候选仍为 0 个；下一步不要继续按早期“未配置 direct_read_candidate 里挑一个”的策略推进。
- 当前仍不支持数组入参、嵌套数组来源或复杂过滤表达式。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `purchaseSaleStorageSelf/page` 的 `dateType=DAY` 配合 `beginDate/endDate` 返回 400/50099；`trafficSkuAnalysis/page` 探测时快速触发 509；`multiTypeWarehouse/page` 响应包含联系人、手机号、邮箱和地址；`quickInbound/query` 是数组入参且请求不稳定。
- `deliveryFee/query`、`relevancePoInfo/query` 和 `traffic_analysis_page` 高频或连续分页时出现过 509；后续类似接口应减少手工扫参，优先用小窗口同步和较长等待。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、6K 执行分层、6L `procure_detail` 参数源证据和当前 disabled 已验证接口清单。
2. 优先从 `needs_param_source` 中选择一个能证明真实上游参数来源的接口；不要优先进入订单、财务敏感明细、客服文本、物流费用或销售售后。
3. 如果候选涉及依赖参数，先只读查询数据库证明参数来源真实存在，再新增默认 disabled 小样本配置。
4. 如果现有 `param_source.fields`、`param_source.filters`、`param_source.auto_advance` 不够用，必须测试先行做最小扩展。
5. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
6. 对限流严格的接口，默认使用更小 `max_pages`、更长 `rate_limit.sleep_seconds` 或独立调度，不要直接加入 daily enabled。
7. 启用接口前，必须把 `max_pages`、日期窗口或参数窗口调整到能覆盖当前目标范围，不能把接入阶段小窗口误当完整拉取。
8. 如本轮选择启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量正确，并用真实批次证明成功。
9. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 同步 DB 配置。
10. 按本轮目标运行单接口同步、小范围 enabled 回归或完整 `--sync-enabled`；完整 enabled 当前要预留约 1.5 小时以上窗口。
11. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
12. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
13. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
14. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
15. 更新 README、三份 docs，并提交推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口或启用评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如新增接口，默认保持 disabled，除非已经明确完成进入日常批量的风险评估。
3. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 46 个、enabled 24 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
