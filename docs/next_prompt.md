# Next Codex Prompt

请继续 `D:\DataProject\coedx_project\jijia-polardb-sync` 项目。统计板块 17 个文档 API 已全部接入并完成真实单接口验证；接下来主线是继续推进全平台尚未配置的只读接口，不要把“统计板块完成”误写成“积加全部接口完成”。

开始前先阅读：
1. AGENTS.md
2. README.md
3. docs/progress.md
4. docs/decisions.md
5. docs/next_prompt.md
6. config/api_config.example.yaml
7. config/jijia_api_catalog.generated.json

注意：
- 不要重建项目，不要回退现有未提交修改，不要直接提交。
- 不要读取或输出 `.env`、token 缓存、真实 API 凭证、数据库密码或 accessToken。
- 先只读核对 Git、YAML、catalog、DB `api_config`、latest batch、named lock、InnoDB 事务和同步进程。
- 不要直接运行完整 `--sync-enabled`；15M 已有 46/46 success 的最终批次证明，16N 没有改变 enabled 数量。
- 新接口仍按 `default-disabled -> --sync-api-configs -> --sync-api -> DB/锁事务审核 -> 文档交接` 单个推进；不要批量新增或直接 enabled。

## 当前状态

- 最新已提交基线：`51a6484 Complete storage inbound detail enabled validation`；16A-16R 修改保持未提交。
- DB/YAML 为 73 个配置、enabled 46；catalog 为公开文档 API 187、真实配置 API 65、configured enabled 46、configured disabled 19。
- 统计板块共有 17 个文档接口，17 个均已配置并完成真实验证：
  - enabled：`traffic_page`、`traffic_sku_page`、`traffic_analysis_page`
  - disabled：`traffic_sku_analysis_page`、`product_analyze_multi_index_page`、`store_sales_performance_page`、`market_analyze_page`、`listing_analyze_page`、`listing_analyze_multi_index_page`、`sale_profit_page`、`allocation_detail_page`、`profit_cost_analysis_page`、`financial_profit_analysis_page`、`financial_analysis_v2_page`、`financial_analysis_columns_query`、`financial_analysis_month_v2_query`、销售表现 `/operation/sts/salesAnalysis/page`（7 个拆分配置）
- 统计菜单缺失文档为 0；3 个 enabled、14 个 disabled。
- 销售表现 7 个拆分配置继续全部 disabled。
- enabled 主链已按 `commit_per_page` 分流；当前 21 个相关配置仍全部 disabled，且没有与 `param_source` 冲突。
- 全平台公开文档 API 共 187 个，已配置真实文档 65 个，尚未配置 122 个。
- 122 个未配置文档中：28 个写入/修改/确认操作和 3 个审核覆盖接口已有终态；其余 91 个分为 `needs_param_source=49`、`needs_sensitive_review=21`、`risk_review_before_probe=19`、`known_risk_review=2`。
- 当前没有可绕过审查直接批量探测的未配置接口。后续必须从 91 个待审候选中逐个选择，并先证明参数来源或风险边界。

## 16A 最终事实

- 新增 `traffic_sku_analysis_page`：`POST /operation/sts/trafficSkuAnalysis/page`，文档 `id=1017`。
- 配置保持 `enabled=false`，使用 `pagesize=100`、`max_pages=20`、`viewType=day`、单日日期窗口、`lag_days=1`、65 秒限流、`commit_per_page=true`。
- 第一次普通长事务尝试遇到 MySQL 2006 / WinError 10054，业务连接和 named lock 连接同时被远端重置；事务完整回滚，未留下候选批次或数据残留。
- `wait_timeout=86400`，本次不是三分钟空闲超时；普通单接口路径把 HTTP、sleep 和多页 raw 写入包在一个事务中，放大了瞬时断链影响。
- 复用已有 `commit_per_page` 单接口短事务路径后，真实批次 `sync_20260715_150626_428012` 成功：
  - `status=success`
  - 19 次请求
  - 1857/1857 条
  - 0 失败
  - 耗时 1263 秒
- raw 为 1857 条、1857 个不同 hash、空主键 1857、空 `data_date` 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=19`、`request_count=19`、`item_count=1857`、`total_count=1857`、`next_window_start=2026-07-03`。
- `failed_request_log=0`；最终 named lock 空闲、外部 `information_schema.innodb_trx=0`、无同步进程残留。
- 16A 当时不能直接 enabled：当时 `commit_per_page` 只在单接口路径生效；该调度缺口已在 16N 补齐，但运行时长和业务风险仍未通过启用评估。

## 16B 最终事实

- 新增 `product_analyze_multi_index_page`：`POST /operation/sts/productAnalyzeMultiIndex/page`，文档 `id=131`。
- 配置保持 `enabled=false`，使用 `showCurrencyType=YUAN`、`pagesize=100`、`max_pages=30`、单日日期窗口、`lag_days=1`、65 秒限流、`commit_per_page=true`。
- 首次批次 `sync_20260715_154048_587898` 在 20 页写入 2000 条后，被完整性校验识别为 `2000/2891` 截断并标记 failed；checkpoint 未前移，失败请求为 0。
- 因官方页大小上限已经是 100，实际 2891 条需要 29 页，TDD 将该接口 `max_pages` 从 20 最小调整到 30，没有放宽完整性校验。
- 成功批次 `sync_20260715_161132_797343`：
  - `status=success`
  - 29 次请求
  - 2891/2891 条
  - 0 失败
  - 耗时 1949 秒
- raw 为 2891 条、2891 个不同 hash、空主键 2891、空 `data_date` 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=29`、`request_count=29`、`item_count=2891`、`total_count=2891`、`next_window_start=2026-07-03`。
- `failed_request_log=0`；最终 named lock 空闲、外部 `information_schema.innodb_trx=0`、无数据库会话残留。
- 候选继续 disabled：16N 已让 enabled 主链复用短事务，但该接口单日验证约 32 分钟，仍需单独评估 cron 成本。

## 16C 最终事实

- 新增 `store_sales_performance_page`：`POST /operation/sts/storeSalesPerformance/page`，文档 `id=132`。
- 配置保持 `enabled=false`，使用 `showCurrencyType=YUAN`、`pagesize=100`、`max_pages=20`、单日日期窗口、`lag_days=1`、65 秒限流、`commit_per_page=true`。
- 文档字段表虽把行 `id`、`statisticsDate` 标为必填，但官方响应示例二者均为 `null`，因此使用 `data_hash` 幂等和请求 `beginDate` 覆盖 `data_date`。
- 成功批次 `sync_20260715_165256_777600`：1 次请求、25/25、0 失败。
- raw 为 25 条、25 个不同 hash、空主键 25、空 `data_date` 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=1`、`request_count=1`、`item_count=25`、`total_count=25`、`next_window_start=2026-07-03`。
- `failed_request_log=0`；最终 named lock 空闲、外部 `information_schema.innodb_trx=0`、无数据库会话残留。
- 16A-16C 三轮复盘已完成：三个新候选均保持 disabled；16B 截断被完整性校验正确拦截。16N 已补齐 enabled 主链短事务分流，但候选仍未完成启用风险评估。

## 16D 最终事实

- 新增 `market_analyze_page`：`POST /operation/sts/marketAnalyze/page`，文档 `id=133`。
- 配置保持 `enabled=false`，使用 `target=unitsOrdered`、`viewType=day`、`showCurrencyType=YUAN`、单日窗口和 `commit_per_page=true`。
- 官方请求体没有 `page/pagesize`，响应说明把 `total/page/pagesize` 标为无效字段；配置因此使用 `page.enabled=false`、`data.rows`，不配置 `total_field`。
- 行没有独立日期，且 `marketId` 不能区分窗口或指标；使用 `data_hash` 幂等和请求 `beginDate` 覆盖 `data_date`。
- 成功批次 `sync_20260715_170801_554088`：1 次请求、25 行、0 失败。
- raw 为 25 条、25 个不同 hash、空主键 25、空 `data_date` 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=1`、`item_count=25`、`total_count=null`、`next_window_start=2026-07-03`；这里不能伪造 25/25。
- `failed_request_log=0`；最终 named lock 空闲、外部 `information_schema.innodb_trx=0`、无数据库会话残留。

## 16E 最终事实

- 新增 `listing_analyze_page`：`POST /operation/sts/listingAnalyze/page`，文档 `id=130`，保持 `enabled=false`，MSKU 维度、单日窗口、`pagesize=100`、`max_pages=45`、65 秒限流、`commit_per_page=true`。
- `sync_20260715_172023_885288` 在 1700 条后遇到 API 连接与 DNS 同时中断；`sync_20260715_182354_185521` 在 4100 条后被 Windows 终端进程结束。两者没有 API log/checkpoint，只在确认锁、事务和进程清理后精确收尾为 failed。
- `sync_20260715_174526_930015` 在 30 页写入 3000 条后被 `3000/4305` 完整性校验正确拦截；TDD 将 `max_pages` 从 30 最小提高到 45，没有放宽完整性校验。
- 成功批次 `sync_20260716_112121_765692`：44 次请求、4309/4309、0 失败；上游总量较前一日增加 4 条。
- raw 为 4309 条、4309 个不同 hash、null 主键 4309、空 `data_date` 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=44`、`request_count=44`、`item_count=4309`、`total_count=4309`、`next_window_start=2026-07-03`；失败请求 0，最终锁、事务、活动会话全清。

## 16F 最终事实

- 新增 `listing_analyze_multi_index_page`：`POST /operation/sts/listingAnalyzeMultiIndex/page`，文档 `id=140`，保持 `enabled=false`。
- 配置使用 MSKU 维度、`isShowTotal=false`、单日窗口、`pagesize=100`、`max_pages=45`、`commit_per_page=true`；官方默认每 5 秒 1 次，因此页间隔为 6 秒。
- TDD 先因配置缺失 RED，再新增唯一候选转 GREEN；完整 101 个测试、`compileall`、无参数 dry-run 通过，enabled 仍为 46。
- 成功批次 `sync_20260716_141834_366978`：44 次请求、4309/4309、0 失败。
- raw 为 4309 条、4309 个不同 hash、null 主键 4309、空 `data_date` 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=44`、`request_count=44`、`item_count=4309`、`total_count=4309`、`next_window_start=2026-07-03`；失败请求 0，最终锁、事务、活动会话全清。
- 16D-16F 三轮复盘已完成：三轮都保持 disabled，16D 如实记录 `total_count=null`，16E/16F 均用同批次总量证明完整，未运行完整 `--sync-enabled`。

