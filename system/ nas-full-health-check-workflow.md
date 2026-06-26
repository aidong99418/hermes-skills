# NAS系统全面健康检查工作流

## 触发场景
系统全身检查/诊断/验证各子系统是否正常运转时激活。全自动执行，不等指令。

## 诊断命令库（按顺序执行）

### 1. Gateway健康
```bash
# Gateway进程和端口
ps aux | grep hermes | grep -v grep
curl -s --max-time 3 http://127.0.0.1:18643/api/status

# 日志位置（重启后从gateway.log切到agent.log，是正常行为）
tail -5 /opt/data/logs/agent.log 2>/dev/null
tail -5 /opt/data/logs/gateway.log 2>/dev/null
```

### 2. 派工板 + 结果板
```python
# 清理failed/stale任务，修复结果板
python3 -c "
import json
from datetime import datetime, timezone
with open('/opt/data/secretary/dispatch_board.json') as f:
    d = json.load(f)
tasks = d.get('tasks', [])
print(f'任务: {len(tasks)}个')
for t in tasks:
    s = t.get('status','?')
    ct = t.get('created_at','?')[:19]
    print(f'  {t.get(\"task_id\",\"?\")[:30]} | {s} | {ct}')
    # 删除failed + 超15min的processing + 超2h的pending
    if s == 'failed': tasks.remove(t)
    # ... 清理逻辑
"
```

### 3. Cron调度
```bash
# 看cron output文件时间戳（真实执行证明，不是last_run字段）
ls -lt /opt/data/cron/output/ | head -20
# 找iron（铁律脉络）相关输出
ls /opt/data/cron/output/ | grep -E "b7b51|9c84b|ac087"
```

### 4. 器官健康
```bash
tail -10 /opt/data/cron/output/organ_health.log 2>/dev/null
```

### 5. Ollama
```bash
curl -s --max-time 5 http://127.0.0.1:11434/api/tags | python3 -c "import json,sys; d=json.load(sys.stdin); [print(m['name']) for m in d.get('models',[])]"
```

### 6. 神经脉络（箭头key特殊处理）
```python
# 重要：synapse.json的key含箭头字符→，不能用get()遍历
python3 -c "
import json
from pathlib import Path
syn = Path('/opt/data/neural_network/synapse.json')
d = json.loads(syn.read_text())
print(f'突触节点: {len(d)}个')
active = [(k,v) for k,v in d.items() if v.get('weight',0) > 0.5]
print(f'活跃: {len(active)}个')
"
```

### 7. Gateway Hook（4个活跃Hook）
```bash
ls /opt/data/hooks/  # 应该在: brain_coordinator emotion_sense router_coordinator synapse_recorder
cat /opt/data/hooks/brain_coordinator/HOOK.yaml  # 验证标准格式
```

### 8. Feishu去重
```python
python3 -c "
import json
with open('/opt/data/feishu_seen_message_ids.json') as f:
    d = json.load(f)
ids = d if isinstance(d, list) else d.get('ids', [])
print(f'去重ID: {len(ids)}个')
"
```

## 已知Cosmetic Bug（不是真故障）

| 现象 | 真相 | 结论 |
|------|------|------|
| `jobs.json` last_run="从未" | 字段不持久化，重启后丢失 | ✅ 正常，文件时间戳才是真据 |
| `gateway.log`重启后空白 | 日志自动切换到`agent.log` | ✅ 正常行为 |
| guardian反复"配置损坏" | providers替换custom_providers后基准线变化 | ✅ 正常，guardian在建立新基准 |

## 清理命令模板
```python
# 清理failed任务
for t in tasks[:]:
    if t.get('status') == 'failed':
        tasks.remove(t); removed += 1

# 清理processing>15min（watcher已处理但未清理）
if t.get('status') == 'processing':
    try:
        age_m = (now - datetime.fromisoformat(t['created_at'].replace('Z','+00:00'))).total_seconds()/60
        if age_m > 15: tasks.remove(t)
    except: pass

# 清理结果板无task_id的占位数据 + >24h的done数据
for r in results[:]:
    if not r.get('task_id') or (r.get('status')=='done' and age>86400):
        results.remove(r)
```

## 固化时机
每次做完文件修改/配置变更后立即固化，不要等提醒。MEMORY只存铁律骨架，细节存skill。
