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

阶段 6E 已完成。下一阶段 6F 继续推进完整覆盖；6E-6G 是当前三轮组。优先用 `date_window` 接入另一个低风险日期窗口接口，默认保持 disabled，暂不扩大 enabled。

当前事实：

- 当前 enabled API 有 23 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`base_currency_query`。
- 当前已配置真实 API 有 41 个，其中 23 个已 enabled；`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`amazon_msku_page`、`platform_msku_page`、`fba_inventory_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`inventory_event_page`、`inventory_age_page`、`traffic_analysis_page`、`transfer_page`、`lot_no_page` 和 `purchase_plan_page` 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 41 个，enabled 23 个。
- 5V 的完整 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled` 批次为 `sync_20260703_104718_888820`，状态 `success`，23 个 API 全部成功，总请求数 3053，总写入行数 306199，运行耗时 5735 秒。
- 5W 已修改 `SyncEngine.sync_enabled_apis()`：批次头先提交，每个 enabled API 独立事务提交 raw、log 和 checkpoint，全部结束后独立事务提交批次汇总状态。
- 6B 新增请求参数日期模板，支持 `{{ today }}`、`{{ yesterday }}`、`{{ days_ago:N }}`。
- 6C 新增 `date_window`：首次从 `default_start` 生成窗口，后续从 checkpoint 的 `next_window_start` 继续。
- 6D 新增 `traffic_analysis_page`，文档 id 为 `1018`，路径为 `POST /operation/sts/trafficAnalysis/page`，默认 `enabled=false`。
- 6D 的 `traffic_analysis_page` 成功批次为 `sync_20260703_134351_398121`，`rows=100`、`requests=1`、失败 0；checkpoint 记录 `window_start=2026-07-02`、`window_end=2026-07-02`、`next_window_start=2026-07-03`。
- `traffic_analysis_page` 真实样本中的 `id` 为 `None`，当前配置使用空 `primary_key.field`，依赖 `data_hash` 幂等。
- `traffic_analysis_page` 连续分页时出现过 509 “接口调用次数已超过限制次数”，当前配置 `max_pages=1`，保持 disabled。
- 6E 不新增 API，不改变 YAML、数据库 `api_config` 或覆盖矩阵数量；真实配置 API 仍为 41 个，enabled 仍为 23 个。
- 6E 补齐 `date_window` 追平当前日期后的跳过策略：当 checkpoint 的 `next_window_start` 晚于当天时，不再发起真实 API 请求。
- 6E 的追平跳过会写入成功日志和 checkpoint，`request_count=0`、`item_count=0`，并保留 `next_window_start`、`window_days` 和 `skipped_reason=date_window_caught_up`。
- 6E 的 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 23 个 enabled API。
- 6E 的 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 已通过。
- 6E 的 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 已通过，57 个测试。
- 当前仍不支持数组入参、嵌套数组来源或复杂过滤表达式。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `deliveryFee/query`、`relevancePoInfo/query` 和 `traffic_analysis_page` 高频或连续分页时出现过 509；后续类似接口应减少手工扫参，优先用小窗口同步和较长等待。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要，不要假设 CLI 支持 `--dry-run`。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、当前 disabled 已验证接口清单、6B-6D 复盘和 6E 追平跳过策略。
2. 优先用 `date_window` 接入另一个低风险日期窗口接口，默认保持 disabled，并用真实单接口小窗口验证请求字段、raw 入库和 checkpoint 推进。
3. 如果继续新增接口，优先选择需要日期窗口且业务风险可控的统计、报表或配置类接口；暂不要直接进入订单、财务敏感明细、客服文本、物流费用或销售售后。
4. 对限流严格的接口，默认使用更小 `max_pages`、更长 `rate_limit.sleep_seconds` 或独立调度，不要直接加入 daily enabled。
5. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
6. 如果候选涉及依赖参数，先只读查询数据库证明参数来源真实存在；如果是直读接口，先用一次真实请求确认响应形态和耗时。
7. 新增 API 配置时默认 `enabled=false`；启用任何接口前，必须先有测试约束 enabled 数量和目标接口状态。
8. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 同步 DB 配置。
9. 按本轮目标运行单接口同步或小范围回归；如果运行完整 `--sync-enabled`，要给足超过 2 小时的窗口。
10. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 都可追踪。
11. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
12. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
13. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
14. 更新 README、三份 docs，并提交推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口或能力改造必须由公开文档、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如新增接口，默认保持 disabled，除非已经明确完成进入日常批量的风险评估。
3. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 41 个、enabled 23 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
