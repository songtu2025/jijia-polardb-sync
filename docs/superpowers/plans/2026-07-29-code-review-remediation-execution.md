# Code Review 问题修复执行计划

## 目标

修复 2026-07-29 全面 Code Review 中确认的同步正确性、事务恢复、敏感日志和配置安全问题，同时保持以下边界：

- 不直接运行完整 `--sync-enabled`。
- 不在未确认前修改 PolarDB 表结构或历史数据。
- 不读取或输出真实人员信息、附件 ID、文件链接、API 凭证或数据库密码。
- 不覆盖、清理或回退当前工作区已有改动。
- 不执行 `git reset --hard`、`git checkout --`、提交或推送。
- 每个修复保持最小范围，先写失败测试，再做实现。

## 当前基线

仓库：

```text
D:\DataProject\coedx_project\jijia-polardb-sync
```

2026-07-29 审查时的事实：

- 当前分支为 `master`，领先 `origin/master` 83 个提交。
- 工作区存在大量未提交和未跟踪文件，均视为用户现有成果，必须保留。
- YAML 共 79 个配置，其中 46 个 enabled。
- catalog 有 187 个公开接口详情、71 个已配置路径、0 个详情错误。
- 项目 `.venv` 中 140 个 unittest 全部通过。
- `compileall app tests` 通过。
- 项目 `.venv` 中 `pip check` 通过。
- 审查未调用真实积加 API，也未写入 PolarDB。

开始前按顺序读取：

1. `AGENTS.md`
2. `README.md`
3. `docs/progress.md`
4. `docs/decisions.md`
5. `docs/next_prompt.md`
6. 本文件
7. `config/api_config.example.yaml`
8. `config/jijia_api_catalog.generated.json`

## 已确认问题

### P1：`max_pages` 截断会被记为成功

位置：

- `app/sync_engine.py:1012-1056`
- `app/sync_engine.py:1232-1252`

已复现：

```text
total=101
page_size=20
max_pages=5
实际读取=100
当前结果=accepted
```

当前完整性检查只对 `date_window` 生效。非日期窗口接口达到 `max_pages` 后仍会更新 checkpoint 并记录成功。

### P1：缺失可选主键会变成字符串 `None`

位置：

- `app/sync_engine.py:835-850`

当前代码：

```python
item_primary_key = str(item.get(primary_key_field))
```

两条没有 `id` 的数据会得到相同的 `source_primary_key="None"`，随后受唯一索引影响发生覆盖。

### P1：更新 raw JSON 时不更新 `data_hash`

位置：

- `app/sync_engine.py:853-873`
- `sql/init_tables.sql:55-70`

当前 upsert 更新 `raw_json`，但没有同步更新 `data_hash`。这会破坏 `data_hash` 与 `raw_json` 的一致性，并可能让后续哈希唯一键命中错误记录。

### P1：已存在的详情对象不会再次刷新

位置：

- `app/sync_engine.py:1292-1317`
- `app/sync_engine.py:1442-1450`

当前下列 enabled 接口使用 `exclude_existing_target=true`：

- `procure_detail`
- `product_detail`
- `storage_inbound_detail`
- `transfer_detail`
- `lot_no_detail`

当前逻辑只补目标表中完全不存在的主键。已抓取对象后续发生状态或字段变化时，不会再请求详情。

### P1：失效数据库事务中继续写失败日志

位置：

- `app/sync_engine.py:438-508`
- `app/sync_engine.py:690-794`

已用 SQLAlchemy 失效连接复现：

```text
PendingRollbackError:
Can't reconnect until invalid transaction is rolled back.
```

普通接口发生连接失效后，异常分支仍使用同一个事务写 `sync_api_log`。结果可能是：

- 当前 API 失败日志没有写入；
- 后续 enabled API 不再执行；
- `sync_batch` 长期保持 `running`。

### P2：敏感接口仍保存请求参数

位置：

- `app/sync_engine.py:1665-1712`

`sensitive_response=true` 只隐藏响应正文和错误文本，仍会完整保存 `failed_request_log.request_params`。例如 `file_file_url_query` 失败时会保存附件 ID。

### P2：数据库连接串没有编码凭证

位置：

- `app/config.py:38-48`

数据库密码包含 `@`、`:`、`/` 或 `#` 时，当前字符串拼接会被 SQLAlchemy 当作 URL 结构解析，导致合法凭证无法连接。