## 16G 最终事实

- 新增 `sale_profit_page`：`POST /operation/sts/saleProfit/page`，文档 `id=1016`，保持 `enabled=false`。
- 配置使用低基数 `type=MARKET`、`showCurrencyType=YUAN`、单日窗口、`pagesize=100`、`max_pages=5`、65 秒限流、哈希幂等和 `commit_per_page=true`。
- TDD 先因配置缺失 RED，再新增唯一候选转 GREEN；完整 102 个测试、`compileall`、dry-run 和差异检查通过，enabled 仍为 46。
- 成功批次 `sync_20260716_143418_686778`：1 次请求、24/24、0 失败。
- raw 为 24 条、24 个不同 hash、null 主键 24、空 `data_date` 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=1`、`request_count=1`、`item_count=24`、`total_count=24`、`next_window_start=2026-07-03`；失败请求 0，最终锁、事务、活动会话全清。

## 16H 最终事实

- 新增 `allocation_detail_page`：`GET /finance/sts/allocationDetail/page`，文档 `id=128`，保持 `enabled=false`。
- 配置固定 `marketDate=2026-06`，使用 `pagesize=100`、`max_pages=20`、3 秒限流和 `commit_per_page=true`；固定单月只用于验证，不代表已有自动月份推进。
- `YYYY-MM` 不直接写 MySQL DATE，使用响应 `createTime` 生成 `data_date`；官方 `id` 为主键但 `required=false`，避免异常空 ID 行被丢弃。
- TDD 先因配置缺失 RED，再新增唯一候选转 GREEN；完整 103 个测试、`compileall`、dry-run 和差异检查通过，enabled 仍为 46。
- 成功批次 `sync_20260716_144111_386873`：10 次请求、903/903、0 失败。
- raw 为 903 条、903 个不同主键、903 个不同 hash、空主键 0、空 `data_date` 0，日期均为 `2026-06-01`。
- checkpoint 为 `last_page=10`、`request_count=10`、`item_count=903`、`total_count=903`，没有伪造 `next_window_start`；失败请求 0，最终锁、事务、活动会话全清。

## 16I 最终事实

- 新增 `profit_cost_analysis_page`：`POST /finance/sts/profitCostAnalysis/page`，文档 `id=129`，保持 `enabled=false`。
- 配置使用 `currency=YUAN`、`platformCodes=[AMAZON]`、`costValues=0`、单日窗口、`pagesize=100`、`max_pages=190`、6 秒页间隔和 `commit_per_page=true`。
- 首批 `sync_20260716_144820_882238` 在 20 页后被正确判定为 `2000/18425` 截断；TDD 将 `max_pages` 从 20 最小调整为 190，没有放宽完整性校验。
- 第二批 `sync_20260716_145343_590447` 在第 94 页写库时发生 MySQL 2013，前 93 页 9300 条已提交；checkpoint 未前移，锁和事务最终清理。
- 已用 TDD 为短事务页写入增加一次受限恢复：仅 `DBAPIError.connection_invalidated=true` 时换新连接重试一次，其他数据库错误原样失败；完整 105 项测试通过。
- 批次 `sync_20260716_151848_575655` 在 300 条后被外部结束，没有 API log/checkpoint；确认进程、锁、事务和会话均清理后精确收尾为 failed。
- 最终前台受管批次 `sync_20260717_101830_525973` 成功：185 次请求、18425/18425、0 失败。
- raw 为 18425 条、18425 个唯一官方主键、18425 个唯一 hash、空主键 0、空日期 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=185`、`request_count=185`、`item_count=18425`、`total_count=18425`、`next_window_start=2026-07-03`；失败请求 0，最终锁、事务、活动会话全清。
- 16G-16I 三轮复盘已完成；三个候选继续 disabled，enabled 仍为 46，未运行完整 `--sync-enabled`。

## 16J 最终事实

- 新增 `financial_profit_analysis_page`：`POST /finance/sts/financialProfitAnalysis/page`，文档 `id=309`，保持 `enabled=false`。
- 首批 `sync_20260717_105203_289692` 被完整性校验正确判定为 `5000/20978` 截断；TDD 将 `max_pages` 从 50 最小提高到 220。
- 最终批次 `sync_20260717_105845_443853` 成功：210 次请求、20978/20978、0 失败。
- raw 为 20978 条、20978 个唯一官方主键和 hash、空主键 0、空日期 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=210`、`request_count=210`、`item_count=20978`、`total_count=20978`、`next_window_start=2026-07-03`；失败请求 0，最终锁、事务、活动会话全清。

## 16K 最终事实

- 新增 `financial_analysis_v2_page`：`POST /finance/sts/financialAnalysis/page/V2`，文档 `id=2256`，保持 `enabled=false`。
- 配置使用 MARKET 维度、首次成本口径、单日窗口、哈希幂等和 11 秒限流。
- 批次 `sync_20260717_112436_771393` 成功：1 次请求、23/23、0 失败。
- raw 为 23 条、23 个唯一 hash、空主键 23、空日期 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=1`、`request_count=1`、`item_count=23`、`total_count=23`、`next_window_start=2026-07-03`；失败请求 0，最终锁、事务、活动会话全清。

## 16L 最终事实

- 新增 `financial_analysis_columns_query`：`GET /finance/sts/colData/query`，文档 `id=2280`，保持 `enabled=false`。
- 批次 `sync_20260717_113058_412348` 成功：1 次请求、55 条、0 失败。
- raw 为 55 条、55 个唯一 `colCode` 和 hash、空主键 0、空日期 55。
- checkpoint 为 `last_page=1`、`request_count=1`、`item_count=55`、`total_count=null`；失败请求 0，最终锁、事务、活动会话全清。
- 16J-16L 三轮复盘已完成；三个候选继续 disabled，enabled 仍为 46。

## 16M 最终事实

- 新增 `financial_analysis_month_v2_query`：`POST /finance/sts/financialAnalysisMonth/query/V2`，文档 `id=2284`，保持 `enabled=false`。
- 固定 `2026-06-01` 至 `2026-06-30`，使用 `costValues=0`、`currency=YUAN`、非分页 `response.item_field=data` 整体保存。
- 批次 `sync_20260717_113608_001647` 成功：1 次请求、1 个整体对象、0 失败。
- raw 根对象同时保留月份轴数组和数据树数组；日期为 `2026-06-01`。
- checkpoint 为 `last_page=1`、`request_count=1`、`item_count=1`、`total_count=null`；失败请求 0，最终锁、事务、活动会话全清。

## 16N 最终事实

- enabled 主链现在会识别 `commit_per_page=true`，短事务接口直接复用现有按页事务路径；普通 API 继续保持每个 API 一个事务。
- TDD 混合批次先按预期 RED，最小实现后 GREEN；4 个定向测试、完整 110 个 unittest、`compileall app tests`、YAML 配置加载和差异检查通过。
- YAML 仍为 72/46；20 个 `commit_per_page` 配置全部 disabled，冲突 `param_source` 配置为 0。
- 未修改 DB 配置、未请求真实 API、未运行完整 `--sync-enabled`、未提交。

## 16O 最终事实

- 20 个 `commit_per_page` disabled 配置已完成只读风险分层：低风险 3 个、中风险 7 个、高风险或阻断 10 个。
- 推荐首个启用前候选为 `financial_analysis_v2_page`：1 请求、23/23、自动单日窗口、有效 total、catalog 无敏感响应标签。
- 固定月份接口、19–210 页长任务和存在历史空 `data_date` 的销售表现高基数配置不能直接 enabled。
- 本轮没有修改代码、YAML、DB 或 enabled 数量，也没有刷新历史 DB 状态。

## 16P 最终事实

- 全平台覆盖主线新增 `monthly_statement_amount_query`：`POST /finance/asset/monthlyStatementAmount/query`，文档 `id=113`，保持 `enabled=false`。
- 配置使用 `typeCode=0`、`viewType=day`、`showCurrencyType=YUAN`、单日自动窗口、非分页 `data` 数组、`data_hash` 幂等、请求 `beginDate` 覆盖 `data_date`、1.1 秒限流和 `commit_per_page=true`。
- 批次 `sync_20260717_153412_241025` 成功：1 次请求、5 条、0 失败。
- raw 为 5 条、5 个不同 hash、空主键 5、空日期 0，日期均为 `2026-07-02`。
- checkpoint 为 `last_page=1`、`request_count=1`、`item_count=5`、`total_count=null`、`next_window_start=2026-07-03`；失败请求 0。
- DB/YAML 为 73/46，catalog 为 187/65/46/19；完整 111 个测试、`compileall`、dry-run 和差异检查通过。
- 最终 named lock 空闲、外部事务 0、数据库活动会话 0、同步进程 0；未运行完整 `--sync-enabled`。

## 当前目标完成

