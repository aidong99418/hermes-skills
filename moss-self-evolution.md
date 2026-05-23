# MOSS: 源码级自进化Agent

> 核心来源: arXiv 2605.22794 | 2026-05-21 | Qianshu Cai et al.

## 核心发现

### 问题：现有自进化只改文本层，永远触不到根因

现有Agent系统部署后静态不变，失败反复出现，直到人工发版修复。自进化方案（如修改skill/prompt/memory）全部局限在**文本层**——但路由逻辑、Hook顺序、状态不变量都写在代码里，文本层根本摸不到。

```python
# 文本层永远够不到的：状态机/路由/调度 都在代码
if intent == "file_operation" and context["dangerous"]:
    raise PermissionError  # ← 这类结构性问题文本层无法修复
```

### MOSS方案：源码级自我重写

Agent运行时能修改自己的源码（Python harness），而不只是改skill文件。

**三层进化能力：**
1. **文本层** - skill / prompt / memory（现有方案）
2. **Harness层** - Agent执行框架（新增）
3. **工具层** - 工具本身的行为（新增）

```python
# Agent可以自己重写自己的逻辑
class AgentHarness:
    def rewrite_routing(self, new_route):
        # 直接改执行框架，而不是改配置
        self.router = DynamicRouter(new_route)
        patch_source(self.__class__, 'router', new_route)
```

## 对机器猫系统的启发

| MOSS发现 | 机器猫现状 | 改进方向 |
|---------|---------|---------|
| 文本层无法修复结构性问题 | Brain/skill都在文本层 | 考虑让Agent能改自己的调度逻辑 |
| Harness层是进化盲区 | 任务执行依赖固定路由 | 学习路由自己也要能升级 |
| 自我重写需安全边界 | 无自修改机制 | 定义进化安全边界（哪些可改/哪些锁死）|

## 核心原则

1. **自进化必须覆盖执行框架**，否则结构性问题永远无法根治
2. **Turing完备性是进化的天花板**——文本层是执行层真子集
3. **安全边界先行**——自我重写必须有只读铁律，否则会自我破坏

---
*提炼自Hermes学习系统 | 2026-05-23*
