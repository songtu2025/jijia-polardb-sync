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

阶段 4T 已完成。下一阶段 4U 继续接入下一批低风险 `direct_read_candidate`，并开始只读梳理依赖型接口参数来源。

当前事实：

- 当前 enabled API 有 18 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`、`kb_product_page`、`fba_warehouse_page`、`store_location_page`、`multi_shop_query`、`crm_tags_page`、`inventory_team_query`。
- 当前已配置真实 API 有 18 个，且 18 个均已 enabled。
- 阶段 4T 成功批次：`sync_20260703_020359_152948`。
- 该批次 `total_api_count=18`、`success_api_count=18`、`failed_api_count=0`。
- 该批次合计 `rows=13235`、`requests=121`。
- `crm_tags_page` 在 enabled 批次中请求 1 次，写入 7 条，7 条 raw 数据都有 `source_primary_key` 和 `data_date`。
- `inventory_team_query` 在 enabled 批次中请求 1 次，写入 1 条，1 条 raw 数据有 `source_primary_key`；该接口无日期字段，`data_date` 为空。
- `api_config.crm_tags_page.enabled=1`、`api_config.inventory_team_query.enabled=1`。
- 覆盖矩阵显示公开文档 API 185 个，真实配置 API 18 个，enabled 18 个。
- 4R-4T 已完成三轮复盘：低风险直读接入节奏有效，但 79 个依赖上游参数接口需要开始设计参数来源。

建议目标：

1. 从 `config/jijia_api_catalog.generated.json` 中选择 1-2 个新的低风险 `direct_read_candidate`。
2. 优先选择无敏感字段、无上游必填参数、主键和分页清晰的接口。
3. 新接口新增 YAML 配置时默认 `enabled=false`。
4. 单接口运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api <api_code>` 并查库验证。
5. 同步 `api_config` 并刷新覆盖矩阵。
6. 只读梳理 1-2 个 `requires_upstream_params` 接口，记录它们需要的参数和可能来自哪些已同步 raw 数据。
7. 运行 `.\\.venv\\Scripts\\python.exe -m compileall app tests`。
8. 运行 `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"`。

验收：

1. 新增直读接口与公开文档一致，且默认不进入 `--sync-enabled`。
2. dry-run enabled API 仍为 18 个。
3. 单接口同步成功并可查库验证。
4. `api_config` 和覆盖矩阵同步到新配置状态。
5. 依赖型接口参数来源只做事实梳理，不编造字段含义，不扩大写入范围。
6. 不提交 `.env`、token 缓存、日志或任何敏感信息。
