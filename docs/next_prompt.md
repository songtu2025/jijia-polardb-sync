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

阶段 3N：调研第三个真实业务 API 候选。

建议目标：

1. 阅读现有 `config/api_config.example.yaml`、`docs/progress.md`、`docs/decisions.md`。
2. 先向用户说明 3N 的小方案并获得确认。
3. 从积加开放平台文档中选择第三个低风险业务 API 候选。
4. 先只做文档调研和候选选择。
5. 明确接口路径、请求体、分页字段、列表字段、总数字段、主键字段和日期字段。
6. 如果新增 YAML 配置，默认 `enabled: false`。
7. 不直接加入 `--sync-enabled`。

验收：

1. `python -m compileall app` 通过。
2. dry-run 和 mock-sync 仍然可用。
3. `--test-token` 仍然可用且不输出 token。
4. `--test-api amazon_shop_page` 仍可分页请求并写入日志。
5. `--sync-api amazon_shop_page` 仍可完成真实单接口同步。
6. `--sync-enabled` 仍可完成 enabled API 同步。
7. 若新增第三个 API 配置，必须默认 `enabled: false`。
8. 不输出任何真实凭证或 accessToken。

当前阶段 3M 已完成内容：

- `python -m app.main` 保持 dry-run。
- `python -m app.main --mock-sync` 可写入 mock 数据。
- `python -m app.main --test-token` 已实测成功。
- 已从文档 `id=153` 读取“查询亚马逊店铺信息”接口。
- 已新增 `amazon_shop_page` API 配置。
- 已实现 `JijiaApiClient.request()`。
- 已新增 `python -m app.main --test-api amazon_shop_page`。
- 已实现单个业务 API 测试落库：写入 `sync_batch`、`sync_api_log`、`raw_api_data`。
- 当前只请求第一页，`pagesize=20`，不做全量分页循环。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall -f app` 并通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main` 并通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --help` 并看到 `--test-api TEST_API`。
- 已在用户确认后运行 `.\\.venv\\Scripts\\python.exe -m app.main --test-api amazon_shop_page`。
- 真实业务 API 执行成功，批次号 `sync_20260702_141413_745961`，写入 7 条 `amazon_shop_page` 原始记录。
- 已查询数据库确认：
  - `sync_batch.status=success`
  - `sync_api_log.status=success`
  - `sync_api_log.success_count=7`
  - `raw_api_data` 本批次写入 7 条
- 验证时没有输出 accessToken，也没有输出完整业务 `raw_json`。
- `JijiaApiClient.request()` 已支持单次请求参数覆盖，用于分页。
- `amazon_shop_page` 配置已新增 `page.max_pages=5`。
- `SyncEngine.test_api_once()` 已按 `data.total` 做最小分页循环。
- 成功后已 upsert `sync_checkpoint`。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --test-api amazon_shop_page`。
- 阶段 3E 真实业务 API 执行成功，批次号 `sync_20260702_163706_146056`。
- 本次 `sync_api_log.request_count=2`，`success_count=13`，`failed_count=0`。
- `sync_checkpoint.last_sync_batch_no=sync_20260702_163706_146056`。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall -f app` 并通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main` 并通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --mock-sync` 并通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --test-token` 并通过，且没有输出 token。
- `amazon_shop_page` 配置已新增 `retry.retries=3`、`retry.delay_seconds=1`。
- 真实 API 分页请求已通过 `retry_call()` 做最小重试。
- 重试失败时已写入 `failed_request_log`。
- 正常真实 API 验证成功，批次号 `sync_20260702_170155_676007`，请求 2 页，写入 13 条。
- 临时错误路径验证成功，失败批次号 `sync_20260702_170231_079008`。
- 失败批次 `sync_api_log.request_count=2`，`failed_request_log.retry_count=1`。
- 已确认失败日志 `request_params` 不包含 `accessToken`。
- 已新增 CLI 参数 `--sync-api`。
- `--sync-api` 复用当前单接口同步链路，包括分页、`sync_checkpoint`、重试和失败日志。
- `--test-api` 保留为开发调试兼容入口。
- README 已补充 `--sync-api amazon_shop_page` 的本地运行、ECS 和 cron 示例。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api amazon_shop_page`。
- `--sync-api` 验证成功，批次号 `sync_20260702_170601_361540`，请求 2 页，写入 13 条。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --test-api amazon_shop_page`。
- `--test-api` 兼容验证成功，批次号 `sync_20260702_170650_348326`，请求 2 页，写入 13 条。
- 已给当前新增关键代码补充中文备注，说明分页参数覆盖、失败上下文脱敏、真实请求次数统计、`max_pages` 保护、重试计数、checkpoint 摘要和失败请求落库边界。
- 已明确批次边界：一个 `sync_batch` 表示一次调度运行，多接口同步时所有 enabled API 共用同一个批次。
- 已整理 YAML 启用状态：`order_list` 和 `product_list` 禁用，`amazon_shop_page` 启用。
- 已新增 CLI 参数 `--sync-enabled`。
- `--sync-enabled` 会读取 YAML 中 `enabled: true` 的接口，在同一个批次下逐个写入 `sync_api_log`。
- 当前第一版 enabled 同步仍只跑 `amazon_shop_page`，没有新增第二个业务接口。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`。
- `--sync-enabled` 验证成功，批次号 `sync_20260702_171221_307284`，`total_api_count=1`，请求 2 页，写入 13 条。
- README 已补充 `--sync-enabled` 本地运行、ECS 和 cron 示例。
- 已从积加开放平台文档 `id=66` 调研“获取本位币币种”，确认其响应 `data` 是单个字符串，不适合当前列表型 raw item 同步模型，暂不接入。
- 已从积加开放平台文档 `id=2537` 调研“查询部门列表”。
- 已选择“查询部门列表”作为第二个低风险业务 API 候选。
- 已确认文档路径为 `POST /middle/base/orgManage/query`，实际请求路径将是 `/api/open/middle/base/orgManage/query`。
- 已确认请求头需要 `accessToken`。
- 已确认请求体字段：`startTime`、`endTime`、`status`、`condition`，均可选。
- 已确认响应列表字段为 `data`，无分页字段。
- 已确认候选主键字段为 `id`，候选日期字段为 `createdTime`。
- 已新增 `org_manage_query` YAML 配置，默认 `enabled: false`。
- 已运行 `.\\.venv\\Scripts\\python.exe -m compileall app` 并通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main`，dry-run 仍只显示 `amazon_shop_page` 一个 enabled API。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`，仍只同步 `amazon_shop_page`。
- 未执行 `org_manage_query` 真实 API，避免在未确认前扩大真实同步范围。
- 已在保持 `org_manage_query.enabled=false` 的前提下执行单接口验证。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api org_manage_query`。
- 验证成功，批次号 `sync_20260702_173136_319602`，请求 1 次，写入 1 条。
- `sync_batch.status=success`，`success_api_count=1`，`failed_api_count=0`。
- `sync_api_log.status=success`，`request_count=1`，`success_count=1`，`failed_count=0`。
- `raw_api_data.source_primary_key` 已从 `id` 写入。
- `raw_api_data.data_date` 已从 `createdTime` 提取日期写入。
- `sync_checkpoint` 已写入 `org_manage_query` 的分页摘要。
- 已再次运行 `--sync-enabled`，确认仍只同步 `amazon_shop_page`，没有执行 `org_manage_query`。
- 已将 `org_manage_query.enabled` 从 `false` 改为 `true`。
- 未新增第三个 API。
- dry-run 已确认 enabled API 变为 2 个：`amazon_shop_page`、`org_manage_query`。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-enabled`。
- 验证成功，批次号 `sync_20260702_174830_926688`，`apis=2`，`rows=14`，`requests=3`。
- 数据库确认该批次 `total_api_count=2`、`success_api_count=2`、`failed_api_count=0`。
- 同一批次下有两条 `sync_api_log`：`amazon_shop_page` 成功写入 13 条，`org_manage_query` 成功写入 1 条。
- 两个 API 的 `sync_checkpoint.last_sync_batch_no` 均已更新到该批次。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --test-token` 并通过，且没有输出 token。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --mock-sync` 并通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api amazon_shop_page` 并通过。
- 已运行 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api org_manage_query` 并通过。
- 已新增 `JIJIA_TOKEN_CACHE_PATH` 配置，默认 `logs/token_cache.json`。
- `JijiaAuthClient.get_access_token()` 已先读取本地 token 缓存，缓存不存在或快过期时才请求 `/api/open/api_token`。
- token 缓存提前 60 秒视为过期。
- `logs/token_cache.json` 已加入 `.gitignore`。
- README 已说明 token 缓存路径、安全边界和当前 enabled API。
- 已连续运行两次 `--test-token`，第二次命中缓存且未输出 accessToken。
- 已运行 `--sync-enabled`，确认 token 缓存不影响真实同步。
- 阶段 3L 验证批次号为 `sync_20260702_175624_199936`，`--sync-enabled` 仍成功同步 2 个 enabled API。
- 已新增 CLI 参数 `--sync-api-configs`。
- 已新增 `SyncEngine.sync_api_configs()`，将 YAML API 配置 upsert 到 `api_config` 表。
- 写入字段包括 `api_code`、`api_name`、`enabled`、`method`、`path`、`config_json`。
- 已连续运行两次 `.\\.venv\\Scripts\\python.exe -m app.main --sync-api-configs`。
- 每次均同步 4 条配置，重复运行没有重复插入。
- 数据库确认 `api_config` 总数为 4，启用数为 2。
- `amazon_shop_page` 和 `org_manage_query` 为启用状态。
- `order_list` 和 `product_list` 为禁用状态。
- 本阶段未新增第三个业务 API，也未请求真实业务接口。
