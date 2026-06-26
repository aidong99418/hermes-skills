---
name: nas-cron-debug-patterns
description: NAS cron 任务排雷三板斧——python vs python3、sys.path shadow、provider配置。触发：cron任务不跑/报错/3天不更新。
triggers: ["调试", "cron任务不跑/报错/3天不更新。", "定时", "错误", "bug", "cron", "调度"]
version: "1.0"
date: 2026-06-04
---

# NAS Cron 任务 Debug 排雷三板斧

当 cron 任务疑似不运行时，按以下顺序诊断：

## 第一板斧：命令验证 — `python` vs `python3`

**问题**：`jobs.json` 中命令写 `python /opt/data/scripts/...` 但 NAS 只有 `python3`。

**症状**：
- cron 日志消失（Job 根本没执行）
- 手动运行报错 `python: command not found`

**验证命令**：
```bash
which python python3
python --version
python3 --version
```

**修复**：jobs.json 中全部 `python /opt/data/` → `python3 /opt/data/`

## 第二板斧：sys.path shadow 陷阱

**问题**：脚本用 `sys.path.insert(0, '/opt/data/scripts')` 会 shadow Python stdlib。

**症状**：
- 离奇 NameError 或 ImportError
- rank_bm25 加载失败（`platform.py` shadow）
- numpy 链式报错

**安全写法**：
```python
sys.path.append('/opt/data/scripts')  # append 而非 insert(0,...)
```

## 第三板斧：Provider 配置铁律

- `deliver=weixin`/`origin`（前台推送）→ `provider: wisemodel`
- `deliver=local`（后台学习）→ `provider: local`

## 快速诊断

```bash
# 检查 python 命令问题数量
grep -c '"command": "python /opt/data' /opt/data/cron/jobs.json

# 检查 sys.path.insert(0,)
grep -rn "sys.path.insert(0,.*opt/data" /opt/data/scripts/*.py 2>/dev/null
```
