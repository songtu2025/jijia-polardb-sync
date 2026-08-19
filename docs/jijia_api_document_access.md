# 积加官方 API 文档获取与核对指南

## 目的

在接入积加 API 前，先取得实时官方接口契约，禁止从页面片段、历史配置、示例值或业务经验中猜测参数、分页、限流和响应结构。

本文入口已于 2026-07-29 在本项目环境中只读验证。获取公开文档不读取 .env，不需要业务凭证，也不调用真实业务 API。

## 官方入口

前台页面：

~~~text
https://open.gerpgo.com/document
~~~

前台依赖 JavaScript，直接抓 HTML 通常只有 loading 页面。应使用官方公开 JSON：

~~~text
GET  https://open.gerpgo.com/api/openAdmin/doc/tree
GET  https://open.gerpgo.com/api/openAdmin/doc/detail?id={doc_id}
POST https://open.gerpgo.com/api/openAdmin/doc/apiMap
~~~

- tree：获取板块、接口名称、路径和 doc_id。
- detail：获取单接口完整定义，是实现的主要依据。
- apiMap：交叉核对 API 地图，不能代替 detail。

本项目的 [app/doc_catalog.py](../app/doc_catalog.py) 使用 tree + detail 生成覆盖矩阵。

## 标准流程

### 1. 从本地 catalog 定位 doc_id

~~~powershell
$catalog = Get-Content -LiteralPath 'config\jijia_api_catalog.generated.json' -Raw -Encoding UTF8 | ConvertFrom-Json

$catalog.apis |
  Where-Object {
    $_.doc_id -eq 91 -or
    $_.api_name -match '供应商产品' -or
    $_.api_url -match 'supplierSkuQuote'
  } |
  Select-Object doc_id, menu_path, api_name, api_url, method
~~~

generated catalog 只适合定位和覆盖统计，不保存完整参数树和限流原始字段，也可能早于官方当前版本。重新生成后必须确认 summary.detail_error_count=0。

### 2. catalog 中没有时查询实时 tree

~~~powershell
$env:JIJIA_DOC_QUERY = 'supplierSkuQuote'

@'
import json
import os

import requests


URL = "https://open.gerpgo.com/api/openAdmin/doc/tree"


def walk(nodes, path=()):
    """递归展开官方菜单。"""
    for node in nodes or []:
        name = node.get("menuName") or node.get("menuCode") or ""
        current = path + (name,)
        for api in node.get("apiList") or []:
            yield {
                "doc_id": api.get("id"),
                "menu_path": " > ".join(current),
                "api_name": api.get("name"),
                "api_url": api.get("url"),
            }
        yield from walk(node.get("subMenu") or [], current)


response = requests.get(URL, timeout=30)
response.raise_for_status()
payload = response.json()
if payload.get("code") != 0 or payload.get("error") is True:
    raise RuntimeError("积加官方文档目录返回失败")

query = os.environ["JIJIA_DOC_QUERY"].casefold()
items = [
    item
    for item in walk(payload.get("data") or [])
    if query in json.dumps(item, ensure_ascii=False).casefold()
]
print(json.dumps(items, ensure_ascii=False, indent=2))
'@ | .\.venv\Scripts\python.exe -

Remove-Item Env:JIJIA_DOC_QUERY
~~~

只使用 tree 返回的 doc_id，不从 URL 顺序或历史编号推测。

### 3. 读取实时 detail

该命令只输出契约字段，不输出请求示例、响应示例或业务数据：

~~~powershell
$env:JIJIA_DOC_ID = '91'

@'
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


URL = "https://open.gerpgo.com/api/openAdmin/doc/detail?id={doc_id}"


def flatten(fields, prefix=""):
    """递归展开 children，避免遗漏嵌套字段。"""
    result = []
    for field in fields or []:
        name = str(field.get("name") or "")
        path = f"{prefix}.{name}" if prefix and name else name or prefix
        result.append(
            {
                "path": path,
                "type": field.get("type"),
                "required": field.get("must"),
                "description": field.get("description"),
            }
        )
        result.extend(flatten(field.get("children") or [], path))
    return result


doc_id = int(os.environ["JIJIA_DOC_ID"])
response = requests.get(URL.format(doc_id=doc_id), timeout=30)
response.raise_for_status()
payload = response.json()
if payload.get("code") != 0 or payload.get("error") is True or not payload.get("data"):
    raise RuntimeError(f"积加官方文档 {doc_id} 未返回有效详情")

