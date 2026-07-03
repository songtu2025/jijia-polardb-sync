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

阶段 6C 已完成。下一阶段 6D 继续推进完整覆盖；6B-6D 是当前三轮组，6D 完成后需要做三轮复盘。enabled 批量仍是长任务，暂不要直接启用大体量接口。

当前事实：

- 当前 enabled API 有 23 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`base_currency_query`。
- 当前已配置真实 API 有 40 个，其中 23 个已 enabled；`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`amazon_msku_page`、`platform_msku_page`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`transfer_page`、`lot_no_page` 和 `purchase_plan_page` 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 40 个，enabled 23 个。
- 5V 的完整 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled` 批次为 `sync_20260703_104718_888820`，状态 `success`，23 个 API 全部成功，总请求数 3053，总写入行数 306199，运行耗时 5735 秒。
- 5W 已修改 `SyncEngine.sync_enabled_apis()`：批次头先提交，每个 enabled API 独立事务提交 raw、log 和 checkpoint，全部结束后独立事务提交批次汇总状态。
- 5Y 新增 `fba_inventory_page`，批次 `sync_20260703_125157_022009` 成功，写入 300 条，总量 `30759`。
- 5Z 新增 `inventory_event_page`，批次 `sync_20260703_130058_411267` 成功，写入 300 条，总量 `2669068`。
- 6A 新增 `inventory_age_page`，文档 id 为 `2542`，路径为 `POST /fulfillment/inventory/inventoryAge/page`，默认 `enabled=false`。
- `inventory_age_page` 响应为 `data.total` 和 `data.rows`；配置使用 `id` 作为主键，使用 `updateDate` 作为日期字段。
- `inventory_age_page` 首次按 `pagesize=100` 运行失败，批次 `sync_20260703_131143_529682`，失败原因为 30 秒读超时，未写入 raw。
- 只读探测确认 `inventory_age_page` 的 `pagesize=10` 第 1 页可返回，耗时约 50 秒，接口总量 `6597161`。
- 6A 已新增 API 级 `timeout_seconds` 配置能力；慢接口可在 YAML 中覆盖请求超时，未配置接口继续使用客户端默认 30 秒。
- 6A 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api inventory_age_page` 批次为 `sync_20260703_131645_314835`，状态 `success`，`rows=30`、`requests=3`、失败 0。
- 数据库确认该批次 `sync_batch.status=success`，`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`、耗时 176 秒。
- 同批次 `sync_api_log` 为 `request_count=3`、`success_count=30`、`failed_count=0`、`error_message=NULL`。
- 同批次 `raw_api_data` 写入 30 条，0 条缺少 `source_primary_key`，30 条都有 `data_hash`，30 条都有 `data_date`。
- 同批次 raw 示例确认 `source_primary_key=39726369`、`id=39726369`、`sku=SK002-Stripe White 704 44-45`、`fnsku=X002CYHRB3`、`asin=B07ZQF975J`、`warehouseId=14`、`updateDate=2026-07-03 12:17:13`。
- `inventory_age_page` checkpoint 已更新到 `sync_20260703_131645_314835`，`checkpoint_value` 为 `last_page=3`、`request_count=3`、`item_count=30`、`total_count=6597161`。
- 数据库确认 `api_config` 总数 42、启用 23；`inventory_age_page.enabled=0`、`timeout_seconds=90`、`page.page_size=10`、`page.max_pages=3`、`primary_key.field=id`、`date_field=updateDate`。
- `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 23 个 enabled API。
- `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary` 已通过，公开文档 185 个，真实配置 40 个，enabled 23 个；该命令会访问公开文档，运行时继续给较长超时。
- 6B 没有新增 API，也没有改变 enabled 数量；本轮新增请求参数日期模板能力，用来支撑后续大表按日期窗口拆分同步。
- `SyncEngine` 现在会在非分页、分页和依赖参数请求前解析 YAML `params` 中的日期模板。
- 当前支持 `{{ today }}`、`{{ yesterday }}`、`{{ days_ago:N }}` 三类占位符，展开格式为 `YYYY-MM-DD`；未知占位符保持原样。
- 6B 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 23 个 enabled API。
- 6B 的 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 已通过。
- 6B 的 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 已通过，53 个测试。
- 5Y-6A 复盘结论：库存域普通分页接口可以继续用默认 disabled 小窗口方式验证，但超大体量和慢响应已经成为主要风险；后续不能靠扩大 `max_pages` 做完整拉取，必须设计时间窗口、增量过滤、独立调度和失败恢复。
- 6B 结论：日期模板只是滚动窗口基础能力，还不是完整增量系统；当前尚未实现按 checkpoint 自动推进历史窗口。
- 6C 没有新增 API，也没有改变 enabled 数量；本轮新增 `date_window` 的 checkpoint 推进能力。
- `date_window` 支持 `enabled=true`、`start_field`、`end_field`、`default_start`、`days`；首次运行从 `default_start` 生成窗口，后续从 checkpoint 的 `next_window_start` 继续。
- 同步成功后 checkpoint 会记录 `window_start`、`window_end`、`next_window_start` 和 `window_days`。
- 日期窗口逻辑已接入非分页、分页和依赖参数请求路径。
- 6C 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 23 个 enabled API。
- 6C 的 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 已通过。
- 6C 的 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 已通过，55 个测试。
- 当前依赖参数来源机制支持 `source_primary_key`、单字段 `raw_json`、多字段 `raw_json`、raw_json 固定等值过滤、checkpoint 小窗口推进，以及按 `primary_key.required=true` 过滤缺主键响应对象。
- 当前响应提取机制支持列表、单对象和标量包装；普通分页列表字段可用 `page.list_field` 点路径指定，例如 `data.rows` 或 `data.records`。
- 当前仍不支持数组入参、嵌套数组来源或复杂过滤表达式。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `deliveryFee/query` 和 `relevancePoInfo/query` 高频探测时出现过 509；后续对类似接口应减少手工扫参，优先用小窗口同步和较长等待。
- 剩余候选更多涉及库存报表、财务、订单、物流、客服文本、采购或销售售后，需要更严格控制 `max_pages`、`timeout_seconds` 和业务风险。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要，不要假设 CLI 支持 `--dry-run`。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、当前 disabled 已验证接口清单、5Y-6A 复盘结论、6B 日期模板和 6C `date_window` 实现。
2. 优先用 `date_window` 接入一个低风险日期窗口接口，默认保持 disabled，并用真实单接口小窗口验证 checkpoint 推进。
3. 如果继续新增接口，优先选择需要日期窗口且业务风险可控的统计、报表或配置类接口；暂不要直接进入订单、财务敏感明细、客服文本或物流费用。
4. 如果候选涉及订单、财务、客服文本、物流费用或销售售后，先说明业务风险边界，再决定是否只做小窗口验证。
5. 暂不强行接入数组入参、嵌套数组来源、疑似写操作或请求编码未确认的接口。
6. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
7. 如果是依赖型接口，先只读查询数据库证明参数来源真实存在；如果是直读接口，先用一次真实请求确认响应形态和响应耗时。
8. 新增一个 API 配置时默认 `enabled=false`；分页直读接口用 `max_pages` 控制接入窗口，必要时用 `timeout_seconds`、日期模板或 `date_window` 控制慢接口或大接口，依赖型接口小样本 `limit` 控制在 3 左右。
9. 启用任何接口前，先有测试约束 enabled 数量和目标接口状态，再同步 DB 配置。
10. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 同步 DB 配置。
11. 按本轮目标运行单接口同步或 `--sync-enabled` 回归；如果运行完整 `--sync-enabled`，要给足超过 2 小时的窗口。
12. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪；如果返回空对象，确认不会产生缺主键脏 raw。
13. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
14. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
15. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
16. 6D 完成后更新 6B-6D 三轮复盘。
17. 更新 README、三份 docs，并提交推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口或启用评估必须由公开文档、真实请求或数据库只读查询证明，不靠猜测字段。
2. 如新增接口，默认保持 disabled，除非已经明确完成进入日常批量的风险评估。
3. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 40 个、enabled 23 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
