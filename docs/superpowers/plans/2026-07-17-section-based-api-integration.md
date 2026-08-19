# 按板块接入积加 API 实施计划

## 计划落盘

执行阶段的第一个动作是创建本地计划文件：

`docs/superpowers/plans/2026-07-17-section-based-api-integration.md`

文件内容使用本计划全文。计划文件保持未暂存、未提交、未推送。

## 总体路线

固定按以下依赖顺序推进：

1. 基础数据
2. 产品
3. 仓库
4. 库存
5. 采购
6. 物流
7. 订单
8. 销售
9. 财务
10. 广告
11. 客服
12. 多平台

统计 17/17、报表 8/8 已接入完成，不重复实施。

每个板块先整板只读预审，再一次只实施一个接口。接口终态包括：

- 已配置并真实验证
- 缺少真实参数来源，暂缓
- 敏感凭证阻断
- 写操作暂缓
- 鉴权框架专用
- 运行时被上游拒绝，保留证据暂缓

板块只有在 `pending_review=0` 后才切换。

## 阶段 16Q：审核终态机制

新增 `config/api_review_overrides.yaml`：

```yaml
reviews:
  - doc_id: 596
    status: framework_auth_only
    reason: 获取 accessToken 已由鉴权模块处理，不属于业务 raw 备份接口。
```

允许的状态：

- `framework_auth_only`
- `defer_no_param_source`
- `defer_sensitive_credentials`
- `defer_runtime_rejected`
- `defer_duplicate_or_obsolete`
- `defer_unsupported_shape`

调整 catalog：

- 判断优先级为：已配置状态 > 审核覆盖表 > 自动分类。
- CLI 增加 `--review-config`。
- 汇总增加板块维度：

```json
{
  "total": 16,
  "configured": 9,
  "enabled": 9,
  "terminal_deferred": 3,
  "pending_review": 4,
  "closed": false
}
```

基础数据初始终态：

- 文档 596 `/api_token`：`framework_auth_only`
- 文档 3095 VC 店铺：响应含 `publicToken/refreshToken`，标记 `defer_sensitive_credentials`
- 文档 61 修改汇率：继续 `defer_write_or_mutation`

以上接口不得执行真实业务同步。

## 阶段 16R：店铺 ID 查询店铺名称

接口：`GET /middle/base/marketNames/query`，文档 id=1177。

新增最小数组参数能力：

```yaml
param_source:
  source_api_code: amazon_shop_page
  limit: 3
  auto_advance: true
  fields:
    - source_field: raw_json.marketListVos[].marketId
      target_field: markerIds
      wrap_in_list: true
```

配置要求：

- `enabled=false`
- 非分页
- 响应标量 `data` 包装为 `marketName`
- 请求参数中的单元素数组规范化为单个 market ID 主键
- `data_date=null`
- 限流间隔 0.2 秒
- 首次最多 3 次请求

如果仍返回历史 400/509，不猜测其他数组编码，记录 `defer_runtime_rejected`。

## 阶段 16S：店铺 ID 查询仓库信息

接口：`GET /middle/base/warehouseIds/query`，文档 id=1179。

配置要求：

- 复用 `wrap_in_list: true`
- 参数来源仍为 `amazon_shop_page.raw_json.marketListVos[].marketId`
- 目标参数为 `marketIdList`
- 初次最多 3 个店铺 ID
- `enabled=false`
- 非分页，`list_field=data`
- 无经文档证明的单字段主键，按完整对象 `data_hash` 幂等
- `data_date=null`
- 限流间隔 1.1 秒

运行失败时采用与 16R 相同的终态处理。

## 阶段 16T：查询所有用户列表

接口：`GET /middle/base/allUser/list`，文档 id=25。

配置要求：

- `enabled=false`
- 非分页，`list_field=data`
- 主键为 `id`
- 单次请求
- 手机号、邮箱、姓名、组织和角色只保存到 `raw_api_data.raw_json`
- 日志、测试和交接文档不得输出敏感字段值

日期处理：

- 官方 `createdTime` 为13位毫秒时间戳
- 增加毫秒时间戳转换
- 按 `Asia/Shanghai` 转换为 `data_date`
- 原有 ISO 日期处理保持不变

## 阶段 16U：附件接口和板块收口

接口：`GET /middle/base/fileFileUrl/query`，文档 id=694。

先只读审核：

- 只统计现有 raw 是否存在语义明确的附件 ID 字段
- 不输出附件 ID 或链接值
- 有稳定真实来源时，单独提交接口最小方案并等待确认
- 没有来源时写入 `defer_no_param_source`
- 禁止使用文档示例 ID、猜测字段或硬编码值

基础数据板块最终要求：

- `pending_review=0`
- enabled 仍为 46
- 所有未配置接口都有明确终态
- 不把“审核收口”表述成“所有接口均已配置”

## 单接口执行闭环

每个接口必须独立执行：

1. 只读检查 Git、YAML、catalog、DB、latest batch。
2. 检查 named lock、外部 InnoDB 事务、数据库活动会话和同步进程。
3. 提交当前接口最小方案并等待确认。
4. TDD 先 RED。
5. 做最小实现并转 GREEN。
6. 新配置保持 `enabled=false`。
7. 执行 `--sync-api-configs`。
8. 仅执行当前 `--sync-api`。
9. 审核 batch、API log、raw、checkpoint、失败日志、锁、事务和进程。
10. 更新 README、progress、decisions、next_prompt 和 catalog。

禁止运行完整 `--sync-enabled`。

## 测试和验收

必须覆盖：

- 审核配置加载、状态优先级和板块关闭计算。
- 未配置审核文件时保持兼容。
- `wrap_in_list` 生成单元素 Python 列表。
- 未启用数组包装的旧接口行为不变。
- 单元素数组主键规范化。
- 13位毫秒时间戳按 `Asia/Shanghai` 转换。
- 三个新接口各自的配置测试。
- 敏感测试数据只使用虚构占位值。

每轮验证：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe -m compileall app tests
.\.venv\Scripts\python.exe -m app.main
git diff --check
```

数据库验收：

- YAML/DB code、enabled、method、path 差异为 0
- batch 和 API log 状态一致
- raw 数量、主键或 hash、`data_date` 符合配置
- checkpoint 正确
- `failed_request_log` 符合实际结果
- named lock 空闲
- 外部事务、活动会话和同步进程均为 0

## 固定边界

- 不重建项目，不回退或覆盖现有修改。
- 写入、修改、确认接口只登记暂缓。
- 含 token、密码、密钥或凭证的响应禁止业务同步。
- 人员或店铺标识接口只允许审核后 raw-only。
- 不读取或输出 `.env`、token 缓存、数据库密码、accessToken 或真实敏感字段值。
- 不批量新增接口。
- 不暂存、提交或推送。
- 基础数据收口后，使用同一机制为产品板块生成新的整板预审清单。
