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
- 开发过程中继续调用 superpowers 插件。

当前阶段：

阶段 15J 已完成。销售表现 `/operation/sts/salesAnalysis/page` 的 enabled 前置条件已重新只读复核：7 个拆分配置仍全部 disabled，`commit_per_page=true` 仍只覆盖 `--sync-api` 单接口路径，历史空 `data_date` 仍为 7728 条，最新单接口验证合计约 1323 秒，尚无真实 enabled 批次证明。本阶段没有启用销售表现，也没有启用 `storage_inbound_detail`。

当前事实：

- 当前最新提交应为阶段 15J 文档提交；开始前请核对 `git status --short --branch` 和 `git log -1 --oneline`。
- 当前 enabled API 有 45 个，catalog summary 当前口径为公开文档 API 187 个、真实配置 API 51 个、enabled API 45 个、configured disabled 6 个。
- 当前 DB `api_config` 共 59 条；销售表现同一个文档接口被拆成 7 个 `api_code`。
- `storage_inbound_detail` 当前配置为 `enabled=false`、`param_source.limit=2000`、`auto_advance=true`、`exclude_existing_target=true`，累计覆盖为 174334/174334 个上游去重 code。
- 15G 批次 `sync_20260712_185853_014941` 成功补齐最后 828 个详情：828 请求、828 成功、0 失败；15H 批次 `sync_20260712_191559_497680` 成功验证空缺口：0 请求、0 写入、0 失败。
- 15I 只读确认 `storage_inbound_detail` enabled 主链路边界：`--sync-enabled` 会复用同一套 `param_source` / `exclude_existing_target=true` 缺口扫描逻辑，YAML 顺序保证 `storage_inbound_page` 先于详情接口执行，当前同口径缺口为 0。
- 15G-15I 三轮复盘已完成：`storage_inbound_detail` 已覆盖 174334/174334，空缺口验证和 enabled 边界只读评估均通过，但尚未启用。
- 15F 曾两次出现 `app.main --sync-api storage_inbound_detail` 通用失败并提示 `release sync task lock failed`；当时未生成可见新批次、覆盖未推进、失败日志为 0，但分别留下 Sleep InnoDB 事务 `5635742` 和 `5637222`，已清理。15G/15H 官方 CLI 均正常返回 0，暂未复现。
- 同步任务互斥已有 MySQL named lock `jijia_polardb_sync_task`，覆盖 `--mock-sync`、`--sync-api-configs`、`--sync-enabled`、`--sync-api`、`--test-api`；现有测试 `tests.test_main_sync_lock` 覆盖拿不到锁退出、异常释放、释放失败不掩盖任务成功和写入口判断。建议下一步加 `AUTOCOMMIT` 到锁专用连接，避免锁连接隐式事务。
- 销售表现 7 个配置均为 `enabled=false`、`commit_per_page=true`、`write_batch_size=10`、`data_date_param=beginDate`、`rate_limit.sleep_seconds=20`、`retry.retries=1`。
- 销售表现真实响应里 `dateLine` 字段存在但值为 JSON `null`；后续不要再依赖 `dateLine` 作为 `raw_api_data.data_date` 来源。
- 15J DB 只读核验显示销售表现 raw 空 `data_date` 合计仍为 7728 条，其中 `sales_analysis_seller_sku_page=2673`、`sales_analysis_asin_page=2651`、`sales_analysis_sku_page=2097`、`sales_analysis_variation_asin_page=217`、`sales_analysis_market_page=44`、`sales_analysis_spu_page=32`、`sales_analysis_country_page=14`。
- 15J 最新销售表现单接口日志合计 43 次请求、7600 条成功、0 失败、1323 秒，约 22 分钟；这不是 enabled 批次证明。
- dry-run 仍显示 45 个 enabled API；DB named lock 空闲且外部 `information_schema.innodb_trx=0`。

建议目标：

- 15K 优先执行一个已确认的最小实施项。当前两个候选：
  - 同步任务互斥锁连接加 `AUTOCOMMIT`：改 `app/main.py` 的 `_sync_task_lock()`，让 `engine.connect().execution_options(isolation_level="AUTOCOMMIT")` 成为锁专用连接；补 `tests/test_main_sync_lock.py` 断言；运行锁测试、dry-run、compileall、unittest、diff-check 和 DB 锁/事务复核。
  - `storage_inbound_detail` enabled 最小实施：更新测试期望、将 `storage_inbound_detail.enabled` 改为 `true`、同步 `api_config`、dry-run 验证 46 个 enabled、运行真实批次证明成功、做 DB 复核。
- 如果没有明确确认，不要直接改代码或 YAML。
- 不要直接把销售表现加入 enabled；必须先满足：enabled 路径支持 `commit_per_page` 或等价短事务、重跑历史窗口补齐 7728 条空 `data_date`、评估约 22 分钟额外单日运行时间、用真实 enabled 批次证明成功。
- 继续只读关注其他 configured disabled API：`market_inventory_query`、`delivery_fee_query`、`inventory_event_page`、`inventory_age_page`。
- 不要直接启用超大接口：`inventory_event_page` 当前约 2669068 条，`inventory_age_page` 当前约 6597161 条且响应慢。

验收：

- 新接口、完整窗口、空缺口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如启用 `storage_inbound_detail`，必须证明 `exclude_existing_target=true` 生效、不会重复拉取全量历史、失败日志为 0，并记录累计覆盖；当前覆盖基线是 174334/174334。
- 如调整互斥锁，必须证明写入口仍受 named lock 保护，拿不到锁会退出，异常路径释放锁，锁连接不留下外部 InnoDB 事务。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 51 个、enabled 45 个、configured disabled 6 个。
- `compileall` 和 `unittest discover` 通过。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
