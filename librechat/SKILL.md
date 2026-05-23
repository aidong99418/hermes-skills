---
name: librechat
description: LibreChat — 54k⭐，自托管AI对话平台，多渠道/多Agent/语音/视觉/文件上传全支持。触发：自建ChatGPT、语音对话、多AI渠道集成。
version: 1.0.0
tags: [librechat, self-hosted, chatgpt, multi-agent, voice, vision]
triggers: ["LibreChat", "自托管AI", "多渠道对话", "语音对话", "视觉对话"]
---

# LibreChat 架构参考

## 核心定位
LibreChat = 开源自托管 ChatGPT 克隆（54k⭐），支持多渠道、多Agent、语音/视觉/文件上传，部署简单，功能丰富。

## 核心特性

| 特性 | 说明 |
|------|------|
| 多渠道 | OpenAI / Anthropic / Azure / Google / 自定义API |
| 多Agent | AutoGPT / OpenAssistant / 定制Agent |
| 语音对话 | TTS语音输入/输出 |
| 视觉理解 | 图片上传分析 |
| 文件上传 | PDF/代码/文档上传 |
| 预设模板 | 快速切换对话角色 |
| Docker一键部署 | `docker compose up -d` |

## Docker部署

```bash
# 克隆
git clone https://github.com/danny-avila/LibreChat.git
cd LibreChat

# 配置
cp .env.example .env
# 编辑.env填入API Keys

# 启动
docker compose up -d
# 访问 http://localhost:3080
```

## 关键.env配置

```env
# OpenAI
OPENAI_API_KEY=sk-xxx

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxx

# 禁用用户注册（私人使用）
ALLOW_REGISTRATION=false
ALLOW_SOCIAL_LOGIN=false

# 域名（反向代理）
DOMAIN_CLIENT=http://localhost:3080
```

## 多渠道配置示例

```env
# 添加自定义渠道
CUSTOM_MODELS=true
CUSTOM_MODELS_LIST=gpt-4,gpt-4-turbo,claude-3-opus

# 代理（可选）
OPENAI_REVERSE_PROXY=https://your-proxy.com/v1/chat/completions
```

## 与其他方案对比

| 方案 | 复杂度 | 多Agent | 语音 | 推荐场景 |
|------|--------|---------|------|---------|
| LibreChat | ⭐⭐ | ✅ | ✅ | 一站式自建AI平台 |
| ChatBotUI | ⭐ | ✅ | ❌ | 轻量多渠道 |
| OpenWebUI | ⭐ | ❌ | ✅ | 纯本地Ollama |

## 坑/注意事项

1. **.env必须完整**：缺少字段会导致启动失败，首次配置参考官方文档
2. **API Key安全**：生产环境建议用环境变量，不要硬编码
3. **反向代理**：国内需要代理才能访问OpenAI API，换硅基流动等国内渠道
4. **数据库**：默认SQLite，生产环境建议换PostgreSQL
5. **更新**：需要`docker compose pull && docker compose up -d`
