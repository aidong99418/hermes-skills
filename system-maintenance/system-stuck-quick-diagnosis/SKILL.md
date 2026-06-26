---
name: system-stuck-quick-diagnosis
description: 系统卡顿/飞书不响应时的5分钟快速诊断流程
triggers:
  - "飞书卡了"
  - "系统卡了"
  - "怎么不动了"
  - "没有产出"
  - "成果停了"
  - "系统空转"
  - "拖后腿"
  - "全面诊断"
  - 飞书收到消息但不回复
tags:
  - 故障诊断
  - cron
  - 飞书推送
version: 1.0
---

# 系统卡顿快速诊断 Skill

## 触发词
"飞书卡了" / "系统卡了" / "怎么不动了" / 任何报系统不动/无响应的场景

## 快速诊断流程

### 第一步：查cron服务状态（零成本，2秒）
```bash
service cron status
```
- `cron is running.` → cron正常，继续下一步
- `cron is not running` → **根因找到！立即 start**

### 第二步：如果cron正常但系统卡，查进程
```bash
ps aux | grep python | grep -v grep | grep -v bash
```

### 第三步：查关键日志
```bash
tail -20 /opt/data/logs/agent.log
tail -20 /opt/data/logs/auto_healing_cron.log
```

### 第四步：查派工板和成果板（⚠️路径：/opt/data/secretary/，不是/opt/data/dispatch/）

> **路径记忆**：派工板和成果板在 `/opt/data/secretary/` 下，不是 `/opt/data/dispatch/`。
> 确认方法：`grep "dispatch_board" /opt/data/scripts/*.py | grep "\.json"` 找硬编码路径。

```python
import json
from pathlib import Path

# 派工板
dp = Path('/opt/data/secretary/dispatch_board.json')
db = json.loads(dp.read_text())
tasks = db.get('tasks', [])
pending = [t for t in tasks if t.get('status') in ['pending','processing']]
done = [t for t in tasks if t.get('status') == 'done']
print(f'派工板: 总{tasks.__len__()} | pending/processing={pending.__len__()} | done={done.__len__()}')

# 成果板
rp = Path('/opt/data/secretary/result_board.json')
rb = json.loads(rp.read_text())
results = rb.get('results', [])
if results:
    latest = max(results, key=lambda x: x.get('created_at',''))
    print(f'成果板: {results.__len__()}条 | 最新={latest.get("created_at")}')
else:
    print('成果板: 0条')
```

### 第五步：验证修复
```bash
# 手动跑一次auto_healing验证推送恢复
/usr/bin/python3 /opt/data/scripts/auto_healing_cron.py
```

## 🔴 诊断第一步：区分"系统坏了"和"系统空转"

**这是最常见的误判！** 系统有两套并行流水线，症状相似但根因完全不同：

### 两套流水线
```
┌─ Cron流水线 ──→ /opt/data/cron/output/（正常产出）
│   驱动：hermes scheduler（44任务）
│   写成果板？不写
│
└─ 派工板流水线 ──→ dispatch_board → 执行器 → result_board
    驱动：前台下发任务
    写成果板：deputy_result.py
    ⚠️ 38小时无新任务 ≠ 系统坏了 = 前台没派活
```

### 判断方法（30秒）
```bash
# 1. cron output目录是否在产出？（最直接）
ls -lt /opt/data/cron/output/ | head -3
# 有12:xx时间戳 → Cron流水线正常 → 不是系统坏，是空转

# 2. 成果板最新结果时间
/opt/hermes/.venv/bin/python3 -c "
import json
from datetime import datetime
rb = json.load(open('/opt/data/secretary/result_board.json'))
results = rb.get('results', [])
if results:
    latest = max(results, key=lambda x: x.get('created_at',''))
    print(f'成果板最新: {latest.get(\"created_at\")}')
else:
    print('成果板: 0条')
"

# 3. 派工板状态
/opt/hermes/.venv/bin/python3 -c "
import json
db = json.load(open('/opt/data/secretary/dispatch_board.json'))
tasks = db.get('tasks', [])
statuses = {}
for t in tasks:
    s = t.get('status','?')
    statuses[s] = statuses.get(s,0)+1
print(f'派工板: {statuses}')
"
```

