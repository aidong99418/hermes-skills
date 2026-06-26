---
name: cron-system-reconstruction
description: Cron调度系统重建工作流 — 从crontab丢失到完整恢复的标准化流程。触发：cron不跑/系统自愈停止/定时任务集体消失。
triggers:
  - cron不跑了
  - auto_healing不推送了
  - 定时任务集体消失
  - 系统自愈停止
version: 1.0
---

# Cron调度系统重建工作流

## 何时用
定时任务集体不跑 → 器官系统断链 → 自愈/学习/进化停止工作。

## 核心教训

> **系统crontab是单一文件**，不是每个任务一个crontab。
> 所有cron写在同一个crontab里（`crontab -l`），任何一个cron失效都意味着整个表可能有问题。

## 标准步骤

### 1. 确认crontab状态
```bash
crontab -l  # 看当前所有cron
# 注意：返回空 ≠ 没有cron，可能看的是错误的用户
```

### 2. 盘点可用的cron脚本
从 `/opt/data/scripts/` 和 `/opt/data/backups/` 两处找：
- `auto_healing_cron.py` — 免疫层，每10分钟
- `evolution_cron.py` — 进化引擎，每30分钟
- `auto_learning.py` — 综合学习，每日08:00
- `brain_backup.py` — 备份，每小时
- `daydream_cron.py` — 白日梦，每2小时
- `memory_sync_cron_wrapper.py` — MEMORY同步，每小时（wrapper版）
- `skill_health_daemon.py` — skill守护，每10分钟
- `hermes_auto_clean.py` — 自净化，每日03:00

### 3. 验证每个脚本可用（语法+依赖）
```bash
python3 -m py_compile /opt/data/scripts/XXX_cron.py
```
**必须跑一次**验证无语法错误。

### 4. 解决import级报错
某些脚本（如memory_sync.py）在模块顶层import依赖，CLI参数解析前就报错。
**解法：写wrapper隔离**
```python
# memory_sync_cron_wrapper.py
def sync():
    try:
        from memory_sync import sync_cron
        sync_cron()
    except ModuleNotFoundError:
        pass  # Chroma不可用时静默跳过
```

### 5. 写入crontab（一行行写入验证）
```bash
# 写入前先读取
crontab -l > /tmp/old_cron.txt  # 备份

# 写入新cron（注意：会覆盖整个crontab）
echo "*/10 * * * * /usr/bin/python3 /opt/data/scripts/auto_healing_cron.py >> /opt/data/logs/auto_healing_cron.log 2>&1" | crontab -
# 或用cat heredoc批量写入
```

### 6. 验证crontab写入
```bash
crontab -l | grep -v "^#" | grep -v "^$" | wc -l
# 应返回实际的cron数量
```

### 7. 立即执行最关键的脚本验证
按优先级验证：
1. `auto_healing_cron.py` — 必须跑通，评分100%
2. `evolution_cron.py` — 跑通
3. `memory_sync_cron_wrapper.py` — Chroma同步成功
4. `brain_backup.py` — 路径存在，备份完成
5. 其他 → 顺延

### 8. 重启守护进程
skill_health_daemon / body_muscle 等进程如果停了，需要手动重启：
```bash
pkill -f skill_health_daemon
python3 /opt/data/scripts/skill_health_daemon.py start &
```

## 常见故障排查

| 症状 | 原因 | 解法 |
|------|------|------|
| `crontab -l` 返回空 | 被覆盖了 | 重建cron表 |
| script报错"No module" | 依赖未安装 | 写wrapper隔离 |
| 守护进程停了 | 手动kill/重启后未恢复 | 重启 |
| 只有1个cron存活 | 写入时被覆盖 | 检查crontab |
| log停在很早日期 | cron从未触发 | 检查cron daemon运行状态 |

## 验证清单
- [ ] crontab -l 显示所有cron
- [ ] auto_healing 评分100%
- [ ] evolution 跑通
- [ ] memory_sync wrapper 同步成功
- [ ] 守护进程运行中
- [ ] 日志文件正在写入
