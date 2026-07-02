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

阶段 4M 已完成。下一阶段 4N 将 `product_page` 和 `parent_product_page` 加入 enabled 批量同步。

当前事实：

- 当前 enabled API 有 10 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`。
- 当前已配置真实 API 有 12 个，`product_page` 和 `parent_product_page` 已通过单接口验证但仍为 `enabled=false`。
- `product_page` 文档路径：`POST /purchase/goods/product/page`。
- `product_page` 单接口完整验证批次：`sync_20260703_004233_884329`，请求 83 次，写入 8258 条，`item_count=total_count=8258`。
- `product_page.page.max_pages` 已调整为 100，避免当前总量被截断。
- `parent_product_page` 文档路径：`POST /purchase/goods/parentProduct/page`。
- `parent_product_page` 单接口验证批次：`sync_20260703_004505_706770`，请求 3 次，写入 124 条，`item_count=total_count=124`。
- `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs` 已同步配置数 14；数据库中两个新接口 `enabled=0`。
- `config/jijia_api_catalog.generated.json` 已刷新，公开文档 API 仍为 185 个，当前真实配置 API 为 12 个，enabled 为 10 个。

建议目标：

1. 将 `product_page.enabled` 和 `parent_product_page.enabled` 从 `false` 改为 `true`。
2. 运行 `.\\.venv\\Scripts\\python.exe -m app.main`，确认 enabled API 变为 12 个。
3. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`。
4. 查询数据库确认 12 个 API 同批次成功，`product_page` 未截断。
5. 运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
6. 查询 `api_config.product_page.enabled=1` 和 `api_config.parent_product_page.enabled=1`。

验收：

1. dry-run 显示 enabled API 为 12 个。
2. `--sync-enabled` 成功同步 12 个 API。
3. `product_page` 在 enabled 批次中 `item_count=total_count`。
4. 数据库 `api_config.product_page.enabled=1`、`api_config.parent_product_page.enabled=1`。
5. `.\\.venv\\Scripts\\python.exe -m compileall app tests` 通过。
6. `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 通过。
7. 不提交 `.env`、token 缓存、日志或任何敏感信息。

完成 4N 后，目标模式已完成三轮子目标：4L、4M、4N。下一阶段应做一次全面复盘。
