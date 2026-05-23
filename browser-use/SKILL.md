---
name: browser-use
description: AI浏览器自动化框架——95k⭐，让LLM直接控制浏览器执行网页任务（填表/购物/搜索/爬虫/自动化测试）。支持自定义工具、多Agent并发、Cloud部署、Playwright底层、Ollama本地模型。触发：AI浏览器自动化、网页任务自动化、爬虫、自动化测试、绕过反爬。
triggers: ["browser automation", "AI browser agent", "网页自动化", "playwright", "browser agent"]
---

# browser-use 深度分析

## 一句话
让AIagent直接"看"网页、"点"按钮、"填"表单——用自然语言控制真实浏览器。

## 核心数据
| 指标 | 数值 |
|------|------|
| ⭐ Stars | 95,212 |
| 🐍 语言 | Python（>=3.11） |
| 🔧 底层 | Playwright |
| 📦 安装 | `uv add browser-use` |
| 🌐 官网 | browser-use.com |

## 对我们价值评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **契合度** | ⭐⭐⭐⭐⭐ 9/10 | 直接解决"AI要操作网页"的核心需求 |
| **实用性** | ⭐⭐⭐⭐⭐ 9/10 | 填表/爬虫/监控/自动化测试全是刚需 |
| **学习价值** | ⭐⭐⭐⭐ 8/10 | Agent设计模式、Playwright集成、tool calling实战 |
| **集成难度** | ⭐⭐⭐⭐ 8/10 | uv安装即可，本地+Cloud两套方案 |
| **综合** | **8.5/10** | 必挖宝库，重点学习 |

## 能解决什么问题（我们的场景）

### 1. 浏览器自动化任务 ✅
- 自动填表（job申请、问卷）
- 电商下单、购物车操作
- 社交媒体发帖/评论
- 银行/政务网站操作

### 2. AI网页爬虫 ✅（替代传统爬虫）
- 不需要逆向JS、不怕反爬
- AI理解页面结构，自动提取数据
- 支持登录后的页面、Ajax加载内容

### 3. 自动化测试 ✅
- 端到端Web测试
- AI生成测试用例、检测异常

### 4. 价格监控/竞品监控 ✅
- 定时抓取竞品价格变化
- 自动比价提醒

### 5. 客服自动化 ✅
- 自动处理重复性客服任务

## 核心架构

```
User Task → Agent (LLM) → Action History
                            ↓
                      循环执行：
                      1. 获取页面状态（DOM/screenshot）
                      2. LLM决策下一步action
                      3. Playwright执行action
                      4. 重复直到完成
```

**关键组件：**
- `Agent` — 核心大脑，接收task，用LLM决策actions
- `Browser` — Playwright封装，管理Chromium实例
- `Tools` — 自定义工具扩展agent能力
- `ChatBrowserUse()` — 官方优化的LLM（3-5x faster，SOTA accuracy）

## 快速上手

### 安装
```bash
uv init && uv add browser-use && uv sync
uvx browser-use install  # 安装Chromium
```

### 基础用法
```python
from browser_use import Agent, Browser, ChatBrowserUse
import asyncio

async def main():
    browser = Browser()
    agent = Agent(
        task="Find the number of stars of the browser-use repo",
        llm=ChatBrowserUse(),
        browser=browser,
    )
    await agent.run()

asyncio.run(main())
```

### 自定义工具（最实用）
```python
from browser_use import Tools

tools = Tools()

@tools.action(description='Search for a product and return top 3 prices')
def search_product(product: str) -> str:
    return f"Top 3 prices for {product}: ..."

agent = Agent(
    task="Find cheapest RTX 5090 on Amazon",
    llm=llm,
    browser=browser,
    tools=tools,
)
```

### 用本地Ollama（免费）
```python
from browser_use import Agent, Browser
from browser_use import ChatOllama  # 内置支持Ollama

agent = Agent(
    task="你的任务",
    llm=ChatOllama(model="qwen2.5:7b"),
    browser=browser,
)
```

### Cloud模式（绕过反爬）
```python
browser = Browser(use_cloud=True)  # Browser Use云端浏览器
agent = Agent(task="...", llm=llm, browser=browser)
```

### 生产部署 @sandbox
```python
from browser_use import Browser, sandbox, ChatBrowserUse
from browser_use.agent.service import Agent

@sandbox(cloud_proxy_country_code='us')  # 代理+隐身
async def production_task(browser: Browser):
    agent = Agent(task="任务", browser=browser, llm=ChatBrowserUse())
    await agent.run()
```

## 与我们系统的集成点

### 1. 替代wechat-stt的网页操作
browser-use + wechat-stt = 微信语音→理解意图→自动操作对应网页

### 2. 增强mcp-servers
browser-use可作为MCP server暴露工具：
```python
# 包装为MCP server
from browser_use import Agent, Browser

# browser-use的网页操作能力可以通过MCP暴露给其他Agent
```

### 3. 集成auto-learning
自动抓取ArXiv/HN时用browser-use代替requests：
- 更可靠（无JS渲染问题）
- 更智能（AI理解页面）

### 4. 集成CowAgent工作流
```
用户请求 → CowAgent分析 → 需要网页操作 → browser-use执行
```

## 局限性

| 问题 | 说明 |
|------|------|
| 资源占用 | Chromium每个实例约200-500MB，多开需谨慎 |
| 速度 | LLM决策+Playwright执行，比纯API慢 |
| 稳定性 | 页面结构变化可能导致任务失败 |
| 反爬 | 本地模式仍可能被检测，Cloud模式更好 |

## 参考资源
- 官方文档：docs.browser-use.com
- GitHub：github.com/browser-use/browser-use
- Cloud API：cloud.browser-use.com
- Claude Code Skill：`curl`获取AGENTS.md后AI Coding Agent直接使用

## 下一步行动
1. 先在NAS上`uv add browser-use`安装试试基础功能
2. 体验`uvx browser-use init`快速模板
3. 尝试用Ollama本地模型（免费）跑简单任务
4. 考虑Cloud模式做需要登录的复杂任务
