---
name: v1-v016-daemon-isolation-audit
version: 2026-06-17
description: V1/V016双容器隔离守护进程审计 — 防止全局gateway模式误杀双容器
---

# V1/V016双容器隔离守护进程审计

## 触发条件
V1和V016同时运行时，任何涉及"杀gateway进程"的代码必须使用**精确路径匹配**，不能使用宽泛模式如`pkill -f "gateway.run"`，否则会同时杀死两个容器。

## 核心教训
`pkill -f "gateway.run"` 匹配：
- V1: `/opt/hermes/.venv/bin/python3 ... hermes gateway run` ✅
- V016: `/volume1/docker/hermes-文件路径/hermes016/bin/python3 ... hermes gateway run` ❌ 误杀

**正确写法**：
```bash
# 只杀V1
pkill -9 -f "/opt/hermes/.venv/bin/hermes gateway run"

# 只杀V016
pkill -9 -f "/volume1/docker/hermes-文件路径/hermes016"
```

## 审计流程（5步）

### 第1步：找所有杀进程的脚本
```bash
grep -rln 'pkill\|pkill\|SIGKILL\|SIGTERM\|os\.kill.*gateway\|subprocess.*kill' /opt/data/scripts/*.py
```

### 第2步：逐个检查上下文
关注以下模式：
- `pkill -f "gateway"` → 危险，宽泛匹配
- `pgrep -f "gateway"` → 检查用，需确认匹配范围
- `pkill -f "gateway.run"` → 危险，V1/V016都匹配
- `pkill -f "/opt/hermes/.venv/bin/hermes"` → 安全，V1专用
- `os.kill(pid, SIGKILL)` → 检查杀的是哪个pid，是否特指gateway

### 第3步：验证进程隔离
```bash
# V1进程
pgrep -f '/opt/hermes/.venv/bin/hermes gateway run'
# 期望：只有V1 PID (PID 1)

# V016进程
pgrep -f '/volume1/docker/hermes-文件路径/hermes016'
# 期望：只有V016相关PID (6122等)
```

### 第4步：修复宽泛匹配
将 `pkill -f "gateway.run"` 改为V1/V016专用路径。

### 第5步：验证修复
使用`pkill -0 -f "精确路径"`测试，确认目标进程匹配、非目标进程不匹配。

## 已验证安全的脚本（2026-06-17）
- `cloud_router_watchdog.py` → `pkill -f "cloud_router.py"` ✅
- `l2_router_watcher.py` → `pkill -f "cloud_router.py"` ✅
- `system_watcher.py` → `SIGKILL` auto_integrator scan进程 ✅
- `skill_health_daemon.py` → SIGTERM/SIGKILL子进程 ✅
- `system_heartbeat.py` → `kill_pid_{N}` 异常Python进程 ✅
- `iron_watcher.py` → `SIGTERM` iron_watcher自身（仅stop命令） ✅
- `secretary_daemon.py` → SIGTERM/SIGKILL secretary子进程 ✅
- `hermes_code_guard.py` → **已修复**，改为V1精确路径 ✅

## 关键文件
- 危险脚本：`/opt/data/scripts/hermes_code_guard.py`
- V1进程：`/opt/hermes/` (PID 1)
- V016进程：`/volume1/docker/hermes-文件路径/hermes016/` (PID 6122)
