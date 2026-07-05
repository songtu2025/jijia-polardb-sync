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

阶段 10Z 已完成。下一阶段 11A 继续推进完整拉取：`lot_no_page` 已完成完整窗口验证并进入 enabled；下一步可优先评估 `procure_detail` 的参数窗口。11A 完成后需要复盘 10Y-11A 三轮。

当前事实：

- 当前 enabled API 有 36 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 36 个已 enabled；剩余 14 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 36 个；执行分层摘要为 `configured=50`、`configured_enabled=36`、`configured_disabled=14`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 阶段 10Z 已将 `lot_no_page.page.max_pages` 从 3 改为 120，先保持 disabled，单接口完整窗口验证通过。
- 阶段 10Z 单接口批次为 `sync_20260705_083557_251344`：`sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- 阶段 10Z 单接口 `lot_no_page` 为 87 次请求、8631 条 raw、8631 个不同主键、8631 个不同 hash；checkpoint 记录 `last_page=87`、`request_count=87`、`item_count=8631`、`total_count=8631`；`failed_request_log=0`。
- 阶段 10Z 已将 `lot_no_page.enabled` 从 `false` 改为 `true`，并同步 API 配置。
- 阶段 10Z dry-run 显示 loaded 36 enabled API config(s)，且包含 `lot_no_page`。
- 阶段 10Z 完整 enabled 批次为 `sync_20260705_083949_209208`：`sync_batch.status=success`、`total_api_count=36`、`success_api_count=36`、`failed_api_count=0`。
- 阶段 10Z enabled 批次 `sync_api_log` 共 36 条且全部 success；总请求数 3228，成功写入 323340 条，失败 0，`failed_request_log=0`。
- 阶段 10Z enabled 批次中 `lot_no_page` 为 `status=success`、`request_count=87`、`success_count=8631`、`failed_count=0`。
- 阶段 10Z DB 核验显示 `api_config` 总配置 52 条、enabled 36 条，`lot_no_page.enabled=1`、`config_json.enabled=true`、`page.max_pages=120`。
- 完整 `lot_no_page` 后有 8631 条带 `poCode` 的 raw，去重为 1153 个采购单号；`procure_detail` 当前只有 3 条小样本。
- 阶段 10Z 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 阶段 10Z 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，82 个测试通过。

建议目标：

- 先只读确认 `procure_detail` 当前配置、checkpoint、raw 基线，以及完整 `lot_no_page.raw_json.poCode` 去重数量。
- 优先评估是否将 `procure_detail.param_source.limit` 从 3 扩到中等窗口，并保持 disabled；不要直接 enabled。
- 如推进 `procure_detail`，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进，并核验失败请求为 0。
- 因 `procure_detail` 响应当前依靠 `data_hash` 幂等，扩大窗口前要重新确认 raw 中没有明显空对象或无意义重复数据。
- 11A 完成后复盘 10Y-11A 三轮。
- 完成后同步 `api_config`、刷新覆盖矩阵并运行编译与单测。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
- 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 36 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
