---
name: watchdog-cleanup-workflow
description: |
  watchdog类脚本融合 + 僵尸进程清理标准流程。
  触发：发现多个watchdog进程、僵尸进程、根因诊断。
triggers:
  - watchdog 融合
  - 僵尸进程 清理
  - Popen subprocess 泄漏
  - 守护进程 冲突
version: 1.0
---

# watchdog-cleanup Workflow

## 核心原则

**融合前先验证现状。** 融合前必须用工具搜实际文件内容，不人肉猜。

## 标准流程（9步法版）

### 1. 环境检查
```bash
# 查找所有 watchdog 相关进程
ps aux | grep -E 'watchdog|inotify|guard' | grep -v grep

# 找所有相关脚本
find /opt/data/scripts -name '*watchdog*' -o -name '*watcher*' 2>/dev/null

# 查cron里的隐藏任务
crontab -l; cat /etc/crontab | grep -v '^#'
```

### 2. 分析 → 确认做不做
- 僵尸进程无害，等重启自动清除
- 找根因：哪个脚本调用了外部命令（Popen subprocess）
- `grep -rn 'Popen\|subprocess' /opt/data/scripts/` 找真正的子进程调用

### 3. 查漏
```bash
# 找调用inotifywait的脚本
grep -rln 'inotifywait' /opt/data/scripts/

# 找PID文件（残留 → 进程已不在）
ls -la /tmp/*.pid

# 找guard脚本
ls -la /opt/data/scripts/*_guard.sh
```

### 4. 深挖
- 读各脚本的`def is_running()`和`def restart()`逻辑
- 确认是否有独立cron/guard触发
- 交叉验证：iron_watcher.py里是否已有其他daemon的逻辑

### 5. 再分析
**关键发现模式：**
- iron_watcher.py已含健康监控+热同步守护 → 融合实际是清理冗余
- skill_health.py已改watchdog → 僵尸是历史残留，不是当前bug
- hermes_guard.py不存在 → 已经被删除或合并

### 6. 验证契合度
融合后是否重复：
- iron_watcher自保 ✅ guard.sh冗余 → 删除
- iron_watcher已有hot_sync守护 ✅ hot_sync_watchdog.py冗余 → 删除

### 7. 清理执行
```bash
TS=$(date +%Y%m%d_%H%M%S)

# 备份旧文件（时间戳命名，不覆盖）
mv /opt/data/scripts/iron_watcher_guard.sh /opt/data/scripts/iron_watcher_guard.sh.bak_$TS
mv /opt/data/scripts/hot_sync_watchdog.py /opt/data/scripts/hot_sync_watchdog.py.bak_$TS

# 清理残留PID文件
rm -f /tmp/iron_watcher.pid /tmp/hot_sync_watchdog.pid /tmp/log_watcher.pid
```

### 8. 验证
```bash
# 检查无残留
ls /opt/data/scripts/iron_watcher_guard.sh 2>/dev/null && echo '残留' || echo '✅ 已清'
ls /opt/data/scripts/hot_sync_watchdog.py 2>/dev/null && echo '残留' || echo '✅ 已清'
ls /tmp/iron_watcher.pid 2>/dev/null && echo '残留PID' || echo '✅ PID已清'
```

### 9. 清除旧版归档
- .bak文件移入 `/opt/data/scripts/`（已带时间戳）
- 僵尸进程等下次系统重启自动清除（无害，无需干预）

## 关键教训

1. **grep搜索实际代码比读注释可靠** — 注释说"已改watchdog"，实际代码可能还有旧调用
2. **融合前必须验证现状** — 假设旧代码还在可能导致做无用功（hermes_guard.py已删）
3. **僵尸无害，等重启** — kill -9对僵尸无效，init会自动回收
4. **修根因而非清尸体** — 僵尸是症状，修复Popen inotifywait才是根治
5. **PID文件存进程号，进程不在时残留** — 清理PID文件不等于清进程
