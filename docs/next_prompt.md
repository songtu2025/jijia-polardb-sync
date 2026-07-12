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

阶段 15I 已完成。`storage_inbound_detail` 已完成 enabled 主链路边界只读评估：`--sync-enabled` 会复用同一套 `param_source` / `exclude_existing_target=true` 缺口扫描逻辑，YAML 顺序保证 `storage_inbound_page` 先于详情接口执行，当前同口径缺口为 0。本阶段没有启用该接口。

当前事实：

- 当前最新提交应为阶段 15I 文档提交；开始前请核对 `git status --short --branch` 和 `git log -1 --oneline`。
- 当前 enabled API 有 45 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`amazon_msku_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`procure_detail`、`storage_return_page`、`strategy_template_page`、`traffic_analysis_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`storage_ledger_detail_page`、`storage_ledger_month_page`、`inventory_receipts_page`、`purchase_sale_storage_fba_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- catalog summary 当前口径：公开文档 API 187 个，真实配置 API 51 个，enabled API 45 个，configured disabled 6 个。
- 当前 DB `api_config` 共 59 条；销售表现同一个文档接口被拆成 7 个 `api_code`。
- `storage_inbound_detail` 当前配置为 `enabled=false`、`param_source.limit=2000`、`auto_advance=true`、`exclude_existing_target=true`，累计覆盖为 174334/174334 个上游去重 code。
- 15G 批次 `sync_20260712_185853_014941` 成功补齐最后 828 个详情：828 请求、828 成功、0 失败；本批次主键和 hash 均唯一，空主键 0。
- 15H 批次 `sync_20260712_191559_497680` 成功验证空缺口：0 请求、0 写入、0 失败，批次耗时 4 秒，API 耗时 2 秒。
- 15I 只读 DB 复核显示累计覆盖 174334/174334、`failed_request_log=0`、named lock 已释放、外部 `information_schema.innodb_trx=0`，DB `api_config` 仍为 59 条、enabled 45 条，`storage_inbound_detail.enabled=0`。
- 15I 代码路径核验显示 `--sync-enabled` 通过 `SyncEngine.sync_enabled_apis()` 遍历 `_enabled_apis()`，每个 API 进入 `_sync_api_in_batch()`；带 `param_source` 的接口复用 `_sync_api_from_param_source_in_batch()`。
- 15I YAML 顺序核验显示 `storage_inbound_page` 位于 `storage_inbound_detail` 之前；内存态启用探针显示 enabled 数量会从 45 变为 46，且上游分页仍先于详情接口。
- 15I 同口径 LEFT JOIN 缺口查询返回 `missing_count=0`；`exclude_existing_target=true` 会忽略 checkpoint offset，按目标表缺失 `source_primary_key` 决定是否请求详情。
- 15G-15I 三轮复盘已完成：15G 补齐历史，15H 验证空缺口，15I 确认 enabled 主链路边界；结论是 `storage_inbound_detail` 具备进入 enabled 的技术边界，但尚未启用。
- 15F 曾两次出现 `app.main --sync-api storage_inbound_detail` 通用失败并提示 `release sync task lock failed`；当时未生成可见新批次、覆盖未推进、失败日志为 0，但分别留下 Sleep InnoDB 事务 `5635742` 和 `5637222`，已清理。15G/15H 官方 CLI 均正常返回 0，暂未复现。
- 销售表现 7 个配置均为 `enabled=false`、`commit_per_page=true`、`write_batch_size=10`、`data_date_param=beginDate`、`rate_limit.sleep_seconds=20`、`retry.retries=1`。
- 销售表现真实响应里 `dateLine` 字段存在但值为 JSON `null`；后续不要再依赖 `dateLine` 作为 `raw_api_data.data_date` 来源。
- `commit_per_page=true` 当前只用于 `--sync-api` 单接口验证路径；普通 enabled 同步路径未改变。

建议目标：

- 15J 优先提出 `storage_inbound_detail` enabled 最小实施方案并等待确认；确认前不要直接启用。
- 如确认启用，最小实施顺序建议为：更新测试期望、将 `storage_inbound_detail.enabled` 改为 `true`、运行目标测试、同步 `api_config`、dry-run 验证 46 个 enabled、运行真实批次证明成功、做 DB 复核。
- 真实批次证明的选择需要明确：`--sync-api storage_inbound_detail` 只能证明单接口空缺口，完整证明 enabled 身份需要真实 `--sync-enabled` 批次；该批次会包含当前 45 个已启用接口，耗时按长任务安排。
- 不要直接把销售表现加入 enabled；必须先满足：enabled 路径支持 `commit_per_page` 或等价短事务、重跑历史窗口补齐 7728 条空 `data_date`、评估约 22 分钟额外单日运行时间、用真实 enabled 批次证明成功。
- 继续只读关注其他 configured disabled API：`market_inventory_query`、`delivery_fee_query`、`inventory_event_page`、`inventory_age_page`。
- 不要直接启用超大接口：`inventory_event_page` 当前约 2669068 条，`inventory_age_page` 当前约 6597161 条且响应慢。

验收：

- 新接口、完整窗口、空缺口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如启用 `storage_inbound_detail`，必须证明 `exclude_existing_target=true` 生效、不会重复拉取全量历史、失败日志为 0，并记录累计覆盖；当前覆盖基线是 174334/174334。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 51 个、enabled 45 个、configured disabled 6 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
