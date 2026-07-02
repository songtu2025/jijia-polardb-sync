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

阶段 4F：调研第九个低风险业务 API 候选。

当前事实：

- 当前 enabled API 有 8 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`。
- 阶段 4E 已将 `country_tree.enabled=true`。
- 阶段 4E enabled 批次：`sync_20260702_213009_933395`，`apis=8`，`rows=3637`，`requests=16`。
- `country_tree` 在 enabled 批次中写入 4 条，数据库 `api_config.country_tree.enabled=1`。
- 近期排除过这些候选：`warehouseIds/query` 需要店铺 ID，`marketNames/query` 需要店铺 ID 且响应为字符串，`multiTypeWarehouse/page` 包含联系人、电话、邮箱、地址和第三方仓 token 字段，`allUser/list` 包含 phone/email。

建议目标：

1. 使用公开文档站只读接口或浏览器调研新的低风险 API。
2. 优先选择无敏感字段、无需上游业务 ID、响应为列表或分页列表的接口。
3. 确认文档 id、业务路径、实际请求路径、请求头、请求体、列表字段、分页字段、候选主键和日期字段。
4. 在 `config/api_config.example.yaml` 中新增配置，默认 `enabled: false`。
5. 不执行新 API 真实同步，下一阶段再做单接口验证。
6. 运行 dry-run、mock-sync、sync-api-configs 和基础测试，确认当前 8 个 enabled API 不受影响。

验收：

1. `.\\.venv\\Scripts\\python.exe -m compileall app tests` 通过。
2. `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 通过。
3. `.\\.venv\\Scripts\\python.exe -m app.main` dry-run 仍显示 8 个 enabled API。
4. `.\\.venv\\Scripts\\python.exe -m app.main --mock-sync` 通过。
5. `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 通过，配置数应变为 11。
6. 数据库中新候选 API 的 `enabled=0`。
7. 不输出任何真实凭证或 accessToken。
