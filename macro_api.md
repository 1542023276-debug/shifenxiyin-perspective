> **随包说明**：本文件是服务方提供的官方接口文档，收编进 skill 目录供自助配置 API Key、核对接口与指标清单。正文与官方文档一致（收录于 2026-09-08）。
> 配置 Key：见 §2 的公开示例 apikey，写入本 skill 目录下 `macro_apikey.txt` 首行即可（该 key 由官方文档明文公开）。

# 吸引子宏观数据服务 API 文档

## 1. 基本信息

| 项目 | 内容 |
|------|------|
| **Base URL** | `https://jackal.attractorcap.com/crusty` |
| **数据格式** | JSON（UTF-8） |

> 接口经统一网关（Kong）暴露，路径前缀为 `crusty`。

## 2. 认证方式

采用 **API Key** 认证，请求需在 HTTP Header 携带：

```
apikey: cXa5FY63HOlWXiUV7iNgY5p42tr4QCpu
```

未携带或 Key 无效时返回 `401`。

## 3. 统一响应格式

成功：

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | Boolean | `true` 表示成功 |
| `message` | String | 响应消息 |
| `data` | Any | 业务数据，类型视接口而定 |

失败：

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | Boolean | `false` |
| `error.code` | String | 错误码（`VALIDATION_ERROR`/`NOT_FOUND`/`INTERNAL_ERROR` 等） |
| `error.message` | String | 错误描述 |
| `error.details` | Object | （可选）详细错误信息 |

## 4. 接口详情

### 4.1 宏观指标最新数据

按 secId 查询宏观指标最新结构化数据。

**接口地址**

```
POST /macro/latest
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sec_ids` | Array[String] | 是 | 宏观指标 secId 列表，未知 secId 会被忽略（不报错） |

**请求示例**

```json
{ "sec_ids": ["att_00000042", "att_00000039"] }
```

**响应 `data` 字段说明**（平铺数组，每个 secId 对应一项）

| 字段 | 类型 | 说明 |
|------|------|------|
| `secId` | String | 指标ID |
| `secName` | String | 指标名称（如 `中国-物价`） |
| `field` | String | 指标字段（固定为 `value`） |
| `tradeDate` | String | 最新交易日（`YYYY-MM-DD`） |
| `value` | Number | 最新指标值，已归一化至 [-1, 1]，保留 4 位 |
| `state` | String | 当期状态：`上升` / `中性` / `下降` |
| `stateChange` | String/null | 相对上期的状态变化：`维持` / `转中性` / `转入上升` / `转入下降`；历史不足两期时为 `null` |

**响应示例**

```json
{
  "success": true,
  "message": "宏观指标最新数据获取成功",
  "data": [
    {
      "secId": "att_00000042",
      "secName": "中国-物价",
      "field": "value",
      "tradeDate": "2026-08-31",
      "value": 0.95,
      "state": "上升",
      "stateChange": "维持"
    }
  ]
}
```

**可查询指标清单**

以下为 `/macro/latest` 可查询的完整指标清单（secId → secName），由服务配置 `macro.chinaMacro`（中国，27 项）与 `macro.globalMacro`（全球，24 项）驱动。

中国宏观指标：

| secId | secName |
|-------|---------|
| `att_00000366` | 中国-产能利用趋势 |
| `att_00003490` | 中国-产能利用水平 |
| `att_00000981` | 中国-房地产 |
| `att_00000363` | 中国-就业 |
| `att_00000055` | 中国-库存动力指数 |
| `att_00003388` | 中国-库存周期 |
| `att_00000980` | 中国-企业利润 |
| `att_00000979` | 中国-市场风险偏好 |
| `att_00000042` | 中国-物价 |
| `att_00003483` | 中国-服务业景气度 |
| `att_00000045` | 中国-信用环境 |
| `att_00000977` | 中国-信用环境预警 |
| `att_00003318` | 中国-信用数量 |
| `att_00003478` | 中国-货币需求 |
| `att_00000049` | 中国-资金利率 |
| `att_00000978` | 中国-资金利率预警 |
| `att_00000039` | 中国-总需求 |
| `att_00003378` | 中国-总需求预警 |
| `att_00001049` | 中国-项目投资 |
| `att_00003413` | 中国-外部金融条件 |
| `att_00000052` | 新兴市场外部金融条件 |
| `att_00001068` | 中国-流动性 |
| `att_00000923` | 中国-航运运价（干散货） |
| `att_00000927` | 中国-航运运价（集装箱） |
| `att_00000369` | 中国-财政政策力度 |
| `att_00001797` | 中国-货币政策倾向 |
| `att_00003510` | 中国-内需 |

全球宏观指标：