- catalog 统计菜单 17/17 均有配置，3 enabled、14 disabled、缺失 0。
- 本轮十三个新增候选最新 checkpoint 均指向 success 批次，API log 与 raw 数量一致，成功批次失败请求均为 0。
- YAML 与 DB 均为 73/46，API code、enabled、method、path 无差异。
- 最新批次为 `sync_20260717_223116_798898`、状态 failed；这是文档 1177 首次请求返回 HTTP 400 的预期保留证据，不代表 enabled 主链失败。
- 下一任务为基础数据阶段 16S 的独立确认门：只处理文档 1179 `/middle/base/warehouseIds/query`；不要同时推进其他接口或统计候选启用。

## 不要做

- 不要删除或放宽 `item_count == total_count` 完整性校验。
- 不要为重复证明重跑 16A-16P 已完成的单接口窗口。
- 不要直接启用十三个新候选或销售表现。
- 不要批量新增多个未验证接口。
- 不要在 named lock 或外部事务不为空时启动写任务。
- 不要为重复证明重跑 15M 完整长批次。

## 16Q 最终事实

- 已新增按板块实施计划文件、`config/api_review_overrides.yaml`、审核终态加载与板块进度汇总测试。
- 文档 596 为 `framework_auth_only`；文档 3095 为 `defer_sensitive_credentials`；文档 61 继续由自动分类保持 `defer_write_or_mutation`。三者均不得执行真实业务同步。
- catalog CLI 已支持 `--review-config`；判断优先级为“已配置 > 审核覆盖 > 自动分类”。
- catalog 为 187 个公开文档、65 个真实配置、46 个 enabled、19 个 configured disabled；审核覆盖后待审总数为 92。
- 基础数据为 `total=16`、`configured=9`、`enabled=9`、`terminal_deferred=3`、`pending_review=4`、`closed=false`。
- 117 个 unittest、`compileall app tests`、无参数 dry-run 和 `git diff --check` 通过；未运行完整 `--sync-enabled`，未修改 DB 配置。

## 16R 最终事实

- 通用参数来源已支持 `wrap_in_list: true`，并把单元素数组请求参数规范化为标量 source primary key；未开启包装的旧接口行为不变。
- 文档 1177 使用 3 个真实上游候选中的第 1 个发起请求，批次 `sync_20260717_223116_798898` 返回 HTTP 400 后立即停止。
- 失败批次和 API log 均 failed，失败日志 1、raw 0、checkpoint 0；没有重试或尝试其他数组编码。
- 文档 1177 已登记为 `defer_runtime_rejected`；临时 YAML/DB 配置已清理，失败证据保留。
- DB/YAML 为 73/46；catalog 为 187/65/46/19。基础数据为 `configured=9`、`terminal_deferred=4`、`pending_review=3`。
- 121 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；未运行完整 `--sync-enabled`。

## 阶段 16S 确认门

- 目标仅为文档 1179：`GET /middle/base/warehouseIds/query`，读取操作。
- 官方必填参数 `marketIdList` 为 `array<int>`，响应 `data` 为对象数组，字段包括 `marketId` 和 `warehouseId`；默认限流每秒 1 次。
- 参数仍来自已证明的 `amazon_shop_page.raw_json.marketListVos[].marketId`，首次最多 3 个，每次使用单元素列表。
- 配置保持 `enabled=false`、非分页、`list_field=data`、1.1 秒间隔；不编造单字段主键，按完整对象 `data_hash` 幂等，`data_date=null`。
- 正常最多 3 次请求，预计数秒；按默认 30 秒超时且不重试计算，上限约 93 秒。
- 确认后先写唯一配置测试，再同步配置和仅运行当前接口；若返回 400/509，登记 `defer_runtime_rejected` 并清理失败候选，不尝试其他编码。
- 开始任何写任务前再次刷新 Git、DB、named lock、InnoDB 事务、数据库会话和同步进程。

## 16S 最终事实

- 文档 1179 使用真实上游 market ID 单元素数组发起小样本请求；未输出任何 ID 值。
- 临时配置保持 disabled、最多 3 个参数、1.1 秒限流、仅 1 次尝试、`data_hash` 幂等和空 `data_date`。
- 批次 `sync_20260718_105341_073837` 第 1 次请求返回 HTTP 400 后立即停止。
- batch/API log 均 failed，失败日志 1、raw 0、checkpoint 0；没有重试或尝试其他数组编码。
- 文档 1179 已登记为 `defer_runtime_rejected`；临时 YAML/DB 配置已清理，失败证据保留。
- DB/YAML 为 73/46；catalog 为 187/65/46/19。基础数据为 `configured=9`、`terminal_deferred=5`、`pending_review=2`。
- 122 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；未运行完整 `--sync-enabled`。
- 最终 named lock 空闲、外部事务、数据库会话和同步进程均为 0。

## 阶段 16T 前置边界

- 下一步只能只读审核文档 25 `GET /middle/base/allUser/list`，先证明读取性质、单次请求、主键、毫秒时间戳日期转换和敏感字段 raw-only 边界，再等待用户独立确认。
- 不要在同一阶段推进文档 694，也不要输出用户姓名、手机号、邮箱、组织或角色字段值。

## 16T 最终事实

- 新增 `all_user_list`：`GET /middle/base/allUser/list`，文档 `id=25`，保持 `enabled=false`、无参数、非分页、主键 `id`、`date_field=createdTime` 和 1.1 秒限流。
- 13 位毫秒时间戳按 `Asia/Shanghai` 转换为 `data_date`，原有 ISO 日期转换不变；`requirements.txt` 已补充 `tzdata>=2024.1`。
- `sensitive_response=true` 只改变失败日志边界：API log 使用通用错误，失败请求不保存响应正文和原始错误；正常成功 raw 仍完整保留，普通接口行为不变。
- 成功批次 `sync_20260720_104305_848823`：1 次请求、35 条、0 失败；35 个不同主键、35 个不同 hash、空主键 0、空日期 0，checkpoint 指向同批次，失败请求 0。
- YAML/DB 为 74/46、code/enabled/method/path 差异 0；catalog 为 187 个公开文档、66 个真实配置、46 个 enabled、20 个 configured disabled。
- 基础数据为 `total=16`、`configured=10`、`enabled=9`、`terminal_deferred=5`、`pending_review=1`、`closed=false`；仅剩文档 694 待审。
- 127 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；最终 named lock 空闲、外部事务、数据库会话和同步进程均为 0。
- 未运行完整 `--sync-enabled`，未暂存、提交或推送；审核和交接没有输出任何真实人员字段值。

## 阶段 16U 下一步边界

- 目标仅为文档 694：`GET /middle/base/fileFileUrl/query`。
- 第一阶段只读统计现有 raw 是否包含语义明确且稳定的附件 ID 字段，不读取或输出附件 ID、文件链接或人员字段值。
- 同时核对公开文档的必填参数、响应形态、读取性质、限流、幂等和日期边界。
- 有真实稳定来源时，单独提交 16U 最小方案并等待确认；没有来源时提出 `defer_no_param_source` 终态方案并等待确认。
- 确认前不新增接口配置、不写审核终态、不请求真实业务接口；不得使用文档示例 ID、猜测字段或硬编码值。

## 16U 只读审核证据（等待确认）

- 文档 694：`GET /middle/base/fileFileUrl/query`，必填 `id:int`，响应 `data:string`，非分页，默认每秒 2 次。
- 现有 raw 中 `attachmentVOList[].id` 来自 `transfer_detail` 的 999 个整数 ID（另有 `procure_detail` 1 个），缺失和空值均为 0；审核未输出 ID 或链接值。
- 建议首轮最多 3 个，参数来源为 `transfer_detail.raw_json.attachmentVOList[].id`，目标字段 `id`；使用请求参数作为 raw 主键，标量响应 `data` 原样保存，`data_date=null`、0.6 秒限流、保持 disabled。
- 这是待用户确认的最小方案；确认后才写唯一配置测试、同步配置并执行当前单接口，未确认前不做任何 16U 写入或真实请求。

## 16U 最终事实

- 文档 694 已接入为 `file_file_url_query`：`GET /middle/base/fileFileUrl/query`，保持 `enabled=false`、非分页、标量 `data` 包装为 `fileUrl`、`data_date=null`、0.6 秒间隔、单次尝试与 `sensitive_response=true`。
- 参数只从 `transfer_detail.raw_json.attachmentVOList[].id` 获取，首轮上限 3、`auto_advance=false`；请求 `id` 仅作为 raw 主键，不进入 raw JSON。审核和交接没有输出附件 ID、文件名或链接。
- 成功批次 `sync_20260720_112016_182107`：3 次请求、3 条、0 失败；raw 为 3 个不同主键和 hash、空日期 3；checkpoint 记录 `last_page=3`、`total_count=3`、`item_count=3`、`param_offset=0`、`param_limit=3`、`next_param_offset=3`。
- YAML/DB 为 75/46，code/enabled/method/path 差异 0；catalog 为 187 个公开文档、67 个真实配置、46 个 enabled、21 个 configured disabled。
- 基础数据为 `total=16`、`configured=11`、`enabled=9`、`terminal_deferred=5`、`pending_review=0`、`closed=true`。这仅说明审核终态收口，不表示全部接口均已配置。
- 130 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；未运行完整 `--sync-enabled`，未暂存、提交或推送。最终 named lock 空闲、外部事务 0、本地同步进程和同步相关活动会话均为 0。

## 下一阶段边界：产品板块整板只读预审

- 不新增产品接口配置、不请求真实产品 API、不运行完整 `--sync-enabled`。
- 先从 catalog 的产品板块输出配置、终态暂缓和待审清单；对待审接口逐个证明真实参数来源、读取性质、分页限流、主键或 hash 幂等、`data_date` 与敏感字段处理。
- 只选择 1 个下一接口，先提交最小方案并等待用户确认后，再进入 TDD、配置同步和单接口验证闭环。

