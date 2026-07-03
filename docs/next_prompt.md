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

阶段 6H 已完成。下一阶段 6I 继续推进“完整拉取所有可访问数据”的覆盖面；可以继续接一个低风险报表/库存日期窗口接口，或评估一个已验证 disabled 接口是否具备进入 enabled 的条件。

当前事实：

- 当前 enabled API 有 23 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`base_currency_query`。
- 当前已配置真实 API 有 44 个，其中 23 个已 enabled；`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`amazon_msku_page`、`platform_msku_page`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`traffic_analysis_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`transfer_page`、`lot_no_page` 和 `purchase_plan_page` 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 44 个，enabled 23 个。
- 5V 的完整 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled` 批次为 `sync_20260703_104718_888820`，状态 `success`，23 个 API 全部成功，总请求数 3053，总写入行数 306199，运行耗时 5735 秒。
- 请求参数日期模板支持 `{{ today }}`、`{{ yesterday }}`、`{{ days_ago:N }}`。
- `date_window` 支持顶层字段和点路径嵌套字段，可用 checkpoint 中的 `next_window_start` 推进历史窗口，并已支持追平当前日期后的自动跳过。
- `traffic_analysis_page`、`shipment_data_page`、`storage_ledger_page` 和 `inventory_receipts_page` 已完成真实单日窗口验证，均保持 `enabled=false`。
- 6D 的 `traffic_analysis_page` 批次 `sync_20260703_134351_398121` 写入 100 条，失败 0；该接口限流严格。
- 6F 的 `shipment_data_page` 批次 `sync_20260703_140547_384755` 写入 58 条，失败 0；`shipmentId` 已证明是货件级字段，不是行级主键，当前依赖 `data_hash` 幂等。
- 6G 的 `storage_ledger_page` 批次 `sync_20260703_141606_982745` 写入 100 条，失败 0；日期字段为 `model.reportStartDate` 和 `model.reportEndDate`。
- 6H 新增 `inventory_receipts_page`，文档 id 为 `21`，路径为 `POST /purchase/store/inventoryReceipts/page`，默认 `enabled=false`。
- `inventory_receipts_page` 是已接收库存列表，必填 `page`、`pagesize`，可选日期字段为 `marketDateBegin` 和 `marketDateEnd`，响应为 `data.rows` 和 `data.total`。
- `inventory_receipts_page` 真实探测确认 `2026-07-02` 单日窗口返回 `total=735`；样本字段包含 `id`、`marketTimeZone`、`createDate`、`fbaShipmentId`、`product` 和 `warehouseName`。
- 6H 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api inventory_receipts_page` 批次为 `sync_20260703_143224_591261`，状态 `success`，`rows=100`、`requests=1`、失败 0。
- 数据库确认该批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`、耗时 14 秒。
- 同批次 `sync_api_log` 为 `request_count=1`、`success_count=100`、`failed_count=0`、`error_message=NULL`。
- 同批次 `raw_api_data` 写入 100 条，100 条都有不同 `source_primary_key`，100 条都有 `data_hash`，100 条都有 `data_date`，日期范围为 `2026-07-02` 到 `2026-07-02`。
- `inventory_receipts_page` checkpoint 已更新到 `sync_20260703_143224_591261`，`checkpoint_value` 记录 `last_page=1`、`request_count=1`、`item_count=100`、`total_count=735`、`window_start=2026-07-02`、`window_end=2026-07-02`、`next_window_start=2026-07-03`、`window_days=1`。
- 数据库确认 `api_config` 总数 46、启用 23；`inventory_receipts_page.enabled=0`、`page.max_pages=1`、`primary_key.field=id`、`date_field=marketTimeZone`、`date_window.start_field=marketDateBegin`、`date_window.end_field=marketDateEnd`。
- 6H 的 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary` 已通过，公开文档 185 个，真实配置 44 个，enabled 23 个。
- 6H 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 23 个 enabled API。
- 当前仍不支持数组入参、嵌套数组来源或复杂过滤表达式。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `deliveryFee/query`、`relevancePoInfo/query` 和 `traffic_analysis_page` 高频或连续分页时出现过 509；后续类似接口应减少手工扫参，优先用小窗口同步和较长等待。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要，不要假设 CLI 支持 `--dry-run`。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、6H 结果、6E-6G 复盘和当前 disabled 已验证接口清单。
2. 优先在两个方向中选择一个最小目标：继续接一个低风险报表/库存日期窗口接口，或评估一个低体量、已验证、非敏感、非依赖型 disabled 接口是否可以进入 enabled。
3. 如果继续新增接口，优先选择统计、报表、库存看板或配置类接口；暂不要直接进入订单、财务敏感明细、客服文本、物流费用或销售售后。
4. 对限流严格的接口，默认使用更小 `max_pages`、更长 `rate_limit.sleep_seconds` 或独立调度，不要直接加入 daily enabled。
5. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
6. 如果候选涉及依赖参数，先只读查询数据库证明参数来源真实存在；如果是直读接口，先用一次真实请求确认响应形态和耗时。
7. 新增 API 配置时默认 `enabled=false`；启用任何接口前，必须先有测试约束 enabled 数量和目标接口状态。
8. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 同步 DB 配置。
9. 按本轮目标运行单接口同步、追平跳过验证或小范围 enabled 回归；如果运行完整 `--sync-enabled`，要给足超过 2 小时的窗口。
10. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
11. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
12. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
13. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
14. 更新 README、三份 docs，并提交推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口或启用评估必须由公开文档、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如新增接口，默认保持 disabled，除非已经明确完成进入日常批量的风险评估。
3. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 44 个、enabled 23 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