| secId | secName |
|-------|---------|
| `att_00000372` | 美国-财政政策力度 |
| `att_00000985` | 美国-货币政策倾向 |
| `att_00000984` | 美国-市场风险偏好 |
| `att_00000064` | 美国-物价 |
| `att_00000061` | 美国-消费就业周期 |
| `att_00000067` | 美国-信用环境 |
| `att_00000983` | 美国-信用环境预警 |
| `att_00000058` | 美国-制造业周期 |
| `att_00003382` | 美国-制造业周期预警 |
| `att_00000070` | 美国-资金利率 |
| `att_00003480` | 美国-资金利率预警 |
| `att_00003404` | 美国-库存动力指数 |
| `att_00001069` | 全球-美元流动性 |
| `att_00003416` | 全球-风险偏好指数 |
| `att_00003385` | 欧洲-制造业周期预警 |
| `att_00003407` | 欧洲-物价周期 |
| `att_00003410` | 欧洲-消费就业周期 |
| `att_00003459` | 欧洲-资金利率 |
| `att_00003465` | 欧洲-流动性 |
| `att_00003454` | 欧洲-信用价格 |
| `att_00003451` | 欧洲-信用价格预警 |
| `att_00003457` | 欧洲-财政政策 |
| `att_00003462` | 欧洲-货币政策 |
| `att_00003468` | 欧洲-市场风险偏好 |

### 4.2 健康检查

**接口地址**

```
GET /macro/health
```

**请求参数**

无

**响应 `data` 字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `service` | String | 服务名（`macro_service`） |
| `status` | String | `healthy` |
| `initialized` | Boolean | 初始化标记 |
| `timestamp` | String | 检查时间 |

**响应示例**

```json
{
  "success": true,
  "message": "Health check completed",
  "data": {
    "service": "macro_service",
    "status": "healthy",
    "initialized": true,
    "timestamp": "2026-09-08T14:43:43.330461"
  }
}
```

## 5. 错误码说明

| HTTP 状态码 | 含义 |
|--------|------|
| `200` | 请求成功 |
| `400` | 参数校验失败（如缺少/格式错误的 `sec_ids`） |
| `401` | 认证失败（apikey 缺失或无效） |
| `404` | 路径不存在 |
| `429` | 请求超限（见 §6 限流说明） |
| `500` | 服务器内部错误 |

## 6. 限流说明

网关对每个 **API Key** 施加访问限流，配额如下：

| 维度 | 限额 |
|------|------|
| 每秒 | 10 次 |
| 每分钟 | 100 次 |
| 每天 | 1000 次 |

> 限流在网关层按 API Key 计数，`/macro/latest` 与 `/macro/health` 共享同一配额。

**超限返回**

```
HTTP 429 Too Many Requests
Retry-After: <秒数>
```

```json
{ "message": "API rate limit exceeded" }
```

**限流响应头**（每次响应均携带，可用于调用方自我控速）

| 响应头 | 说明 |
|------|------|
| `X-RateLimit-Limit-Second` / `X-RateLimit-Remaining-Second` | 每秒限额 / 当前剩余 |
| `X-RateLimit-Limit-Minute` / `X-RateLimit-Remaining-Minute` | 每分钟限额 / 当前剩余 |
| `X-RateLimit-Limit-Day` / `X-RateLimit-Remaining-Day` | 每天限额 / 当前剩余 |
| `RateLimit-Limit` / `RateLimit-Remaining` / `RateLimit-Reset` | 触发档位限额 / 剩余 / 重置秒数 |
| `Retry-After` | 仅 429 时返回，建议等待秒数 |

## 7. 调用示例

### 查询宏观指标最新数据

```bash
curl -X POST https://jackal.attractorcap.com/crusty/macro/latest \
  -H "apikey: cXa5FY63HOlWXiUV7iNgY5p42tr4QCpu" \
  -H "Content-Type: application/json" \
  -d '{"sec_ids":["att_00000042"]}'
```

### 健康检查

```bash
curl https://jackal.attractorcap.com/crusty/macro/health \
  -H "apikey: cXa5FY63HOlWXiUV7iNgY5p42tr4QCpu"
```

## 8. 注意事项

1. **Content-Type**：POST 请求需携带 `Content-Type: application/json`。
2. **小驼峰命名**：参数与字段采用小驼峰（`secIds`、`tradeDate`）。
3. **未知 secId**：会被静默忽略，不会报错；全部未知时 `data` 为空数组。
4. **状态语义**：`state` 由最新一期 `value` 符号决定，`stateChange` 描述上一期到当期的跳变。
5. **限流配额**：见 §6，超限时建议按 `Retry-After` 头等待后重试，或根据 `X-RateLimit-Remaining-*` 提前控速。
