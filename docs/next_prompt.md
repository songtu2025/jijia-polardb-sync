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

阶段 15G 已完成。`storage_inbound_detail` 使用官方 CLI 路径补齐最后 828 个缺失入库单详情，批次 `sync_20260712_185853_014941` 成功；当前覆盖 174334/174334，完成 100.00%，剩余 0。下一阶段 15H 建议做空缺口验证和 enabled 边界评估，并作为本组三轮第 2 轮。

当前事实：

- 当前 enabled API 有 45 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`amazon_msku_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 覆盖矩阵当前口径：公开文档 API 187 个，真实配置 API 51 个，enabled API 45 个，configured disabled 6 个。
- 当前 DB `api_config` 共 59 条；销售表现同一个文档接口被拆成 7 个 `api_code`。
- `storage_inbound_detail` 当前配置为 `enabled=false`、`param_source.limit=2000`、`auto_advance=true`、`exclude_existing_target=true`，累计覆盖为 174334/174334 个上游去重 code。
- 15G 批次 `sync_20260712_185853_014941` 成功：828 次请求、828 条成功计数、失败 0，批次耗时 656 秒，API 耗时 654 秒。
- 15G 批次 raw 为 828 条、828 个 `source_primary_key`、828 个不同主键、828 个 `data_hash`、空主键 0，`data_date` 覆盖 `2025-09-23` 到 `2026-07-04`。
- 15G 最终 DB 复核显示累计覆盖 174334/174334、`failed_request_log=0`、named lock 已释放、外部 `information_schema.innodb_trx=0`，DB `api_config` 仍为 59 条、enabled 45 条，`storage_inbound_detail.enabled=0`。
- 15F 曾两次出现 `app.main --sync-api storage_inbound_detail` 通用失败并提示 `release sync task lock failed`；当时未生成可见新批次、覆盖未推进、失败日志为 0，但分别留下 Sleep InnoDB 事务 `5635742` 和 `5637222`，已清理。
- 15G 短 `_sync_task_lock` 烟测未复现 Sleep InnoDB 事务残留；官方 CLI 也正常返回 0。本问题保留为观察项，不要在没有复现证据时过度改造。
- 销售表现 7 个配置均为 `enabled=false`、`commit_per_page=true`、`write_batch_size=10`、`data_date_param=beginDate`、`rate_limit.sleep_seconds=20`、`retry.retries=1`。
- 销售表现最近单接口验证均成功：`seller_sku=2673` 行/14 请求，`asin=2651` 行/14 请求，`sku=2097` 行/11 请求，`spu=34` 行/1 请求，`variation_asin=113` 行/1 请求，`country=7` 行/1 请求，`market=24` 行/1 请求。
- 销售表现真实响应里 `dateLine` 字段存在但值为 JSON `null`；后续不要再依赖 `dateLine` 作为 `raw_api_data.data_date` 来源。
- `commit_per_page=true` 当前只用于 `--sync-api` 单接口验证路径；普通 enabled 同步路径未改变。
- 15D-15F 三轮复盘已完成：覆盖从 167506/174334 推进到 173506/174334，净增 6000。15G 已作为下一组三轮第 1 轮完成，覆盖从 173506 推进到 174334/174334，剩余 0。

建议目标：

- 15H 优先做 `storage_inbound_detail` 空缺口验证：运行前只读核验覆盖率、锁和事务；运行单接口后证明 0 请求或无新增缺口、失败日志为 0、锁和事务收口正常。
- 不要直接把 `storage_inbound_detail` 加入 enabled；先评估 enabled 路径是否会因为 `exclude_existing_target=true` 在每日任务中稳定跳过已覆盖历史，同时能发现新增上游 code。
- 不要直接把销售表现加入 enabled；必须先满足：enabled 路径支持 `commit_per_page` 或等价短事务、重跑历史窗口补齐 7728 条空 `data_date`、评估约 22 分钟额外单日运行时间、用真实 enabled 批次证明成功。
- 继续只读关注其他 configured disabled API：`market_inventory_query`、`delivery_fee_query`、`inventory_event_page`、`inventory_age_page`。
- 不要直接启用超大接口：`inventory_event_page` 当前约 2669068 条，`inventory_age_page` 当前约 6597161 条且响应慢。

验收：

- 新接口、完整窗口、空缺口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如继续 `storage_inbound_detail`，必须证明 `exclude_existing_target=true` 生效、不会重复拉取全量历史、失败日志为 0，并记录累计覆盖进度；当前覆盖基线是 174334/174334。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 51 个、enabled 45 个、configured disabled 6 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
