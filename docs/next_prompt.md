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

阶段 11M 已完成。下一阶段 11N 继续推进完整拉取：`procure_detail` 已追平当前完整 `lot_no_page` 的 1153 个去重采购单号，并通过空缺口/no-op 验证；当前累计覆盖 1153/1153，仍保持 disabled。11N 应先解决日增量 enabled 的稳定键或缺失扫描语义，再决定是否启用。

当前事实：

- 当前 enabled API 有 36 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`platform_msku_page`、`crm_tags_page`、`inventory_team_query`、`product_inventory_page`、`storage_inbound_page`、`transfer_page`、`lot_no_page`、`storage_return_page`、`strategy_template_page`、`traffic_page`、`traffic_sku_page`、`shipment_data_page`、`storage_ledger_page`、`inventory_receipts_page`、`purchase_plan_page`、`product_detail`、`country_province_query`、`transfer_detail`、`lot_no_detail`、`base_currency_query`。
- 当前已配置真实 API 有 50 个，其中 36 个已 enabled；剩余 14 个真实配置 API 已验证但保持 disabled。
- DB `api_config` 表当前有 52 条配置、36 条 enabled、16 条 disabled；该 52 是 YAML 入库总数，覆盖矩阵真实 API 口径仍为 50 个。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 50 个，enabled 36 个；执行分层摘要为 `configured=50`、`configured_enabled=36`、`configured_disabled=14`、`needs_upstream_params=63`、`needs_sensitive_review=22`、`defer_or_review=50`。
- `procure_detail.param_source.limit=100`，仍保持 `enabled=false`。
- 阶段 11M 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api procure_detail`，批次 `sync_20260705_115907_773766` 成功。
- 阶段 11M 单接口 `procure_detail` 为 0 次请求、0 条 raw、失败 0。
- 阶段 11M 后 `procure_detail` 累计 raw 为 1153 条、1153 个 hash、1153 条空 `source_primary_key`。
- 阶段 11M checkpoint 为 `param_offset=1153`、`param_limit=100`、`next_param_offset=1153`。
- DB 核验显示 `api_config.procure_detail.enabled=0`、`config_json.enabled=false`、`param_source.limit=100`。
- 完整 `lot_no_page` 后有 1153 个去重 `poCode`；`procure_detail` 当前覆盖 1153/1153，历史覆盖已追平且 no-op 不重复拉取。
- 阶段 11M 启用前评估发现：`procure_detail` raw 顶层 `poCode`、`procureId`、`id` 覆盖均为 0；返回顶层主要为 `deliveryOrde`、`procureItemVos`、`attachmentVOList`、`planAttachmentVOList`、`warehouseProcureItemVos`，暂不能直接用 `lot_no_page.poCode` 反查目标表是否已存在。
- 当前 offset 参数源按来源字段排序后推进，已适合历史回填和 no-op 验证；但如果未来新增采购单号排序落在已推进 offset 之前，直接 enabled 可能漏扫。
- 阶段 11M 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 52 条配置。
- 阶段 11M dry-run 显示 loaded 36 enabled API config(s)，确认 `procure_detail` 没有进入每日 enabled 批量同步。
- 阶段 11M 已运行 `.\\.venv\\Scripts\\python.exe -m app.doc_catalog --output config\\jijia_api_catalog.generated.json --summary`，公开文档 API 185 个、真实配置 API 50 个、enabled 36 个、configured disabled 14 个。
- 阶段 11M 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests` 并通过。
- 阶段 11M 已运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`，82 个测试通过。
- 11K-11M 复盘结论：11K 新增 100 个 `procure_detail` 详情，11L 新增 50 个详情，11M no-op 验证请求 0、写入 0；覆盖从 1003/1153 推进到 1153/1153，三轮均失败 0，enabled API 保持 36 个。

建议目标：

- 先不要直接启用 `procure_detail`。
- 只读检查 `procure_detail` 响应结构，确认是否存在可稳定回填为 `source_primary_key` 的字段或组合字段。
- 如果能找到稳定键，先设计最小迁移/回填方案，再评估 `param_source.exclude_existing_target=true` 或等价缺失扫描。
- 如果找不到稳定键，优先考虑为参数型详情接口记录请求参数到 raw 元数据或新增最小字段，使未来 daily 增量能按来源参数判断缺失，而不是依赖排序 offset。
- 只有在证明不会漏扫新增 `lot_no_page.poCode` 后，才将 `procure_detail.enabled` 改为 `true`，dry-run 确认 enabled 数量变为 37，并运行完整 `--sync-enabled`。
- 完成后同步 `api_config`、刷新覆盖矩阵并运行编译与单测。
- 下一次三轮复盘放在 11P 完成后。

验收：

- 新接口、完整窗口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如调整参数型详情接口的幂等或缺失扫描逻辑，必须先证明旧数据不丢、新数据可发现，并用测试覆盖关键逻辑。
- 如推进日期窗口，必须证明 `item_count == total_count` 或者明确说明接口返回总量为 0。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 50 个、enabled 36 个、configured disabled 14 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存和日志不提交。
