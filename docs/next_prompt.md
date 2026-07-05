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

阶段 11C 已完成。下一阶段 11D 继续推进完整拉取：`procure_detail` 已完成第三个 100 条窗口，当前累计覆盖 303/1153 个采购单号，仍保持 disabled。11A-11C 三轮复盘已完成。

当前事实：

- 当前 enabled API 有 36 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 36 个已 enabled；剩余 14 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 36 个；执行分层摘要为 `configured=50`、`configured_enabled=36`、`configured_disabled=14`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- `procure_detail.param_source.limit=100`，仍保持 `enabled=false`。
- 阶段 11C 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api procure_detail`，批次 `sync_20260705_102515_657377` 成功。
- 阶段 11C 单接口 `procure_detail` 为 100 次请求、100 条 raw、100 个不同 hash、空对象 0，失败 0。
- 阶段 11C 后 `procure_detail` 累计 raw 为 303 条、303 个不同 hash。
- 阶段 11C checkpoint 为 `param_offset=203`、`param_limit=100`、`next_param_offset=303`。
- DB 核验显示 `api_config.procure_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=100`。
- 完整 `lot_no_page` 后有 8631 条带 `poCode` 的 raw，去重为 1153 个采购单号；`procure_detail` 当前覆盖 303/1153，仍有约 850 个历史缺口。
- 阶段 11C 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条配置。
- 阶段 11C dry-run 显示 loaded 36 enabled API config(s)，确认 `procure_detail` 没有进入每日 enabled 批量同步。
- 阶段 11C 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 阶段 11C 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，82 个测试通过。
- 11A-11C 复盘结论：三轮累计新增 300 个 `procure_detail` 采购订单详情，三轮均为 100 请求、100 raw、失败 0、空对象 0；覆盖从 3/1153 推进到 303/1153，仍不应 enabled。

建议目标：

- 继续保持 `procure_detail.enabled=false` 和 `param_source.limit=100`，从 checkpoint 的 `next_param_offset=303` 继续推进下一批采购单号。
- 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api procure_detail`，预期新增约 100 条，checkpoint 推进到 `next_param_offset=403`。
- 核验同批次 `sync_batch`、`sync_api_log`、`raw_api_data`、`sync_checkpoint` 和 `failed_request_log`，确认 100 请求成功、失败为 0、空对象为 0。
- 不要运行完整 `--sync-enabled`，因为本轮没有 enabled 变更；除非下一轮明确决定启用某个接口。
- 完成后同步 `api_config`、刷新覆盖矩阵并运行编译与单测。
- 11D 完成后需要复盘 11B-11D 三轮。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
- 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 36 个、configured disabled 14 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