### P2：`enabled` 配置为 fail-open

位置：

- `app/config.py:60-76`
- `app/sync_engine.py:191-228`
- `app/sync_engine.py:796-798`

风险：

- 缺少 `enabled` 时默认启用；
- 写成字符串 `"false"` 时，因为字符串非空，也会被当成启用；
- 当前加载器没有校验重复 `api_code`、必需字段或布尔类型。

## 执行顺序

## 阶段 0：只读校准

先执行：

```powershell
git status --short --branch
git diff --check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m pip check
```

验收：

- 记录当前 Git 状态，不清理工作区。
- 140 个现有测试应通过。
- 如果基线已经失败，先记录真实错误，不要带着未知失败开始改代码。

## 阶段 1：只读数据库影响审计

本阶段只允许 `SELECT`，不得执行 `UPDATE`、`DELETE`、`ALTER`、`--sync-api-configs`、`--sync-api` 或 `--sync-enabled`。

### 1.1 检查异常主键

```sql
SELECT
  api_code,
  SUM(source_primary_key = 'None') AS literal_none_count,
  SUM(source_primary_key = '') AS empty_string_count,
  SUM(source_primary_key IS NULL) AS null_count,
  COUNT(*) AS total_count
FROM raw_api_data
GROUP BY api_code
HAVING literal_none_count > 0 OR empty_string_count > 0
ORDER BY literal_none_count DESC, empty_string_count DESC, api_code;
```

只输出 API code 和聚合数量，不输出真实业务主键。

### 1.2 检查长期 running 批次

```sql
SELECT
  sync_batch_no,
  status,
  started_at,
  TIMESTAMPDIFF(MINUTE, started_at, NOW()) AS running_minutes,
  total_api_count,
  success_api_count,
  failed_api_count
FROM sync_batch
WHERE status = 'running'
ORDER BY started_at;
```

此查询发现异常时只记录，不直接修改批次状态。

### 1.3 检查 checkpoint 是否超过分页容量

```sql
SELECT
  checkpoint.api_code,
  CAST(
    JSON_UNQUOTE(JSON_EXTRACT(checkpoint.checkpoint_value, '$.item_count'))
    AS UNSIGNED
  ) AS item_count,
  CAST(
    JSON_UNQUOTE(JSON_EXTRACT(checkpoint.checkpoint_value, '$.total_count'))
    AS UNSIGNED
  ) AS total_count,
  CAST(
    JSON_UNQUOTE(JSON_EXTRACT(api.config_json, '$.page.page_size'))
    AS UNSIGNED
  ) AS page_size,
  CAST(
    JSON_UNQUOTE(JSON_EXTRACT(api.config_json, '$.page.max_pages'))
    AS UNSIGNED
  ) AS max_pages,
  checkpoint.last_sync_batch_no
FROM sync_checkpoint AS checkpoint
JOIN api_config AS api
  ON api.api_code = checkpoint.api_code
WHERE JSON_EXTRACT(api.config_json, '$.page.enabled') = TRUE
  AND JSON_EXTRACT(checkpoint.checkpoint_value, '$.total_count') IS NOT NULL
  AND CAST(
        JSON_UNQUOTE(JSON_EXTRACT(checkpoint.checkpoint_value, '$.total_count'))
        AS UNSIGNED
      )
      >
      CAST(
        JSON_UNQUOTE(JSON_EXTRACT(api.config_json, '$.page.page_size'))
        AS UNSIGNED
      )
      *
      CAST(
        JSON_UNQUOTE(JSON_EXTRACT(api.config_json, '$.page.max_pages'))
        AS UNSIGNED
      )
ORDER BY checkpoint.api_code;
```

### 1.4 检查详情接口新鲜度

```sql
SELECT
  api_code,
  COUNT(*) AS row_count,
  MIN(updated_at) AS oldest_updated_at,
  MAX(updated_at) AS newest_updated_at,
  TIMESTAMPDIFF(DAY, MAX(updated_at), NOW()) AS newest_age_days
FROM raw_api_data
WHERE api_code IN (
  'procure_detail',
  'product_detail',
  'storage_inbound_detail',
  'transfer_detail',
  'lot_no_detail'
)
GROUP BY api_code
ORDER BY api_code;
```

### 1.5 检查 `data_hash` 一致性

