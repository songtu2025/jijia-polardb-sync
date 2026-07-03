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

阶段 5N 已完成。下一阶段 5O 继续回到覆盖矩阵，选择下一个低风险接口扩大覆盖；优先在剩余直读候选中避开订单、物流费用、写操作、数组编码未知和强限流接口。

当前事实：

- 当前 enabled API 有 20 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`。
- 当前已配置真实 API 有 29 个，其中 20 个已 enabled，`product_detail`、`market_inventory_query`、`storage_inbound_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`delivery_fee_query`、`base_currency_query` 和 `amazon_msku_page` 已验证但保持 disabled。
- `amazon_msku_page` 文档 id 为 `1921`，路径为 `POST /purchase/goods/amazonMsku/page`。
- `amazon_msku_page` 无必填入参、普通分页、非敏感响应；真实探测确认响应 `code=200`，`data` 包含 `page`、`pagesize`、`rows`、`total`。
- 阶段 5N 探测时当前账号 `amazon_msku_page.total=18430`，首条记录字段包含 `sku`、`msku`、`warehouseId`、`recordDate`、`memo`。
- `amazon_msku_page` 没有单一明确业务主键，本轮未使用 `sku` 或 `msku` 编造主键，而是保持 `primary_key.field=""`，依赖 `data_hash` 去重。
- `amazon_msku_page` 配置默认 `enabled=false`，`page.list_field=data.rows`，`page.total_field=data.total`，`page.max_pages=3`，`date_field=recordDate`。
- 阶段 5N 正式同步批次为 `sync_20260703_091918_162958`，`rows=300`，`requests=3`。
- 数据库已确认该批次 `total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- `amazon_msku_page` 同批次 `sync_api_log` 为 `request_count=3`、`success_count=300`、`failed_count=0`、`error_message=NULL`。
- 同批次 raw 写入 300 条，300 条都有 `data_hash`；`source_primary_key` 为空是预期，因为该接口没有单一明确主键。
- 同批次 raw 的 `data_date` 范围为 `2026-05-22` 到 `2026-07-02`。
- `amazon_msku_page` checkpoint 指向批次 `sync_20260703_091918_162958`，`checkpoint_value` 记录 `last_page=3`、`request_count=3`、`item_count=300`、`total_count=18430`。
- `failed_request_log` 中该批次该接口为 0 条。
- `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 显示 20 个 enabled API。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步配置数为 31；其中 2 个是占位示例，真实 API 为 29 个。
- 数据库已确认 `api_config.amazon_msku_page.enabled=0`、`config_json.enabled=false`、`page.max_pages=3`、`primary_key.field=""`、`date_field=recordDate`，数据库配置总数 31、启用 20。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 29 个，enabled 20 个。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`，通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，通过，38 个测试。
- 当前依赖参数来源机制支持 `source_primary_key`、单字段 `raw_json`、多字段 `raw_json`、raw_json 固定等值过滤、checkpoint 小窗口推进，以及按 `primary_key.required=true` 过滤缺主键响应对象。
- 当前响应提取机制支持列表、单对象和标量包装。
- 当前仍不支持数组入参、嵌套数组来源或复杂过滤表达式。
- `marketNames/query` 的常见 GET 数组编码已试过会返回 400，暂不要在未确认真实编码前强行接入。
- `deliveryFee/query` 和 `relevancePoInfo/query` 高频探测时出现过 509；后续对类似接口应减少手工扫参，优先用小窗口同步和较长等待。
- `app.doc_catalog` 会访问公开文档并重建 185 个详情；如果 120 秒左右超时，可在确认不是代码错误后用更长超时重跑。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要，不要假设 CLI 支持 `--dry-run`。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 只读读取覆盖矩阵，筛选尚未配置、无敏感字段、无写操作、无数组编码不确定性的候选接口。
2. 优先选择普通分页直读接口、单对象直读接口，或能复用 `response.scalar_field`、`source_primary_key`、`param_source.fields`、`param_source.filters`、`primary_key.required` 的低风险接口。
3. 暂不强行接入数组入参、嵌套数组来源、疑似写操作或请求编码未确认的接口。
4. 阅读候选接口公开文档详情，确认路径、方法、必填参数、响应形态、主键和日期字段。
5. 如果是依赖型接口，先只读查询数据库证明参数来源真实存在；如果是直读接口，先用一次真实请求确认响应形态。
6. 新增一个 API 配置，默认 `enabled=false`；分页直读接口用 `max_pages` 控制接入窗口，依赖型接口小样本 `limit` 控制在 3 左右。
7. 如果现有机制足够，优先不改代码；如果不够，必须测试先行做最小扩展。
8. 运行新接口 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api <api_code>` 做小样本真实同步。
9. 查询数据库确认新接口批次成功，`sync_api_log`、`raw_api_data`、checkpoint 都可追踪；如果返回空对象，确认不会产生缺主键脏 raw。
10. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
11. 查询 `<api_code>.enabled=0`。
12. 运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，确认真实配置 API 增加 1 个、enabled 仍为 20 个。
13. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
14. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
15. 更新三份 docs，并提交推送；不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口完成文档确认和小样本真实同步，默认保持 disabled，除非它是已充分验证并明确决定进入日常批量的低风险直读接口。
2. 参数来源或响应形态由数据库只读查询或真实请求证明，不靠猜测字段。
3. 新接口同步批次成功，`sync_api_log`、`raw_api_data` 和 checkpoint 可核验。
4. `api_config` 与覆盖矩阵显示真实配置 API 增加 1 个，enabled 仍为 20 个。
5. `compileall` 和 `unittest discover` 通过。
6. 不提交 `.env`、token 缓存、日志或真实凭证。
