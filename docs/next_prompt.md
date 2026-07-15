# Next Codex Prompt

请继续 `D:\DataProject\coedx_project\jijia-polardb-sync` 项目。

开始前先阅读：
1. AGENTS.md
2. README.md
3. docs/progress.md
4. docs/decisions.md
5. config/api_config.example.yaml
6. config/jijia_api_catalog.generated.json

注意：
- 不要重建项目，不要回退现有未提交修改，不要直接提交。
- 不要读取或输出 `.env`、token 缓存、真实 API 凭证、数据库密码或 accessToken。
- 先只读核对 Git、YAML、catalog、DB `api_config`、latest batch、named lock、InnoDB 事务和同步进程。
- 不要直接重跑完整 `--sync-enabled`；15M 已有 46/46 success 的最终批次证明。

## 当前状态

- 最新提交：`9bcd0a9 Use autocommit for sync task lock`。
- 当前分支基线为 `master...origin/master [ahead 82]`，有未提交修改。
- `storage_inbound_detail` 已在 YAML 和 DB 中启用；YAML/DB 为 59 个配置、enabled 46，catalog 为公开文档 API 187、真实配置 API 51、configured enabled 46、configured disabled 5。
- 销售表现 7 个拆分配置仍全部 disabled。
- 15M 已完成，但当前修改仍未提交；先复核范围并等待用户决定是否提交。

## 15M 最终事实

- CLI 顶层异常和 named lock 释放异常已用 TDD 改为记录异常类型、message 和 traceback。
- 四个日期窗口接口的 `page.max_pages` 已统一为 20；`traffic_sku_page.rate_limit.sleep_seconds` 已按 90008 调用次数超限根因从 0.5 调整为 65。
- `traffic_sku_page` 单接口批次 `sync_20260714_112649_287490` 成功：1990/1990、10 请求、0 失败，checkpoint 推进到 `2026-07-08`。
- 最终完整 enabled 批次 `sync_20260714_113841_049234` 成功：
  - `status=success`
  - `total_api_count=46`
  - `success_api_count=46`
  - `failed_api_count=0`
  - 5645 次请求、568730 条成功计数、失败计数 0
  - 运行 9605 秒
- 最终批次中四个修复接口全部 `item_count == total_count`：`traffic_page=3655/3655`、`traffic_sku_page=1980/1980`、`storage_ledger_page=5052/5052`、`inventory_receipts_page=688/688`，checkpoint 均推进到 `2026-07-09`。
- `storage_inbound_detail` 在最终批次同步 37/37；累计覆盖 174599/174599、缺口 0。
- DB/YAML 为 59 个配置、enabled 46；catalog 为公开文档 API 187、真实配置 API 51、configured enabled 46、configured disabled 5。
- 定向 12 个测试、完整 95 个 unittest、`compileall app tests`、dry-run 46 API、`git diff --check` 均通过。
- 最终无同步进程残留，named lock 空闲，外部 `information_schema.innodb_trx=0`，`failed_request_log=0`；销售表现仍全部 disabled。

## 下一步

1. 只读复核当前 Git diff、YAML、catalog、DB 59/46、最终批次和锁事务状态。
2. 不要再次运行完整长批次；等待用户决定是否提交 15M 当前未提交变更。
3. 如用户要求提交，先展示变更范围与最终测试证据，再按用户明确指令执行。

## 不要做

- 不要删除或放宽 `item_count == total_count` 的完整性校验。
- 不要直接启用销售表现，不要新增 API。
- 不要在 named lock 或外部事务不为空时启动写任务。

## 销售表现仍不能 enabled

进入 enabled 前必须满足：
- enabled 路径支持 `commit_per_page` 或等价短事务。
- 重跑历史窗口，补齐 7728 条空 `data_date`。
- 评估加入后约 22 分钟的额外单日运行时间。
- 用真实 enabled 批次证明成功。