## 产品板块最终事实

- 产品菜单 18 个文档接口已按审核终态收口：8 个已配置且 enabled、10 个终态暂缓、0 个待审、`closed=true`。这不表示全部接口均已配置。
- 文档 5070 `GET /purchase/goods/attribute/detail` 是唯一待审读取接口；必填 `attributeName`、非分页、默认每秒 3 次、无日期字段。
- 已对 36,820 条相关产品 raw 做字段名聚合，未发现 `attributeName` 或属性项字段；`product_page.variantProperty` 为 null，不能作为真实来源。
- 文档 5070 已登记 `defer_no_param_source`；没有新增业务 YAML、没有同步 DB `api_config`、没有请求真实 API、没有产生 batch/raw/checkpoint/API log。
- catalog 为 187 个公开文档、67 个真实配置、46 个 enabled、21 个 configured disabled；YAML/DB 保持 75/46。
- 130 个 unittest、`compileall app tests` 和 dry-run 通过；未运行完整 `--sync-enabled`，未暂存、提交或推送。

## 下一阶段边界：仓库板块整板只读预审

- 不新增仓库接口配置、不请求真实仓库 API、不运行完整 `--sync-enabled`。
- 先按公开 catalog 列出仓库板块的已配置、终态暂缓和待审接口；只对待审候选核对真实参数来源、读取性质、分页限流、幂等、`data_date` 和敏感字段边界。
- 只选择 1 个下一接口，提交最小方案并等待用户确认后，才进入实现、配置同步和单接口验证闭环。

## 阶段 16V 最终事实

- 已接入文档 64 `POST /purchase/inventory/supplierWarehouse/page` 为 `supplier_warehouse_page`，保持 `enabled=false`。无业务参数来源，`data.rows`/`data.total` 分页，`id` 必填主键，`createDate` 为 `data_date`，0.5 秒限流，`sensitive_response=true`。
- 成功批次 `sync_20260720_152244_506820`：1 次请求、0 条、0 失败；batch/API log 均 success，checkpoint 为 `last_page=1`、`request_count=1`、`item_count=0`、`total_count=0`，raw/failed request 均为 0。上游空列表是当前账号真实结果，不是拒绝证据。
- YAML/DB 为 76/46，code/enabled/method/path 差异 0；catalog 为 187 个公开文档、68 个真实配置、46 个 enabled、22 个 configured disabled。仓库板块为 `configured=3`、`enabled=2`、`terminal_deferred=0`、`pending_review=3`、`closed=false`。
- 131 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；未运行完整 `--sync-enabled`，未暂存、提交或推送。最终 named lock 空闲、外部事务 0、同步相关活动会话和本地同步进程均为 0。

## 下一阶段边界：仓库板块下一接口只读预审

- 不新增仓库接口配置、不请求真实仓库 API、不运行完整 `--sync-enabled`。
- 仅从文档 212、1035、1449 中选择一个候选，逐项证明真实参数来源、读取性质、分页与限流、幂等、`data_date` 和敏感字段边界；先提交最小方案并等待确认。

## 阶段 16W 最终事实

- 已接入文档 212 `POST /purchase/inventory/selfWarehouse/page` 为 `self_warehouse_page`，保持 `enabled=false`。无业务参数来源，`data.rows`/`data.total` 分页，`id` 必填主键，`data_date=null`，0.5 秒限流，`sensitive_response=true`。
- 成功批次 `sync_20260720_155429_491510`：1 次请求、27 条、0 失败；batch/API log 均 success，checkpoint 为 `last_page=1`、`request_count=1`、`item_count=27`、`total_count=27`，raw 为 27 个不同主键与 hash、空日期 27，失败请求为 0。交接未输出任何联系人字段值。
- YAML/DB 为 77/46，code/enabled/method/path 差异 0；catalog 为 187 个公开文档、69 个真实配置、46 个 enabled、23 个 configured disabled。仓库板块为 `configured=4`、`enabled=2`、`terminal_deferred=0`、`pending_review=2`、`closed=false`。
- 132 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；未运行完整 `--sync-enabled`，未暂存、提交或推送。最终 named lock 空闲、外部事务 0、同步相关活动会话和本地同步进程均为 0。

## 下一阶段边界：仓库板块剩余接口只读预审

- 不新增仓库接口配置、不请求真实仓库 API、不运行完整 `--sync-enabled`。
- 仅从文档 1035、1449 中选择一个候选，逐项证明真实参数来源、读取性质、分页与限流、幂等、`data_date` 和敏感字段边界；先提交最小方案并等待确认。

## 阶段 16X 最终事实

- 仓库板块已审核终态收口：文档 1035 为 `defer_sensitive_credentials`，文档 1449 为 `defer_no_param_source`。两项均未新增业务 YAML、未请求真实业务 API。
- catalog 保留 187 个有效公开详情并按当前审核覆盖重分类；仓库板块为 `total=6`、`configured=4`、`enabled=2`、`terminal_deferred=2`、`pending_review=0`、`closed=true`。这是审核收口，不代表所有接口均已配置。
- YAML/DB 仍为 77/46 且配置差异 0；最新业务批次 `sync_20260720_155429_491510` 为 success。未运行 `--sync-api-configs`、`--sync-api` 或完整 `--sync-enabled`。

## 下一阶段边界：库存板块整板只读预审

- 不新增库存接口配置、不请求真实库存 API、不运行完整 `--sync-enabled`。

## 阶段 16Y 最终事实

- 库存板块已审核终态收口：文档 1022 为 `defer_runtime_rejected`；它没有新增业务 YAML、没有请求真实业务 API。
- catalog 保留 187 个有效公开详情并按当前审核覆盖重分类；库存板块为 `total=14`、`configured=9`、`enabled=8`、`terminal_deferred=5`、`pending_review=0`、`closed=true`。这是审核收口，不代表所有接口均已配置。
- YAML/DB 仍为 77/46 且配置差异 0；最新业务批次 `sync_20260720_155429_491510` 为 success。未运行 `--sync-api-configs`、`--sync-api` 或完整 `--sync-enabled`。

## 下一阶段边界：采购板块整板只读预审

- 不新增采购接口配置、不请求真实采购 API、不运行完整 `--sync-enabled`。
- 先生成采购板块的完整预审清单，再只选择 1 个候选，证明真实参数来源、读取性质、分页与限流、幂等、`data_date` 和敏感边界后提交最小方案等待确认。
## 阶段 16Z 最终事实

- 已接入文档 86 `POST /purchase/srm/procure/page` 为 `procure_page`，保持 `enabled=false`；嵌套分页字段为 `pageInfo.page` 和 `pageInfo.pagesize`，首轮仅第 1 页、每页 100。
- 新增嵌套分页 TDD 覆盖；普通分页和参数来源分页都使用点路径写入，现有扁平字段配置保持兼容。
- 成功批次 `sync_20260720_171204_853350`：1 次请求、100 条成功、0 失败；raw 为 100 个不同主键和 hash、空日期 0，checkpoint 指向该批次，失败请求为 0。
- YAML/DB 均为 78/46，code/enabled/method/path 差异 0；catalog 187 个有效公开详情离线重分类为 70 个真实配置、46 个 enabled。采购板块为 `configured=6`、`enabled=5`、`terminal_deferred=11`、`pending_review=6`、`closed=false`。
- 最终 named lock 空闲、外部 InnoDB 事务 0、同步相关活动会话 0、本地同步进程 0；未运行完整 `--sync-enabled`，未暂存、提交或推送。

## 下一阶段边界：采购板块剩余接口只读预审

- 不新增采购接口配置、不请求真实采购 API、不运行完整 `--sync-enabled`。
- 先只读审核剩余 6 个待审接口，逐项证明真实参数来源、读取性质、分页与限流、主键或 `data_hash` 幂等、`data_date` 与敏感字段边界；只选择 1 个候选，再提交最小方案等待确认。
- 含敏感响应、写入/修改/确认操作或缺少真实参数来源的接口，只能登记明确终态，不得使用文档示例值或猜测值。

## 阶段 16AA 最终事实

- 文档 90 `GET /purchase/srm/relevancePoInfo/query` 已登记 `defer_no_param_source`；它需要采购计划单号 `code`，非分页、未公开限流、响应不含敏感字段。
- 唯一语义匹配的 `procure_page.raw_json.purchasePlanCode` 在 100 条 raw 中均为空，`purchase_plan_page` 没有可用 raw；没有使用采购订单号、文档示例值或猜测参数。
- 本阶段没有新增 YAML、DB `api_config`、batch、raw、checkpoint 或失败日志，也没有请求真实业务接口。
- catalog 保留 187 条有效公开详情并离线重分类：采购板块为 `configured=6`、`enabled=5`、`terminal_deferred=12`、`pending_review=5`、`closed=false`；YAML/DB 仍为 78/46，配置差异 0。

## 下一阶段边界：采购板块剩余接口只读预审

- 不新增采购接口配置、不请求真实采购 API、不运行完整 `--sync-enabled`。
- 仅从剩余 5 项待审接口中选择 1 项，先证明真实参数来源、读取性质、分页和限流、主键或 `data_hash` 幂等、`data_date` 与敏感字段边界，再提交最小方案等待确认。
- 含敏感响应或已有风险记录的接口，优先审查是否应登记明确终态；没有真实参数来源时只登记 `defer_no_param_source`，不得猜测或复用语义不一致字段。

## 阶段 16AB 最终事实

