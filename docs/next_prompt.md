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

阶段 4D：单接口验证 `country_tree`。

当前事实：

- 当前 enabled API 有 7 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`。
- `country_tree` 已在阶段 4C 添加为第八个候选接口，默认 `enabled=false`。
- `country_tree` 对应文档 id `4563`，名称是“获取已授权店铺区域国家”。
- 文档路径为 `GET /middle/base/countryTree/page`，实际请求路径为 `/api/open/middle/base/countryTree/page`。
- 请求头需要 `accessToken`，请求体示例为空 `{}`。
- 响应列表字段为 `data`，文档未展开 `data` 元素字段，因此第一版使用 `data_hash` 去重。
- 阶段 4C 已运行 `--sync-api-configs`，数据库配置总数为 10，`country_tree.enabled=0`。

建议目标：

1. 阅读现有 `config/api_config.example.yaml`、`docs/progress.md`、`docs/decisions.md`。
2. 保持 `country_tree.enabled=false`。
3. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api country_tree` 做单接口验证。
4. 查询数据库确认 `sync_batch`、`sync_api_log`、`raw_api_data`、`sync_checkpoint`。
5. 确认无稳定主键时使用 `data_hash` 去重。
6. 再运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`，确认仍只同步已启用的 7 个 API。
7. 验证通过后，下一阶段再决定是否把 `country_tree` 加入 `--sync-enabled`。

验收：

1. `.\\.venv\\Scripts\\python.exe -m compileall app tests` 通过。
2. `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 通过。
3. `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 仍显示 7 个 enabled API。
4. `.\\.venv\\Scripts\\python.exe -m app.main --mock-sync` 通过。
5. `country_tree` 单接口验证成功。
6. `--sync-enabled` 仍只同步当前 7 个 enabled API。
7. 数据库 `api_config.country_tree.enabled=0`。
8. 不输出任何真实凭证或 accessToken。
