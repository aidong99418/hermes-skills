---
name: librechat
description: LibreChat增强版ChatGPT克隆技能 — 54k星，自托管AI对话平台，支持多渠道/Agents/MCP/多模型聚合，比官方ChatGPT更强大更私密。
triggers:
  - 自托管AI对话
  - 多模型聚合
  - AI对话界面
---

# LibreChat 技能

## 是什么
开源增强版ChatGPT克隆，支持自定义AI模型、多渠道、安全自托管。

## 星数
54k+ ⭐ | danny-avila/LibreChat

## 核心功能
- **多模型支持**：OpenAI/Claude/Gemini/DeepSeek/AWS/Azure等
- **多会话管理**：对话搜索、历史保存
- **Agents模式**：内置AI Agents
- **MCP支持**：Model Context Protocol集成
- **DALL-E图像生成**：内置绘图能力
- **代码解释器**：沙箱代码执行
- **多用户+权限**：团队使用
- **API Actions**：调用自定义API

## Docker部署
```bash
git clone https://github.com/danny-avila/LibreChat.git
cd LibreChat
cp .env.example .env
# 编辑.env配置API密钥
docker compose up -d
```

## 与Hermes对比
LibreChat定位是"人的AI对话界面"，Hermes定位是"AI的NAS控制中枢"。两者不在同一赛道，但Hermes可以调用LibreChat的API做模型聚合。
