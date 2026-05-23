---
name: tools
description: 通用工具脚本集 — brain备份触发、brain_thinker调用、对话看门狗。触发：需要后台自动化脚本、brain调用封装。
version: 1.0.0
tags: [script, brain, automation]
triggers: ["工具脚本", "brain调用", "后台任务"]
---

# 工具脚本集

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `brain_backup_trigger.py` | brain系统备份触发器 |
| `brain_invoke.py` | brain_thinker轻量调用封装 |
| `dialog_watchdog.py` | 对话超时看门狗 |

## 使用方式

```bash
# brain调用
python3 /opt/data/skills/tools/brain_invoke.py "问题内容"

# 备份触发
python3 /opt/data/skills/tools/brain_backup_trigger.py

# 看门狗
python3 /opt/data/skills/tools/dialog_watchdog.py
```