不要直接使用 MySQL JSON 文本计算哈希，因为 MySQL JSON 序列化格式可能与 Python 的 `sort_keys=True` 不同。

使用项目 `.venv` 做只读流式检查，只输出每个 API 的聚合数量：

```powershell
@'
import hashlib
import json
from collections import Counter

from sqlalchemy import text

from app.config import load_settings
from app.db import create_db_engine


settings = load_settings()
engine = create_db_engine(settings)
checked = Counter()
mismatched = Counter()

with engine.connect().execution_options(stream_results=True) as connection:
    result = connection.execute(
        text(
            """
            SELECT api_code, raw_json, data_hash
            FROM raw_api_data
            ORDER BY api_code, id
            """
        )
    )
    for row in result.mappings():
        raw_json = row["raw_json"]
        item = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        canonical = json.dumps(
            item,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        api_code = str(row["api_code"])
        checked[api_code] += 1
        if expected != row["data_hash"]:
            mismatched[api_code] += 1

for api_code in sorted(checked):
    print(
        api_code,
        f"checked={checked[api_code]}",
        f"mismatched={mismatched[api_code]}",
    )
'@ | .\.venv\Scripts\python.exe -
```

如果数据量过大，应先按 `api_code` 分批执行，不要一次性加载全部 raw JSON 到内存。

### 阶段 1 验收

输出一份简短审计结论：

- 哪些 API 有 `"None"` 或空主键；
- 是否存在哈希不一致；
- 是否存在分页容量风险；
- 是否存在长期 running 批次；
- 5 个详情接口的新鲜度。

不得修改数据库。根据审计结果决定后续是否需要历史数据修复。

## 阶段 2：修复分页完整性

先增加失败测试：

1. 普通分页接口：`total=101`、容量 100，结果必须失败。
2. `commit_per_page` 接口：相同场景必须失败。
3. 截断时不得更新成功 checkpoint。
4. 完整读取时保持原行为。
5. 官方明确无有效 total 且 `page.enabled=false` 的接口保持兼容。

实现要求：

- 将“分页完整性检查”从 `date_window` 专用逻辑提升为通用分页逻辑。
- 只有配置了有效 `total_field` 时比较完整性。
- `item_count < total_count` 必须记录失败。
- 错误信息保留 `api_code/item_count/total_count/page_size/max_pages`，不得包含响应数据。
- 不修改现有 API 的 `max_pages`，除非只读证据证明具体配置容量不足，并另行确认。

阶段测试：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sync_engine_param_templates -v
.\.venv\Scripts\python.exe -m unittest tests.test_sync_api_commit_per_page -v
```

## 阶段 3：修复失效事务后的失败记录

先增加失败测试：

1. 普通接口 raw 写入抛出 `DBAPIError(connection_invalidated=True)`。
2. 原 API 事务必须回滚。
3. 失败 API log 必须通过新事务写入。
4. enabled 批次必须继续下一个 API。
5. 批次最终状态必须是 `partial_failed` 或 `failed`，不能保持 `running`。
6. 单接口模式也必须完成 batch 收尾。

实现边界：

- 不在失效事务中继续执行 SQL。
- 普通 API 事务退出并回滚后，再使用新的 `engine.begin()` 写失败日志。
- 保留真实 `request_count`；已回滚的 raw 行不得计入成功行数。
- `commit_per_page` 已提交的前置页面可以保留，但 API 整体失败时 checkpoint 不推进。
- 不吞掉第二次失败日志写入异常；顶层日志要保留异常类型和堆栈。

建议重构方向：

- 让“单 API 事务生命周期”由统一的外层方法管理；
- `_sync_api_in_batch()` 只负责单 API 业务步骤；
- DBAPI 失效由事务外层捕获；
- 不复制两套普通 API 与单接口 API 的失败收尾代码。

阶段测试：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sync_enabled_transaction_scope -v
.\.venv\Scripts\python.exe -m unittest tests.test_main_error_logging -v
```

## 阶段 4：修复主键与哈希幂等

本阶段先完成代码和测试设计；涉及 PolarDB 索引的 DDL 必须单独向用户确认。

### 4.1 应用层主键规范

要求：

- 主键值为 `None` 或 `""` 时，`source_primary_key` 写 SQL `NULL`。
- 数值 `0` 是有效主键，不能当成空值。
- `primary_key.required=true` 时仍由响应过滤逻辑拒绝空主键。
- `primary_key.required=false` 时空主键回退到哈希去重。
- 请求参数提供的 `source_primary_key` 使用相同规范。