- 已接入文档 43 `POST /purchase/srm/supplier/page` 为 `supplier_page`，保持 `enabled=false`、一页 100 条、1 秒间隔、单次尝试；接口不依赖业务参数来源。
- 供应商编号未在运行前证明唯一，因此使用 `data_hash` 幂等；`createdAt` 生成 `data_date`。联系人、电话、邮箱和地址只保存在 raw JSON，审核和交接没有输出真实值；敏感接口失败时不保存响应正文。
- 成功批次 `sync_20260720_182049_479213`：1 次请求、27 条成功、0 失败；raw 为 27 个不同 hash、空日期 0、业务主键为空，checkpoint 指向同批次，失败请求为 0。
- YAML/DB 均为 79/46，code/enabled/method/path 差异 0；catalog 187 条有效公开详情离线重分类为 71 个真实配置、46 个 enabled。采购板块为 `configured=7`、`enabled=5`、`terminal_deferred=12`、`pending_review=4`、`closed=false`。
- 最终 named lock 空闲、外部 InnoDB 事务 0、同步相关活动会话 0、本地同步进程 0；未运行完整 `--sync-enabled`，未暂存、提交或推送。

## 下一阶段边界：采购板块剩余接口只读预审

- 不新增采购接口配置、不请求真实采购 API、不运行完整 `--sync-enabled`。
- 仅从剩余 4 项待审接口中选择 1 项，先证明真实参数来源、读取性质、分页和限流、主键或 `data_hash` 幂等、`data_date` 与敏感字段边界，再提交最小方案等待确认。
- 对敏感响应接口，先判断是否仅涉及可 raw-only 备份的业务联系信息；若含凭证或无法建立安全边界，只登记明确终态，不得调用接口。

## 阶段 16AC 最终事实

- 文档 88 `POST /purchase/srm/plan/detail` 已登记 `defer_no_param_source`；它要求采购计划 `id` 或 `code`，非分页、未公开限流，响应含人员账号/姓名等敏感字段。
- `purchase_plan_page` 没有 raw；采购订单不含计划 ID且计划编号为空；交货单 `fid` 是采购订单 ID。没有使用示例值、猜测参数或语义不一致的字段。
- 本阶段没有新增 YAML、DB `api_config`、batch、raw、checkpoint 或失败日志，也没有请求真实业务接口。
- catalog 保留 187 条有效公开详情并离线重分类：采购板块为 `configured=7`、`enabled=5`、`terminal_deferred=13`、`pending_review=3`、`closed=false`；YAML/DB 仍为 79/46，配置差异 0。

## 下一阶段边界：采购板块剩余接口只读预审

- 不新增采购接口配置、不请求真实采购 API、不运行完整 `--sync-enabled`。
- 仅从剩余 3 项待审接口中选择 1 项，先证明真实参数来源、读取性质、分页和限流、主键或 `data_hash` 幂等、`data_date` 与敏感字段边界，再提交最小方案等待确认。
- 若接口含人员/供应商等敏感字段，只能在 `sensitive_response=true`、raw-only 和失败响应不落库边界明确后考虑探测；含凭证或缺少真实参数来源时只能登记终态。

## 阶段 16AD 最终事实

- 文档 91 已配置为 `supplier_sku_quote_page`，保持 `enabled=false`；`POST /purchase/srm/supplierSkuQuote/page` 无业务必填参数，首轮为 `page/pagesize=1/100`，主键 `id`、日期字段 `createdAt`，`sensitive_response=true`。
- 已运行 `--sync-api-configs`，YAML/DB 均为 80/46 且 code/enabled/method/path 差异为 0；只运行 `--sync-api supplier_sku_quote_page`，未运行完整 `--sync-enabled`。
- 批次 `sync_20260729_120154_588297` 为 failed：1 次请求、100 条成功计数、失败计数 1；raw 的主键/hash 均为 100 个、空日期 0，checkpoint 和失败请求均为 0。
- 原因是有效总量超过单页容量，分页完整性保护阻止截断数据写成功 checkpoint；不是上游拒绝，不登记 `defer_runtime_rejected`，也不表述为真实验证成功。
- 最终 named lock 空闲、外部 InnoDB 事务 0、同步相关活动会话 0、本地同步进程 0；catalog 为 187/72/46，采购板块为 `configured=8`、`enabled=5`、`terminal_deferred=13`、`pending_review=2`、`closed=false`。

## 下一步边界：供应商产品列表分页上限确认门

- 不要重跑当前一页配置，不要运行完整 `--sync-enabled`。
- 先提交新的受限分页上限、预计请求量和运行时间；只有用户明确确认后，才修改 `max_pages` 并重新执行当前单接口。
- 任何新写任务前仍先只读核对 Git、YAML、catalog、DB `api_config`、latest batch、named lock、外部 InnoDB 事务、同步会话和本地同步进程。

## 阶段 16AE 最终事实

- 用户确认后，`supplier_sku_quote_page.max_pages` 已由 1 调整为 2，配置仍为 `enabled=false`；YAML/DB 均为 80/46，code/enabled/method/path 差异 0。
- 仅运行两页单接口批次 `sync_20260729_121333_642328`：2 次请求、200 条成功计数、失败计数 1；raw 的主键/hash 均为 200 个、空日期 0，checkpoint 和失败请求均为 0。
- 上游两页正常返回，但有效总量仍超过 200；本地分页完整性保护阻止截断数据记为成功。不是上游拒绝，不能登记 `defer_runtime_rejected`，也不能表述为真实验证成功。
- 最终 named lock 空闲、外部 InnoDB 事务 0、同步相关活动会话 0、本地同步进程 0；未运行完整 `--sync-enabled`，未暂存、提交或推送。

## 下一步边界：供应商产品列表更高分页上限确认门

- 禁止重跑 1 页或 2 页配置，禁止直接设置未知的高上限，禁止运行完整 `--sync-enabled`。
- 先提交新的明确页数、正常及重试上限请求量、预计运行时间；只有用户明确确认后，才修改 `max_pages` 并重新执行当前单接口。
- 开始任何写任务前，先只读核对 Git、YAML、catalog、DB `api_config`、latest batch、named lock、外部 InnoDB 事务、同步会话和本地同步进程。

## 阶段 16AF 最终事实

- 已新增只读 `--probe-api <api_code>`，普通分页接口首页会返回总数、页大小、所需页数和请求次数，不创建数据库引擎或写入同步表。
- `supplier_sku_quote_page` 预检为总量 9,727、每页 100、所需 98 页、请求 1 次；最新 batch 仍为旧失败批次，raw 仍为 200，checkpoint 为 0。
- YAML/DB 为 80/46、差异 0；锁、外部事务、同步会话和本地同步进程均为 0。完整回归 160 个 unittest 通过，未运行完整 `--sync-enabled`。

## 下一步确认门：供应商产品列表 98 页单接口同步

- 当前接口保持 `enabled=false`、`max_pages=2`。如需完成验证，必须先确认改为 98 页，且只运行 `--sync-api supplier_sku_quote_page`。
- 预计请求量为 98 次。`retries=1` 表示每页只尝试一次；按每次 30 秒超时和 97 次页间 1 秒限流计算，保守上限约 51 分钟。执行前重新只读检查 Git、配置、DB、锁、事务、会话和进程。

## 阶段 16AG 最终事实

- 官方文档 91 明确 `page/pagesize`、单页最大 100、`data.rows/data.total` 和默认每秒 1 次，但没有固定总页数上限。
- 同步引擎已支持省略 `max_pages` 后按每页最新 `total` 自动分页；运行中 total 增长也会继续，缺失或非法 total 会在首页 raw 写入前失败。所有已有固定 `max_pages` 配置保持旧行为。
- `supplier_sku_quote_page` 的本地 YAML 已删除 `max_pages=2` 并增加 `commit_per_page=true`，继续 `enabled=false`。DB 配置尚未同步，仍保留旧两页快照。
- 只读 probe 仍为总量 9,727、每页 100、当次 98 页、1 次请求，耗时 2.502 秒。后续业务增长时按运行当次 total 重新计算，不固定沿用 98 页。
- 完整回归 162 个 unittest、`compileall`、dry-run 和 `git diff --check` 通过。
- probe 后 latest batch 仍为 `sync_20260729_121333_642328` failed；目标 raw 200、checkpoint 0、API log 2、failed request 0。named lock 空闲、外部事务和活动会话为 0，没有运行真实同步。

## 下一步确认门：同步 total 驱动配置并运行供应商产品列表

- 未获再次确认前，不运行 `--sync-api-configs`、`--sync-api supplier_sku_quote_page` 或完整 `--sync-enabled`。
- 用户确认后，先重新只读检查 Git、YAML、catalog、DB、latest batch、named lock、InnoDB 事务、数据库活动会话和本地同步进程。
- 只同步 YAML 配置到 DB，然后仅运行 `--sync-api supplier_sku_quote_page`。实际请求页数按运行时最新 `total` 计算；当前预检值对应 98 次正常请求和 97 秒固定限流等待，网络响应耗时另计。
- 完成后审核 batch、API log、raw 主键/hash、`data_date`、checkpoint、失败日志、锁、事务、会话和进程，并更新交接文档。接口继续保持 `enabled=false`。

## 阶段 16AH 最终事实

