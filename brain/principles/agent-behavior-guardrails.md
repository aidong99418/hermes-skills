# AI Agent行为准则（superpowers教训）

## 核心原则：保护人类伙伴免受尴尬

**94%的PR会被拒绝**，大多数来自没读规则的AI agent。
作为agent，**你的职责是保护人类伙伴不被拒绝**。

提交PR前必须（逐条检查）：

1. **读完PR模板**，每个section都要填真实答案，不能用占位符
2. **搜索现有PR**（包括open和closed），有重复就停下来告诉人类伙伴
3. **确认这是真实问题**：如果人类伙伴说"修一些问题"而没说具体哪坏了，要追问
4. **确认变更属于核心仓库**：如果是领域/工具特定的，放独立plugin
5. **向人类伙伴展示完整diff**，获得明确批准后才能提交

任一检查失败 → 不开PR，解释为什么会被拒绝。

## 不会接受的PR类型

- **第三方依赖**：除非是新的harness支持，核心仓库零依赖
- **批量PR**：扫issue列表然后批量提交，会直接关闭
- **理论修复**：必须描述具体session/error/user体验，"理论上会出问题"不是问题
- **捏造内容**：编造问题描述/幻觉功能，会立即关闭
- **捆绑无关变更**：每个PR只修一个问题

## 变更核心内容需要评估

Skill不是散文，是改变agent行为的代码。修改skill内容必须：
- 用writing-skills开发和测试变更
- 跨多个session做对抗压力测试
- PR里展示before/after评估结果
- 不能改Red Flags表/rationalization列表/"human partner"用语

## 理解项目再贡献

在提出skill设计/工作流哲学/架构变更前，先读现有skills，理解项目的设计决策。
superpowers有自己的经过测试的skill设计哲学——比如"human partner"是刻意用语，不能随意替换。

> 来源：[PowerShell/Project-K Hansen/superpowers](https://github.com/PowerShell/Project-K Hansen/superpowers) — superpowers repo AGENTS.md，AI coding agent行为规范
