# Next Codex Prompt

请继续这个项目。

开始前请先阅读：

1. AGENTS.md
2. README.md
3. docs/progress.md
4. docs/decisions.md
5. 当前项目目录结构和关键代码

注意：

- 不要重建项目。
- 不要覆盖已有实现。
- 不要读取或输出 `.env` 中的真实敏感信息。
- 不要写入真实 API 凭证、数据库密码或 accessToken。
- 如果发现代码和文档状态不一致，先说明差异，再决定怎么处理。
- 完成本阶段后，请更新 `docs/progress.md`、`docs/decisions.md` 和 `docs/next_prompt.md`。
- 保持 KISS：先做最小可验证主流程，不要一次性做完整生产级同步。

当前要执行的阶段：

阶段 4G：单接口验证 `category_page`。

当前事实：

- 当前 enabled API 有 8 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`。
- `category_page` 已在阶段 4F 添加为第九个候选接口，默认 `enabled=false`。
- `category_page` 对应文档 id `54`，名称是“查询品类信息”。
- 文档路径为 `POST /purchase/goods/category/page`，实际请求路径为 `/api/open/purchase/goods/category/page`。
- 请求头需要 `accessToken`，请求体必填 `page` 和 `pagesize`，可选 `state` 和 `valueList`。
- 响应列表字段为 `data.rows`，总数字段为 `data.total`，候选主键字段为 `id`。
- 阶段 4F 已运行 `--sync-api-configs`，数据库配置总数为 11，`category_page.enabled=0`。

建议目标：

1. 阅读现有 `config/api_config.example.yaml`、`docs/progress.md`、`docs/decisions.md`。
2. 保持 `category_page.enabled=false`。
3. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api category_page` 做单接口验证。
4. 查询数据库确认 `sync_batch`、`sync_api_log`、`raw_api_data`、`sync_checkpoint`。
5. 确认 `raw_api_data.source_primary_key` 来自 `id`。
6. 再运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`，确认仍只同步已启用的 8 个 API。
7. 验证通过后，下一阶段再决定是否把 `category_page` 加入 `--sync-enabled`。

验收：

1. `.\\.venv\\Scripts\\python.exe -m compileall app tests` 通过。
2. `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 通过。
3. `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 仍显示 8 个 enabled API。
4. `.\\.venv\\Scripts\\python.exe -m app.main --mock-sync` 通过。
5. `category_page` 单接口验证成功。
6. `--sync-enabled` 仍只同步当前 8 个 enabled API。
7. 数据库 `api_config.category_page.enabled=0`。
8. 不输出任何真实凭证或 accessToken。
