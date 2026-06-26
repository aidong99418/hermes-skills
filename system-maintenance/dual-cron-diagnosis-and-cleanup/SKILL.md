---
name: dual-cron-diagnosis-and-cleanup
description: 双调度冲突诊断与清理 — 系统cron和Hermes scheduler同时跑导致重启爆发，2026-06-03实操固化。
triggers:
  - 重启后任务卡顿
  - 两套cron同时触发大批量任务
  - 系统cron和Hermes scheduler共存
notes:
  - 2026-06-03实操教训：分析花太多时间不动手，清理时误删了supercat等其他功能文件
  - 教训：删文件前先看清单，不要用find全删；分析完立即动手
version: 1.0
---

# 双调度冲突诊断与清理

## 症状
- 重启后任务瞬间堆积
- 飞书/微信消息响应卡顿
- agent.log大量 "missed... fast-forwarding"
- 多组job同时执行

## 根因
系统cron和Hermes scheduler同时运行，同类任务重复执行，资源打爆。

## 诊断命令
```bash
# 系统cron状态
which cron && crontab -l && ps aux | grep cron

# Hermes job数和撞车情况
python3 -c "
import json
d=json.load(open('/opt/data/cron/jobs.json'))
jobs=d['jobs']
enabled=[j for j in jobs if j.get('enabled',True)]
# grace=0的高频job=重启爆发根因
no_grace=[j for j in enabled if j.get('grace_seconds',0)==0 and '*/' in str(j.get('schedule',{}))]
print(f'总{len(enabled)}个job, 无grace高频{len(no_grace)}个')
"
```

## 修复操作步骤

### 一、关闭系统cron
按顺序执行：
1. `crontab -r` 清空定时条目
2. `pkill cron` 停止守护进程
3. 删除cron二进制：`/usr/sbin/cron` `/usr/bin/crontab`
4. 删除cron配置：`/etc/crontab` + `/etc/cron.d/` `/etc/cron.daily/` `/etc/cron.hourly/` `/etc/cron.monthly/` `/etc/cron.weekly/`
5. **不要删**：`/etc/supercat/*`（其他功能）、logrotate配置、apt配置

### 二、给Hermes job加grace（防爆发）
```python
import json
from datetime import datetime
data = json.load(open('/opt/data/cron/jobs.json'))
for j in data['jobs']:
    if not j.get('enabled',True): continue
    s = j.get('schedule',{})
    expr = s.get('expr','') if isinstance(s,dict) else ''
    mins = s.get('minutes',0) if isinstance(s,dict) else 0
    if mins <=1: j['grace_seconds']=60
    elif mins <=5: j['grace_seconds']=300
    elif mins <=10: j['grace_seconds']=600
    elif mins <=30: j['grace_seconds']=1800
    elif '*/1' in expr: j['grace_seconds']=60
    elif '*/5' in expr: j['grace_seconds']=300
    elif '*/10' in expr: j['grace_seconds']=600
data['updated_at']=datetime.now().isoformat()
with open('/opt/data/cron/jobs.json','w') as f:
    json.dump(data,f,ensure_ascii=False,indent=2)
```

### 三、删除重复job
```python
import json
data = json.load(open('/opt/data/cron/jobs.json'))
TO_DELETE = [
    '白日梦引擎（每2小时）','仔仔配置每日快照','仔仔每日快照（凌晨3点）',
    '秘书处Daemon自愈守护','GitHub挖宝（每6小时）','情报秘书每小时挖宝',
    'GitHub每日挖宝','全平台极致挖宝+提炼','iron_watcher保活',
    'dispatch_listener保活','额叶皮层_总控轮询','秘书轮询_任务检查',
    '机器猫自升级引擎','版本系统自检','融入巡检','架构自清洁（每周）',
]
data['jobs'] = [j for j in data['jobs'] if j.get('name','') not in TO_DELETE]
with open('/opt/data/cron/jobs.json','w') as f:
    json.dump(data,f,ensure_ascii=False,indent=2)
```

## 验证
```bash
which cron && crontab -l  # 应无输出
python3 -c "import json; d=json.load(open('/opt/data/cron/jobs.json')); print(f'{len(d[\"jobs\"])}个job')"
ps aux | grep hermes | grep -v grep
```

## 常见重复类别
| 类别 | 典型冗余 | 处理 |
|------|---------|------|
| 白日梦 | 2个每2小时 | 留1个 |
| 备份/快照 | 凌晨3点多个 | 合并1个 |
| 守护 | 5分钟×6个 | 留核心2-3个 |
| GitHub挖宝 | 多时间点 | 合并为每日9点 |
| 铁律保活 | iron_watcher×2 | 通过iron_cron_touch统一 |

## 重要教训
1. **分析完立即动手**，不要说一堆不动手
2. **删文件前先看清单**，`find`全删会误伤其他功能（如supercat）
3. **cron和Hermes是独立两套**，grace是Hermes参数，跟系统cron无关
4. **watchdog≠cron**：watchdog是Python文件监控库
5. **disk quota和cron无关**：quota是磁盘配额系统，在不同目录
