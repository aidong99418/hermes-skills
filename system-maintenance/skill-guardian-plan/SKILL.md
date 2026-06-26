---
name: skill-guardian-plan
description: 技能卫士 v2.2 — skill智能管家完整文档。融合依赖管理器+健康守护+器官健康检查+智能挖宝，已在生产运行。
triggers: ["工具", "skill", "技能"]
version: "2.2"
created: "2026-06-02"
updated: "2026-06-03"
trigger: 技能卫士/skill健康/skill合并/skill重命名/实时监控守护进程/器官健康
---

# 技能卫士 v2.2 — skill智能管家

## 定位
NAS上所有skill的统一维护工具，一个脚本搞定所有。

## 入口
```
/opt/data/scripts/skill_health.py          # 主脚本
/opt/data/scripts/skill_health_daemon.py   # 守护进程管理
```

## CLI命令
```bash
python3 skill_health.py scan         # 扫描169个skill，建立引用图谱
python3 skill_health.py health       # Skill引用健康检查，检测失效引用
python3 skill_health.py organ-hc     # 器官健康检查（全部13个器官）
python3 skill_health.py organ-hc xxx # 只检查指定器官（如 organ-hc auto_healing）
python3 skill_health.py fix          # 自动修复失效引用
python3 skill_health.py merge a,b c  # 合并多个skill，自动更新所有引用
python3 skill_health.py move old new # 重命名skill，自动更新所有引用
python3 skill_health.py watch        # 实时监控（inotify守护进程）
python3 skill_health.py gap          # 知识缺口检测→触发挖宝
python3 skill_health.py full         # 完整检查+修复+缺口分析
```

## 守护进程
```bash
python3 skill_health_daemon.py start   # 启动
python3 skill_health_daemon.py stop    # 停止
python3 skill_health_daemon.py restart # 重启
python3 skill_health_daemon.py status  # 状态
```
- PID文件：`/tmp/skill_health_watch.pid`
- 日志：`/opt/data/secretary/skill_health_watch.log`
- 开机自启：已写入crontab @reboot

## 融合记录
- `skill_dependency.py` (267行) → 已删除，功能合并进 skill_health.py
- 新增函数：`backup_skill()`, `_replace_refs()`, `merge_skills()`, `move_skill()`
- 融合后共享同一个注册表：`/opt/data/secretary/skill_registry.json`

## 器官健康检查（v2.2新增）
检查全部13个器官的 `health_check()` 接口，直接调用并采集结果。

**HC_TEMPLATES 定义**（skill_health.py 第57行起）：
- 标准器官：返回 `{organ, healthy(bool), last_heartbeat, details, severity}` → `health_field: "healthy"`
- 非标准器官（如 alert_sender/task_board/feishu_card_sender）：返回 `{organ, status: "healthy"/"degraded", detail}` → `health_field: "status"`, `health_true: "healthy"`

**13个器官列表**：
ae4_bridge / alert_sender / auto_healing / evolution_engine / feishu_card_sender / intent_engine / learning_loop / neural_safe / organ_bus / skills_factory / task_board / unified_push / workflow_engine

**⚠️ 踩坑：器官文件 duplicate health_check() 导致 SyntaxError**
- alert_sender.py、feishu_card_sender.py、task_board.py 各自有两个 `def health_check()`
- 第一个是残缺的（`return {` 不完整，缺闭合 `}`）→ 引发 SyntaxError: `{ was never closed`
- Python 只报第一个 SyntaxError 就停，导致整个文件无法导入
- **修复**：删除第一个（残缺的）health_check，保留第二个（正确的）
- 定位方法：找所有 `def health_check()` 行号，第一个到 `if __name__` 之间就是残缺部分
- 批量删除脚本：
```python
# 0-indexed行号
"/opt/data/organs/alert_sender.py":     {"broken_start": 310, "keep_line": 324},
"/opt/data/organs/feishu_card_sender.py": {"broken_start": 368, "keep_line": 382},
"/opt/data/organs/task_board.py":       {"broken_start": 553, "keep_line": 567},
# 执行：lines[:broken_s] + lines[keep:] → 写回文件 → py_compile 验证
```

## 脚本碎片清理模式（本次实践）
1. 扫描所有相关脚本，找功能重叠
2. 识别每个脚本的**独特价值**（没有重叠的功能必须保留）
3. 把独特功能合并进主脚本
4. 验证新脚本运行正常
5. 删除旧脚本
6. 重启相关守护进程加载新版本
7. 测试触发验证（用 `touch` 模拟文件变更）

## 依赖文件
- 注册表：`/opt/data/secretary/skill_registry.json`
- 备份：`/opt/data/secretary/skill_backups/`
- 日志：`/opt/data/secretary/skill_health.log`

## ⚠️ 踩坑记录（2026-06-03）

### 1. `trigger_treasure_mining()` 内 sys 未导入
**症状**：微信推送报错 `name 'sys' is not defined`，日志里持续出现此错误

**根因**：`trigger_treasure_mining()` 是嵌套函数，使用了 `sys.path.insert()` 但没有 `import sys`。外层 `main()` 里有 `import sys`，但那是函数局部变量，不在嵌套函数作用域里。

**修复**：在 `trigger_treasure_mining` 内部局部导入：
```python
import sys as _sys_module
_sys_module.path.insert(0, '/opt/data')
```
不能用 `from ... import` 替代，因为 `from` 语句不在当前作用域。

### 2. cron prompt 必须指定子命令
**症状**：cron触发后AI会话永久挂起，每次产生一个挂起的子进程

**根因**：`skill_health.py` 无参数时会进入 `watch_and_react()` 监控模式（while True + sleep），永远不会退出。cron的prompt写的是 `运行 /opt/data/scripts/skill_health.py`（无参数），导致AI执行时脚本永久阻塞。

**修复**：cron prompt 必须明确指定子命令：
```bash
/usr/bin/python3 /opt/data/scripts/skill_health.py health  # 健康检查，一次性退出
/usr/bin/python3 /opt/data/scripts/skill_health.py fix     # 修复失效引用
```

### 3. jobs.json 格式特殊性
**jobs.json 使用的是 Python repr 风格的 `\\u` 转义（双反斜杠），不是标准JSON的 `\u`**
搜索和匹配时注意：搜索 `skill\u5065\u5eb7` 能匹配，但普通文本编辑器/grep 搜中文名不一定能匹配。

定位skill_health job要通过 `id: c52c58be9daf`，而不是通过name（因为job数组很长，容易误匹配其他健康类job）。

### 4. 默认行为：无参数时进入watch模式
`skill_health.py` 无参数时走默认分支，会调用 `health_check()` 然后检查缺口，但**不会进入监控模式**——只有显式 `watch` 子命令才会进入watchdog循环。但cron里如果脚本本身就是守护进程型的（没有子命令=watch），则会导致永久阻塞。

