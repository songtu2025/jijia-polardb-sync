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

阶段 11R 已完成。下一阶段 11S 继续推进完整拉取，并完成 11Q-11S 三轮复盘。`traffic_analysis_page` 已通过 `date_window.lag_days=1` 进入 enabled 主链路；当前真实配置 API 为 50 个，enabled API 为 38 个，configured disabled 为 12 个。

当前事实：

- 当前 enabled API 有 38 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 38 个已 enabled；剩余 12 个真实配置 API 已验证但保持 disabled。
- `date_window.lag_days` 已支持：默认 0，不改变现有接口；配置为 1 时只同步昨天及更早完整日。
- `traffic_analysis_page` 当前配置为 `enabled=true`、`page_size=500`、`max_pages=8`、`rate_limit.sleep_seconds=65`、`retry.retries=1`、`date_window.lag_days=1`。
- `traffic_analysis_page` 已补齐 `2026-07-02` 的 3537/3537 条、`2026-07-03` 的 3548/3548 条、`2026-07-04` 的 114/114 条，累计 raw 为 7216 条、7216 个 `data_hash`。
- `traffic_analysis_page` checkpoint 当前为 `next_window_start=2026-07-05`，在 `2026-07-05` 当天因 `lag_days=1` 被视为已追平，跳过请求。
- 阶段 11R 单接口批次 `sync_20260705_142751_374712` 成功，`traffic_analysis_page` 请求 0 次、写入 0 条、失败 0；DB 显示 `api_config.enabled=1`、`config_json.enabled=true`、`lag_days=1`。
- 阶段 11R 完整 enabled 批次 `sync_20260705_142844_991672` 成功，38 个 API 全成功，3230 次请求，323340 条成功计数，失败 0，耗时 4283 秒。
- 同批次 `traffic_analysis_page` 为 `status=success`、`request_count=0`、`success_count=0`、`failed_count=0`、`error_message=NULL`。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 38 个；执行分层摘要为 `configured=50`、`configured_enabled=38`、`configured_disabled=12`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 阶段 11R dry-run 显示 loaded 38 enabled API config(s)。
- 阶段 11R 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 阶段 11R 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，84 个测试通过。

建议目标：

- 先做 11Q-11S 三轮复盘：11Q 补齐 `traffic_analysis_page` 的 `2026-07-04`，11R 增加 `lag_days` 并将其纳入 enabled，11S 应评估下一批候选风险。
- 只读盘点剩余 configured disabled API：`market_inventory_query`、`storage_inbound_detail`、`delivery_fee_query`、`amazon_msku_page`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`purchase_sale_storage_fba_page`。
- 优先从低风险、可控分页或已具备日期窗口的接口中选择下一阶段目标；大库存表、费用类和参数型详情接口应先做只读风险评估，不要直接 enabled。
- 如选择新接口，继续按“default-disabled candidate -> 单接口验证 -> enabled 评估 -> `--sync-api-configs` -> dry-run -> 必要时 `--sync-enabled` -> docs”闭环推进。
- 完成 11S 后必须写 11Q-11S 三轮复盘。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功；涉及缺失扫描时必须先证明不会重复拉取全部历史，也不会漏扫新增来源参数。
- 如调整参数型详情接口的幂等或缺失扫描逻辑，必须先证明旧数据不丢、新数据可发现，并用测试覆盖关键逻辑；如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 38 个、configured disabled 12 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
