---
name: brain-system-maintenance
description: 机器猫大脑系统日常维护 — 让brain真正运转起来的检查清单和更新流程
tags: [brain, maintenance, knowledge-management]
owner: hermes
created: 2026-05-23
version: 1.0
---

# 机器猫大脑维护手册

## 大脑架构

```
/opt/data/brain/
├── reasoning_patterns/     # 推理模式（核心技巧+思路）
│   ├── content/            # 实际知识（coding_patterns, python_mastery等）
│   └── ai_insights_*.md    # 每日学习提炼
├── scenarios/              # 场景案例（解决过的问题）
│   ├── shell_scripting.md
│   ├── docker_devops.md
│   └── ai_learn_YYYYMMDD.md # auto_learning每日写
├── problem_types/          # 问题类型决策树
│   ├── debugging.md        # 调试判断树
│   ├── coding.md           # 编码流程
│   ├── decision.md         # 架构决策
│   ├── research.md         # 研究流程
│   └── data_analysis.md    # 数据分析
├── tool_templates/         # 工具使用模板
├── neural/
│   ├── connections.json    # 关联图谱
│   └── inference_paths.json
└── trigger_config.md       # 触发规则
```

## 每日自动维护

auto_learning.py 跑完后自动：
1. 写 `scenarios/ai_learn_YYYYMMDD.md`（AI学习案例）
2. 写 `scenarios/security_learn_YYYYMMDD.md`（安全学习案例）
3. 写 `reasoning_patterns/ai_insights_YYYYMMDD.md`（推理模式）
4. 追加neural connections
5. 重建brain缓存

## 手动维护命令

```bash
# 重建brain缓存
cd /opt/data/scripts && python3 -c "from brain_retriever import BrainRetriever; r=BrainRetriever(rebuild=True); print(f'{len(r.chunks)} chunks')"

# 测试检索
python3 /opt/data/scripts/brain_retriever.py "关键词"
```

## 问题类型扩展

扩展 problem_types 时：
1. 写 MD 文件（判断树+速查表+例子）≥500字
2. 写同名 JSON 文件（keywords+trigger_file）
3. 重建缓存