### 诊断结论
| Cron Output | 成果板 | 派工板 | 结论 |
|-------------|--------|--------|------|
| ✅ 有产出 | 停滞>24h | 空 | 🔵 **空转** — 不是系统坏，是没派活 |
| ✅ 有产出 | 有新结果 | 有任务 | ✅ 完全正常 |
| ❌ 无产出 | 停滞 | 空 | 🔴 **系统坏** — 查gateway/daemon |

**空转不是故障，是正常待机状态。** 系统设计如此运转，不需要修复。

---

## 🟡 成果板停滞但Cron正常时的根因排查

当判定为"空转"后，如果董哥问"为什么不产出"，才进一步查：

### 1. deputy_result.py 是否在跑？
```bash
ps aux | grep deputy_result | grep -v grep
# 无输出 = 没在跑
tail -20 /opt/data/secretary/logs/deputy_result.log
# 看最后一行时间戳，推断何时停止
```

### 2. deputy_result 为何断链？
```bash
# 典型断链特征：日志停在"特秘第1次推理..."然后卡死
grep "ERROR\|特秘" /opt/data/secretary/logs/deputy_result.log | tail -5
# 常见错误：
#   - "Request URL is missing an 'http://'" → API URL配置丢失（读/opt/data/config.yaml但文件不存在）
#   - "object of type 'NoneType' has no len()" → 结果解析失败
#   - "[WARN] 进程已在运行中" → daemon重复启动冲突
```

### 3. 修复：如果 deputy_result 确实坏了
**方案A**：用cron任务续接（已存在，每5分钟）
```bash
# 检查是否已启用
/opt/hermes/.venv/bin/python3 -c "
import json
d=json.load(open('/opt/data/cron/jobs.json'))
for j in d.get('jobs',[]):
    if '续接' in str(j.get('name','')):
        print(f'[{j[\"id\"]}] {j[\"name\"]} | last_run={j.get(\"last_run_at\")} | status={j.get(\"last_status\")}')
"
```

**方案B**：直接触发一次恢复
```bash
/opt/hermes/.venv/bin/python3 /opt/data/scripts/task_recovery_cron.py
```

---

## 🟢 系统"动起来"的激活清单（空转时可用）

当判定为空转而非故障时，可主动触发后台任务让系统产出：

| 任务 | 命令 | 耗时 | 产出 |
|------|------|------|------|
| 白日梦 | `/opt/hermes/.venv/bin/python3 /opt/data/scripts/brain_daydream.py` | 30秒 | 跨域联想报告 |
| AE4轻量 | `/opt/hermes/.venv/bin/python3 /opt/data/scripts/ae4_quick_cron.py` | 5秒 | 容量守护 |
| GitHub挖宝 | `/opt/hermes/.venv/bin/python3 /opt/data/scripts/brain_treasure_hunt.py` | 5分钟 | 新知识 |
| 白日梦落地 | `/opt/hermes/.venv/bin/python3 /opt/data/scripts/brain_daydream_evolution.py` | 2分钟 | 建议→执行 |
| 自动学习 | `/opt/hermes/.venv/bin/python3 /opt/data/scripts/auto_learning.py` | 2分钟 | 知识采集 |

并行触发多个任务的正确方式：
```bash
# 后台并行，跑完推送结果
nohup python3 /opt/data/scripts/brain_daydream.py > /tmp/daydream.log 2>&1 &
nohup python3 /opt/data/scripts/ae4_quick_cron.py > /tmp/ae4.log 2>&1 &
```

---

## ✅ 诊断结论模板

给董哥的诊断报告格式：
```
✅ 正常：具体数值
🟡 警告：具体问题+建议
🔴 严重：具体问题+修复建议
🔵 空转：系统待机，等待前台派活
⚠️ Cron Error：具体job名+last_status，继续观察或查日志
```

**严禁**：把"空转"当成"系统坏了"上报，这会导致不必要的修复操作。

