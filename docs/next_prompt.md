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

阶段 10X 已完成。下一阶段 10Y 继续推进完整拉取：`lot_no_detail` 已进入 enabled，下一步不要继续围绕它回填；应只读盘点剩余 configured disabled 和 needs_param_source API，选择下一个低风险目标。

当前事实：

- 当前 enabled API 有 34 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 34 个已 enabled；剩余 16 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 34 个；执行分层摘要为 `configured=50`、`configured_enabled=34`、`configured_disabled=16`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 阶段 10V 新增 200 个 `lot_no_detail` 交货单详情，覆盖从 8006/8261 推进到 8206/8261。
- 阶段 10W 新增最后 55 个 `lot_no_detail` 交货单详情，覆盖追平到 8261/8261，剩余缺口 0。
- 阶段 10X 已将 `lot_no_detail.enabled` 从 `false` 改为 `true`，并加入 `param_source.exclude_existing_target=true`。
- 阶段 10X 已同步 API 配置 52 条；dry-run 显示 loaded 34 enabled API config(s)。
- 阶段 10X DB 核验显示 `api_config` 总配置 52 条、enabled 34 条，`lot_no_detail.enabled=1`、`config_json.enabled=true`、`param_source.exclude_existing_target=true`。
- 阶段 10X enabled 前缺失扫描核验显示 8261 个 LNInbound 交货单号已全部覆盖，剩余缺口 0，缺失候选 0。
- 阶段 10X 完整 enabled 批次为 `sync_20260705_053106_519317`：`sync_batch.status=success`、`total_api_count=34`、`success_api_count=34`、`failed_api_count=0`。
- 阶段 10X 同批次 `sync_api_log` 共 34 条且全部 success；总请求数 3078，成功写入 307950 条，失败 0，`failed_request_log=0`。
- 阶段 10X 同批次 `lot_no_detail` 为 `status=success`、`request_count=0`、`success_count=0`、`failed_count=0`、raw 写入 0 条；说明缺口为 0 时不会重复请求 8261 个历史交货单号。
- 阶段 10X 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 阶段 10X 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，82 个测试通过。
- 10V-10X 复盘结论：`lot_no_detail` 已从历史回填尾段转为 daily enabled，enabled API 从 33 增至 34；下一阶段应换目标。

建议目标：

- 先只读读取覆盖矩阵、YAML 和 DB 中 configured disabled 清单，按请求量、参数来源、写入风险排序。
- 优先选择已配置但 disabled、低请求量、参数来源清晰的候选；避免直接启用 `inventory_event_page`、`inventory_age_page` 这类超大分页接口。
- 对候选接口先做单接口真实运行或小窗口验证，再决定是否进入 enabled。
- 如涉及参数型详情接口，必须证明参数来源、缺失扫描和 checkpoint 边界。
- 如涉及日期窗口接口，必须证明 `item_count == total_count` 后才推进 checkpoint。
- 下一次三轮复盘放在 11A 完成后，覆盖 10Y-11A。
- 完成后同步 `api_config`、刷新覆盖矩阵并运行编译与单测。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
- 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 34 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
