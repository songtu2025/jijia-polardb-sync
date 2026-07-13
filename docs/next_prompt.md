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

阶段 15L 已完成。15L 实施了同步任务互斥锁连接 `AUTOCOMMIT` 最小改造，并完成 15J-15L 三轮复盘。本阶段没有启用任何 API，没有修改 YAML，也没有同步 DB enabled 状态。

当前事实：

- 当前最新提交应为阶段 15L 提交；开始前请核对 `git status --short --branch` 和 `git log -1 --oneline`。
- 当前 enabled API 有 45 个，catalog summary 当前口径为公开文档 API 187 个、真实配置 API 51 个、enabled API 45 个、configured disabled 6 个。
- YAML 共 59 个 `api_code`，真实配置 57 个、enabled 45 个、disabled 12 个；DB `api_config` disabled 为 14 条，因为还包含 7 个销售表现拆分配置和 2 个占位示例 `order_list`、`product_list`。
- 同步任务互斥已有 MySQL named lock `jijia_polardb_sync_task`，覆盖 `--mock-sync`、`--sync-api-configs`、`--sync-enabled`、`--sync-api`、`--test-api`；15L 已将锁专用连接改为 `engine.connect().execution_options(isolation_level="AUTOCOMMIT")`。
- 15L 锁测试已覆盖拿不到锁退出、异常释放、释放失败不掩盖任务成功、以及锁连接 AUTOCOMMIT；真实 DB 锁烟测显示持锁期间锁非空闲、释放后锁空闲，外部 `information_schema.innodb_trx=0`。
- `storage_inbound_detail` 当前配置仍为 `enabled=false`、`param_source.limit=2000`、`auto_advance=true`、`exclude_existing_target=true`，累计覆盖为 174334/174334 个上游去重 code；最新空缺口批次 `sync_20260712_191559_497680` 为 0 请求、0 写入、0 失败。
- `storage_inbound_detail` 是最接近 enabled 的候选；15I 已只读确认 `--sync-enabled` 会复用同一套 `param_source` / `exclude_existing_target=true` 缺口扫描逻辑，YAML 顺序保证 `storage_inbound_page` 先于详情接口执行，当前同口径缺口为 0。
- catalog 中 6 个 configured disabled 真实文档接口为：`market_inventory_query`、`storage_inbound_detail`、`delivery_fee_query`、`inventory_event_page`、`inventory_age_page` 和销售表现 `/operation/sts/salesAnalysis/page`。
- `delivery_fee_query` 当前 OROutbound 发货单参数约 142288 个，目标覆盖 0；最新验证为 3 请求、0 成功、0 失败。该接口属于费用类查询，进入生产级调度前需要更小窗口和风险确认。
- `market_inventory_query` 当前库存参数对约 111307 个，当前 raw 4 条但主键均为空、`data_date` 均为空；进入生产级调度前需要先确定稳定主键或幂等口径。
- `inventory_event_page` 当前小样本 raw 300 条，历史估算总量约 2669068 条、约 26691 页；`inventory_age_page` 当前小样本 raw 30 条，历史估算总量约 6597161 条，当前每页 10 且响应慢，并有 1 条失败日志。二者继续 disabled。
- 销售表现 7 个配置均为 `enabled=false`、`commit_per_page=true`、`write_batch_size=10`、`data_date_param=beginDate`、`rate_limit.sleep_seconds=20`、`retry.retries=1`。
- 销售表现真实响应里 `dateLine` 字段存在但值为 JSON `null`；后续不要再依赖 `dateLine` 作为 `raw_api_data.data_date` 来源。
- 15J DB 只读核验显示销售表现 raw 空 `data_date` 合计仍为 7728 条，其中 `sales_analysis_seller_sku_page=2673`、`sales_analysis_asin_page=2651`、`sales_analysis_sku_page=2097`、`sales_analysis_variation_asin_page=217`、`sales_analysis_market_page=44`、`sales_analysis_spu_page=32`、`sales_analysis_country_page=14`。
- 15J 最新销售表现单接口日志合计 43 次请求、7600 条成功、0 失败、1323 秒，约 22 分钟；这不是 enabled 批次证明。
- dry-run 仍显示 45 个 enabled API；15L 终态 DB named lock 空闲且外部 `information_schema.innodb_trx=0`。

建议目标：

- 阶段 15M 建议在明确确认后实施 `storage_inbound_detail` enabled 最小变更，并作为下一组三轮的第 1 轮。
- 最小范围：更新测试期望、将 `storage_inbound_detail.enabled` 改为 `true`、同步 DB `api_config`、dry-run 验证 46 个 enabled、运行真实 enabled 批次证明成功、做 DB 复核。
- 如果启用 `storage_inbound_detail`，必须证明 `exclude_existing_target=true` 生效、不会重复拉取全量历史、不会漏扫新增来源参数、失败日志为 0，并记录累计覆盖。
- 不要直接把销售表现加入 enabled；必须先满足：enabled 路径支持 `commit_per_page` 或等价短事务、重跑历史窗口补齐 7728 条空 `data_date`、评估约 22 分钟额外单日运行时间、用真实 enabled 批次证明成功。
- `delivery_fee_query`、`market_inventory_query`、`inventory_event_page`、`inventory_age_page` 和销售表现继续保持只读观察，不要直接 enabled。

验收：

- 新接口、完整窗口、空缺口或 enabled 评估必须由公开文档、覆盖矩阵、真实请求、数据库只读查询或测试证明，不靠猜测字段。
- 如启用接口，必须证明 `api_config.enabled=1`、dry-run enabled 数量变化正确，并用真实同步批次证明成功。
- 如启用 `storage_inbound_detail`，必须证明 `exclude_existing_target=true` 生效、不会重复拉取全量历史、失败日志为 0，并记录累计覆盖；当前覆盖基线是 174334/174334。
- `api_config` 与覆盖矩阵显示真实配置 API 或 enabled 数量符合本轮目标；当前基线是真实配置 API 51 个、enabled 45 个、configured disabled 6 个。
- `compileall`、锁测试和 `unittest discover` 通过。
- DB named lock 空闲，外部 `information_schema.innodb_trx=0`。
- 继续保持 `.env`、token 缓存、日志和真实凭证不提交。
