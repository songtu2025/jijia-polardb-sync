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

阶段 4L 已完成。下一阶段 4M 从覆盖矩阵中的未配置直接读取候选里接入下一批低风险接口。

当前事实：

- 当前 enabled API 有 10 个：`amazon_shop_page`、`org_manage_query`、`role_list`、`dictionary_query`、`rate_page`、`continent_country_tree`、`ship_transport_list`、`country_tree`、`category_page`、`brand_page`。
- `config/jijia_api_catalog.generated.json` 是公开文档覆盖矩阵。
- 公开文档 API 共 185 个，详情拉取成功 185 个，失败 0 个。
- 当前分类结果：`direct_read_candidate=58`、`requires_upstream_params=79`、`sensitive_review=23`、`write_or_mutation=24`、`unsupported_shape_review=1`。
- 覆盖矩阵是公开文档视角，不等同于当前账号真实授权可调用结果；真实可访问性仍以 `--sync-api` 单接口验证为准。
- 第一批未配置直接读取候选包括：
  - `doc_id=53` `/purchase/goods/product/page` 查询产品列表
  - `doc_id=1921` `/purchase/goods/amazonMsku/page` 查询SKU关联亚马逊MSKU
  - `doc_id=1956` `/purchase/goods/kbProduct/page` 查询捆绑产品列表
  - `doc_id=4835` `/purchase/goods/parentProduct/page` 查询父产品信息

建议目标：

1. 先逐个只读查看上述候选的公开文档详情。
2. 为 1-2 个低风险接口新增 YAML 配置，默认 `enabled: false`。
3. 运行 dry-run，确认 enabled API 仍为 10 个。
4. 逐个运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api <api_code>`。
5. 查询数据库确认单接口批次、API 日志、raw 写入和 checkpoint。
6. 单接口验证通过后，再决定下一轮是否加入 enabled 批量同步。

验收：

1. 新增配置与公开文档路径、方法、分页、主键字段一致。
2. 新增接口默认不进入 `--sync-enabled`。
3. 单接口真实同步成功并可查库验证。
4. `.\\.venv\\Scripts\\python.exe -m compileall app tests` 通过。
5. `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_*.py"` 通过。
6. 不提交 `.env`、token 缓存、日志或任何敏感信息。