**Cron Error Job 判断三板斧**：
1. 查 `cronjob list` 里 last_status=error 的 job 数量（2-3个error ≠ 系统全坏）
2. 手动跑脚本验证：`python3 /opt/data/scripts/config_guardian.py` 和 `python3 /opt/data/scripts/cron_recovery_watchdog.py` 都正常 → 是历史残留标记，脚本本身无问题
3. 清除残留标记：`cronjob run <job_id>` 手动触发一次，scheduler 自动更新状态为 ok
   - Config Guardian error → 根因：凌晨 config.yaml 有一次解析损坏后自愈，标记残留
   - Cron Recovery Watchdog error → 同上历史残留，手动触发后 last_status 变 ok

**症状识别**：
- 今天日志为空（`grep "$(date +%Y-%m-%d)" log` 返回0）
- 飞书收到消息Flushing了但没`Sending response`日志
- 微信响应极慢（>60秒）

**修复命令**：
```bash
service cron start
```

**备注**：cron进程被kill后状态显示`failed`，但进程本身可能还在跑（僵尸），所以要先检查`service cron status`再决定是否restart。

**多种cron同时报错排查三板斧**：
1. 查 `/opt/data/cron/output/{job_id}/` 目录里最新 `.md` 文件，看 `## Error` 字段的真实报错
2. 对比所有 error job 的 `Run Time` — 如果时间戳相同（如全在 17:28），根因是 API/Provider 临时抖动，不是脚本坏了
3. 典型瞬时抖动特征：`RuntimeError: Unknown provider 'wisemodel'` 批量出现 → scheduler 自愈，下一波 schedule 自动恢复

## 🔴 新增：Cron执行了但结果不对——逻辑Bug诊断模式

**症状**：cron 任务日志显示"Running job"，但结果密度/数值完全不变，或始终是地板值。

**诊断流程**（以 AE4 容量守护为例）：
```bash
# 1. 先查 jobs.json 中的 skill 引用（可能是幽灵 skill）
python3 -c "
import json
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)
for j in data['jobs']:
    skill = j.get('skill') or (j.get('skills') or [None])[0]
    name = j.get('name','')
    if skill:
        print(f'{name}: skill={skill}')
"

# 2. 查 agent.log 找 skill 缺失警告（关键证据）
grep "skill not found\|skipping" /opt/data/logs/agent.log

# 3. 手动执行脚本摸清真实行为（最可靠）
python3 -c "
import sys, os
sys.path.insert(0, '/opt/data/brain/neural')
sys.path.append('/opt/data/scripts')
os.environ['AE4_MIN_DENSITY'] = '0.15'
from activation_engine import ActivationEngineV4, ae4_quick_activate
eng = ActivationEngineV4()
density = eng.get_activation_density()
print(f'当前密度: {density:.4f}')
if density < 0.15:
    result = ae4_quick_activate(task_id='manual_test', suppress_wechat=True)
    new_density = result.get('results', {}).get('density_after', density)
    print(f'执行后密度: {new_density:.4f}（变化: {density:.4f}→{new_density:.4f}）')
"

# 4. 检查根因：密度地板值问题
#    密度 = min(avg_adopt/10, 1.0)
#    当所有节点 adoptions=0，密度永远是 0.0001（地板值）
#    ae4_quick_activate 只做健康检查+遗忘+自省，不增加 adoptions
#    → 触发 ae4_quick_activate 无法改变密度
```

**幽灵 Skill 修复**（从 jobs.json 移除无效引用）：
```python
import json
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)
for j in data['jobs']:
    if j.get('name') == 'AE4容量守护（每2小时）':
        j.pop('skill', None)
        j['skills'] = []
        print('已移除幽灵 skill 引用')
with open('/opt/data/cron/jobs.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

**关键教训**：cron 任务"能跑"≠"结果正确"。skill 缺失只发 WARNING 不阻止执行，但可能导致上下文不全。更危险的是逻辑 Bug（如 ae4_quick_activate 不改变密度），需要手动执行+对比数值才能发现。

---

## watchdog类cron健康检查（非阻塞）

当需要诊断 watchdog/cron 是否正常运行，但不接受"日志写入=正常"的假设时：

```bash
# 1. 查 jobs.json 的实际运行记录（最可靠）
#    看 last_run_at / next_run_at / last_status / repeat.completed

