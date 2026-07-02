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

当前阶段：

阶段 4N 已完成。4L-4N 三轮复盘已写入 `docs/progress.md`。下一阶段 4O 开启第二组目标，继续接入下一批低风险 direct_read_candidate。

当前事实：

- 当前 enabled API 有 12 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`、`product_page`、`parent_product_page`。
- 当前已配置真实 API 有 12 个，且 12 个均已 enabled。
- 阶段 4N 成功批次：`sync_20260703_005314_970429`。
- 该批次 `total_api_count=12`、`success_api_count=12`、`failed_api_count=0`。
- `product_page` 在 enabled 批次中请求 83 次，写入 8258 条，`item_count=total_count=8258`。
- `parent_product_page` 在 enabled 批次中请求 3 次，写入 124 条，`item_count=total_count=124`。
- `api_config.product_page.enabled=1`、`api_config.parent_product_page.enabled=1`。
- 覆盖矩阵仍显示公开文档 API 185 个，真实配置 API 12 个，enabled 12 个。

复盘结论：

- 覆盖矩阵 -> 默认禁用配置 -> 单接口验证 -> enabled 批量验证，这条路径有效。
- `product_page` 暴露了 `max_pages` 截断风险，后续大分页接口必须先看 `total_count` 和 checkpoint。
- enabled 批量同步已有 105 次请求，后续继续加大接口前要关注运行时长。
- 依赖上游参数接口有 79 个，后续需要设计依赖参数来源，不能全部靠静态 YAML。

建议目标：

1. 从 `config/jijia_api_catalog.generated.json` 中选择 1-2 个新的低风险 `direct_read_candidate`。
2. 优先选择分页清晰、有稳定 `id` 或明确业务主键、无敏感字段的接口。
3. 暂缓 `amazon_msku_page` 这类无单字段 id 的接口，除非先明确 data_hash 或复合主键策略。
4. 新接口新增 YAML 配置时默认 `enabled=false`。
5. 单接口运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api <api_code>` 并查库验证。
6. 单接口验证通过后再进入下一轮 enabled。

验收：

1. 新增配置与公开文档一致，且默认不进入 `--sync-enabled`。
2. dry-run enabled API 仍为 12 个。
3. 单接口同步成功并可查库验证。
4. `.\\.venv\\Scripts\\python.exe -m compileall app tests` 通过。
5. `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 通过。
6. 不提交 `.env`、token 缓存、日志或任何敏感信息。
