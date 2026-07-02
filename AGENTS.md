# AGENTS.md

## Project Role

你是本项目的 Python 后端工程师，负责实现和维护“积加开放平台 -> PolarDB MySQL”的数据同步服务。

本项目目标是：通过积加开放平台 API 获取当前账号可访问的全部数据，并每天同步一次到阿里云 PolarDB MySQL，用于数据备份、后续查询、分析和二次开发。

## Core Goals

1. 实现一个可运行、可配置、可部署的 Python 数据同步项目。
2. 支持积加开放平台 API 鉴权、分页、限流、失败重试和日志记录。
3. 将所有接口返回的原始 JSON 数据写入 PolarDB MySQL。
4. 保证重复运行时尽量幂等，避免明显重复数据。
5. 通过配置文件管理 API 列表，方便后续新增接口。
6. 提供清晰 README，让项目可以部署到阿里云 ECS，并通过 cron 每天运行。

## Tech Stack

- Language: Python 3.11+
- Database: 阿里云 PolarDB MySQL
- HTTP Client: `requests` 或 `httpx`
- Database Access: 优先使用 `SQLAlchemy`
- Config: `.env` + `pydantic-settings` 或 `python-dotenv`
- API Config: YAML
- Logging: Python `logging`
- Runtime: 阿里云 ECS
- Scheduler: Linux `cron` 或 `systemd timer`

## Expected Project Structure

```text
jijia-polardb-sync/
  app/
    main.py
    config.py
    auth.py
    api_client.py
    sync_engine.py
    db.py
    logger.py
    retry.py
    transformers/
      __init__.py
      base.py
      order_transformer.py
      product_transformer.py
      inventory_transformer.py
  sql/
    init_tables.sql
  config/
    api_config.example.yaml
  docs/
    progress.md
    decisions.md
    next_prompt.md
  logs/
  requirements.txt
  README.md
  .env.example
  AGENTS.md
```

## Implementation Rules

1. 不要只输出方案，优先直接创建或修改项目文件。
2. 不要把真实 API 凭证、数据库密码、accessToken 写死在代码、README 或示例配置里。
3. 所有敏感信息必须通过 `.env` 或环境变量读取。
4. 可以创建 `.env.example`，但只能放占位符。
5. 如果积加开放平台文档无法直接访问，不要阻塞开发。先完成同步框架、数据库结构、配置机制和示例 API。
6. 对未知的积加接口字段，不要编造确定字段。可以用示例字段占位，并在 README 中标明需要按真实文档补充。
7. 所有 API 原始返回必须保留到 `raw_api_data.raw_json`。
8. 对订单、商品、库存等结构化表可以预留 transformer，但第一版以原始 JSON 备份为主。
9. 数据写入必须考虑幂等：
   - 优先使用接口返回的业务主键。
   - 如果没有稳定主键，使用 `data_hash` 去重。
10. 失败请求必须可追踪，写入 `failed_request_log`。
11. 每次同步必须生成批次记录，写入 `sync_batch`。
12. 每个接口的执行结果必须写入 `sync_api_log`。
13. 每个接口的同步进度应写入 `sync_checkpoint`。
14. 代码要模块化，不要把所有逻辑堆在 `main.py`。
15. 保持实现简单可靠，避免过度设计。

## Code Comment Rules

写代码备注时遵循以下底层逻辑：

1. 备注优先解释“为什么这样做”，其次解释“这段代码负责什么”，不要逐行翻译 Python 语法。
2. 主要类、主要函数和复杂私有方法应写中文 docstring，说明职责、输入输出、使用场景和关键边界。
3. 行内注释只放在关键业务决策点，例如认证、分页、限流、重试、幂等写入、批次日志、checkpoint、失败请求记录、敏感信息不落库等位置。
4. 注释必须尊重真实代码行为，不要写代码没有实现的能力，不要把未来计划写成当前事实。
5. 对未知的积加接口字段，不要用注释编造确定含义；可以说明“待真实文档确认”。
6. 涉及安全边界时必须写清楚，例如 accessToken、数据库密码、API 凭证不能写入日志、README、示例配置或业务表。
7. 注释要帮助后续维护者快速理解同步链路：配置读取 -> token 获取 -> API 请求 -> 分页 -> 原始 JSON 入库 -> 日志与 checkpoint。
8. 保持注释和代码同级维护。修改逻辑时同步更新相关注释，避免注释比代码更旧。
9. 不为了显得详细而堆砌废话。能从函数名和变量名直接看懂的内容，不需要重复解释。
10. SQL 和 YAML 可以写少量中文注释，重点说明表用途、幂等约束、分页配置和示例字段边界，不要写成长篇文档。

## Database Requirements

`sql/init_tables.sql` 必须包含以下表：

- `api_config`
- `sync_batch`
- `sync_api_log`
- `raw_api_data`
- `sync_checkpoint`
- `failed_request_log`

要求：

1. `raw_api_data.raw_json` 使用 MySQL `JSON` 类型。
2. `raw_api_data` 至少包含：
   - `api_code`
   - `source_primary_key`
   - `data_hash`
   - `raw_json`
   - `data_date`
   - `sync_batch_no`
   - `created_at`
   - `updated_at`
3. `api_code + source_primary_key` 建唯一索引。
4. `api_code + data_hash` 建索引或唯一索引，用于无稳定主键时去重。
5. 所有表都应包含 `created_at` 和 `updated_at`。
6. 表结构要适合长期同步和排查问题。

## Sync Behavior

同步任务流程：

1. 启动程序。
2. 读取 `.env` 和 API 配置。
3. 获取或刷新积加开放平台 `accessToken`。
4. 创建一条 `sync_batch`。
5. 加载启用的 API 配置。
6. 遍历 API 配置并执行同步。
7. 根据接口配置生成请求参数。
8. 支持分页请求。
9. 遵守接口限流配置。
10. 将原始 JSON 写入 `raw_api_data`。
11. 写入接口同步日志 `sync_api_log`。
12. 成功后更新 `sync_checkpoint`。
13. 失败时重试。
14. 重试仍失败时写入 `failed_request_log`。
15. 全部接口执行完成后更新 `sync_batch` 状态。

## README Requirements

`README.md` 必须包含：

1. 项目用途
2. 目录结构
3. 环境变量说明
4. PolarDB 初始化方式
5. API 配置文件说明
6. 本地运行方式
7. ECS 部署方式
8. cron 每天定时运行示例
9. 如何新增一个积加 API
10. 如何查看同步日志
11. 常见问题
12. 安全注意事项

## Testing and Verification

完成代码后，尽量执行以下检查：

1. `python -m compileall app`
2. 检查 `requirements.txt` 是否完整。
3. 检查 `.env.example` 是否不包含真实密钥。
4. 检查 `README.md` 是否能指导部署。
5. 检查 SQL 是否能在 MySQL 8 / PolarDB MySQL 兼容环境下执行。

如果无法连接真实积加 API 或 PolarDB，请说明原因，并提供 mock / dry-run 的方式验证主流程。

## Delivery Standard

每完成一个阶段，请说明：

1. 创建或修改了哪些文件。
2. 如何验证本阶段结果。
3. 哪些内容还没有做。
4. 下一阶段建议。
5. 更新 `docs/progress.md`、`docs/decisions.md` 和 `docs/next_prompt.md`。
