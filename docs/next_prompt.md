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

阶段 10Y 已完成。下一阶段 10Z 继续推进完整拉取：`transfer_page` 已完成完整窗口验证并进入 enabled；下一步可优先评估 `lot_no_page` 的完整窗口和 enabled 边界。

当前事实：

- 当前 enabled API 有 35 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 35 个已 enabled；剩余 15 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 35 个；执行分层摘要为 `configured=50`、`configured_enabled=35`、`configured_disabled=15`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 阶段 10Y 选择 `transfer_page`，因为它是直读分页、已完成 3 页小样本验证、体量低于 `lot_no_page` 和库存大表。
- 阶段 10Y 已将 `transfer_page.page.max_pages` 从 3 改为 100，先保持 disabled，单接口完整窗口验证通过。
- 阶段 10Y 单接口批次为 `sync_20260705_070031_049820`：`sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- 阶段 10Y 单接口 `transfer_page` 为 68 次请求、6759 条 raw、6759 个不同主键、6759 个不同 hash；checkpoint 记录 `last_page=68`、`request_count=68`、`item_count=6759`、`total_count=6759`；`failed_request_log=0`。
- 阶段 10Y 已将 `transfer_page.enabled` 从 `false` 改为 `true`，并同步 API 配置。
- 阶段 10Y dry-run 显示 loaded 35 enabled API config(s)，且包含 `transfer_page`。
- 阶段 10Y 完整 enabled 批次为 `sync_20260705_070823_117795`：`sync_batch.status=success`、`total_api_count=35`、`success_api_count=35`、`failed_api_count=0`。
- 阶段 10Y enabled 批次 `sync_api_log` 共 35 条且全部 success；总请求数 3141，成功写入 314709 条，失败 0，`failed_request_log=0`。
- 阶段 10Y enabled 批次中 `transfer_page` 为 `status=success`、`request_count=68`、`success_count=6759`、`failed_count=0`。
- 阶段 10Y DB 核验显示 `api_config` 总配置 52 条、enabled 35 条，`transfer_page.enabled=1`、`config_json.enabled=true`、`page.max_pages=100`。

建议目标：

- 先只读确认 `lot_no_page` 当前配置、checkpoint 和 raw 基线；历史小样本为 3 页 300 条，旧 total 为 8602。
- 用 TDD 将 `lot_no_page.page.max_pages` 从 3 扩到足够覆盖完整窗口，先保持 disabled。
- 同步 API 配置后运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_page`，确认 `item_count == total_count`、raw 主键数与 total 一致、失败请求为 0。
- 单接口完整验证通过后，再评估是否将 `lot_no_page.enabled` 改为 `true`，并用完整 `--sync-enabled` 批次证明 36 个 API 同批次成功。
- 如 `lot_no_page` total 已变动，按真实 total 更新文档，不沿用旧的 8602。
- 下一次三轮复盘放在 11A 完成后，覆盖 10Y-11A。
- 完成后同步 `api_config`、刷新覆盖矩阵并运行编译与单测。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
- 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 35 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
