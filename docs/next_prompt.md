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

阶段 5U 已完成，并已完成 5S-5U 三轮复盘。下一阶段 5V 进入新一组三轮：继续扩大覆盖，但需要更重视剩余候选的业务敏感度和运行窗口；优先选择能明确主键、分页和响应形态的接口，或开始评估已验证 disabled 接口的分组启用条件。

当前事实：

- 当前 enabled API 有 20 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`。
- 当前已配置真实 API 有 36 个，其中 20 个已 enabled，`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`base_currency_query`、`amazon_msku_page`、`platform_msku_page`、`fba_inventory_v2_page`、`inventory_adjustments_page`、`transfer_page`、`lot_no_page`、`storage_return_page` 和 `strategy_template_page` 已验证但保持 disabled。
- `strategy_template_page` 文档 id 为 `102`，路径为 `POST /operation/ads/strategyTemplate/page`。
- `strategy_template_page` 是广告分时策略模板列表，响应列表字段为 `data.records`，不是常见的 `data.rows`。
- `strategy_template_page` 真实探测确认响应 `code=200`，`data` 包含 `total` 和 `records`，当前 `total=19`。
- `strategy_template_page` 首条记录字段包含 `id`、`templateName`、`strategyType`、`templateExpression`、`countryIds`、`countryNames`、`createTime`、`updateTime`、`status`、`useNum`。
- `strategy_template_page` 使用 `id` 作为 `source_primary_key`，使用 `updateTime` 作为 `data_date` 来源。
- `strategy_template_page` 配置默认 `enabled=false`，`page.list_field=data.records`，`page.total_field=data.total`，`page.max_pages=3`，`page.page_size=100`，`primary_key.field=id`，`date_field=updateTime`。
- 阶段 5U 正式同步批次为 `sync_20260703_103557_599935`，`rows=19`，`requests=1`。
- 数据库已确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- `strategy_template_page` 同批次 `sync_api_log` 为 `request_count=1`、`success_count=19`、`failed_count=0`、`error_message=NULL`。
- 同批次 raw 写入 19 条，0 条缺少 `source_primary_key`，19 条都有 `data_hash`，19 条都有 `data_date`。
- 同批次 raw 的 `data_date` 范围为 `2022-12-06` 到 `2025-12-02`。
- `strategy_template_page` checkpoint 指向批次 `sync_20260703_103557_599935`，`checkpoint_value` 记录 `last_page=1`、`request_count=1`、`item_count=19`、`total_count=19`。
- `failed_request_log` 中该批次该接口为 0 条。
- `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 20 个 enabled API。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 38；其中 2 个是占位示例，真实 API 为 36 个。
- 数据库已确认 `api_config.strategy_template_page.enabled=0`、`page.max_pages=3`、`page.page_size=100`、`page.list_field=data.records`、`primary_key.field=id`、`date_field=updateTime`，数据库配置总数 38、启用 20。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 36 个，enabled 20 个。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`，通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，通过，45 个测试。
- 5U 新增了 `tests/test_strategy_template_page_config.py`，用来约束该接口默认 disabled、`data.records` 分页窗口、主键和日期字段。
- 5U 同轮只读探测确认：`purchase_plan_page.total=0`，`inventory_receipts_page.total=493411`，`customer_voice_page` 含订单编号、买家备注和评论文本，本轮未接入。
- 5S-5U 复盘已记录：5S 新增 `lot_no_page`，5T 新增 `storage_return_page`，5U 新增 `strategy_template_page`；三者都真实验证成功但保持 disabled。
- 当前依赖参数来源机制支持 `source_primary_key`、单字段 `raw_json`、多字段 `raw_json`、raw_json 固定等值过滤、checkpoint 小窗口推进，以及按 `primary_key.required=true` 过滤缺主键响应对象。
- 当前响应提取机制支持列表、单对象和标量包装；普通分页列表字段可用 `page.list_field` 点路径指定，例如 `data.rows` 或 `data.records`。
- 当前仍不支持数组入参、嵌套数组来源或复杂过滤表达式。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `deliveryFee/query` 和 `relevancePoInfo/query` 高频探测时出现过 509；后续对类似接口应减少手工扫参，优先用小窗口同步和较长等待。
- 剩余低风险直读候选减少，后续接口更多涉及库存报表、财务、订单、物流、客服文本、采购或销售售后，需要更严格控制 `max_pages` 和业务风险。
- `app.doc_catalog` 会访问公开文档并重建 185 个详情；本轮耗时约 149 秒，应继续用较长超时运行。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要，不要假设 CLI 支持 `--dry-run`。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵和当前 disabled 已验证接口清单，决定 5V 是继续新增一个低风险接口，还是开始做 disabled 接口分组启用评估。
2. 如果继续新增接口，优先选择无敏感字段、无写操作、无数组编码不确定性、能明确主键和日期字段的候选。
3. 如果候选涉及订单、财务、客服文本、物流费用或销售售后，先说明业务风险边界，再决定是否只做小窗口验证。
4. 暂不强行接入数组入参、嵌套数组来源、疑似写操作或请求编码未确认的接口。
5. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
6. 如果是依赖型接口，先只读查询数据库证明参数来源真实存在；如果是直读接口，先用一次真实请求确认响应形态。
7. 新增一个 API 配置时默认 `enabled=false`；分页直读接口用 `max_pages` 控制接入窗口，依赖型接口小样本 `limit` 控制在 3 左右。
8. 如果现有机制足够，优先不改代码；如果不够，必须测试先行做最小扩展。
9. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 同步 DB 配置。
10. 运行新接口 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api <api_code>` 做小样本真实同步。
11. 查询数据库确认新接口批次成功，`sync_api_log`、`raw_api_data`、checkpoint 都可追踪；如果返回空对象，确认不会产生缺主键脏 raw。
12. 查询 `<api_code>.enabled=0`。
13. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 增加或启用状态符合预期，enabled 仍为预期数量。
14. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
15. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
16. 更新三份 docs，并提交推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口或启用评估必须由公开文档、真实请求或数据库只读查询证明，不靠猜测字段。
2. 如新增接口，默认保持 disabled，除非已经明确完成进入日常批量的风险评估。
3. 新接口同步批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 可核验。
4. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
