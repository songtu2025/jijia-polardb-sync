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

阶段 4H：将 `category_page` 加入 enabled 批量同步。

当前事实：

- 当前 enabled API 有 8 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`。
- `category_page` 已在阶段 4G 完成单接口真实验证。
- 阶段 4G 成功批次：`sync_20260702_213741_496366`。
- `category_page` 单接口验证结果：请求 1 次，写入 42 条，`source_primary_key` 来自 `id`，`data_date` 为空。
- 阶段 4G 后 `category_page.enabled=false`，未加入 enabled 批量同步。
- 最近一次 enabled 批次：`sync_20260702_213820_543116`，`apis=8`，八个 API 均成功。

建议目标：

1. 阅读现有 `config/api_config.example.yaml`、`docs/progress.md`、`docs/decisions.md`。
2. 将 `category_page.enabled` 从 `false` 改为 `true`。
3. 运行 `.\\.venv\\Scripts\\python.exe -m app.main`，确认 enabled API 变为 9 个。
4. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`。
5. 查询数据库确认 `sync_batch`、`sync_api_log`、`raw_api_data`、`sync_checkpoint`。
6. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`，同步 `api_config` 表。
7. 查询 `api_config`，确认 `category_page.enabled=1`。

验收：

1. `.\\.venv\\Scripts\\python.exe -m compileall app tests` 通过。
2. `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 通过。
3. dry-run 显示 enabled API 为 9 个。
4. `--sync-enabled` 成功同步 9 个 API。
5. `category_page` 在 enabled 批次中成功写入 42 条。
6. `--sync-api-configs` 成功，同步配置数为 11。
7. 数据库 `api_config.category_page.enabled=1`。
8. 不输出任何真实凭证或 accessToken。