detail = payload["data"]
contract = {
    "retrieved_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
    "doc_id": detail.get("id"),
    "api_name": detail.get("apiName"),
    "api_url": detail.get("apiUrl"),
    "method": str(detail.get("erpMethod") or "").upper(),
    "op_type": detail.get("opType"),
    "description": detail.get("description"),
    "memo": detail.get("memo"),
    "document_status": {
        "api_status_name": detail.get("apiStatusName"),
        "is_public": detail.get("isPublic"),
        "show_open": detail.get("showOpen"),
    },
    "rate_limit_fields": {
        "limit_times": detail.get("limitTimes"),
        "limit_type_name": detail.get("limitTypeName"),
        "limit_period": detail.get("limitPeriod"),
        "default_limit_times": detail.get("defaultLimitTimes"),
        "default_limit_type_name": detail.get("defaultLimitTypeName"),
        "default_limit_period": detail.get("defaultLimitPeriod"),
    },
    "request_headers": flatten(detail.get("requestHeader") or []),
    "request_body": flatten(detail.get("requestBody") or []),
    "response_body": flatten(detail.get("responseBody") or []),
}
print(json.dumps(contract, ensure_ascii=False, indent=2))
'@ | .\.venv\Scripts\python.exe -

Remove-Item Env:JIJIA_DOC_ID
~~~

requestBodyDemo 和 responseBodyDemo 只能用于理解 JSON 外形，不能证明真实参数来源，禁止直接用于真实探测。

## 接入前核对清单

1. id、apiName、apiUrl 与候选一致。
2. erpMethod 是 HTTP 方法，转大写后写入配置。
3. opType、名称、路径和说明共同证明读写性质。
4. requestBody 每个字段的 name、type、must、description。
5. 递归展开 children，确认分页对象、数组元素和嵌套路径。
6. 页码、页大小、官方单页上限、列表路径和 total 路径。
7. 显式限流；显式值为空时再核对官方默认限流。
8. 主键或 data_hash 策略，以及 data_date 来源。
9. 人员、联系方式、地址、金额、token、密码、密钥等敏感字段类别。
10. apiStatusName、isPublic、showOpen 是否允许公开使用。

官方未明确说明的内容保持未知，不能套用其他接口惯例。

## 分页规则

官方文档决定分页协议和单页上限，不能凭业务规模预设总页数。

1. 从 requestBody 确认分页字段和最大 page size。
2. 从 responseBody 确认列表路径和 total 路径。
3. 新配置保持 enabled=false。
4. 用只读首页预检取得当次 total：

~~~powershell
.\.venv\Scripts\python.exe -m app.main --probe-api <api_code>
~~~

5. 按当次响应计算：

~~~text
required_pages = ceil(total / page_size)
~~~

后续数据增长时，每次都用当次 total 重新计算。禁止写死 120 页或任何猜测总页数，禁止把小样本页数当正式上限。total 缺失或官方说明无效时，保留 total_count=null，并单独确认终止条件。

## 限流规则

detail 返回：

- 显式值：limitTimes、limitTypeName、limitPeriod。
- 默认值：defaultLimitTimes、defaultLimitTypeName、defaultLimitPeriod。

先使用非空显式值；显式值为空时，按官方页面核对默认值。调用速度不得快于官方限流。不要把空值解释为无限流，也不要擅自增加长期业务限制。

单接口验证可以临时放慢，但必须注明这是验证策略，不是官方规则。

## 常见坑

### 前台 HTML 只有 loading

页面依赖 JavaScript。改用 tree 定位，detail 获取契约。

### catalog 缺少完整字段

catalog 是覆盖矩阵，不是完整文档。实现前必须读取实时 detail。

### PowerShell 偶发 TLS 接收错误

Invoke-RestMethod 可能报“基础连接已经关闭”。优先使用项目虚拟环境的 requests 和 30 秒超时；对同一 URL 有限重试。不得关闭 TLS 校验或改用不明镜像。

### success 字段是假值

已验证的成功响应为 HTTP 200、code=0、success=0、error=false 且 data 有值。应检查 HTTP、code、error 和 data，不能直接判断 success 的布尔值。

### 只读取顶层字段

会遗漏 data.rows、数组元素和嵌套分页对象。必须递归展开 children。

### 把 POST 直接判成写操作

部分查询接口使用 POST。必须结合 opType、名称、路径、说明和字段定义判断。

### 使用文档示例参数

示例 ID、日期和数组值不是参数来源。业务参数必须来自语义已证明一致的上游 API 或用户确认来源；没有来源就暂缓。

### 用猜测页数替代 total

固定页数会截断当前数据，也无法适应未来增长。必须用当次 total 计算请求次数并审核分页完整性。

## 证据模板

不记录真实业务参数值和响应值，只记录契约：

~~~text
获取时间：
doc_id：
板块与接口名称：
HTTP 方法与路径：
读取/写入性质及官方证据：
必填参数、类型和真实上游来源：
分页字段、单页上限、列表路径、total 路径：
官方限流字段：
主键或 data_hash 策略：
data_date 来源：
敏感字段类别及保存边界：
预计请求量的计算方式：
仍未被官方文档证明的事项：
结论：可提交最小方案 / 暂缓
~~~

## 安全边界

- 只访问 open.gerpgo.com 的公开文档接口。
- 不读取 .env、token 缓存、数据库密码或真实 API 凭证。
- 不把请求或响应示例值写进业务配置。
- 不输出真实业务参数和敏感字段值。
- 获取文档不等于获准调用业务 API；真实探测仍需只读检查、方案确认和单接口闭环。