- 写前只读门禁确认 YAML/DB 均为 80/46、配置差异 0；named lock 空闲、外部 InnoDB 事务 0、活动数据库会话 0、本地同步进程 0。
- 官方文档 91 已再次确认 `page/pagesize`、单页最大 100、`data.rows/data.total` 和默认每秒 1 次；没有固定总页数上限。
- 已运行 `--sync-api-configs`，DB 目标配置不含 `max_pages`、`commit_per_page=true`、`enabled=false`。
- 仅运行 `--sync-api supplier_sku_quote_page`；批次 `sync_20260729_151815_934165` 为 success，共 98 次请求、9,727 条成功、0 失败，未运行完整 `--sync-enabled`。
- raw 共 9,727 条，主键/hash 各 9,727 个，空主键和空 `data_date` 均为 0；checkpoint 为第 98 页、98 次请求、9,727 条和 total 9,727，失败请求为 0。
- 最终 named lock 空闲、外部事务、活动会话和同步进程均为 0；完整回归 162 个 unittest 通过。接口继续保持 disabled。
- catalog 状态保持 187 个有效公开详情、72 个已配置、46 个 enabled；采购板块为 `configured=8`、`enabled=5`、`terminal_deferred=13`、`pending_review=2`、`closed=false`。

## 下一步确认门：采购板块剩余两项只读预审

- 不重跑供应商产品列表，不运行完整 `--sync-enabled`。
- 采购板块仅剩文档 1080 `POST /purchase/srm/quickInbound/query` 和文档 5262 `POST /purchase/srm/purchaseSubject/list` 待审。

## 阶段 16AI 最终事实

- 官方文档 1080 规定 `POST /purchase/srm/quickInbound/query` 使用可选字符串数组 `data`，最多 100 个采购单号，默认每秒 1 次；真实参数来源已证明为 `procure_page.raw_json.code`。
- 同步引擎已支持对顶层 param source 字段显式配置 `wrap_in_list=true`，生成单元素 Python 列表；没有该配置的旧接口行为不变。
- 仅运行一次当前接口。批次 `sync_20260730_100043_263810` 在首个官方格式请求收到 HTTP 400 后失败，没有重试或尝试其他数组编码；raw 和 checkpoint 均为 0。
- 失败日志只保留 HTTP 状态和脱敏摘要，未保存请求参数、响应正文或真实采购单号。文档 1080 已登记为 `defer_runtime_rejected`。
- 临时 YAML/DB 接口配置已精确清理，失败 batch/API log/failed request 证据保留。最终 YAML/DB 均为 80/46，code/enabled/method/path 差异为 0，锁、外部事务、活动会话和本地同步进程均为空。
- 实时官方 catalog 现为 189 个有效详情、72 个已配置、46 个 enabled；相较上一快照新增的 2 个文档均属于物流板块。采购板块为 `configured=8`、`enabled=5`、`terminal_deferred=14`、`pending_review=1`、`closed=false`。
- 未运行完整 `--sync-enabled`，未暂存、提交或推送。

## 下一步确认门：采购板块文档 5262 敏感终态收口

- 先重新只读核对官方文档 5262、Git、YAML、catalog、DB、latest batch、锁、事务、会话和同步进程。
- 官方响应包含联系人、邮箱、电话、税号、地址、银行信息和印章图片等敏感字段；下一阶段只提交 `defer_sensitive_credentials` 最小终态方案并等待确认，不执行真实业务 API。
- 文档 5262 终态完成且采购板块 `pending_review=0` 后，才能按既定板块顺序进入物流板块；不得把本次 catalog 新增的 2 个物流文档与采购收口混在同一阶段。

## 阶段 16AJ 最终事实

- 实时官方文档 5262 为 `POST /purchase/srm/purchaseSubject/list`，无请求体、非分页、默认每秒 1 次；响应包含联系方式、税号、地址、银行账户和公章图片链接等高敏感字段。
- 文档 5262 已登记为 `defer_sensitive_credentials`，没有新增业务 API 配置，没有调用真实业务接口或写数据库。
- catalog 实时刷新为 189 个有效详情、72 个已配置、46 个 enabled，详情错误 0；采购板块为 `configured=8`、`enabled=5`、`terminal_deferred=15`、`pending_review=0`、`closed=true`。
- YAML/DB 仍为 80/46、差异 0；latest batch 仍是文档 1080 的失败证据，named lock、外部事务、活动会话和同步进程均为空。
- 采购板块已经完成审核终态收口，但不是 23 个接口全部配置。未运行完整 `--sync-enabled`，未暂存、提交或推送。

## 下一步确认门：物流板块整板只读预审

- 物流板块当前为 21 个文档接口、3 个已配置、2 个 enabled、2 个终态暂缓、16 个待审，`closed=false`。
- 先实时读取官方 tree/detail，对整个物流板块核对接口读写性质、参数、分页、限流、响应结构和敏感字段，并为每个未配置接口给出候选或暂缓依据。
- 整板预审阶段不调用任何真实业务 API、不新增配置、不写数据库；上一 catalog 快照新增的 2 个物流文档也必须按官方详情重新审核，不能沿用旧分类猜测。
- 完成整板预审后只选择 1 个下一接口，提交真实参数来源、分页和请求量、幂等、日期及敏感边界的最小方案，等待用户确认后再实施。

## 阶段 16AK-A 最终事实

- 文档 3059 当前官方契约为 `GET /fulfillment/ship/transport/list`，必填 `page/pagesize`、单页最大 100，响应 `data.rows/data.total`，默认每秒 1 次。
- 本地 `ship_transport_list` 已改为 `enabled=false`、GET、1 秒限流，并删除固定 `max_pages=10`；分页由每页最新有效 total 驱动。
- 唯一一次只读预检得到 total 292、每页 100、所需 3 页、实际请求 1 次、耗时 1.613 秒；没有写数据库。
- 本地 YAML/catalog 为 80 个配置、45 个 enabled；DB 仍是 80/46，目标 DB 配置仍为 POST/enabled。该差异是等待二次确认的临时状态。
- catalog 保留 189 条有效官方详情、72 个已配置、45 个 enabled；物流板块为 3 个 configured、1 个 enabled、2 个 terminal、16 个 pending。
- 168 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 已通过；没有运行 `--sync-api-configs`、`--sync-api` 或完整 `--sync-enabled`，没有暂存、提交或推送。

## 下一步确认门：16AK-B 物流方式 GET 单接口真实验证

- 正常请求量为 3 次，页间固定等待共 2 秒；结合首页预检，正常运行预计不到 1 分钟。当前重试配置下异常请求上限为 9 次。
- 未获用户明确确认前，不运行 `--sync-api-configs` 或 `--sync-api ship_transport_list`。
- 用户确认后先重新只读检查 Git、YAML/catalog、DB、latest batch、named lock、外部 InnoDB 事务、活动会话和本地同步进程。
- 只同步配置，然后仅运行当前 `--sync-api ship_transport_list`；审核 batch、API log、raw 主键/hash、空 `data_date`、checkpoint、失败日志、锁、事务、会话和进程。禁止运行完整 `--sync-enabled`。
- 16AK-B 完成后再决定是否恢复 enabled；在此之前不得并行推进文档 1027。

## 阶段 16AK-B 最终事实

- 文档 3059 的实时官方契约和真实业务调用均已确认使用 `GET /fulfillment/ship/transport/list`；接口是读取操作，单页最大 100，按每页最新 `data.total` 自动分页，默认每秒 1 次。
- `--sync-api-configs` 后 YAML/DB 均为 80 个配置、45 个 enabled，目标接口 GET、disabled、无固定 max_pages；code/enabled/method/path 差异均为 0。
- 唯一单接口批次 `sync_20260730_112541_515611` 为 success：运行时 total 292、请求 3 次、成功 292、失败 0，未运行完整 `--sync-enabled`。
- 本批次 raw 主键/hash 各 292 个、空主键 0、`data_date` 均为 null；总表 293 条，额外 1 条是本次上游未返回的历史记录，按备份原则保留。
- checkpoint 为第 3 页、3 次请求、292 条、total 292；本批次和接口累计失败请求为 0。named lock 空闲，外部事务、活动会话和同步进程均为 0。
- catalog 保持 189 个有效详情、72 个已配置、45 个 enabled；物流板块为 3 个 configured、1 个 enabled、2 个 terminal、16 个 pending。
- 168 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；没有暂存、提交或推送。

## 下一步确认门：16AK-C 恢复物流方式 daily enabled

- `ship_transport_list` 已完成当前官方 GET 契约的真实单接口验证，数据量小、主键稳定、无敏感响应字段，建议恢复 `enabled=true`。
- 未获确认前保持 disabled，不运行 `--sync-api-configs` 或完整 `--sync-enabled`。
- 用户确认后先重新检查 Git、YAML/catalog、DB、latest batch、锁、事务、会话和进程；TDD 将本地 enabled 恢复为 true并同步 DB。
- 只审核配置同步结果，不运行完整 `--sync-enabled`；YAML/DB 和 catalog 应恢复为 80/46，物流板块 enabled 应恢复为 2。
- 16AK-C 完成后，下一阶段才对文档 1027 提交独立最小方案。

## 阶段 16AK-C 最终事实

- `ship_transport_list` 已恢复 `enabled=true`；YAML/DB 均为 80 个配置、46 个 enabled，code/enabled/method/path 差异均为 0。
- 目标 DB 配置继续是当前官方 GET、无固定 max_pages、每页 100、按 `data.total` 动态分页、1 秒限流；没有回退到历史 POST 配置。
- catalog 为 189 个有效详情、72 个已配置、46 个 enabled；物流板块为 3 个 configured、2 个 enabled、2 个 terminal、16 个 pending。
- 本阶段只执行 `--sync-api-configs`，未调用业务 API、未运行 `--sync-api` 或完整 `--sync-enabled`；latest batch 仍为 `sync_20260730_112541_515611` success，raw 293、API log 51、checkpoint 和失败请求均未变化。
- 168 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；named lock 空闲，外部事务、活动会话和同步进程均为 0；未暂存、提交或推送。

## 下一步确认门：物流文档 1027 最小接入方案

