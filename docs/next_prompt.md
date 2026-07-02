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
- 你负责把控和审核项目结果，以真实命令、数据库状态和 Git diff 为准。

当前阶段：

阶段 4K 已完成。下一阶段 4L 先确认方向，不要直接扩大 enabled 范围。

当前事实：

- 当前 enabled API 有 10 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`。
- `brand_page` 已加入 enabled 批量同步。
- 阶段 4K 成功批次：`sync_20260702_234239_362350`。
- 该批次 `total_api_count=10`、`success_api_count=10`、`failed_api_count=0`。
- `brand_page` 在 enabled 批次中请求 1 次，写入 8 条。
- `api_config.brand_page.enabled=1`，`api_config` 总数为 12，启用数为 10。
- `.\\.venv\\Scripts\\python.exe -m compileall app tests` 已通过。
- `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 已通过。

建议目标：

1. 先向用户确认下一步方向。
2. 如果准备部署，做 ECS/cron 前检查，不新增 API。
3. 如果继续扩展接口，先只读调研积加文档，新增配置默认 `enabled: false`。
4. 不要在未确认候选接口前修改 enabled 范围。

验收：

1. 下一步方向明确。
2. 不输出任何真实凭证或 accessToken。
3. 不提交 `.env`、token 缓存、日志或任何敏感信息。
