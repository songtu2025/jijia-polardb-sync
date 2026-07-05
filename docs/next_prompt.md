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

阶段 12B 已完成。下一阶段 12C 继续推进完整拉取。`storage_inbound_detail` 缺失扫描窗口已从 1000 提高到 2000，本轮补齐 2000 个缺失入库单详情；当前真实配置 API 为 50 个，enabled API 为 45 个，configured disabled 为 5 个。

当前事实：

- 当前 enabled API 有 45 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`amazon_msku_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 45 个已 enabled；剩余 5 个真实配置 API 已验证但保持 disabled。
- 剩余 configured disabled API 为：`market_inventory_query`、`storage_inbound_detail`、`delivery_fee_query`、`inventory_event_page`、`inventory_age_page`。
- `storage_inbound_detail` 当前配置为 `enabled=false`、`param_source.limit=2000`、`auto_advance=true`、`exclude_existing_target=true`，参数来自 `storage_inbound_page.raw_json.code`，响应主键为 `code`。
- 阶段 12B 单接口批次 `sync_20260706_064400_057740` 成功，2000 次请求、2000 条成功计数、失败 0，耗时 1725 秒。
- 同批次 `storage_inbound_detail` raw 为 2000 条、2000 个 `source_primary_key`、2000 个不同主键、2000 个 `data_hash`，`data_date` 覆盖 `2023-07-27` 到 `2024-02-01`。
- `storage_inbound_detail` 累计覆盖为 3506/174334 个上游去重 code；还没有达到 enabled 条件。
- DB 配置已确认 `api_config.storage_inbound_detail.enabled=0`、`param_source.limit=2000`、`exclude_existing_target=true`、`auto_advance=true`。
- 阶段 12B dry-run 显示 loaded 45 enabled API config(s)，确认未误启用 `storage_inbound_detail`。
- 阶段 12B 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 45 个，configured disabled 5 个。
- 阶段 12B 已完成 11Z-12B 三轮复盘；下一次三轮复盘放在 12E 完成后。

建议目标：

- 优先继续 `storage_inbound_detail` 缺失扫描回填；下一轮可保持 `limit=2000` 再跑一批，或先只读评估是否把窗口提高到 3000/5000。
- 不要直接把 `storage_inbound_detail` 加入 enabled；它当前只覆盖 3506/174334。
- 继续只读关注其他 configured disabled API：`market_inventory_query`、`delivery_fee_query`、`inventory_event_page`、`inventory_age_page`。
- 不要直接启用超大接口：`inventory_event_page` 当前约 2669068 条，`inventory_age_page` 当前约 6597161 条且响应慢。
- `market_inventory_query` 无稳定主键，`delivery_fee_query` 有空费用对象边界；二者进入 enabled 前必须先证明缺失扫描和幂等边界。

验收：

- 新接口、完整窗口或回填评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功；涉及缺失扫描时必须先证明不会重复拉取全部历史，也不会漏扫新增来源参数。
- 如继续 `storage_inbound_detail`，必须证明 `exclude_existing_target=true` 生效、批次没有重复主键、失败日志为 0，并记录累计覆盖进度。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 45 个、configured disabled 5 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
