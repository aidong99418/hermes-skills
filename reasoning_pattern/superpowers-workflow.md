# Superpowers 7步开发流水线

## 概述

Superpowers（203K★）是AI Coding Agent的全栈开发方法论，7个skill自动触发串联成流水线：

```
brainstorming → using-git-worktrees → writing-plans →
subagent-driven-development → TDD → requesting-code-review → finishing-a-branch
```

**核心理念**：agent写代码前先问"你到底想做什么"，设计通过后才开始，任务按2-5分钟粒度拆分。

## 流水线详解

### Step 1: brainstorming（构思）
- 写代码前激活，Socratic式追问
- 细化粗糙想法，探索备选方案
- 分块呈现设计供用户确认
- 保存设计文档

### Step 2: using-git-worktrees（隔离分支）
- 设计批准后激活
- 在新分支创建隔离工作空间
- 运行项目初始化，验证干净测试基线

### Step 3: writing-plans（写计划）
- 设计批准后激活
- 拆解成2-5分钟的小任务
- 每个任务有确切文件路径、完整代码、验证步骤
- 计划要足够清晰——即使一个"缺乏项目上下文、没有判断力的热情初级工程师"也能照着做

### Step 4: subagent-driven-development（子Agent驱动开发）
- 有计划后激活
- 每个任务派发一个全新子agent
- **两阶段review**：spec合规性审查 → 代码质量审查
- agent可以自主工作数小时不偏离计划

### Step 5: test-driven-development（TDD）
- 实现过程中激活
- 强制RED-GREEN-REFACTOR循环
- 写测试前删掉先写的代码

### Step 6: requesting-code-review（请求审查）
- 任务之间激活
- 对照计划审查，报告问题按严重程度分
- 关键问题阻塞进度

### Step 7: finishing-a-development-branch（完成分支）
- 任务完成后激活
- 验证测试，提供选项（合并/PR/保留/丢弃）
- 清理工作树

## 设计哲学

| 原则 | 说明 |
|------|------|
| **TDD** | 永远先写测试 |
| **Systematic over ad-hoc** | 流程优于猜测 |
| **Complexity reduction** | 简洁是首要目标 |
| **Evidence over claims** | 验证后才宣告成功 |
| **YAGNI** | You Aren't Gonna Need It |
| **DRY** | Don't Repeat Yourself |

## Skill即代码原则

修改skill内容 = 改变agent行为，需要eval证据证明改进。
skill不接受"理论上更好"——必须是"实际解决过真实问题"。

> 来源：[obra/superpowers](https://github.com/obra/superpowers) 203K stars