测试：

- 两条缺少可选主键的数据都写入 `NULL`，不得写 `"None"`。
- 空字符串写入 `NULL`。
- `0` 保留为 `"0"`。
- 必填主键为空的响应继续被过滤。

### 4.2 `data_hash` 一致性

要求：

- 每次更新 `raw_json` 时同步更新 `data_hash`。
- 增加测试证明 `data_hash` 始终等于当前 `raw_json` 的规范化 SHA-256。
- 增加“相同 raw JSON、不同业务主键”的测试，避免哈希唯一键误更新另一个业务对象。

### 4.3 推荐索引模型

当前两个全局唯一索引不能准确表达“有业务主键时按主键去重，无业务主键时按哈希去重”。

推荐 MySQL 8 / PolarDB MySQL 模型：

```sql
ALTER TABLE raw_api_data
  ADD COLUMN dedupe_hash CHAR(64)
    GENERATED ALWAYS AS (
      CASE
        WHEN source_primary_key IS NULL OR source_primary_key = ''
          THEN data_hash
        ELSE NULL
      END
    ) STORED,
  ADD UNIQUE KEY uk_raw_api_dedupe_hash (api_code, dedupe_hash);

ALTER TABLE raw_api_data
  DROP INDEX uk_raw_api_data_hash,
  ADD KEY idx_raw_api_data_hash (api_code, data_hash);
```

语义：

- 有业务主键：由 `api_code + source_primary_key` 唯一。
- 无业务主键：生成 `dedupe_hash=data_hash`，由 `api_code + dedupe_hash` 唯一。
- 不同业务主键即使 raw JSON 相同，也不会因全局 hash 唯一键互相覆盖。

执行 DDL 前必须：

1. 完成阶段 1 审计。
2. 检查 PolarDB MySQL 版本是否支持 stored generated column。
3. 获取 `SHOW CREATE TABLE raw_api_data`。
4. 评估表行数、表大小、DDL 锁和执行窗口。
5. 生成备份或可恢复方案。
6. 向用户展示精确 DDL、影响范围和回滚方案并等待确认。

未获确认时只修改代码和测试，不执行上述 DDL。

## 阶段 5：修复详情对象永久不刷新

此项需要业务策略确认，不能直接猜刷新频率。

先只读确认：

- 各详情接口每次请求成本与限流；
- 目标对象是否存在业务更新时间或终态字段；
- 当前 raw 的最新更新时间；
- 每日新增数量和全量对象数量。

推荐新增可选配置：

```yaml
param_source:
  exclude_existing_target: true
  refresh_after_days: 7
```

期望语义：

- 目标不存在：立即请求。
- 目标存在但 `updated_at` 早于刷新阈值：允许重新请求。
- 目标仍在刷新期内：跳过。
- 未配置 `refresh_after_days`：保持当前只补缺失行为。

不要在没有证据时给 5 个接口统一设置相同天数。应逐个接口提交建议并等待用户确认。

测试至少覆盖：

- 缺失目标被选中；
- 新鲜目标被跳过；
- 过期目标被重新选中；
- 刷新后 `updated_at/raw_json/data_hash/sync_batch_no` 更新；
- limit、排序和缺失扫描不会造成永久跳过。

## 阶段 6：敏感日志、数据库 URL 与配置校验

### 6.1 敏感请求参数

最小策略：

- `sensitive_response=true` 时，`failed_request_log.request_params` 写 `NULL`。
- 保留请求方法、状态码、API code、批次号和重试次数。
- 不保存附件 ID、人员筛选值或其他敏感业务标识。

增加测试：

- `file_file_url_query` 失败时 request params、response body、原始错误均不落库。
- 普通接口仍保留现有失败上下文。

### 6.2 数据库 URL

使用 SQLAlchemy `URL.create()`，不要手工拼接：

```python
from sqlalchemy import URL

URL.create(
    "mysql+pymysql",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    query={"charset": "utf8mb4"},
)
```

测试密码至少包含：

```text
@
:
/
#
空格
```

测试不得输出真实连接串或密码。

### 6.3 API YAML 校验

保持 KISS，只校验当前生产安全必需项：

