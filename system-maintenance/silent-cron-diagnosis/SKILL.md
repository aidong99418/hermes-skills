---
name: silent-cron-diagnosis
description: 静默Cron任务诊断——mtime去重型脚本的正确验证方法。触发：cron任务无输出/不清楚是否运行/想确认脚本是否真的在跑。
triggers:
  - cron任务运行了但没有任何输出
  - 想确认dialog_watchdog等轮询脚本是否在运行
  - 不清楚脚本为什么静默（没报错也没成功消息）
version: 1.0
---

# 静默Cron任务诊断

## 典型场景

某些cron脚本设计为"静默成功"——当内容无变化时只更新状态，不打印日志。常见模式：
- mtime去重：比较文件修改时间，内容未变则静默
- 消息去重：对比上次消息，新消息才处理，否则静默更新mtime

**关键认知：静默无输出 ≠ 脚本失败。** 这是正确行为。

## 诊断步骤

### Step 1: 检查状态文件（最关键）

状态文件记录了脚本的"记忆"——上一次处理到哪了。

```bash
# 查看状态文件内容
cat /opt/data/brain/performance/dialog_watchdog_state.json
```

重点字段：
- `last_mtime`: 脚本上次处理的文件时间戳（Unix时间戳）
- `last_file`: 上次处理的文件路径
- `last_user_msg`: 上次处理的消息内容

### Step 2: 对比状态 vs 实际文件

```bash
# 查看最新session文件时间
ls -lt /opt/data/sessions/*.json | head -3

# 将last_mtime转为可读时间
python3 -c "import datetime; print(datetime.datetime.fromtimestamp(<last_mtime>))"
```

**验证逻辑：**
- `状态last_mtime ≈ 最新session时间` → 脚本运行正常，已追上最新文件 ✅
- `状态last_mtime << 最新session时间` → 脚本可能卡住或跳过处理 ⚠️
- `状态last_mtime > 最新session时间` → 有新文件但脚本没感知 → 查日志 🔴

### Step 3: 理解"静默跳过"的原因

如果状态已追上，但日志没有新条目，检查是否内容重复：

脚本日志最后几行应该显示：
```
检测到新对话: session_xxx.json       ← 发现了新文件
用户: 'xxx'                           ← 有新消息内容
tier: 2 🧠思考通道                    ← 成功处理
```

如果看到的是：
```
无新用户消息或内容相同: '开始'        ← 静默跳过，内容没变
```

说明：cron会话的用户消息是 `[SYSTEM: You are running as a scheduled cron job...]`，与上次完全相同，脚本正确去重，跳过处理。

### Step 4: 直接运行脚本验证

```bash
cd /opt/data && /opt/hermes/.venv/bin/python3 -u /opt/data/scripts/dialog_watchdog.py 2>&1
```

运行后检查：
- 状态文件 `last_mtime` 是否更新
- 日志是否出现新的"检测到新对话"条目

## dialog_watchdog 特殊说明

- **会话格式兼容**：支持旧格式（JSONL，每行一个JSON对象）和新格式（单JSON含messages数组）
- **消息去重**：以 `last_user_msg` 为准，完全相同则静默
- **系统消息过滤**：跳过 `[System note:]` 和 `[Your active task...]` 前缀的消息
- **洞察存档**：`/opt/data/brain/performance/dialog_insights/` 目录
- **行为日志**：`/opt/data/brain/performance/dialog_insights/insights_log.jsonl`

## 关键文件路径

- 状态文件: `/opt/data/brain/performance/dialog_watchdog_state.json`
- 行为日志: `/opt/data/brain/performance/dialog_insights/insights_log.jsonl`
- 洞察存档: `/opt/data/brain/performance/dialog_insights/insight_*.json`
- 脚本: `/opt/data/scripts/dialog_watchdog.py`
- 会话目录: `/opt/data/sessions/`

## Hermes Cron Job 注册表定位（关键）

不要硬编码 `~/.hermes/cron/jobs.json`！HERMES_HOME 在不同环境指向不同路径。

**正确方法——通过 Python 动态获取：**

```bash
cd /opt/hermes && python3 -c "
import sys; sys.path.insert(0, '/opt/hermes')
from cron.jobs import HERMES_DIR, CRON_DIR, JOBS_FILE
print('HERMES_DIR:', HERMES_DIR)
print('CRON_DIR:', CRON_DIR)
print('JOBS_FILE:', JOBS_FILE)
print('JOBS_FILE exists:', JOBS_FILE.exists())
"
```

**已知路径（供快速参考）：**
| 环境 | HERMES_HOME | Cron jobs 路径 |
|------|------------|----------------|
| UGREEN NAS | `/opt/data` | `/opt/data/cron/jobs.json` |
| 其他环境 | `~/.hermes` | `~/.hermes/cron/jobs.json` |

**在 jobs.json 中查找 job：**
```bash
grep -n 'dialog_watchdog' /opt/data/cron/jobs.json
```
找到后读取完整 job 定义（含 `enabled`/`state`/`next_run_at`/`last_run_at`/`last_status`）。

## 陷阱警示

- ❌ 看到脚本"没有输出"就认为它失败了 → 静默成功是最优行为
- ❌ 只看日志文件行数判断是否运行 → 状态文件mtime才是真相
- ✅ 先查状态文件 `last_mtime`，再对比实际session文件时间
- ✅ cron会话消息是系统生成的，`[SYSTEM: ...cron job...]` 与上次相同会被正确去重