# 2. 查 state 文件的 last_mtime 和 last_file（实时跟踪点）
cat /opt/data/brain/performance/dialog_watchdog_state.json
#    对比 state 文件本身的 mtime，判断 state 是否在持续更新

# 3. 查 sessions 目录，找出 state 之后的新会话（积压检测）
find /opt/data/sessions/ -name "*.json" -mtime -2 | head -20
#    如果 last_file 是 session_A，但 sessions 目录里有 session_B、session_C（更晚）
#    → 说明 watchdog 漏处理了，积压未处理

# 4. 手动跑一次验证（最直接）
cd /opt/data && /opt/hermes/.venv/bin/python3 /opt/data/scripts/dialog_watchdog.py
#    看是否有新的 insight 文件生成
```

**关键教训**：watchdog 类脚本的 `print()` 重定向到 cron 子进程 stdout，日志文件可能不写入（依赖 flush 和 heredoc 行为），state 文件和 session 目录才是真实状态来源。

**关键教训**：
修复后让用户在飞书发条消息，确认能收到正常回复。

---

## Scheduler Watchdog 健康检查（2026-06-09 实测）

### 正确路径（踩坑校正）
- **Watchdog日志**: `/opt/data/logs/scheduler_watchdog.log`（不是 `/opt/data/cron/` 下）
- **Watchdog脚本**: `/opt/data/scripts/scheduler_watchdog.py`
- **输出扫描对象**: `/opt/data/cron/output/**/*.md`（扫描.md文件，非sessions目录）
- **Cron状态命令**: `/opt/hermes/.venv/bin/hermes cron status`

### Pre-run数字与实查不符的原因
- Pre-run采集时截取了结果，但cron下一秒又执行了新job，产生新.md文件
- 导致pre-run报的数（7）与execute_code实查（5）不一致
- 正常现象，非故障，pre-run是上一轮cron产出，execute_code是当前实时

### 诊断命令链（execute_code版）
```python
from pathlib import Path
import subprocess, time, os

# 1. cron状态
result = subprocess.run(["/opt/hermes/.venv/bin/hermes", "cron", "status"],
                        capture_output=True, text=True, timeout=15)
print(result.stdout[:500])

# 2. Watchdog日志
log_file = "/opt/data/logs/scheduler_watchdog.log"
with open(log_file) as f:
    lines = f.read().strip().split("\n")
print("\nWatchdog log (last 5):")
for l in lines[-5:]: print(f"  {l}")

# 3. 最近3分钟.md产出
now = time.time()
output_dir = Path("/opt/data/cron/output")
new_files = [(md, now - md.stat().st_mtime)
             for md in output_dir.rglob("*.md")
             if (now - md.stat().st_mtime) < 180]
print(f"\n最近180s .md文件: {len(new_files)}")
for md, age in sorted(new_files)[:5]: print(f"  {md.name} ({age:.0f}s ago)")

# 4. PID 1 是否hermes gateway
result2 = subprocess.run(["ps", "-p", "1", "-o", "args="],
                         capture_output=True, text=True)
print(f"\nPID 1: {result2.stdout.strip()}")
```

## ⚠️ Cron 脚本诊断不要用 execute_code，要用 terminal

`execute_code` 强制 5 分钟超时杀死脚本，但带 `fcntl.flock` 的 cron 脚本在等锁时会无限阻塞（`BlockingIOError` 无法被 except 捕获导致提前退出），永远跑不完。**正确做法**：用 `terminal()` 直接读 board JSON 状态，秒级完成诊断。

```bash
# ❌ execute_code 会卡死（超时杀进程）
python3 /opt/data/scripts/task_recovery_cron.py

# ✅ terminal 直接读文件状态，秒级完成
python3 -c "
import json
from pathlib import Path
dp = Path('/opt/data/secretary/dispatch_board.json')
data = json.loads(dp.read_text())
tasks = data.get('tasks', [])
stuck = [t for t in tasks if t.get('status') == 'processing']
print(f'卡住: {len(stuck)}')
"

# ✅ 清理残留锁文件的正确方式（不要 kill）
rm -f /tmp/task_recovery_cron.lock
# 如果 rm 卡死，用 terminal 直接执行（不通过 execute_code）
```
