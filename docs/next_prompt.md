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

阶段 10A 已完成。下一阶段 10B 继续推进完整拉取：继续 `lot_no_detail` 历史回填，不启用；目标是把 checkpoint 从 `next_param_offset=4006` 再推进一个 200 窗口到约 4206。下一次三轮复盘放在 10C 完成后。

当前事实：

- 当前 enabled API 有 33 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 33 个已 enabled；剩余 17 个真实配置 API 已验证但保持 disabled。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 33 个；执行分层摘要为 `configured=50`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- 9G 已将 `transfer_detail.enabled` 从 `false` 改为 `true`，完整 enabled 批次 `sync_20260704_193955_361555` 为 33/33 success，失败请求 0。
- 9H 已将 `lot_no_detail.param_source.limit` 从 3 调整为 200，`lot_no_detail.enabled` 仍为 `false`。
- 9I-9K 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；200 窗口节奏稳定，但当时仅覆盖 806/8261，仍不应启用。
- 9L-9N 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；批次耗时约 248 秒、263 秒、296 秒，节奏稳定，但当时仅覆盖 1406/8261，仍不应启用。
- 9O-9Q 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 1406/8261 推进到 2006/8261，但仍有 6255 个缺口，不满足 enabled 前提。
- 9R-9T 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 2006/8261 推进到 2606/8261，但仍有 5655 个缺口，不满足 enabled 前提。
- 9R 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260704_225302_414309` 成功，请求 200 次、写入 200 条、失败 0；9R 后累计 raw 2206 条，checkpoint 为 `param_offset=2006`、`param_limit=200`、`next_param_offset=2206`，剩余缺口 6055。
- 9S 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260704_230406_864784` 成功，请求 200 次、写入 200 条、失败 0；9S 后累计 raw 2406 条，checkpoint 为 `param_offset=2206`、`param_limit=200`、`next_param_offset=2406`，剩余缺口 5855。
- 9T 起点只读确认 `lot_no_detail` 已覆盖 2406/8261 个交货单详情，剩余缺口 5855。
- 9T 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260704_231602_545149` 成功，请求 200 次、写入 200 条、失败 0。
- 9T 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-04 23:16:03` 到 `2026-07-04 23:20:42`。
- 9T 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 9T 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 9T 后 `lot_no_detail` checkpoint 指向批次 `sync_20260704_231602_545149`，记录 `param_offset=2406`、`param_limit=200`、`next_param_offset=2606`、`item_count=200`、`total_count=200`。
- 9T 后 `lot_no_detail` 累计 raw 为 2606 条、2606 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 5655 个。
- 9U 起点只读确认 `lot_no_detail` 已覆盖 2606/8261 个交货单详情，剩余缺口 5655。
- 9U 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260704_232906_917435` 成功，请求 200 次、写入 200 条、失败 0。
- 9U 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-04 23:29:07` 到 `2026-07-04 23:33:43`。
- 9U 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 9U 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 9U 后 `lot_no_detail` checkpoint 指向批次 `sync_20260704_232906_917435`，记录 `param_offset=2606`、`param_limit=200`、`next_param_offset=2806`、`item_count=200`、`total_count=200`。
- 9U 后 `lot_no_detail` 累计 raw 为 2806 条、2806 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 5455 个。
- 9V 起点只读确认 `lot_no_detail` 已覆盖 2806/8261 个交货单详情，剩余缺口 5455。
- 9V 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260704_234029_450921` 成功，请求 200 次、写入 200 条、失败 0。
- 9V 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-04 23:40:29` 到 `2026-07-04 23:44:48`。
- 9V 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 9V 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 9V 后 `lot_no_detail` checkpoint 指向批次 `sync_20260704_234029_450921`，记录 `param_offset=2806`、`param_limit=200`、`next_param_offset=3006`、`item_count=200`、`total_count=200`。
- 9V 后 `lot_no_detail` 累计 raw 为 3006 条、3006 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 5255 个。
- 9W 起点只读确认 `lot_no_detail` 已覆盖 3006/8261 个交货单详情，剩余缺口 5255。
- 9W 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260704_235158_844882` 成功，请求 200 次、写入 200 条、失败 0。
- 9W 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-04 23:51:59` 到 `2026-07-04 23:56:10`。
- 9W 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 9W 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 9W 后 `lot_no_detail` checkpoint 指向批次 `sync_20260704_235158_844882`，记录 `param_offset=3006`、`param_limit=200`、`next_param_offset=3206`、`item_count=200`、`total_count=200`。
- 9W 后 `lot_no_detail` 累计 raw 为 3206 条、3206 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 5055 个。
- 9U-9W 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 2606/8261 推进到 3206/8261，但仍有 5055 个缺口，不满足 enabled 前提。
- 9X 起点只读确认 `lot_no_detail` 已覆盖 3206/8261 个交货单详情，剩余缺口 5055。
- 9X 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_000244_482705` 成功，请求 200 次、写入 200 条、失败 0。
- 9X 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 00:02:44` 到 `2026-07-05 00:08:19`。
- 9X 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 9X 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 9X 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_000244_482705`，记录 `param_offset=3206`、`param_limit=200`、`next_param_offset=3406`、`item_count=200`、`total_count=200`。
- 9X 后 `lot_no_detail` 累计 raw 为 3406 条、3406 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 4855 个。
- 9X 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 9X DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 9X dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 9X 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 9X 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 9X 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 9Y 起点只读确认 `lot_no_detail` 已覆盖 3406/8261 个交货单详情，剩余缺口 4855。
- 9Y 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_001721_536399` 成功，请求 200 次、写入 200 条、失败 0。
- 9Y 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 00:17:22` 到 `2026-07-05 00:22:55`。
- 9Y 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 9Y 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 9Y 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_001721_536399`，记录 `param_offset=3406`、`param_limit=200`、`next_param_offset=3606`、`item_count=200`、`total_count=200`。
- 9Y 后 `lot_no_detail` 累计 raw 为 3606 条、3606 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 4655 个。
- 9Y 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 9Y DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 9Y dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 9Y 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 9Y 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 9Y 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 9Z 起点只读确认 `lot_no_detail` 已覆盖 3606/8261 个交货单详情，剩余缺口 4655。
- 9Z 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_002945_035704` 成功，请求 200 次、写入 200 条、失败 0。
- 9Z 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 00:29:45` 到 `2026-07-05 00:35:07`。
- 9Z 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 9Z 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 9Z 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_002945_035704`，记录 `param_offset=3606`、`param_limit=200`、`next_param_offset=3806`、`item_count=200`、`total_count=200`。
- 9Z 后 `lot_no_detail` 累计 raw 为 3806 条、3806 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 4455 个。
- 9Z 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 9Z DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 9Z dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 9Z 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 9Z 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 9Z 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 9X-9Z 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 3206/8261 推进到 3806/8261，但仍有 4455 个缺口，不满足 enabled 前提。
- 10A 起点只读确认 `lot_no_detail` 已覆盖 3806/8261 个交货单详情，剩余缺口 4455。
- 10A 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_004147_347473` 成功，请求 200 次、写入 200 条、失败 0。
- 10A 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 00:41:47` 到 `2026-07-05 00:46:27`。
- 10A 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10A 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10A 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_004147_347473`，记录 `param_offset=3806`、`param_limit=200`、`next_param_offset=4006`、`item_count=200`、`total_count=200`。
- 10A 后 `lot_no_detail` 累计 raw 为 4006 条、4006 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 4255 个。
- 10A 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10A DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10A dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10A 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10A 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10A 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- `app.doc_catalog` 近期可能超过 120 秒，请预留 300 秒。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读确认 `lot_no_detail` 当前 checkpoint、累计 raw、剩余缺口和 `api_config.enabled=0`。
2. 继续复用 `lot_no_detail.param_source.limit=200`，运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`。
3. 查询数据库确认新批次成功、`sync_api_log.request_count=200`、`success_count=200`、`failed_count=0`、raw 新增 200 条、`failed_request_log=0`。
4. 确认 checkpoint 从 `param_offset=4006` 推进到 `next_param_offset=4206`，或如实际上游有变化，按 DB 事实记录。
5. 10B 不启用 `lot_no_detail`，除非已先证明历史缺口为 0 并验证缺失主键扫描边界。
6. 如果再次遇到业务接口 401，先核验失败批次是否推进 checkpoint 或留下 raw；必要时清理 token 缓存后重跑同一窗口。
7. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
10. 更新三份 docs；如 README 的运行说明或 API 状态变动需要同步，也一起更新。
11. 下一次三轮复盘放在 10C 完成后；10B 只需要记录本轮窗口证据和趋势。
12. 提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口、参数窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 10B 默认不启用 `lot_no_detail`；如启用新接口，必须先证明历史缺口为 0、`api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实 `--sync-enabled` 批次证明全部 enabled API 同批次成功。
3. 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
4. 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 33 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
