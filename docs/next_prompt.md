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

阶段 5X 已完成。下一阶段 5Y 继续推进完整覆盖：可以继续接入一个低风险未配置接口，也可以继续评估已验证 disabled 接口的启用条件。5V-5X 三轮已完成并复盘；enabled 批量仍是长任务，暂不要直接启用大体量接口。

当前事实：

- 当前 enabled API 有 23 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`base_currency_query`。
- 当前已配置真实 API 有 37 个，其中 23 个已 enabled，`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`amazon_msku_page`、`platform_msku_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`transfer_page`、`lot_no_page` 和 `purchase_plan_page` 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 37 个，enabled 23 个。
- 阶段 5V 将 `base_currency_query`、`storage_return_page` 和 `strategy_template_page` 从 disabled 改为 enabled。
- 5V 的完整 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled` 批次为 `sync_20260703_104718_888820`，状态 `success`，`total_api_count=23`、`success_api_count=23`、`failed_api_count=0`。
- 5V 完整批次总请求数为 3053，总写入行数为 306199，失败行数为 0，运行耗时 5735 秒。
- 5W 已修改 `SyncEngine.sync_enabled_apis()`：批次头先提交，每个 enabled API 独立事务提交 raw、log 和 checkpoint，全部结束后独立事务提交批次汇总状态。
- 5W 的事务边界修改不改变分页、重试、raw 幂等、失败日志和 checkpoint 的业务语义。
- 5W 真实轻量回归批次为 `sync_20260703_123218_791772`，3 个低风险 enabled API 全部成功，写入 21 条，失败 0。
- 5X 新增 `purchase_plan_page`，文档 id 为 `87`，路径为 `POST /purchase/srm/plan/page`，默认 `enabled=false`。
- `purchase_plan_page` 选择依据：采购计划列表只有 `page` 和 `pagesize` 为分页必填，无业务必填字段；普通分页、非写操作，风险低于订单、财务、物流费用、客服文本和大体量库存报表。
- `purchase_plan_page` 响应为 `data.total` 和 `data.rows`；配置使用 `code` 作为主键，使用 `createdAt` 作为日期字段。
- 5X 的 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api purchase_plan_page` 批次为 `sync_20260703_124115_334136`，状态 `success`，`rows=0`、`requests=1`、失败 0。
- 数据库确认该批次 `sync_batch.status=success`，`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`、耗时 4 秒。
- 同批次 `sync_api_log` 为 `request_count=1`、`success_count=0`、`failed_count=0`、`error_message=NULL`。
- 同批次 `raw_api_data` 为 0 条，这是当前账号该接口 `total_count=0` 的预期结果。
- `purchase_plan_page` checkpoint 已更新到 `sync_20260703_124115_334136`，`checkpoint_value` 为 `last_page=1`、`request_count=1`、`item_count=0`、`total_count=0`。
- 数据库确认 `api_config` 总数 39、启用 23；`purchase_plan_page.enabled=0`、`page.max_pages=3`、`primary_key.field=code`、`date_field=createdAt`。
- `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 23 个 enabled API。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 185 个，真实配置 37 个，enabled 23 个。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`，通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，通过，48 个测试。
- 5V-5X 复盘结论：enabled 覆盖、事务边界和新增覆盖都完成一轮推进；但 0 数据接口不能作为进入 enabled 的充分证据，大体量和敏感域仍默认 disabled 小窗口验证。
- 当前依赖参数来源机制支持 `source_primary_key`、单字段 `raw_json`、多字段 `raw_json`、raw_json 固定等值过滤、checkpoint 小窗口推进，以及按 `primary_key.required=true` 过滤缺主键响应对象。
- 当前响应提取机制支持列表、单对象和标量包装；普通分页列表字段可用 `page.list_field` 点路径指定，例如 `data.rows` 或 `data.records`。
- 当前仍不支持数组入参、嵌套数组来源或复杂过滤表达式。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `deliveryFee/query` 和 `relevancePoInfo/query` 高频探测时出现过 509；后续对类似接口应减少手工扫参，优先用小窗口同步和较长等待。
- 剩余低风险直读候选减少，后续接口更多涉及库存报表、财务、订单、物流、客服文本、采购或销售售后，需要更严格控制 `max_pages` 和业务风险。
- `app.doc_catalog` 会访问公开文档并重建 185 个详情；运行时继续给较长超时。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要，不要假设 CLI 支持 `--dry-run`。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、当前 disabled 已验证接口清单和 5V-5X 复盘结论。
2. 如果继续启用 disabled 接口，只考虑低体量、已验证、非敏感、非依赖型接口；暂不要启用 `transfer_page`、`lot_no_page`、库存大表、订单、财务、客服文本和物流费用接口。
3. 如果继续新增接口，优先选择无敏感字段、无写操作、无数组编码不确定性、能明确主键和日期字段的候选。
4. 如果候选涉及订单、财务、客服文本、物流费用或销售售后，先说明业务风险边界，再决定是否只做小窗口验证。
5. 暂不强行接入数组入参、嵌套数组来源、疑似写操作或请求编码未确认的接口。
6. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
7. 如果是依赖型接口，先只读查询数据库证明参数来源真实存在；如果是直读接口，先用一次真实请求确认响应形态。
8. 新增一个 API 配置时默认 `enabled=false`；分页直读接口用 `max_pages` 控制接入窗口，依赖型接口小样本 `limit` 控制在 3 左右。
9. 启用任何接口前，先有测试约束 enabled 数量和目标接口状态，再同步 DB 配置。
10. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 同步 DB 配置。
11. 按本轮目标运行单接口同步或 `--sync-enabled` 回归；如果运行完整 `--sync-enabled`，要给足超过 2 小时的窗口。
12. 查询数据库确认批次成功，`sync_api_log`、`raw_api_data`、checkpoint 都可追踪；如果返回空对象，确认不会产生缺主键脏 raw。
13. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
14. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
15. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
16. 更新 README、三份 docs，并提交推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口或启用评估必须由公开文档、真实请求或数据库只读查询证明，不靠猜测字段。
2. 如新增接口，默认保持 disabled，除非已经明确完成进入日常批量的风险评估。
3. 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 37 个、enabled 23 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