- 重新实时读取文档 1027 `POST /fulfillment/ship/delivery/page`，以其自身官方参数、分页、限流和响应结构为准，不套用 doc3059。
- 该接口无必填业务筛选参数，可先保持 `enabled=false`，只读首页预检运行时 total；使用响应 `id` 幂等、`updateTime` 生成 `data_date`，店铺账号标识仅 raw 备份。
- 先提交实时 total、预计请求量和运行时间，再等待用户确认；未获确认前不新增配置、不调用业务 API、不写数据库。
- 不运行完整 `--sync-enabled`，不与其他物流接口并行推进。

## 阶段 16AL-A 最终事实

- 官方文档 1027 为 `POST /fulfillment/ship/delivery/page` 读取接口；`page/pagesize` 必填、单页最大 100，响应 `data.rows/data.total`，默认每秒 2 次，业务筛选条件均可选。
- 本地已新增 `delivery_page` 并保持 `enabled=false`；不设置 `max_pages`、日期窗口或参数来源，`id` 非必填主键缺失时回退 `data_hash`，`updateTime` 生成 `data_date`，敏感响应只作 raw 备份。
- 唯一一次首页 probe 得到实时 total 18162、每页 100、所需 182 页、实际请求 1 次，耗时 5.065 秒；182 页不是长期上限。
- 当前正常完整同步基线为 182 次请求和 181 次页间 0.5 秒等待，固定限流等待 90.5 秒；实际页数必须按同步时最新 total 重新计算。
- 本阶段没有写数据库。YAML 为 81/46、DB 为 80/46，唯一差异是 `delivery_page`；目标 DB 配置、API log、raw、checkpoint 和失败日志均为 0，latest batch 仍是 `sync_20260730_112541_515611` success。
- catalog 为 189/73/46；物流板块为 21 个接口、4 个 configured、2 个 enabled、2 个 terminal、15 个 pending，尚未收口。
- 169 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；named lock 空闲，外部事务、活动会话和同步进程均为 0，未暂存、提交或推送。

## 下一步确认门：16AL-B 发货单列表真实单接口验证

- 当前 total 基线对应 182 页；运行时必须重新读取最新 total 并动态分页，不配置固定 `max_pages`，不因本次快照限制后续业务增长。
- 真实同步前先以 TDD 增加 `commit_per_page=true`，每页 raw 使用独立短事务；接口继续保持 `enabled=false`。
- 用户确认后重新只读检查官方文档、Git、YAML/catalog、DB、latest batch、named lock、外部 InnoDB 事务、活动会话和本地同步进程。
- 只执行 `--sync-api-configs`，然后仅运行 `--sync-api delivery_page`；不运行完整 `--sync-enabled`，不并行推进其他接口。
- 审核 batch/API log 的实际 total、请求数和成功失败数；raw 使用 `id` 或 hash 幂等，核对 `data_date`、checkpoint 和失败日志，且不输出敏感字段值。
- 当前固定限流等待基线为 90.5 秒；可用首页 probe 的 5.065 秒作为粗略排期参考，但它包含启动和鉴权耗时，不应被当作官方 SLA 或代码限制。
- 完成锁、事务、会话和进程收尾复核后，再单独决定是否将该接口加入 daily enabled。

## 阶段 16AL-B 最终事实

- 官方 detail 和 apiMap 已再次确认文档 1027 为公开且审核通过的 `POST /fulfillment/ship/delivery/page` 读取接口；每页最大 100、返回 `data.rows/data.total`、默认每秒 2 次。
- `delivery_page` 使用运行时 total 动态分页、`commit_per_page=true`、`id` 非必填主键、`updateTime` 日期和敏感 raw-only，继续保持 `enabled=false`，没有固定 `max_pages`。
- YAML/DB 均为 81 个配置、46 个 enabled，code/enabled/method/path 差异为 0；catalog 为 189/73/46，物流板块为 4 个 configured、2 个 enabled、2 个 terminal、15 个 pending。
- 唯一批次 `sync_20260730_143314_977605` 为 success：运行时 total 18168、182 次请求、18168 条成功、0 失败，DB 批次耗时 1110 秒，CLI 总耗时 1116.106 秒。
- raw 行数、不同业务主键数和不同 data hash 数均为 18168；空主键、缺失 id、主键不一致、空日期、缺失 updateTime 和日期不一致均为 0。
- checkpoint 为第 182 页、182 次请求、18168 条、total 18168；本批次及目标累计失败请求均为 0。
- 169 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；named lock 空闲，外部事务、活动会话和同步进程均为 0；未运行完整 `--sync-enabled`，未暂存、提交或推送。

## 下一步确认门：16AL-C 发货单列表 daily enabled 决策

- 技术验收已通过，可以考虑把 `delivery_page` 恢复为 daily enabled；按本次数据量会增加约 182 次请求和 18.5 分钟运行时间，实际请求数仍按每次最新 total 动态变化。
- 未获明确确认前保持 `enabled=false`，不运行 `--sync-api-configs`、业务 API 或完整 `--sync-enabled`。
- 用户确认后先重新检查官方文档、Git、YAML/catalog、DB、latest batch、named lock、外部事务、活动会话和同步进程。
- TDD 只把目标 enabled 期望改为 true，并把全局 enabled 总数从 46 改为 47；GET/POST、分页、事务、主键、日期、限流和敏感边界均不改动。
- 只执行 `--sync-api-configs`，预期 YAML/DB 为 81/47，catalog 为 189/73/47，物流板块 enabled 为 3。
- 16AL-C 不调用 `delivery_page` 或其他业务 API，不运行完整 `--sync-enabled`；latest batch、raw、checkpoint 和失败日志应保持 16AL-B 证据不变。
- 配置验收后再回到物流板块，从剩余 15 个待审接口中只选择 1 个下一候选。

## 阶段 16AL-C 最终事实

- 官方 detail 与 apiMap 再次确认文档 1027 契约未变；`delivery_page` 已加入 daily enabled，其他分页、事务、主键、日期、限流和敏感配置均未修改。
- YAML/DB 均为 81 个配置、47 个 enabled，code/enabled/method/path 差异为 0；catalog 为 189/73/47，物流板块为 4 个 configured、3 个 enabled、2 个 terminal、15 个 pending。
- 本阶段只执行 `--sync-api-configs`，未调用业务 API、未运行单接口或完整 `--sync-enabled`。
- latest batch 仍为 `sync_20260730_143314_977605` success；raw 18168、主键/hash 各 18168、空日期 0，API log 1、失败请求 0，checkpoint 仍为第 182 页、182 次请求、18168 条、total 18168。
- 169 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；named lock 空闲，外部事务、活动会话和同步进程均为 0；无 staged，未提交或推送。

## 下一步确认门：16AM-A 物流费用金额明细只读分页预检

- 候选为官方文档 1778“查询物流费用金额明细”，`POST /fulfillment/ship/cost/page`，公开且审核通过，属于读取分页接口。
- 官方业务筛选参数 `codes/feeTypes/expenseTypes/updateTimeStart/updateTimeEnd/createTimeStart/createTimeEnd` 均为可选，因此不需要猜测或伪造业务上游参数；预检只传官方分页字段。
- 分页字段为 `page/pagesize`、单页最大 100，响应列表 `data.rows`、总数 `data.total`；默认每秒 2 次，配置间隔 0.5 秒。
- 响应 `id` 非必填，优先作为主键并设置 `required=false`，缺失时按完整对象 `data_hash` 幂等；`updateAt` 生成 `data_date`。
- 费用、金额、币种、组织、付款条件和物流单号等业务敏感字段只允许写入 raw，配置 `sensitive_response=true`，日志、测试和交接不输出字段值。
- 用户确认后先重新核对官方文档、Git、YAML/catalog、DB、latest batch、named lock、外部事务、活动会话和同步进程。
- TDD 新增 `logistics_cost_page` 配置测试；配置保持 `enabled=false`、POST、每页 100、无 `max_pages`、无 date_window/param_source/commit_per_page、限流 0.5 秒、重试 1 次。
- 不执行 `--sync-api-configs`，严格只执行一次 `--probe-api logistics_cost_page`；probe 不创建数据库连接，不写 batch、raw、checkpoint 或失败日志。
- 取得实时 total、所需页数和耗时后，再按数据量提交是否增加按页短事务以及真实单接口同步方案；不得把本次页数固化为长期上限。

## 阶段 16AM-A 最终事实

- 官方 detail/apiMap 确认文档 1778 为 `POST /fulfillment/ship/cost/page` 读取接口；业务筛选可选、单页最大 100、响应 `data.rows/data.total`、默认每秒 2 次。
- 本地新增 `logistics_cost_page` 并保持 disabled；无 max_pages、date_window、param_source 或 commit_per_page，使用 `id required=false`、`updateAt` 日期和敏感 raw-only。
- TDD 配置测试先 RED 后 GREEN；catalog 为 189/74/47，物流板块为 5 个 configured、3 个 enabled、2 个 terminal、14 个 pending。
- 170 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；dry-run 仍只加载 47 个 enabled。
- 唯一一次 `--probe-api logistics_cost_page` 在 1.213 秒后返回 `ApiRequestError`，没有取得 total、页数或运行时间估算；没有重试或改参数。
- 现有 probe 只输出包装异常类型，非 token 日志也没有 HTTP 状态证据；不能猜测为上游拒绝或网络问题，不能提交真实同步方案。
- 本地 YAML 为 82/47、DB 仍为 81/47，唯一差异是未同步的目标；目标 DB 配置、API log、raw、checkpoint 和失败日志均为 0，latest batch 仍为 `sync_20260730_143314_977605` success。
- named lock 空闲，外部事务、活动会话和同步进程均为 0；未运行配置同步、业务同步或完整 enabled，未暂存、提交或推送。

## 下一步确认门：16AM-B probe 安全错误分类与一次复检

