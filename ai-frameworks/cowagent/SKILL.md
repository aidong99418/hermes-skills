---
name: cowagent
description: CowAgent架构研究技能 — 超级AI助理框架，37k星，架构与Hermes高度相似。支持多渠道（微信/飞书/钉钉等）+多Agent协作+Skills系统+长期记忆+知识库。重要参考对象。
triggers:
  - CowAgent架构
  - 多Agent框架参考
  - 微信多渠道AI
  - Skills系统设计
  - 长期记忆实现
---

# CowAgent 架构研究

## 基本信息
- 仓库：zhayujie/CowAgent（chatgpt-on-wechat升级版）
- 星数：44k+ ⭐
- 语言：Python
- 协议：MIT

## 核心架构（与Hermes对比）

| 模块 | CowAgent | Hermes | 对Hermes启示 |
|------|----------|--------|------------|
| 多渠道接入 | 微信/飞书/钉钉/企微/QQ/公众号/网页 | Weixin | ✅ 值得学习多渠道架构 |
| Agent核心 | 自主任务规划+工具调用 | brain_thinker三层思考 | 思考模式不同但目标一致 |
| 记忆系统 | 核心记忆+日级记忆+梦境蒸馏 | brain_doc+RAG | 可参考梦境蒸馏思想 |
| Skills系统 | 技能广场+GitHub一键安装 | skill系统 | 架构思路一致 |
| 知识库 | 知识图谱+向量检索 | knowledge_box | 方向一致实现不同 |
| 多模型支持 | DeepSeek/Claude/GPT/Gemini/GLM/Qwen | Ollama+API | 都追求多模型 |
| MCP支持 | ✅ 已支持 | mcporter/native-mcp | 都接入了MCP |

## 记忆系统（值得借鉴）
```
三层记忆：
1. 核心记忆 - 最重要信息，长期保留
2. 日级记忆 - 日常对话摘要
3. 梦境蒸馏 - 自动从日级记忆中蒸馏精华到核心
```

这个"梦境蒸馏"概念很有意思——Hermes的brain_neural网络可能可以借鉴这个思路。

## Skills系统
- 技能市场：https://skills.cowagent.ai/
- 支持从GitHub一键安装
- 对话中可创造新Skills

## 部署方式
```bash
git clone https://github.com/zhayujie/CowAgent.git
cd CowAgent
pip install -r requirements.txt
# 配置config.py（渠道、API密钥等）
python app.py
```

## 对Hermes的价值
1. **多渠道架构**：可以研究其channel层设计，移植到Hermes
2. **记忆蒸馏**：梦境记忆→核心记忆的自动压缩机制
3. **Skills生态**：技能市场+一键安装的设计模式
4. **工具调用**：MCP集成方式

## 注意
CowAgent是商业公司的开源项目，有LinkAI云服务依赖，但核心框架MIT开源可自由使用。
