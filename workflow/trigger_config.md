# 机器猫大脑 - 自适应触发机制 v2.0
# 核心目标：让brain真正成为"活"的思考伙伴，而非静态知识库

## 触发时机（按优先级）

### 🔴 P0 - 每次必检（进入回复流程前）
- 涉及编程/DevOps/Linux/架构/安全 → 先检索brain再回答
- 命令：`python3 /opt/data/scripts/brain_retriever.py "问题关键词"`

### 🟡 P1 - 问题解决后自动沉淀
- 复杂问题（≥5步工具调用）→ 写进brain/scenarios/
- 遇到新错误/坑 → 写进brain/problem_types/
- 工具使用技巧 → 写进brain/tool_templates/
- 成功模式 → 写进brain/reasoning_patterns/

### 🟢 P2 - 每日学习自动更新
- auto_learning跑完 → 自动写brain/scenarios/ai_learn_YYYYMMDD.md
- neural connections自动追加新节点

### 🔵 P3 - 定期维护（每周一次）
- brain缓存满了 → 压缩/归档旧条目
- neural connections去重
- problem_types检查完整性

## 触发关键词映射

| 关键词 | 自动触发brain模块 |
|--------|-----------------|
| 调试/报错/error/失败 | problem_types/debugging.md |
| 写代码/脚本/python/shell | problem_types/coding.md |
| 设计/架构/方案/怎么选 | problem_types/decision.md |
| 分析/统计/报告/数据 | problem_types/data_analysis.md |
| 原理/原理是什么/区别 | problem_types/research.md |
| 学习/arxiv/论文/cve | auto_learning + brain/scenarios |
| Ollama/模型/prompt | brain/reasoning_patterns/llm_notes.md |
| Docker/容器 | brain/reasoning_patterns/devops_notes.md |
| 存储/磁盘/nas | 直接查系统 + 主动告警 |

## 自检清单（每次回复前）

```
1. 这个问题之前遇到过吗？ → brain/scenarios 检索
2. 有没有现成的工具模板？ → brain/tool_templates 检索
3. 这个知识值得沉淀吗？ → 写进brain（条件：董哥可能再遇到 OR 有坑要提醒）
4. 系统有没有隐患？ → 机器猫守护自检
```

## Brain内容质量标准

- problem_types：每个文件≥500字，有判断树+速查表+具体例子
- scenarios：每篇≥300字，有背景+结论+适用范围
- reasoning_patterns：每篇≥200字，有核心技巧+使用场景
- tool_templates：每篇有完整命令示例
- neural：connections.json有实际关联，无孤立节点
