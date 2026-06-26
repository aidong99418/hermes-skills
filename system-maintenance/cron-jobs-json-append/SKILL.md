---
name: cron-jobs-json-append
description: 向 /opt/data/cron/jobs.json 安全追加 Hermes Scheduler 任务的规范流程 + 常见陷阱修复
triggers: ["调度", "cron", "定时"]
trigger: 向 /opt/data/cron/jobs.json 追加新任务时激活
tags: [cron, scheduler, jobs.json, hermes]
version: 1.0
---

# Hermes Scheduler Jobs.json 追加规范

## 标准追加步骤

向 `/opt/data/cron/jobs.json` 添加新任务时，必须：

1. **读文件结尾**（`read_file` offset=1400）找到最后一个任务的闭合 `}`
2. **确保闭合完整**：`origin` 对象必须同时有 `thread_id` 和 `}`，前一个任务以 `}` 结尾
3. **追加模板**（直接贴在最后一个 `}` 后面）：
   ```json
   ,
   {
     "id": "<唯一ID>",
     "name": "...",
     "prompt": "...",
     "skills": [],
     "skill": null,
     "model": null,
     "provider": null,
     "base_url": null,
     "script": null,
     "schedule": {
       "kind": "cron",
       "expr": "0 4 * * *",
       "display": "0 4 * * *"
     },
     "schedule_display": "0 4 * * *",
     "repeat": { "times": null, "completed": 0 },
     "enabled": true,
     "state": "scheduled",
     "paused_at": null,
     "paused_reason": null,
     "created_at": "<ISO时间>",
     "next_run_at": "<ISO时间>",
     "last_run_at": null,
     "last_status": null,
     "last_error": null,
     "last_delivery_error": null,
     "deliver": "local",
     "origin": {
       "platform": "weixin",
       "chat_id": "o9cq80_9LbP7XSIpUop6t4NlIT4o@im.wechat",
       "chat_name": null,
       "thread_id": null
     },
     "command": "python3 /opt/data/scripts/<脚本名>.py",
     "grace_seconds": 60
   }
   ```

## 追加后必验证

```bash
python3 -c "import json; json.load(open('/opt/data/cron/jobs.json')); print('✅ JSON有效')"
```

## 常见陷阱

- **origin 对象残缺**：`chat_name` 后直接跟 `command`，缺少 `thread_id` 和 `}`。修复：
  ```
  "chat_name": "...",
  "thread_id": null
  },
  ```
- **末尾多余逗号**：`jobs` 数组最后一个元素后不能有逗号
- **updated_at 陈旧**：追加后通常更新为当前时间

## 重要区分：04:00 的两个任务

| 脚本 | 职责 | 来源 |
|------|------|------|
| `evolution_cron.py` | 岛屿遗传算法引擎（`/opt/data/organs/evolution_engine`） | 器官系统 |
| `ae4_daily_evolution.py` | AE4 激活进化引擎（遗忘+快照+自省+涌现） | 大脑神经网络 |

两者职责不同，04:00 共存无冲突。