- `api_code` 必填且唯一；
- `path` 必填；
- `enabled` 必须显式存在且为布尔值；
- `_enabled_apis()` 只接受 `enabled is True`；
- 缺少 `enabled`、字符串 `"false"`、重复 `api_code` 都必须启动失败；
- 允许多个配置共享同一 path，因为销售表现按 `groupByType` 拆分。

## 阶段 7：全量本地验证

完成代码修改后运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --branch
```

无参数 dry-run 会写本地日志；确认允许后再运行：

```powershell
.\.venv\Scripts\python.exe -m app.main
```

本地验收：

- 原有 140 个测试全部通过。
- 每个确认问题都有至少一个回归测试。
- 不读取 `.env` 内容，不输出敏感配置。
- enabled 数仍为 46。
- YAML API code 集合和当前目标一致。
- 不产生真实 API 请求和数据库写入。
- 未修改无关文件。

## 阶段 8：数据库与真实链路确认门

代码验证结束后停止，向用户汇报：

1. 修改文件清单。
2. 新增测试与结果。
3. 阶段 1 审计发现。
4. 是否需要 DDL。
5. 是否需要修复历史 `"None"` 主键或错误哈希。
6. 详情刷新策略的逐接口建议。
7. 下一条拟执行的精确命令。

只有用户再次确认后，才能执行：

- PolarDB DDL；
- 历史数据修复；
- `--sync-api-configs`；
- 单接口真实同步；
- enabled 批次。

如果需要真实验证，固定顺序为：

1. 检查 named lock。
2. 检查外部 InnoDB 事务和同步进程。
3. 执行必要的配置同步。
4. 只运行一个低风险接口。
5. 等命令完全结束。
6. 只读核对 batch、API log、raw、checkpoint、失败日志。
7. 再次检查 named lock 和事务。
8. 不直接运行完整 `--sync-enabled`。

## 完成标准

只有同时满足以下条件，才能认为本次修复完成：

- 非日期窗口分页达到容量上限时不会静默成功。
- 缺失可选主键不再写入 `"None"` 或空字符串。
- `data_hash` 与当前 `raw_json` 保持一致。
- 不同业务主键不会因相同 raw hash 互相覆盖。
- 数据库连接失效时失败日志和批次状态可追踪，后续 API 能按设计继续。
- 敏感失败请求不保存请求参数、响应正文或原始错误。
- 数据库密码包含 URL 保留字符时仍能正常构造连接。
- YAML 配置缺失或错误类型的 `enabled` 不会意外启用接口。
- 详情接口有经过确认的刷新策略，或明确记录为尚未实施的业务决策。
- 全量本地测试、编译、依赖和差异检查通过。
- 未经确认没有执行数据库写入、DDL、真实 API 或完整 enabled 批次。

## 新会话可复制提示词

```text
请在 D:\DataProject\coedx_project\jijia-polardb-sync 继续 Code Review 问题修复。

全程使用中文。先阅读：
1. AGENTS.md
2. README.md
3. docs/progress.md
4. docs/decisions.md
5. docs/next_prompt.md
6. docs/superpowers/plans/2026-07-29-code-review-remediation-execution.md
7. config/api_config.example.yaml
8. config/jijia_api_catalog.generated.json

必须遵守：
- 当前 master 比 origin/master 领先 83 个提交，并有大量未提交/未跟踪成果；全部保留，不 reset、不 checkout、不清理。
- 先按执行文档完成阶段 0 基线校准和阶段 1 只读数据库审计。
- 阶段 1 只允许 SELECT，不请求真实 API，不执行 --sync-api-configs、--sync-api 或 --sync-enabled。
- 不读取或输出真实人员字段、附件 ID、文件链接、API 凭证或数据库密码。
- 代码修复严格按执行文档阶段 2-7 推进，每项先写失败测试，再做最小实现。
- PolarDB DDL、历史数据修复、配置同步和真实 API 验证必须另行向我展示精确方案并等待确认。
- 不直接运行完整 --sync-enabled。
- 不提交、不推送，除非我另行明确授权。

当前已知基线：
- YAML 79 个配置、46 个 enabled。
- catalog 187 个公开接口、71 个已配置路径、0 个详情错误。
- 项目 .venv 中 140 个 unittest、compileall 和 pip check 已通过。

开始后先报告：
1. Git 与测试基线；
2. 阶段 1 聚合审计结果；
3. 你准备首先修复的最小代码范围；
4. 明确说明本阶段不会执行哪些写操作。
```
