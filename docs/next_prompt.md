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

阶段 12H 已完成。`storage_inbound_detail` 因当前执行窗口限制从 5000 调整回 2000 缺失扫描窗口，批次 `sync_20260710_193937_362020` 成功补齐 2000 个缺失入库单详情；12F-12H 三轮复盘已完成。下一阶段 12I 继续推进完整拉取，优先继续 `storage_inbound_detail` 缺失扫描，或先评估是否需要更稳妥的长任务 runner。

当前事实：

- 当前 enabled API 有 45 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`amazon_msku_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 覆盖矩阵当前口径：公开文档 API 187 个，真实配置 API 51 个，enabled API 45 个，configured disabled 6 个。
- 当前 DB `api_config` 共 59 条；销售表现同一个文档接口被拆成 7 个 `api_code`。
- 销售表现 7 个配置为：`sales_analysis_seller_sku_page`、`sales_analysis_asin_page`、`sales_analysis_variation_asin_page`、`sales_analysis_sku_page`、`sales_analysis_spu_page`、`sales_analysis_country_page`、`sales_analysis_market_page`。
- 销售表现 7 个配置均为 `enabled=false`、`commit_per_page=true`、`write_batch_size=10`、`data_date_param=beginDate`、`rate_limit.sleep_seconds=20`、`retry.retries=1`。
- 销售表现最近单接口验证均成功：`seller_sku=2673` 行/14 请求，`asin=2651` 行/14 请求，`sku=2097` 行/11 请求，`spu=34` 行/1 请求，`variation_asin=113` 行/1 请求，`country=7` 行/1 请求，`market=24` 行/1 请求。
- 修正 `data_date_param` 后，`sales_analysis_spu_page` 批次 `sync_20260707_102027_648202` 成功写入 35 条，DB 核验新窗口 `data_date=2026-07-03`。
- 销售表现真实响应里 `dateLine` 字段存在但值为 JSON `null`；后续不要再依赖 `dateLine` 作为 `raw_api_data.data_date` 来源。
- `commit_per_page=true` 当前只用于 `--sync-api` 单接口验证路径；普通 enabled 同步路径未改变。
- `storage_inbound_detail` 当前配置为 `enabled=false`、`param_source.limit=2000`、`auto_advance=true`、`exclude_existing_target=true`，累计覆盖为 23506/174334 个上游去重 code。
- 12H 批次 `sync_20260710_193937_362020` 成功：2000 次请求、2000 条成功计数、失败 0；本批次 raw 为 2000 条、2000 个 `source_primary_key`、2000 个不同主键、2000 个 `data_hash`，`data_date` 覆盖 `2023-12-14` 到 `2024-10-21`。
- 阶段 12F 曾遇到 `raw_api_data` upsert 锁等待超时，根因是后台启动尝试留下 MySQL Sleep 事务；如再遇到锁等待，应先查 `information_schema.processlist` 和 `information_schema.innodb_trx`。
- 当前核验显示 `information_schema.innodb_trx` 为空。

建议目标：

- 优先继续 `storage_inbound_detail` 缺失扫描回填；下一轮建议继续 `limit=2000`，避免当前前台执行窗口再次被 5000 长任务拖住。
- 不要直接把 `storage_inbound_detail` 加入 enabled；它当前只覆盖 23506/174334。
- 不要直接把销售表现加入 enabled；先评估 7 个粒度每天按 20 秒页间隔运行的 cron 窗口。
- 继续只读关注其他 configured disabled API：`market_inventory_query`、`delivery_fee_query`、`inventory_event_page`、`inventory_age_page`。
- 不要直接启用超大接口：`inventory_event_page` 当前约 2669068 条，`inventory_age_page` 当前约 6597161 条且响应慢。
- 下一次三轮复盘放在 12K 完成后。

验收：

- 新接口、完整窗口或回填评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如继续 `storage_inbound_detail`，必须证明 `exclude_existing_target=true` 生效、批次没有重复主键、失败日志为 0，并记录累计覆盖进度。
- 如继续推进销售表现，必须区分“7 个拆分 api_code”和“覆盖矩阵 1 个文档接口”的口径差异。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 51 个、enabled 45 个、configured disabled 6 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
