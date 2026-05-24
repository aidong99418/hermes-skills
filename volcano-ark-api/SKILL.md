---
name: volcano-ark-api
description: 火山引擎ARK大模型API接入 — 模型发现+可用性检查+接入配置。触发：接入火山引擎豆包/Seed等模型API。
triggers:
  - 火山引擎
  - volcano
  - doubao
  - 豆包API
  - ark API
---

# 火山引擎 ARK API 接入指南

## API基础信息
- **Base URL**: `https://ark.cn-beijing.volces.com/api/v3`
- **认证**: `Authorization: Bearer <ARK_API_KEY>`（格式：`ark-xxx`）
- **模型列表**: `GET /models`

## ⚠️ 关键发现：API列表≠已开通
火山引擎API的`/models`接口返回所有可用模型，但**不代表你的账号已开通**。
未开通的模型会返回错误：
```
{"error":{"code":"ModelNotOpen","message":"Your account has not activated the model XXX"}}
```

**必须先在控制台开通模型**才能调用：
1. 登录 https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement
2. 找到目标模型，点"开通"
3. 开通后API才能调用

## 当前账号可用模型（2026-05-24）
账号ID: 2121292784

```
doubao-1-5-lite-32k-250115     # LLM轻量
doubao-1-5-pro-32k-250115      # LLM主力，支持函数调用
doubao-1-5-vision-pro-32k-250115  # VLM视觉
doubao-seed-1-6-flash-250828   # VLM最新
doubao-seed-1-6-251015         # VLM主力
doubao-seedance-1-0-pro-250528 # 视频生成
doubao-embedding-vision-250615 # 向量嵌入
doubao-seed-1-6-vision-250815  # VLM
doubao-1-5-pro-32k-character-250715 # 角色扮演
```

## 接入Hermes配置示例

```yaml
# config.yaml 添加volcano provider
providers:
  volcano:
    provider: volcano
    base_url: https://ark.cn-beijing.volces.com/api/v3
    api_key: ark-3d19f9a3-f0cb-435e-a08a-048e31381b47-1336d
    model: doubao-seed-1-6-251015
    api_mode: chat
    max_tokens: 8000

# 支持的模型ID参考
LLM对话:     doubao-1-5-pro-32k-250115
VLM视觉:    doubao-seed-1-6-251015
视频生成:    doubao-seedance-1-0-pro-250528
嵌入向量:    doubao-embedding-vision-250615
```

## 测试命令
```bash
curl -s "https://ark.cn-beijing.volces.com/api/v3/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ark-YOUR-KEY" \
  -d '{"model":"模型ID","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

## 与wisemodel对比
| | wisemodel | 火山引擎 |
|--|-----------|---------|
| 模型 | MiniMax系列 | 豆包/Seed系列 |
| 视觉 | minimax-m2.5-highspeed | doubao-seed-1-6 |
| 视频 | ❌ | doubao-seedance系列 |
| 免费额度 | 不确定 | 需查控制台 |
| 接入复杂度 | 已通 | 需开通模型 |

## 接入建议
- 火山引擎VLM（doubao-seed）适合作为Hermes视觉备选，262K上下文超长
- 视频生成模型适合内容创作场景
- 需先在控制台开通才能用
