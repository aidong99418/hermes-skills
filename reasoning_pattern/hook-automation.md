# Hook自动化系统

> 来源: Claude Code Game Studios — 12个自动化钩子

## 核心理念

自动化安全检查 + 会话生命周期管理，让Agent在关键时刻自动触发验证，用户无需手动介入。

## Hook类型分类

### 1. 预执行钩子（PreToolUse）
在危险操作前自动拦截：

```
validate-commit.sh   → git commit前: 硬编码值/TODO格式/JSON合法性
validate-push.sh     → git push前: 警告受保护分支
validate-assets.sh   → 资源文件变更后: 命名规范/JSON结构
validate-skill-change.sh → skill文件变更后: 建议运行测试
```

### 2. 会话生命周期钩子

```
Session Start  → 显示分支状态 + 最近提交 (session-start.sh)
Detect Gaps    → 检测新项目 → 建议 /start (detect-gaps.sh)
Pre Compact    → 压缩前保存进度到 active.md (pre-compact.sh)
Post Compact   → 压缩后恢复 active.md (post-compact.sh)
Session Stop   → 归档active.md + 记录git活动 (session-stop.sh)
```

### 3. 监控钩子

```
log-agent.sh       → Agent启动时记录审计日志
log-agent-stop.sh  → Agent停止时完成审计记录
notify.sh          → Windows通知（跨平台桌面通知）
```

## Hook设计原则

1. **快速退出**: 不相关操作立即 exit 0，不影响性能
2. **失效安全**: 工具缺失时优雅降级，不阻断流程
3. **精准触发**: 钩子基于路径/命令类型过滤，避免误报
4. **可观测**: 日志记录所有钩子触发，便于调试

## Hermes可借鉴场景

| Hook | Hermes对应场景 |
|------|--------------|
| validate-commit | 危险Shell命令执行前检查 |
| detect-gaps | 缺失必要配置/skill时主动提醒 |
| pre/post-compact | 会话压缩前保存状态，恢复后恢复 |
| log-agent | Agent调用审计轨迹 |
| session-start | 展示系统状态摘要 |

## 轻量实现（无Claude Code）

即使没有官方Hook API，也可通过：
- 别名覆盖危险命令（rm → rm -i）
- Shell PROMPT_COMMAND 注入检查逻辑
- cron定时健康检查
- 会话启动/压缩时的状态持久化脚本
