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

阶段 11S 已完成。下一阶段 11T 继续推进完整拉取。`amazon_msku_page` 已完成 185 页全量同步并进入 enabled 主链路；当前真实配置 API 为 50 个，enabled API 为 39 个，configured disabled 为 11 个。

当前事实：

- 当前 enabled API 有 39 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`amazon_msku_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 39 个已 enabled；剩余 11 个真实配置 API 已验证但保持 disabled。
- `amazon_msku_page` 当前配置为 `enabled=true`、`page_size=100`、`max_pages=200`、空 `primary_key.field`，使用 `data_hash` 幂等。
- 阶段 11S 单接口批次 `sync_20260705_160248_556873` 成功，`amazon_msku_page` 185 次请求、18430 条成功计数、失败 0。
- `amazon_msku_page` checkpoint 当前为 `last_page=185`、`request_count=185`、`item_count=18430`、`total_count=18430`。
- `amazon_msku_page` 当前 raw 为 18430 条、18430 个 `data_hash`、0 个 `source_primary_key`，`data_date` 覆盖 `2022-08-31` 到 `2026-07-02`。
- 阶段 11S 完整 enabled 批次 `sync_20260705_160652_068698` 成功，39 个 API 全成功，3414 次请求，341770 条成功计数，失败 0，耗时 4779 秒。
- 同批次 `amazon_msku_page` 为 `status=success`、`request_count=185`、`success_count=18430`、`failed_count=0`、`error_message=NULL`。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 39 个；执行分层摘要为 `configured=50`、`configured_enabled=39`、`configured_disabled=11`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 11Q-11S 三轮复盘已完成：11Q 补齐 `traffic_analysis_page` 的 `2026-07-04`，11R 增加 `lag_days` 并将其纳入 enabled，11S 全量补齐并启用 `amazon_msku_page`。
- 阶段 11S dry-run 显示 loaded 39 enabled API config(s)。
- 阶段 11S 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 阶段 11S 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，84 个测试通过。

建议目标：

- 只读盘点剩余 configured disabled API：`market_inventory_query`、`storage_inbound_detail`、`delivery_fee_query`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`purchase_sale_storage_fba_page`。
- 优先从主键明确、分页可控或已具备日期窗口的接口中选择下一阶段目标。
- 不要直接启用超大接口：`inventory_event_page` 当前约 2669068 条，`inventory_age_page` 当前约 6597161 条且响应慢。
- 参数型详情接口和费用类接口必须先证明缺失扫描或字段过滤不会重复拉取全部历史，也不会漏扫新增来源参数。
- 如选择新接口，继续按“default-disabled candidate -> 单接口验证 -> enabled 评估 -> `--sync-api-configs` -> dry-run -> 必要时 `--sync-enabled` -> docs”闭环推进。
- 下一次三轮复盘在 11V 完成时执行。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功；涉及缺失扫描时必须先证明不会重复拉取全部历史，也不会漏扫新增来源参数。
- 如调整参数型详情接口的幂等或缺失扫描逻辑，必须先证明旧数据不丢、新数据可发现，并用测试覆盖关键逻辑；如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 39 个、configured disabled 11 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
