# OpenCode Skill驱动执行模型（addyosmani）

## 核心规则

**技能优先原则**：如果任务匹配某个skill，必须调用它，绝不直接实现。

- Skills位于 `skills/<skill-name>/SKILL.md`
- 永远完整遵循skill指令（不能部分应用）
- 不要"这太小了不需要skill"——只要有1%可能性就检查

## Intent → Skill 映射

| 用户意图 | 触发Skill链 |
|----------|------------|
| 新功能 | spec-driven-development → incremental-implementation → test-driven-development |
| 规划/拆解 | planning-and-task-breakdown |
| Bug/错误 | debugging-and-error-recovery |
| 代码审查 | code-review-and-quality |
| 重构/简化 | code-simplification |
| API/接口设计 | api-and-interface-design |
| UI工作 | frontend-ui-engineering |

## 生命周期隐式命令

OpenCode不支持`/spec`/`/plan`等斜杠命令，agent必须内部遵循生命周期：

- DEFINE → `spec-driven-development`
- PLAN → `planning-and-task-breakdown`
- BUILD → `incremental-implementation` + `test-driven-development`
- VERIFY → `debugging-and-error-recovery`
- REVIEW → `code-review-and-quality`
- SHIP → `shipping-and-launch`

## 编排：Personas/Skills/Commands三层

- **Skills** (`SKILL.md`)：工作流+步骤+退出条件，**怎么做**
- **Personas** (`agents/<role>.md`)：视角+输出格式，**谁来做**
- **Slash Commands**：用户入口，**何时触发**

编排规则：**用户（或slash command）是编排者，Personas不调用其他 Personas**。
唯一支持的多Persona模式：**并行扇出+合并**（/ship命令并发跑code-reviewer/security-auditor/test-engineer再汇总）。

## 最佳实践

- SKILL.md保持在500行以内，详细参考放单独文件
- 脚本不占context（只有输出占），代码多的放脚本
- 每个skill用kebab-case命名（`web-quality`）
- 文件引用只支持一层深度

> 来源：[addyosmani/prompts](https://github.com/addyosmani/prompts) — OpenCode skill驱动执行模型设计