- 目标是补足安全可观测性，不扩大接口范围：`ApiRequestError` 只输出原始异常类型和 HTTP 状态码，不输出消息正文、请求参数、响应正文或敏感字段。
- TDD 为 `_probe_single_api` 增加包装 HTTP 异常和无 response 异常测试，先 RED 再做最小实现；原有成功 probe 行为不变。
- 完整回归必须继续通过，dry-run enabled 数量保持 47；本阶段仍不运行 `--sync-api-configs`。
- 复检前重新读取官方文档 1778，并只读核对 Git、YAML/catalog、DB、latest batch、named lock、外部事务、活动会话和同步进程。
- 严格最多再执行一次 `--probe-api logistics_cost_page`，仍只传 `page=1/pagesize=100`，不增加筛选条件或其他数组编码。
- 若成功，记录实时 total、所需页数和耗时，再提交按页短事务的真实同步方案；不在同阶段写库。
- 若获得明确 HTTP 4xx/5xx，立即停止并按证据登记 `defer_runtime_rejected`，不再次调用；若仍无 HTTP 状态，则保留 configured disabled 并报告网络类阻断。
- 不运行真实 `--sync-api` 或完整 `--sync-enabled`，不暂存、提交或推送。

## 阶段 16AM-B 最终事实

- 实时官方文档 1778 的接口说明明确要求“发货单集合、时间必传一项”；字段级 `must=false` 不能证明允许无筛选请求，16AM-A 的无条件预检前提已纠正。
- 16AM-A 的唯一无筛选 probe 返回 `ApiRequestError`，但该请求不满足完整官方说明；不再用它推断 HTTP 拒绝、网络故障或运行终态。
- TDD 已使包装异常安全输出原始异常类型和 HTTP 状态码；测试同时证明异常正文、URL、参数和响应正文不会进入日志。
- 172 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；enabled 仍为 47。
- 本阶段没有再次调用业务 API，没有执行配置同步或任何数据库写入；YAML 为 82/47、DB 为 81/47，唯一差异仍是目标 disabled 配置。
- catalog 为 189/74/47，物流板块为 configured=5、enabled=3、terminal=2、pending=14；latest batch、目标五张表、named lock、事务、会话和进程均保持零写入证据。

## 下一步确认门：16AM-C 物流费用必填条件来源只读审核

- 16AM-C 只做只读审核，不调用文档 1778，不运行 `--sync-api-configs`、`--sync-api` 或完整 `--sync-enabled`。
- 重新核对发货单列表官方文档，证明其响应字段与文档 1778 的 `codes` 在业务语义上是否一致。
- 对现有 `delivery_page` raw 只统计候选字段的非空数、唯一数和日期覆盖，不输出发货单号、费用值或其他敏感内容。
- 同时核对官方是否规定 `codes` 数组上限、时间字段组合和时间范围；未规定的边界保持未知，不自行猜测批量大小或历史窗口。
- 只有一条参数路线的来源、分页、限流、幂等、日期、敏感处理、预计请求量和运行时间全部可证明时，才提交该路线的最小实施方案。
- 若两条路线都缺少官方边界或真实来源，目标继续 configured disabled，并按证据提出暂缓方案；实施仍需用户再次确认。

## 阶段 16AM-C 最终事实

- 官方文档证明 delivery_page.raw_json.code 是发货单号，现有 18,168 条均非空且唯一，可语义对应文档 1778 的 codes。
- 文档 1778 没有规定 codes 数组上限或时间筛选跨度，不能自行猜测批量大小、请求上限或历史窗口。
- 用户已确认暂缓文档 1778；logistics_cost_page 保持 configured disabled，不再探测或同步。

## 阶段 16AN-A 最终事实

- 官方文档 1028 为 POST /fulfillment/ship/delivery/query 非分页读取接口；参数使用单元素 deliveryCodes 和 needItem=true，响应为 data 数组，默认每秒 5 次。
- 真实参数只来自 delivery_page.raw_json.code；当前来源 18,168 条均可用且唯一，首次严格 limit=1。
- delivery_detail_query 已写入 YAML/DB 并保持 disabled；YAML/DB 均为 83 个配置、47 个 enabled，code/enabled/method/path 差异为 0。
- 唯一批次 sync_20260731_105320_767996 为 success：1 次请求、1 条成功、0 失败；未运行 probe 或完整 --sync-enabled。
- 1 条 raw 的 deliveryCode 是空字符串，因此没有业务主键，按唯一 data_hash 幂等；updateTime -> data_date 正确，明细数组存在。
- checkpoint 为 1 次请求、1 条结果、参数偏移 0、下一个偏移 1；失败请求为 0。
- 文档 1778 只随配置同步写入 disabled DB 配置，没有 API log、raw、checkpoint 或失败记录。
- 173 个 unittest、compileall app tests、dry-run 和 git diff --check 通过；锁、事务、同步会话和本项目 Python 进程均为空；未暂存、提交或推送。

## 下一步确认门：物流下一个候选只读审核

- 文档 1028 继续保持 disabled，不立即扩大到 18,168 个来源，也不加入 daily enabled；按每个来源一次请求和官方每秒 5 次计算，仅固定限流等待就约 60.56 分钟。
- 单个真实样本的 deliveryCode 为空，当前只能依赖 data_hash；在扩大同步前必须重新审核幂等风险，不能擅自改用其他字段。
- 下一阶段从物流剩余 13 个待审文档中只选 1 个候选，先实时读取官方 tree/detail，再提交参数来源、分页/限流、幂等、日期、敏感字段、请求量和运行时间方案。
- 不重跑文档 1028，不调用文档 1778，不运行完整 --sync-enabled，不批量新增接口。
- 实施任何下一接口前继续只读检查 Git、YAML/catalog、DB、latest batch、named lock、外部事务、活动会话和本地同步进程，并等待用户确认。

## 阶段 16AO-A 最终事实

- 官方文档 9 为 `POST /operation/sale/returnOrder/page` 读取分页接口；必填参数只有 `page/pagesize`，单页最大 100，响应约定为 `data.rows/data.total`，默认每秒 5 次。
- 唯一一次无数据库首页 probe 只发送 `page/pagesize=1/100`，1.154 秒后返回 HTTP 400；没有取得 total 或所需页数。
- 没有重试、猜测筛选条件、改换编码或输出响应内容；没有运行 `--sync-api-configs`、`--sync-api` 或完整 `--sync-enabled`。
- 文档 9 已登记 `defer_runtime_rejected`，临时 YAML 配置已清理；接口测试验证无业务配置和审核终态。
- YAML/DB 均为 83/47 且配置差异为 0；catalog 为 189/75/47，销售板块 configured=0、enabled=0、terminal=2、pending=13、closed=false。
- latest batch 仍为 `sync_20260731_105320_767996` success；目标在 DB 配置、API log、raw、checkpoint 和失败日志中的计数均为 0。
- 174 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过；named lock、外部事务、活动会话和项目 Python 进程均为空。
- 未暂存、提交或推送，其他既有未提交修改全部保留。

## 下一关键节点

- 由于首页预检没有取得 total，16AO-B 数据库同步阶段取消；在有新官方证据前不得重复调用文档 9。
- 后续可自主只读审核销售板块剩余 13 个待审文档，每次只选择 1 个候选并证明官方契约、参数来源、分页限流、幂等、日期、敏感边界和预计请求量。
- 到真实业务 API 调用、`--sync-api-configs`、`--sync-api`、完整运行或 daily enabled 等关键节点时，再向用户提交最小方案确认。
- 不运行完整 `--sync-enabled`，不批量新增接口，不读取或输出凭证和真实敏感字段值。

## 阶段 16AO-B 最终事实

- 真实错误响应已经补充证明 `/operation/sale/returnOrder/page` 必须带日期查询条件，日期跨度不能超过 31 天；此前 HTTP 400 的运行阻断已解除。
- 独立脚本 `request_sale_return_order_page.py` 支持 `--all-pages`，按每次响应的实时 `data.total` 动态计算请求页数，不设置猜测性固定页数上限，不写数据库或输出订单明细。
- `2026-08-04` 至 `2026-08-10` 全店铺站点真实验证成功：HTTP 200、业务码 200、`total=11007`、实际 111 页、累计 11007 条、完整性通过，耗时约 113 秒。
- 175 个 unittest、`compileall app tests`、dry-run 和 `git diff --check` 通过。
- YAML/DB 仍为 83/47；`sale_return_order_page` 的配置、API log、raw、checkpoint 和失败日志仍为 0，latest batch 未变化，named lock、外部事务、会话和进程均为空。
- 文档 9 已从 `defer_runtime_rejected` 审核覆盖中移除，恢复为待正式接入审核；独立真实测试不等于完成数据库同步接入。

## 阶段 16AO-C 下一关键节点

- 若继续正式接入，只新增 `sale_return_order_page` 一个接口并保持 `enabled=false`；配置使用 `returnStartDate/returnEndDate`、最多 31 天窗口、`pagesize=100`、实时 total 分页、`commit_per_page=true`、`id` 优先并回退 `data_hash`、`returnDateTime` 生成 `data_date`、敏感 raw-only。
- 执行前重新只读检查 Git、YAML/catalog、DB、latest batch、named lock、外部事务、数据库会话和本地同步进程；真实数据库写入仍需用户确认。
- 正式闭环固定为配置测试 -> `--sync-api-configs` -> 仅运行当前 `--sync-api sale_return_order_page` -> 审核 batch、API log、raw、checkpoint、失败日志、锁、事务和进程 -> 再决定是否进入 daily enabled。
- 不运行完整 `--sync-enabled`，不批量新增接口，不读取或输出凭证、订单明细或真实敏感字段值。
