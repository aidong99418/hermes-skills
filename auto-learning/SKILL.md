---
name: ollama-auto-learning
description: 本地 Ollama 大模型自动学习系统 — 每日抓取 ArXiv + CVE/HN 安全资讯，Ollama分析生成报告；Ollama不可用时自动切换SiliconFlow(DeepSeek-V2.5)兜底，永不中断。核心教训：永远用 qwen2.5:3b做日常任务；只用HTTP API；Ollama失败自动API兜底。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Ollama, AI, Security, Automation, Cron]
---

# Ollama 自动学习系统

## 架构

```
用户 → Hermes(常驻主控) → 调度 Ollama → 整合结果 → 回用户
```

**核心原则：**
- Hermes 永远是唯一入口，永远常驻待命
- Ollama 是后台 worker pool，由 Hermes 协调
- 绝不把任务完全丢给模型后自己退出

## 快速上手

```bash
# 手动运行今日学习
python3 /opt/data/scripts/auto_learning.py

# 设置每日定时任务（每天早上9点）
cronjob create --name "每日自动学习" --schedule "0 9 * * *"
```

## 关键经验教训（踩坑记录）

### ⚡ 模型选择
- **默认用 `qwen2.5:3b-instruct-q4_K_M`** — 速度最快(~5秒)，日常任务够用
- `qwen2.5:7b` 和 `deepseek-r1` 生成慢(30s+)，容易 timeout
- Ollama 每次调用超时设 180 秒

### 📦 内容存储格式（重要！）
- **报告/数据均为原始 Markdown/JSON，无压缩**
- 存储路径：`/volume2/数据备份/AI技术学习/` 和 `/volume2/数据备份/白帽技术学习/`
- 每日报告命名：`YYYY-MM-DD_AI技术学习报告.md`、`YYYY-MM-DD_白帽技术学习报告.md`
- 若需压缩，用 `gzip` / `bz2` 手动压缩，或在备份脚本中加压缩步骤（但会增加读取延迟）

### 🔧 常见 bug
- **KeyError 'url'** — 安全资讯条目没有 url 字段，用 `.get('url')` 保险
- **curl timeout** — 网络请求加 `--max-time 15`
- **Ollama timeout** — subprocess 的 curl 超时 + python timeout 双保险；深度学习每篇耗时 5-10 分钟，需 timeout ≥ 1800s
- **ArXiv URL 编码** — 多词查询必须用 `urllib.parse.quote()`，否则 "URL can't contain control characters"
- **并发 Ollama 调用** — 必须用 threading + 锁，同一模型不能并发调用；不同模型可安全并行（建议最多3个同时）

### 📁 输出目录
```
/volume2/数据备份/
├── AI技术学习/    → 2026-05-16_AI技术学习报告.md
├── 白帽技术学习/  → 2026-05-16_白帽技术学习报告.md
└── 2026-05-16_每日学习简报.md
```

### 🔄 数据源
- ArXiv (cs.CL, cs.LG, cs.AI, cs.CV) — AI 技术论文
- NVD CVE — 安全漏洞数据
- Exploit-DB RSS — 漏洞利用信息
- Hacker News — 安全社区热帖

## Ollama API 调用规范（铁则）

```bash
# 生成文本
curl -s --max-time 60 http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:3b-instruct-q4_K_M","prompt":"问题","stream":false}'

# 获取嵌入向量（需 nomic-embed-text）
curl -s --max-time 15 http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"文本"}'

# 拉取模型（通过API，禁止 ollama CLI）
curl -X POST http://localhost:11434/api/pull \
  -d '{"name":"模型名","stream":false}'
```

**环境判断：** 当前是**宿主机直跑**环境，Ollama 端点为 `localhost:11434`（`host.docker.internal` 在此环境不可用）。

## RAG 知识库

```bash
# 构建索引（扫描已有报告，向量化存入本地）
python3 /opt/data/scripts/rag_lite.py build

# 增量更新
python3 /opt/data/scripts/rag_lite.py update

# 检索（完全本地，零API消耗）
python3 /opt/data/scripts/rag_lite.py search "AI Agent最新进展"

# 查看索引状态
python3 /opt/data/scripts/rag_lite.py stats
```

`rag_lite.py` 只用 Python 标准库，无需 faiss。`rag_knowledge.py` 可选，依赖 faiss-cpu。

## 两套学习脚本

### 脚本路径
| 脚本 | 路径 | 特点 |
|------|------|------|
| 轻量日常学习 | /opt/data/scripts/auto_learning.py | 简单串行，qwen2.5:3b 单一模型 |
| 深度并行学习 | /opt/data/scripts/deep_learning.py | 6模块，3模型并行（qwen2.5:3b + qwen2.5:7b + deepseek-r1） |

### 自动学习工作流（推荐）
```bash
# 注意：timeout 至少 1800（30分钟），脚本会自动重试直到完成
0 4 * * *  python3 /opt/data/scripts/deep_learning.py  # 深度并行学习（cs.AI/CL/CV/LG等分类轮询）
10 4 * * * python3 /opt/data/scripts/rag_lite.py update  # 增量更新RAG索引
```

## 深度并行学习 Pipeline（deep_learning.py）

6步流水线，数据源 + 并行模型分析：

```
[1/6] ArXiv 论文抓取 (5主题 × 8-12篇)
      主题：LLM/AI Agents、Reasoning/RAG、Code Generation、
           Multimodal/Fine-tuning、AI Safety
[2/6] 安全资讯抓取 (CVE NVD + Hacker News + GitHub Trending)
[3/6] qwen2.5:3b 并行分析 AI 论文（多线程）
[4/6] qwen2.5:7b 并行深度分析（多线程）
[5/6] deepseek-r1 生成综合专家洞见
[6/6] 保存报告 + 更新 RAG 知识库
```

### 超时与重试（重要经验）
- 每篇论文需 Ollama 调用 **6次**（摘要+4阶段+综合），每篇实际耗时约 5-10 分钟
- cron 默认 timeout=300s 严重不足；即使 timeout=600s 也会超时
- **脚本是幂等的**：按 ArXiv ID 查重，已保存的文件会跳过，重复运行安全
- **最佳实践**：
  - cron 任务用 `timeout=1800`（30分钟）或更高
  - 或接受多次自动重试——脚本从中断处继续，直到看到 `深夜深度学习完成`
  - `batch=N` 实际执行**多轮** 2-paper 批次，直到全部论文处理完毕
  - 日志中每轮会显示 `[1/2]`、`[2/2]`、再进入下一轮直到 `本次学习 1 篇` 收尾

### 并发安全规则：
- 同一模型：线程锁保护，禁止并发调用
- 不同模型：可安全并行，建议最多3个同时跑
- 超时：每模型独立 120s 超时兜底，单个卡住不影响其他

### 深度并行学习 Pipeline（deep_learning.py）
```bash
python3 /opt/data/scripts/auto_learning.py
```

单模型串行流程：ArXiv → CVE → HN → qwen2.5:3b 分析 → 保存报告

## 添加新模型后的更新
1. 通过 API 拉取：`curl -X POST http://localhost:11434/api/pull -d '{"name":"xxx"}'`
2. 测试速度：`curl --max-time 60 http://localhost:11434/api/generate -d '{"model":"xxx","prompt":"test","stream":false}'`
3. 速度 <15秒 → 可加入 pipeline；否则 → 仅用于需深度推理的单独任务
