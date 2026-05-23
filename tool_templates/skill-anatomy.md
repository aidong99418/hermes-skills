# Skill Anatomy 最佳实践（四大仓库标准格式）

## 标准SKILL.md格式

```yaml
---
name: skill-name
description: |
  一句话描述这个skill做什么（第三人称）
  Use when + 触发条件（自然语言告诉模型何时调用）
disable-model-invocation: true   # 可选：直接返回指令，不调用模型
---

# Skill标题

## Philosophy（可选）
核心原则，为什么这样做

## Workflow / Process
具体步骤，带编号或表格

## Anti-Patterns / Red Flags
反面教材，告诉模型"不要这样"

## Common Rationalizations
常见自我辩护/借口，要明确驳斥

## Verification（可选）
验证步骤，确保技能生效

## Rules / Composition
使用规则：何时调用、如何组合其他skill
```

## Skill描述的精准写法

```yaml
# ❌ 太宽泛（永远不会被触发）
description: "Helps with testing"

# ✅ 精确触发（多种场景都能命中）
description: "Test-driven development with red-green-refactor loop.
Use when user wants to build features or fix bugs using TDD, mentions
'red-green-refactor', wants integration tests, or asks for test-first development."
```

## 每个Skill必须有的6个组成部分

| 部分 | 必须 | 内容 |
|------|------|------|
| Overview/Philosophy | ✓ | 这个skill做什么，为什么重要 |
| When to Use | ✓ | 何时触发，用什么词触发 |
| Process | ✓ | 编号步骤，含决策树 |
| Common Rationalizations | ✓ | agent会找的借口，明确驳斥 |
| Red Flags | ✓ | 警示信号 |
| Verification | 建议 | 如何确认技能生效 |

## 极简Skill有时最有效

mattpocock/zoom-out仅7行：
```yaml
---
name: zoom-out
description: Tell the agent to zoom out...
disable-model-invocation: true
---
I don't know this area of code well. Go up a layer of abstraction.
Give me a map of all the relevant modules and callers...
```

## 内容复用原则

不在SKILL.md里重复其他skill的内容——直接引用：
```markdown
See [tests.md](tests.md) for examples and [mocking.md](mocking.md)
```

## 质量门槛

顶级skill的PR拒绝率：
- **obra/superpowers: 94%被拒**
- 每个变更需要**eval证据**
- 不接受"理论上有用"——必须实际解决过真实问题

> 来源：obra/superpowers · anthropics/skills · mattpocock/skills · addyosmani/agent-skills 四大仓库共同标准
