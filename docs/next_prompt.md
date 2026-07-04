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

阶段 7V 已完成。下一阶段 7W 继续推进完整拉取：优先评估是否将 `product_detail` 启用到 daily enabled；如果启用，必须跑完整 `--sync-enabled` 并用 DB 证明 31 个 enabled API 同批次成功。

当前事实：

- 当前 enabled API 有 30 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`country_province_query`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 30 个已 enabled；剩余 20 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 30 个；执行分层摘要为 `configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 7V 修改了 `product_detail` 的 daily 增量机制，但仍保持 `enabled=false`。
- 7V 只读 DB 发现 `product_page.source_primary_key` 是字符串形态：lexicographic 最大值为 `999`，数值最大值为 `8459`。因此旧的 `ORDER BY source_primary_key LIMIT/OFFSET` 不能保证新增数值 ID 会排在旧 offset 之后。
- 7V 已在 `product_detail.param_source` 增加 `exclude_existing_target: true`。
- 7V 后 `source_primary_key` 参数来源在 `exclude_existing_target=true` 时会反连接目标 API，只取上游存在但当前 API 尚未入库的主键。
- 7V 后 `exclude_existing_target=true` 不再读取 checkpoint offset；缺失主键扫描自身就是进度边界。
- 7V 已运行 `.\\.venv\\Scripts\\python.exe -m unittest tests.test_product_detail_param_source`，6 个测试通过。
- 7V 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，输出 `api configs synced: count=52`。
- 7V DB 核验：`api_config.product_detail.enabled=0`、`config_json.param_source.exclude_existing_target=true`、`auto_advance=true`、`limit=500`。
- 7V 的真实单接口批次为 `sync_20260704_091054_370330`，`product_detail` 请求 0 次、写入 0 条、失败 0。
- 7V 数据库核验：该批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`。
- 7V 同批次 `sync_api_log.status=success`、`request_count=0`、`success_count=0`、`failed_count=0`。
- 7V 同批次 `raw_api_data` 写入 0 条 `product_detail`；同批次 `failed_request_log` 为 0 条。
- 7V 后 `product_detail` checkpoint 指向批次 `sync_20260704_091054_370330`，记录 `param_offset=0`、`param_limit=500`、`next_param_offset=0`、`item_count=0`、`total_count=0`。
- 7V 后 DB 缺失详情数为 0，`product_detail` 与 `product_page` 均为 8258 个不同产品主键。
- 7V 后 dry-run 仍显示 30 个 enabled API，说明 `product_detail` 尚未进入 enabled。
- 7V 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary` 并通过。
- 7V 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 7V 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，78 个测试通过。
- 7V 结论：`product_detail` 的 daily 增量边界应使用目标表缺失主键，而不是历史 offset。
- `product_detail` 当前瓶颈已经从“能否拾取新增 ID”变成“能否进入 enabled 并通过完整 enabled 批次验证”。
- `traffic_analysis_page` 在 `2026-07-02` 单日 CNY 窗口总量 528 条，但限流严格，曾在第 2 页触发 509。
- `storage_ledger_detail_page` 在 `2026-07-02` 单日窗口总量 27104 条，不适合直接完整窗口。
- `storage_ledger_month_page` 在 `2026-06` 月窗口总量 6044 条，不适合直接进入 daily enabled。
- `purchase_sale_storage_fba_page` 当前 MSKU 数量维度总量 58955 条，且不是 date_window 接口。
- 当前未配置且可直接普通探测的候选仍为 0 个；不要回到早期“未配置 direct_read_candidate 里挑一个”的策略。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- `app.doc_catalog` 近期可能超过 120 秒，请预留 300 秒。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读读取覆盖矩阵、7V `product_detail` 缺失主键扫描证据和当前 30 enabled 批次耗时。
2. 如启用 `product_detail`，将 `enabled` 改为 `true` 后先运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
3. 启用后确认 `.\\.venv\\Scripts\\python.exe -m app.main` 显示 loaded 31 enabled API config(s)。
4. 运行完整 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`，预计耗时可能接近或超过 7A 的约 80 分钟。
5. 查询数据库确认最新 enabled 批次 31 个 API 同批次成功；特别确认 `product_detail` 在缺失数为 0 时请求 0 次且状态成功。
6. 查询 `api_config.product_detail.enabled=1` 和 `config_json.param_source.exclude_existing_target=true`。
7. 如果不启用 `product_detail`，必须说明阻止启用的真实证据，并转向下一个低风险参数型接口。
8. 任何日期窗口完整验证都必须证明 `item_count == total_count`；如触发 `date window page truncated`，先修正分页上限后重跑。
9. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
11. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
12. 更新三份 docs；如 README 的运行说明或 API 状态变动需要同步，也一起更新。
13. 提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口、参数窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 如启用 `product_detail`，必须证明 `api_config.enabled=1`、dry-run enabled 数量从 30 变为 31，并用真实 `--sync-enabled` 批次证明成功。
3. 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
4. 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 30 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
