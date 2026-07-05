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

阶段 11N 已完成。下一阶段 11O 继续推进完整拉取：`procure_detail` 已通过稳定主键回填、缺失扫描和完整 enabled 批次验证，进入每日 enabled 主链路。当前真实配置 API 为 50 个，enabled API 为 37 个，configured disabled 为 13 个。

当前事实：

- 当前 enabled API 有 37 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 37 个已 enabled；剩余 13 个真实配置 API 已验证但保持 disabled。
- 剩余 13 个 configured disabled API 是：`market_inventory_query`、`storage_inbound_detail`、`delivery_fee_query`、`amazon_msku_page`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`traffic_analysis_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`purchase_sale_storage_fba_page`。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 37 个；执行分层摘要为 `configured=50`、`configured_enabled=37`、`configured_disabled=13`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- `procure_detail` 配置为 `enabled=true`、`primary_key.param_field=poCode`、`param_source.exclude_existing_target=true`。
- 阶段 11N 已验证 `warehouseProcureItemVos[].procureItemVos[].code` 与 `lot_no_page.raw_json.poCode` 的 1153 个去重值完全重合。
- 阶段 11N 已将历史 `procure_detail` raw 从 1153 条空 `source_primary_key` 回填为 1153 条非空主键、1153 个不同主键。
- 阶段 11N 单接口缺失扫描批次 `sync_20260705_121606_608741` 成功，请求 0 次、写入 0 条、失败 0，`missing_by_pk=0`。
- 阶段 11N dry-run 显示 loaded 37 enabled API config(s)，且包含 `procure_detail`。
- 阶段 11N 完整 enabled 批次 `sync_20260705_121739_107135` 成功，37 个 API 全成功，3230 次请求，323340 条成功计数。
- 同批次 `procure_detail` 为请求 0 次、写入 0 条、失败 0，证明进入 enabled 后不会重复请求历史。
- 阶段 11N 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 37 个、configured disabled 13 个。
- 阶段 11N 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 阶段 11N 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，83 个测试通过。
- 当前 37 个 enabled API 的真实批量同步耗时约 4664 秒，必须按长耗时任务安排 cron 窗口。

建议目标：

- 先只读复核剩余 13 个 configured disabled API 的风险、总量、窗口和依赖参数。
- 优先选择总量小、已具备日期窗口或缺失扫描边界、不会显著拉长 enabled 批次的候选；当前可重点复核 `traffic_analysis_page` 的限流和日期窗口是否已满足进入 enabled 的条件。
- 如果启用新 API，必须先改 YAML、同步 `api_config`、dry-run 确认 enabled 数量从 37 变为 38，再运行完整 `--sync-enabled`。
- 如只是推进 disabled API 的窗口或补充安全边界，必须证明 checkpoint、raw、失败日志和覆盖矩阵变化符合预期。
- 完成后同步 `api_config`、刷新覆盖矩阵并运行编译与单测。
- 下一次三轮复盘放在 11P 完成后。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如调整参数型详情接口的幂等或缺失扫描逻辑，必须先证明旧数据不丢、新数据可发现，并用测试覆盖关键逻辑。
- 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 37 个、configured disabled 13 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存和日志不提交。
