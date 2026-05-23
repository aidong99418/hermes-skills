# 游戏工作室多Agent架构（Claude Code Game Studios）

## 核心定位

**单Agent会话 = 无结构**。Claude Code Game Studios 通过 49个专业Agent + 层级编排，让AI会话拥有真实工作室的组织结构。

- 49 agents · 73 skills · 12 hooks · 11 rules · 41 templates
- 用户始终做决策，Agent提供结构和专业能力

---

## 三层Agent等级

```
Tier 1 — 总监（Opus级别，战略层）
  creative-director    technical-director    producer

Tier 2 — 部门主管（Sonnet级别，执行层）
  game-designer        lead-programmer       art-director
  audio-director       narrative-director    qa-lead
  release-manager      localization-lead

Tier 3 — 专家（Sonnet/Haiku，操作层）
  gameplay-programmer  engine-programmer     ai-programmer
  network-programmer   ui-programmer         systems-designer
  level-designer       technical-artist      qa-tester
  ...（23个专科专家）
```

### 引擎专家集（按项目选用）

| 引擎 | Lead Agent | 专项 |
|------|-----------|------|
| **Godot 4** | godot-specialist | GDScript, Shaders, GDExtension |
| **Unity** | unity-specialist | DOTS/ECS, Shaders/VFX, Addressables |
| **Unreal 5** | unreal-specialist | GAS, Blueprints, Replication, UMG |

---

## 73斜杠命令分类

| 类别 | 命令 |
|------|------|
| **入职&导航** | `/start` `/help` `/project-stage-detect` `/setup-engine` `/adopt` |
| **游戏设计** | `/brainstorm` `/map-systems` `/design-system` `/quick-design` `/review-all-gdds` |
| **艺术&资产** | `/art-bible` `/asset-spec` `/asset-audit` |
| **UX设计** | `/ux-design` `/ux-review` |
| **架构** | `/create-architecture` `/architecture-decision` `/architecture-review` |
| **故事&冲刺** | `/create-epics` `/create-stories` `/dev-story` `/sprint-plan` `/story-done` |
| **审查** | `/design-review` `/code-review` `/balance-check` `/scope-check` `/gate-check` |
| **QA&测试** | `/qa-plan` `/smoke-check` `/soak-test` `/regression-suite` `/test-evidence-review` |
| **发布** | `/release-checklist` `/launch-checklist` `/changelog` `/patch-notes` `/hotfix` |
| **团队编排** | `/team-combat` `/team-narrative` `/team-ui` `/team-release` `/team-polish` |

---

## 协调规则

| 规则 | 说明 |
|------|------|
| **垂直委托** | 总监→主管→专家，信息层层下达 |
| **横向协商** | 同级Agent互相咨询，但不能跨域做约束性决策 |
| **冲突升级** | 设计分歧→creative-director，技术分歧→technical-director |
| **变更传播** | 跨域变更由producer协调 |
| **域边界** | Agent不越权修改自己领域之外的文件 |

---

## 协作协议（用户始终控制）

```
1. 问   — 先提问，再提方案
2. 选项 — 2-4个方案带优缺点
3. 你决定 — 用户始终做最终决策
4. 草稿 — 最终化前展示成果
5. 审批 — 未经用户签字不写任何内容
```

---

## 自动化安全（12 Hooks）

| Hook | 触发 | 行为 |
|------|------|------|
| `validate-commit.sh` | Bash(commit) | 检查硬编码值/TODO格式/JSON有效性 |
| `validate-push.sh` | Bash(push) | 警告受保护分支推送 |
| `validate-assets.sh` | Write/Edit(assets/) | 验证命名规范+JSON结构 |
| `session-start.sh` | 会话开启 | 显示分支+最近提交 |
| `detect-gaps.sh` | 会话开启 | 检测空项目/缺设计文档 |
| `pre-compact.sh` | 上下文压缩前 | 保存进度到active.md |
| `post-compact.sh` | 上下文压缩后 | 从active.md恢复状态 |
| `log-agent.sh` | 子agent启动 | 审计轨迹开始 |
| `log-agent-stop.sh` | 子agent停止 | 审计轨迹完成 |
| `session-stop.sh` | 会话关闭 | 归档active.md到会话日志 |
| `notify.sh` | 通知事件 | Windows系统通知 |
| `validate-skill-change.sh` | Write(skills/) | 建议运行`/skill-test` |

> 所有hook在命令/路径不相关时立即exit 0（正常行为，非性能问题）

---

## 路径作用域规则（11条）

| 路径 | 强制规则 |
|------|---------|
| `src/gameplay/**` | 数据驱动值、delta time、不引用UI |
| `src/core/**` | 热路径零分配、线程安全、API稳定 |
| `src/ai/**` | 性能预算、可调试性、数据驱动参数 |
| `src/networking/**` | 服务端权威、版本化消息、安全 |
| `src/ui/**` | 不拥有游戏状态、本地化就绪、无障碍 |
| `design/gdd/**` | 必须8个章节、公式格式、边缘情况 |
| `tests/**` | 测试命名、覆盖率要求、fixture模式 |
| `prototypes/**` | 宽松标准、README必须、假设记录 |

---

## 41文档模板

覆盖 GDD、UX规格、ADR、冲刺计划、HUD设计、可访问性、生成文档等。

---

## 审查强度三档

| 模式 | 说明 |
|------|------|
| `full` | 所有总监门禁（全面质量） |
| `lean` | 仅阶段门禁（效率优先） |
| `solo` | 无自动审查（单Agent快速迭代） |

在`/start`时设置，或通过`--review solo`覆盖任何skill。

---

## 对Hermes的启发

| Game Studios模式 | Hermes适配 |
|-----------------|-----------|
| 三层Agent等级 | 分快手/工具/推理三元组 |
| Hook自动化 | cron job + pre/post script |
| 路径作用域规则 | 按场景自动切换行为 |
| 协作协议 | delegate_task始终先问再动 |
| 审查强度 | full/lean/solo三档 |
| 团队编排 | 多skill并行派发 |
| 会话状态持久化 | active.md + session日志 |

> 来源：[Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) — MIT License · 700+ stars
