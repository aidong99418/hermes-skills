---
name: hermes-cron-daemon-diagnosis
description: 诊断NAS上脚本是Daemon还是Cron触发型 — 快速判断进程/cron ID/最后运行状态。触发：检查XXX脚本是否在运行/cron任务状态/daemon和cron混淆。
triggers: ["调度", "cron", "定时"]
trigger: 检查XXX脚本是否在运行 / cron任务状态 / daemon还是cron触发
version: 1.0
---

# Hermes Cron / Daemon 诊断速查

## 核心判断：Daemon vs Cron触发

| 特征 | Daemon（守护进程） | Cron触发（一次性脚本） |
|---|---|---|
| `pgrep`结果 | 有长期运行的进程 | **无**进程（每次运行后退出） |
| 日志规律 | 持续追加、心跳 | 每次cron触发一行，最后一行时间≈上次cron |
| 日志内容 | "无新消息"循环 | 单次执行后正常退出 |
| 管理方式 | 手动start/stop | Hermes cron scheduler |

**大多数 `/opt/data/scripts/*.py` 都是 Cron触发型**，不是daemon。

## 诊断命令速查

```bash
# 1. 检查 Hermes cron 任务列表（最关键）
/opt/hermes/.venv/bin/hermes cron list

# 2. 搜索特定脚本的 cron 条目
/opt/hermes/.venv/bin/hermes cron list | grep -i 'script_name'

# 3. 检查进程（daemon模式才有用）
pgrep -fa script_name

# 4. 查看日志最后修改时间和内容
tail -5 /path/to/log.log
stat /path/to/log.log | grep Modify
```

## 常见陷阱

1. **误以为脚本"挂了"** — cron触发型脚本本身就不应该有持久进程，`ps aux | grep` 返回空是正常的
2. **看 crontab 找不到** — Hermes 使用内置 scheduler，不依赖系统 crontab，`crontab -l` 是空的
3. **日志停在很久以前** — 如果 cron `Last run` 显示 ok 但日志没更新，检查 cron scheduler 是否正常

## 日志分析法

日志最后一行判断：
- `"无新消息 (文件未更新)"` → 脚本正常运行，空闲中
- `"检测到新对话: XXX"` → 检测到新用户消息并处理
- `Traceback ... ModuleNotFoundError` → 依赖缺失，需修复
- 最后行时间 > 2分钟前 → 可能 cron scheduler 挂了

## Cron任务状态含义

- `ok` — 本次运行成功
- 空或无 last run → 从未运行或被禁用
- `failed` — 脚本报错，需查看日志
- `[paused]` — 被手动暂停

## ⚠️ "Paused但仍在产出" — 系统cron驱动的Jobs

**现象：** Hermes Scheduler 中 11 个 jobs 显示 `state=paused`，但其 `/opt/data/cron/output/{job_id}/` 目录仍有最近的文件产出。

**根因：** 这些 Job 在 jobs.json 中**没有 `command` 和 `script` 字段**，Hermes Scheduler 无法调度它们。它们由**系统层 cron**（可能是 docker 容器外的宿主机cron，或容器内独立进程）直接驱动。

**诊断方法：**

```python
import json
from pathlib import Path
import time

with open("/opt/data/cron/jobs.json") as f:
    data = json.load(f)

paused_with_output = []
for job in data['jobs']:
    if job.get('state') != 'paused':
        continue
    job_id = job['id']
    out_dir = Path(f"/opt/data/cron/output/{job_id}")
    if not out_dir.exists():
        continue
    files = list(out_dir.glob("*.md"))
    if not files:
        continue
    latest = max(files, key=lambda f: f.stat().st_mtime)
    age_mins = (time.time() - latest.stat().st_mtime) / 60
    has_cmd = bool(job.get('command'))
    has_script = bool(job.get('script'))
    if age_mins < 30:
        paused_with_output.append({
            'name': job['name'],
            'job_id': job_id,
            'age_mins': age_mins,
            'has_command': has_cmd,
            'has_script': has_script,
        })
        print(f"⚠️ {job['name'][:40]}")
        print(f"   command={'Yes' if has_cmd else 'No'} | script={'Yes' if has_script else 'No'}")
        print(f"   最后文件: {age_mins:.0f}分钟前")
```

**结论判断：**
- `command=None` 且 `script=None` → 系统cron驱动，不是bug，正常行为 ✅
- `command` 或 `script` 有值但仍paused → 可能需要恢复

## ⚠️ 常见报错诊断

### "No inference provider configured"

**根因：** job 同时配置了 `script` 和 `prompt` 字段。scheduler 行为：
1. 先运行 `script`（Python脚本）
2. 将脚本输出注入 `prompt`
3. **再用 AI 模型执行 prompt**（需要 inference provider/API key）
4. 如果没有配置 API key → 报错 `No inference provider`

**受影响的 job 类型：**
- 数据采集型：配置了 `script` 但也写了 `prompt`，跑完脚本后还想让AI总结
- 触发条件：`jobs.json` 中 job 同时有 `"script"` 和非空 `"prompt"` 字段

**诊断命令：**
```bash
# 查看报错任务的配置（无 get 命令，只能读文件）
python3 -c "
import json
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)
for job in data['jobs']:
    sid = job.get('id','')
    has_script = bool(job.get('script'))
    has_prompt = bool(job.get('prompt'))
    if has_script and has_prompt:
        print(f'⚠️  [{sid}] {job[\"name\"]}')
        print(f'   script={job[\"script\"]}')
        print(f'   prompt长度={len(job[\"prompt\"])}')
        print()
"
```

**修复方案：** 清空 `prompt` 字段，改为纯 `script` 模式（数据采集脚本不需要AI总结）
```python
import json
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)
# 目标job_id
target = '目标job_id'
for job in data['jobs']:
    if job.get('id') == target:
        job['prompt'] = ''        # 清除AI推理
        job['skills'] = []         # 清除触发skill（如果原本没有真实skill）
        # 如果script为None但prompt存在，则改为纯prompt模式
        if not job.get('script'):
            job['script'] = '实际脚本.py'
with open('/opt/data/cron/jobs.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

**验证：** 运行脚本本身应该成功（不需要API key）
```bash
# 直接运行脚本验证
/opt/hermes/.venv/bin/python3 /opt/data/scripts/脚本.py
```

### "ModuleNotFoundError" in cron

参见 skill: `hermes-cron-script-fix`（bash脚本被Python执行）

## Cron jobs.json 速查

- 路径：`/opt/data/cron/jobs.json`
- 结构：`{"jobs": [...], "updated_at": "..."}` — **jobs 是 list，不是 dict**，遍历时 `for job in data['jobs']`
- job 字段：id / name / script / prompt / skills / model / state / schedule / deliver / command
- **易错：** 如果直接 `for j in data`（未加 `['jobs']`），会遍历到 `['jobs', 'updated_at']` 两个 key，用 `j.get()` 报 `AttributeError: 'str' object has no attribute 'get'`

**注意：** `hermes cron get <id>` 不存在，只能用 `hermes cron list` 或直接读 `jobs.json` 文件。
