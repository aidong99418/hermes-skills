---
name: dispatcher-cleanup-workflow
description: 派工器/秘书处重复配置清理工作流 — 多版本并行时快速定位活跃脚本、批量删除废弃文件、修复报错cron。触发：发现多个dispatcher版本/多个秘书目录/系统有历史包袱。
triggers: ["清理", "派工", "废弃脚本", "cleanup", "重复配置", "任务分发", "旧派工器"]
trigger: cleanup, 清理, 重复配置, 废弃脚本, 旧派工器
tags: [cleanup, dispatcher, secretary, maintenance]
created: 2026-05-29
version: 1.0
---

# 派工器/秘书处重复配置清理工作流

## 核心原则

**先确认再删除，逐项验证，不盲删**

## 诊断流程（四步定位活跃版本）

### 第一步：锁定活跃进程

```bash
# 1. 锁文件内容
cat /tmp/xxx_dispatcher.lock

# 2. 实际在跑的进程
ps aux | grep -E "dispatcher" | grep -v grep

# 3. 进程启动时间
ps -p <PID> -o lstart=

# 4. 代码修改时间

# 5. 代码vs进程时间对比 → 判断进程是否在跑新代码
```

**关键经验**：仅看进程名不够，必须比对 `进程启动时间` vs `代码修改时间`，如果进程启动早于代码修改，说明跑的是旧代码。

### 第二步：检查日志文件路径

```bash
# 找到日志路径后再 tail 看最新记录
```

### 第三步：全面文件盘点

```bash
# 派工器脚本

# 秘书处脚本
find /opt/data/secretary -type f -name "*.py"

# 锁文件
ls -la /tmp/*.lock

# Cron任务
crontab -l
```

### 第四步：验证路径存在性（cron专用）

```bash
for path in "/opt/data/secretary/行政秘书/run.py" \
            "/opt/data/secretary/策略秘书/run.py"; do
  if [ -f "$path" ]; then
    echo "✅ $path"
  else
    echo "❌ $path 不存在"
  fi
done
```

## 删除前必做：交叉引用检查

```bash
grep -r "autogen_dispatcher\|dispatcher\.py\|worker\.py" \
```

## 典型废弃清单（可参考本次清理）

### 废弃派工器 → 全删
- `autogen_dispatcher.py`（未运行的旧版）
- `autogen_config.py` / `autogen_multi_agent.py` / `autogen_test.py`
- `simple_agent.py` / `dispatcher.py` / `worker.py`
- `two_faction_architecture.py`（只是说明文档）

**保留**：`secretary_dispatcher.py`（当前唯一活跃）

### 废弃秘书处脚本 → 全删
- `secretary.py` / `secretary_base.py`
- `secretary_intel.py` / `secretary_writing.py` / `secretary_learning.py` ✅ 已清理（2026-05-29）
- `parallel_dispatcher.py` / `shadow_clone.py`
- `ctrl.py` / `round.py` / `verify.py`
- `task_clone.py` / `result_clone.py` / `check_results.py`
- `_old_files_backup/` 整个目录

### 废弃锁文件 → 删除
- `realtime_learning.lock`（当前仍在使用）

### 报错cron → 从crontab删除

```bash
# 确认日志有报错
grep -l "策略秘书\|文秘\|推理秘书" /opt/data/secretary/logs/*.log

# 删除路径不存在的cron任务
(crontab -l | grep -v "策略秘书\|文秘/run.py\|推理秘书/run.py") | crontab -
```

## 删除顺序（安全）

1. 删除废弃脚本文件
2. 删除废弃锁文件
3. 清理废弃日志
4. 修改crontab（最后一步，避免影响正在跑的任务）

## 验证清理结果

```bash
ps aux | grep -E "dispatcher|secretary" | grep -v grep
crontab -l | grep -v "^#"
```
