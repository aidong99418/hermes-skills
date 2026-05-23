---
name: cowagent
description: CowAgent微信Agent框架 — 37k⭐，Agent+Memory分离设计，Skills机制，多渠道接入（微信/飞书/钉钉），梦境蒸馏长期记忆。触发：微信Agent、聊天机器人架构、记忆系统设计、多渠道消息聚合。
version: 1.0.0
tags: [wechat, agent, memory, multi-channel, skills]
triggers: ["CowAgent", "微信Agent", "聊天机器人", "多渠道接入", "Agent+Memory分离", "梦境蒸馏"]
---

# CowAgent 架构设计参考

## 核心定位
CowAgent = 微信等IM平台的AI Agent框架（37k⭐），核心：Agent与Memory分离、Skills热插拔、多渠道消息统一处理、长期记忆"梦境蒸馏"机制。

## 核心架构

```
┌─────────────────────────────────────────────────┐
│           消息接入层（Multi-Channel）            │
│   微信 / 飞书 / 钉钉 / Telegram / HTTP Webhook  │
└──────────────────────┬──────────────────────────┘
                       │ 统一消息格式
                       ▼
┌─────────────────────────────────────────────────┐
│              Agent 核心引擎                      │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐│
│  │  Intent解析  │→│  Task规划   │→│  Action  ││
│  └─────────────┘  └─────────────┘  └──────────┘│
└──────────────────────┬──────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ 短时记忆  │ │ 工作记忆  │ │ 长期记忆  │
    │ (Context) │ │(Session) │ │(Dream++) │
    └──────────┘ └──────────┘ └──────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │   Skills 引擎（技能商店）│
           │  热插拔式技能扩展机制    │
           └───────────────────────┘
```

## Agent与Memory分离设计

这是CowAgent最核心的设计理念——**记忆独立于Agent存在**：

### 短期记忆（Context）
- 当前对话窗口内的历史消息
- 用滑动窗口或token上限控制
- LLM直接看到的上下文

### 工作记忆（Session）
- 按session_id隔离的会话状态
- 跨轮次的任务进度跟踪
- 技能间的数据传递

### 长期记忆（Dream++ 梦境蒸馏）
- 将短期经验压缩为结构化知识
- 定期触发（低峰期/定时）
- 压缩算法：extract → abstract → store
- 向量存储，支持语义检索

```python
class DreamDistiller:
    """梦境蒸馏：经验 → 知识的压缩过程"""
    def distill(self, session_log: list[Message]) -> MemoryNode:
        # 1. 从对话日志提取关键信息
        facts = self.extract_facts(session_log)
        # 2. 抽象为通用知识
        knowledge = self.abstract(facts)
        # 3. 存入记忆向量库
        return self.store(knowledge)
```

## Skills机制（热插拔技能）

类似本项目的skill系统，CowAgent支持动态加载技能：

```python
# 安装技能
/skill install code-reviewer
/skill install image-generator

# 技能目录结构
skills/
  code-reviewer/
    __init__.py      # Skill基类
    manifest.toml    # 技能元信息
    prompts/         # 提示词模板
    tools/           # 关联工具
```

### Skill Manifest示例

```toml
[skill]
name = "code-reviewer"
version = "1.0.0"
trigger_keywords = ["review", "代码审查", "PR"]
requires_tools = ["git", "llm"]

[skill.capabilities]
analysis = true
auto_fix = false

[skill.limits]
max_file_size = "1MB"
timeout = "30s"
```

## 多渠道接入

```python
# 统一消息格式
class UnifiedMessage:
    platform: str      # "wechat" | "feishu" | "dingtalk"
    user_id: str       # 平台用户ID
    content: str       # 消息内容
    msg_type: str      # "text" | "image" | "voice"
    timestamp: float

# 各渠道适配器
class WechatAdapter(MessageAdapter)
class FeishuAdapter(MessageAdapter)
class DingtalkAdapter(MessageAdapter)
```

## 与本项目的契合点

| CowAgent特性 | 本项目借鉴点 |
|-------------|------------|
| Agent+Memory分离 | 记忆模块独立，可对接mem0 |
| Dream++梦境蒸馏 | 长期记忆压缩机制 |
| Skills热插拔 | 与hermes-skills机制高度吻合 |
| 多渠道消息统一 | 微信/飞书/钉钉聚合接入 |
| TOML/manifest | 技能元信息配置格式 |

## 快速启动

```bash
git clone https://github.com/zhayujie/CowAgent.git
cd CowAgent
pip install -r requirements.txt

# 配置微信/飞书等渠道
cp config.example.toml config.toml
# 编辑 config.toml 填入Token

# 启动
python run.py
```

## 坑/注意事项

1. **微信平台限制**：个人微信容易被封，用测试账号
2. **飞书/钉钉**：需要企业账号申请Bot
3. **Dream++内存**：梦境蒸馏在低峰期运行，避免影响响应
4. **Skills安全**：第三方skill可能执行任意代码，需要沙箱
5. **多渠道一致性**：不同平台消息格式差异大，适配器要充分测试
