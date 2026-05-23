# AI团队协作架构（Claude Code Game Studios 700★）

## 核心洞察

**单Agent会话 = 无结构。49个专业Agent + 层级编排 = 真正工作室。**

用户仍然做所有决策，但有团队帮你问对问题、早抓错误、全程保持项目组织。

## 三层架构

```
Tier 1 — 总监（Opus级别，战略层）
  creative-director    technical-director    producer

Tier 2 — 部门主管（Sonnet级别，执行层）
  game-designer        lead-programmer       art-director
  audio-director       narrative-director    qa-lead
  release-manager      localization-lead

Tier 3 — 专家（Sonnet/Haiku，操作层）
  gameplay-programmer  engine-programmer     ai-programmer
  network-programmer   ui-programmer         qa-tester
  ...（按领域细分的专科专家）
```

## 协调规则

| 规则 | 说明 |
|------|------|
| **垂直委托** | 总监→主管→专家，信息层层下达 |
| **横向协商** | 同级Agent可以互相咨询，但不能跨域做约束性决策 |
| **冲突升级** | 分歧上报共同父级（设计→creative-director，技术→technical-director） |
| **变更传播** | 跨域变更由producer协调 |
| **域边界** | Agent不越权修改自己领域之外的文件 |

## 协作协议（自动化非自主）

每个Agent必须遵守：
1. **问** — 先提问，再提方案
2. **展示选项** — 2-4个选项带优缺点
3. **用户决定** — 用户始终做最终决策
4. **先草稿** — 最终化前展示成果
5. **审批** — 未经签字不写任何内容

## 自动化安全（Hooks）

| Hook | 触发时机 | 行为 |
|------|----------|------|
| `validate-commit.sh` | Bash工具(commit) | 检查硬编码/TODO格式/JSON有效性 |
| `validate-push.sh` | Bash工具(push) | 警告受保护分支 |
| `validate-assets.sh` | Write/Edit(assets/) | 验证命名规范 |
| `session-start.sh` | 会话开始 | 显示当前分支+最近提交 |
| `detect-gaps.sh` | 会话开始 | 检测空项目/缺设计文档 |
| `pre-compact.sh` | 上下文压缩前 | 保存进度到active.md |
| `post-compact.sh` | 上下文压缩后 | 从active.md恢复状态 |
| `log-agent.sh` | 子agent启动 | 审计轨迹开始 |
| `session-stop.sh` | 会话关闭 | 归档active.md到会话日志 |

## 路径作用域规则（按文件位置自动强制）

| 路径 | 强制规则 |
|------|----------|
| `src/gameplay/**` | 数据驱动值、delta time、不引用UI |
| `src/core/**` | 热路径零分配、线程安全、API稳定 |
| `src/networking/**` | 服务端权威、版本化消息、安全 |
| `src/ui/**` | 不拥有游戏状态、本地化就绪、可访问性 |
| `prototypes/**` | 宽松标准、必须README、记录假设 |

## 对Hermes的启发

| Game Studios模式 | Hermes适配 |
|-----------------|-----------|
| 三层Agent等级 | 分快手/工具/推理三元组 |
| Hook自动化 | cron job + pre/post script |
| 路径规则 | 按场景自动切换行为 |
| 协作协议 | delegate_task始终先问再动 |
| 审查强度 | full/lean/solo三档 |

> 来源：[Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) 700 stars — 49 agents / 73 skills / 12 hooks / 11 rules
