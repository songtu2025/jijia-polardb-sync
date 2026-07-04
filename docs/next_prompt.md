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

阶段 10W 已完成。下一阶段 10X 继续推进完整拉取：`lot_no_detail` 已追平当前 8261 个 LNInbound 交货单详情，下一步优先评估 enabled 边界；先确认缺失主键扫描不会重复拉取全部历史，再决定是否启用并跑完整 `--sync-enabled`。10X 完成后需要复盘 10V-10X 三轮。

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
- 10B 起点只读确认 `lot_no_detail` 已覆盖 4006/8261 个交货单详情，剩余缺口 4255。
- 10B 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_005227_636220` 成功，请求 200 次、写入 200 条、失败 0。
- 10B 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 00:52:28` 到 `2026-07-05 00:57:10`。
- 10B 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10B 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10B 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_005227_636220`，记录 `param_offset=4006`、`param_limit=200`、`next_param_offset=4206`、`item_count=200`、`total_count=200`。
- 10B 后 `lot_no_detail` 累计 raw 为 4206 条、4206 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 4055 个。
- 10B 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10B DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10B dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10B 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10B 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10B 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10C 起点只读确认 `lot_no_detail` 已覆盖 4206/8261 个交货单详情，剩余缺口 4055。
- 10C 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_010437_904794` 成功，请求 200 次、写入 200 条、失败 0。
- 10C 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 01:04:38` 到 `2026-07-05 01:11:10`。
- 10C 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10C 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10C 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_010437_904794`，记录 `param_offset=4206`、`param_limit=200`、`next_param_offset=4406`、`item_count=200`、`total_count=200`。
- 10C 后 `lot_no_detail` 累计 raw 为 4406 条、4406 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 3855 个。
- 10C 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10C DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10C dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10C 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10C 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10C 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10A-10C 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 3806/8261 推进到 4406/8261，但仍有 3855 个缺口，不满足 enabled 前提。
- 10D 起点只读确认 `lot_no_detail` 已覆盖 4406/8261 个交货单详情，剩余缺口 3855。
- 10D 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_011845_553625` 成功，请求 200 次、写入 200 条、失败 0。
- 10D 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 01:18:46` 到 `2026-07-05 01:24:24`。
- 10D 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10D 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10D 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_011845_553625`，记录 `param_offset=4406`、`param_limit=200`、`next_param_offset=4606`、`item_count=200`、`total_count=200`。
- 10D 后 `lot_no_detail` 累计 raw 为 4606 条、4606 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 3655 个。
- 10D 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10D DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10D dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10D 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10D 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10D 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10E 起点只读确认 `lot_no_detail` 已覆盖 4606/8261 个交货单详情，剩余缺口 3655。
- 10E 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_013034_265972` 成功，请求 200 次、写入 200 条、失败 0。
- 10E 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 01:30:34` 到 `2026-07-05 01:36:24`。
- 10E 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10E 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10E 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_013034_265972`，记录 `param_offset=4606`、`param_limit=200`、`next_param_offset=4806`、`item_count=200`、`total_count=200`。
- 10E 后 `lot_no_detail` 累计 raw 为 4806 条、4806 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 3455 个。
- 10E 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10E DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10E dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10E 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10E 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10E 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10F 起点只读确认 `lot_no_detail` 已覆盖 4806/8261 个交货单详情，剩余缺口 3455。
- 10F 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_014223_409877` 成功，请求 200 次、写入 200 条、失败 0。
- 10F 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 01:42:23` 到 `2026-07-05 01:46:58`。
- 10F 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10F 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10F 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_014223_409877`，记录 `param_offset=4806`、`param_limit=200`、`next_param_offset=5006`、`item_count=200`、`total_count=200`。
- 10F 后 `lot_no_detail` 累计 raw 为 5006 条、5006 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 3255 个。
- 10F 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10F DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10F dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10F 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10F 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10F 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10D-10F 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 4406/8261 推进到 5006/8261，但仍有 3255 个缺口，不满足 enabled 前提。
- 10G 起点只读确认 `lot_no_detail` 已覆盖 5006/8261 个交货单详情，剩余缺口 3255。
- 10G 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_015431_044307` 成功，请求 200 次、写入 200 条、失败 0。
- 10G 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 01:54:31` 到 `2026-07-05 01:58:48`。
- 10G 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10G 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10G 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_015431_044307`，记录 `param_offset=5006`、`param_limit=200`、`next_param_offset=5206`、`item_count=200`、`total_count=200`。
- 10G 后 `lot_no_detail` 累计 raw 为 5206 条、5206 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 3055 个。
- 10G 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10G DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10G dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10G 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10G 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10G 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10H 起点只读确认 `lot_no_detail` 已覆盖 5206/8261 个交货单详情，剩余缺口 3055。
- 10H 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_020744_241759` 成功，请求 200 次、写入 200 条、失败 0。
- 10H 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 02:07:44` 到 `2026-07-05 02:12:56`。
- 10H 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10H 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10H 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_020744_241759`，记录 `param_offset=5206`、`param_limit=200`、`next_param_offset=5406`、`item_count=200`、`total_count=200`。
- 10H 后 `lot_no_detail` 累计 raw 为 5406 条、5406 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 2855 个。
- 10H 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10H DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10H dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10H 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10H 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10H 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10I 起点只读确认 `lot_no_detail` 已覆盖 5406/8261 个交货单详情，剩余缺口 2855。
- 10I 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_021930_865405` 成功，请求 200 次、写入 200 条、失败 0。
- 10I 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 02:19:31` 到 `2026-07-05 02:24:22`。
- 10I 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10I 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10I 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_021930_865405`，记录 `param_offset=5406`、`param_limit=200`、`next_param_offset=5606`、`item_count=200`、`total_count=200`。
- 10I 后 `lot_no_detail` 累计 raw 为 5606 条、5606 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 2655 个。
- 10I 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10I DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10I dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10I 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10I 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10I 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10G-10I 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 5006/8261 推进到 5606/8261，但仍有 2655 个缺口，不满足 enabled 前提。
- 10J 起点只读确认 `lot_no_detail` 已覆盖 5606/8261 个交货单详情，剩余缺口 2655。
- 10J 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_023234_494584` 成功，请求 200 次、写入 200 条、失败 0。
- 10J 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 02:32:34` 到 `2026-07-05 02:37:32`。
- 10J 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10J 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10J 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_023234_494584`，记录 `param_offset=5606`、`param_limit=200`、`next_param_offset=5806`、`item_count=200`、`total_count=200`。
- 10J 后 `lot_no_detail` 累计 raw 为 5806 条、5806 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 2455 个。
- 10J 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10J DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10J dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10J 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10J 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10J 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10K 起点只读确认 `lot_no_detail` 已覆盖 5806/8261 个交货单详情，剩余缺口 2455。
- 10K 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_024423_315385` 成功，请求 200 次、写入 200 条、失败 0。
- 10K 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 02:44:23` 到 `2026-07-05 02:49:12`。
- 10K 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10K 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10K 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_024423_315385`，记录 `param_offset=5806`、`param_limit=200`、`next_param_offset=6006`、`item_count=200`、`total_count=200`。
- 10K 后 `lot_no_detail` 累计 raw 为 6006 条、6006 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 2255 个。
- 10K 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10K DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10K dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10K 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10K 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10K 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10L 起点只读确认 `lot_no_detail` 已覆盖 6006/8261 个交货单详情，剩余缺口 2255。
- 10L 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_025627_748467` 成功，请求 200 次、写入 200 条、失败 0。
- 10L 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 02:56:28` 到 `2026-07-05 03:00:49`。
- 10L 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10L 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10L 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_025627_748467`，记录 `param_offset=6006`、`param_limit=200`、`next_param_offset=6206`、`item_count=200`、`total_count=200`。
- 10L 后 `lot_no_detail` 累计 raw 为 6206 条、6206 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 2055 个。
- 10L 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10L DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10L dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10L 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10L 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10L 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10J-10L 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 5606/8261 推进到 6206/8261，但仍有 2055 个缺口，不满足 enabled 前提。
- 10M 起点只读确认 `lot_no_detail` 已覆盖 6206/8261 个交货单详情，剩余缺口 2055。
- 10M 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_030953_593844` 成功，请求 200 次、写入 200 条、失败 0。
- 10M 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 03:09:54` 到 `2026-07-05 03:15:31`。
- 10M 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10M 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10M 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_030953_593844`，记录 `param_offset=6206`、`param_limit=200`、`next_param_offset=6406`、`item_count=200`、`total_count=200`。
- 10M 后 `lot_no_detail` 累计 raw 为 6406 条、6406 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 1855 个。
- 10M 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10M DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10M dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10M 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10M 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10M 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10N 起点只读确认 `lot_no_detail` 已覆盖 6406/8261 个交货单详情，剩余缺口 1855。
- 10N 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_032312_449483` 成功，请求 200 次、写入 200 条、失败 0。
- 10N 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 03:23:12` 到 `2026-07-05 03:27:42`。
- 10N 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10N 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10N 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_032312_449483`，记录 `param_offset=6406`、`param_limit=200`、`next_param_offset=6606`、`item_count=200`、`total_count=200`。
- 10N 后 `lot_no_detail` 累计 raw 为 6606 条、6606 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 1655 个。
- 10N 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10N DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10N dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10N 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10N 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10N 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10O 起点只读确认 `lot_no_detail` 已覆盖 6606/8261 个交货单详情，剩余缺口 1655。
- 10O 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_033330_655101` 成功，请求 200 次、写入 200 条、失败 0。
- 10O 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 03:33:31` 到 `2026-07-05 03:38:04`。
- 10O 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10O 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10O 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_033330_655101`，记录 `param_offset=6606`、`param_limit=200`、`next_param_offset=6806`、`item_count=200`、`total_count=200`。
- 10O 后 `lot_no_detail` 累计 raw 为 6806 条、6806 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 1455 个。
- 10O 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10O DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10O dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10O 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10O 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10O 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10M-10O 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 6206/8261 推进到 6806/8261，但仍有 1455 个缺口，不满足 enabled 前提。
- 10P 起点只读确认 `lot_no_detail` 已覆盖 6806/8261 个交货单详情，剩余缺口 1455。
- 10P 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_034700_432376` 成功，请求 200 次、写入 200 条、失败 0。
- 10P 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 03:47:00` 到 `2026-07-05 03:51:46`。
- 10P 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10P 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10P 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_034700_432376`，记录 `param_offset=6806`、`param_limit=200`、`next_param_offset=7006`、`item_count=200`、`total_count=200`。
- 10P 后 `lot_no_detail` 累计 raw 为 7006 条、7006 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 1255 个。
- 10P 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10P DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10P dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10P 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10P 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10P 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10Q 起点只读确认 `lot_no_detail` 已覆盖 7006/8261 个交货单详情，剩余缺口 1255。
- 10Q 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_035827_574625` 成功，请求 200 次、写入 200 条、失败 0。
- 10Q 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 03:58:28` 到 `2026-07-05 04:03:52`。
- 10Q 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10Q 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10Q 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_035827_574625`，记录 `param_offset=7006`、`param_limit=200`、`next_param_offset=7206`、`item_count=200`、`total_count=200`。
- 10Q 后 `lot_no_detail` 累计 raw 为 7206 条、7206 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 1055 个。
- 10Q 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10Q DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10Q dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10Q 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10Q 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10Q 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10R 起点只读确认 `lot_no_detail` 已覆盖 7206/8261 个交货单详情，剩余缺口 1055。
- 10R 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_041111_747328` 成功，请求 200 次、写入 200 条、失败 0。
- 10R 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 04:11:12` 到 `2026-07-05 04:16:37`。
- 10R 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10R 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10R 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_041111_747328`，记录 `param_offset=7206`、`param_limit=200`、`next_param_offset=7406`、`item_count=200`、`total_count=200`。
- 10R 后 `lot_no_detail` 累计 raw 为 7406 条、7406 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 855 个。
- 10R 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10R DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10R dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10R 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10R 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10R 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10P-10R 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 6806/8261 推进到 7406/8261，但仍有 855 个缺口，不满足 enabled 前提。
- 10S 起点只读确认 `lot_no_detail` 已覆盖 7406/8261 个交货单详情，剩余缺口 855。
- 10S 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_042345_204110` 成功，请求 200 次、写入 200 条、失败 0。
- 10S 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 04:23:45` 到 `2026-07-05 04:28:33`。
- 10S 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10S 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10S 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_042345_204110`，记录 `param_offset=7406`、`param_limit=200`、`next_param_offset=7606`、`item_count=200`、`total_count=200`。
- 10S 后 `lot_no_detail` 累计 raw 为 7606 条、7606 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 655 个。
- 10S 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10S DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10S dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10S 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10S 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10S 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10T 起点只读确认 `lot_no_detail` 已覆盖 7606/8261 个交货单详情，剩余缺口 655。
- 10T 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_043736_871286` 成功，请求 200 次、写入 200 条、失败 0。
- 10T 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 04:37:37` 到 `2026-07-05 04:42:28`。
- 10T 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10T 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10T 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_043736_871286`，记录 `param_offset=7606`、`param_limit=200`、`next_param_offset=7806`、`item_count=200`、`total_count=200`。
- 10T 后 `lot_no_detail` 累计 raw 为 7806 条、7806 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 455 个。
- 10T 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10T DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10T dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10T 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10T 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10T 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10S-10U 复盘结论：三轮累计新增 600 个 `lot_no_detail` 交货单详情，三轮均为 200 请求、200 raw、失败 0；覆盖从 7406/8261 推进到 8006/8261，但仍有 255 个缺口，不满足 enabled 前提。
- 10U 起点只读确认 `lot_no_detail` 已覆盖 7806/8261 个交货单详情，剩余缺口 455。
- 10U 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_045048_577028` 成功，请求 200 次、写入 200 条、失败 0。
- 10U 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 04:50:49` 到 `2026-07-05 04:55:35`。
- 10U 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10U 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10U 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_045048_577028`，记录 `param_offset=7806`、`param_limit=200`、`next_param_offset=8006`、`item_count=200`、`total_count=200`。
- 10U 后 `lot_no_detail` 累计 raw 为 8006 条、8006 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 255 个。
- 10U 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10U DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=200`。
- 10U dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10U 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10U 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10U 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10V 起点只读确认 `lot_no_detail` 已覆盖 8006/8261 个交货单详情，剩余缺口 255。
- 10V 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_050255_559206` 成功，请求 200 次、写入 200 条、失败 0。
- 10V 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 05:02:56` 到 `2026-07-05 05:09:26`。
- 10V 同批次 `sync_api_log` 为 `status=success`、`request_count=200`、`success_count=200`、`failed_count=0`、`error_message=NULL`。
- 10V 同批次 raw 为 200 条、200 个不同 `source_primary_key`、200 个不同 `data_hash`；`failed_request_log=0`。
- 10V 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_050255_559206`，记录 `param_offset=8006`、`param_limit=200`、`next_param_offset=8206`、`item_count=200`、`total_count=200`。
- 10V 后 `lot_no_detail` 累计 raw 为 8206 条、8206 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 55 个。
- 10V 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10V DB 核验显示 `api_config` 总配置 52 条、enabled 33 条，`lot_no_detail.enabled=0`、`config_json.enabled=false`。
- 10V dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 没有误进入 enabled。
- 10V 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10V 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10V 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10V 复盘结论：本轮只推进历史回填，不改 YAML、不启用；`lot_no_detail` 覆盖从 8006/8261 推进到 8206/8261，剩余 55 个尾段缺口，缺口归零前不满足 enabled 前提。
- 10W 起点只读确认 `lot_no_detail` 已覆盖 8206/8261 个交货单详情，剩余缺口 55。
- 10W 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api lot_no_detail`，批次 `sync_20260705_051850_119507` 成功，请求 55 次、写入 55 条、失败 0。
- 10W 同批次 `sync_batch.status=success`、`total_api_count=1`、`success_api_count=1`、`failed_api_count=0`，从 `2026-07-05 05:18:50` 到 `2026-07-05 05:20:43`。
- 10W 同批次 `sync_api_log` 为 `status=success`、`request_count=55`、`success_count=55`、`failed_count=0`、`error_message=NULL`。
- 10W 同批次 raw 为 55 条、55 个不同 `source_primary_key`、55 个不同 `data_hash`；`failed_request_log=0`。
- 10W 后 `lot_no_detail` checkpoint 指向批次 `sync_20260705_051850_119507`，记录 `param_offset=8206`、`param_limit=200`、`next_param_offset=8261`、`item_count=55`、`total_count=55`。
- 10W 后 `lot_no_detail` 累计 raw 为 8261 条、8261 个不同交货单号；按 `storage_inbound_page.raw_json.fcode` 且 `opType=LNInbound` 口径剩余缺口为 0 个，缺失样本为空。
- 10W 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条 API 配置到 DB。
- 10W dry-run 显示 loaded 33 enabled API config(s)，说明 `lot_no_detail` 仍没有误进入 enabled。
- 10W 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 33 个。
- 10W 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 10W 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，80 个测试通过。
- 10W 结论：`lot_no_detail` 历史回填已追平，但 YAML 仍为 `enabled=false`，且当前配置缺少 `exclude_existing_target=true`；启用前应先补齐或确认缺失扫描边界。
- `app.main` 当前没有 `--dry-run` 参数；如需确认 enabled 数量，用 `.\\.venv\\Scripts\\python.exe -m app.main` 或 `app.doc_catalog` 摘要。
- `app.doc_catalog` 近期可能超过 120 秒，请预留 300 秒。
- 本地 Git 应与远端同步；开始前仍请先看 `git status --short --branch` 和 `git log -1 --oneline`。

建议目标：

1. 先只读确认 `lot_no_detail` 当前 checkpoint、累计 raw、剩余缺口为 0、缺失样本为空，并确认 `api_config.enabled=0`。
2. 在 YAML 中评估并补齐 `lot_no_detail.param_source.exclude_existing_target=true`，使启用后只扫描目标表缺失主键。
3. 如决定启用，将 `lot_no_detail.enabled` 从 `false` 改为 `true`。
4. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，确认 DB 中 `api_config.lot_no_detail.enabled=1` 且 `config_json.enabled=true`。
5. 运行 `.\\.venv\\Scripts\\python.exe -m app.main` dry-run，确认 enabled API 从 33 变为 34，并包含 `lot_no_detail`。
6. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`，确认 34 个 enabled API 同批次成功；重点确认 `lot_no_detail` 在缺口为 0 时请求数为 0 或只请求新增缺失项。
7. 如果再次遇到业务接口 401，先核验失败批次是否推进 checkpoint 或留下 raw；必要时清理 token 缓存后重跑同一窗口。
8. 需要刷新覆盖矩阵时，运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`。
9. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
10. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。
11. 更新三份 docs；如 README 的运行说明或 API 状态变动需要同步，也一起更新。
12. 10X 完成后复盘 10V-10X 三轮。
13. 提交推送时不要提交 `.env`、token 缓存、日志或任何敏感信息。

验收：

1. 新接口、完整窗口、参数窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
2. 10X 可评估启用 `lot_no_detail`；如启用，必须先证明历史缺口为 0、缺失扫描边界正确、`api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实 `--sync-enabled` 批次证明全部 enabled API 同批次成功。
3. 如推进参数型单接口窗口，必须证明 checkpoint 的 `param_offset`、`param_limit`、`next_param_offset` 按预期推进。
4. 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
5. `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量变化符合本轮目标；当前基线是真实配置 API 50 个、enabled 33 个。
6. `compileall` 和 `unittest discover` 通过。
7. 不提交 `.env`、token 缓存、日志或真实凭证。
