---
name: auto-healing-nas-monitoring
description: 用现有器官系统搭建NAS全天候监控 — 从发现免疫层到cron触发的完整链路。触发：需要给NAS建立健康监控/定时检测/第一时间发现进程挂了。
triggers:
  - 给NAS建立全天候监控
  - 发现免疫层/auto_healing存在
  - 定时检测进程存活
  - cron触发器官层健康检查
notes:
  - 核心教训：先用现有系统，再造轮子
  - auto_healing full 命令走格式化文本，不用CLI解析；直接 import full_health_check() 更可靠
  - Hermes 用自己的调度引擎，不依赖系统 crond
version: 1.0
---

# Auto-Healing 全天候监控落地工作流

## 架构现状（2026-06-03）

```
免疫层器官（/opt/data/organs/auto_healing.py）
├─ DETECTION_RULES 基础设施检测（Hernes/Ollama/磁盘等）
├─ check_organ_heartbeat() 器官层动态心跳
└─ full_health_check() 双层汇总评分

事件总线（/opt/data/organs/organ_bus.py）
└─ healing.started / healing.fixed 事件

统一推送（/opt/data/organs/unified_push.py）
└─ push_warning() → 飞书告警

器官网关（/opt/data/neural_network/organ_gateway.py）
└─ register_organ/send_to/broadcast API
```

## 落地步骤

### 1. 诊断现状

先跑一次 full 验证系统能跑通：
```bash
cd /opt/data/organs && python3 auto_healing.py full
```
**常见错误**：语法错误（healthy_pattern 重复、缺 {、缺 severity）→ 直接修 DETECTION_RULES

### 2. 检查 auto_healing 语法

auto_healing.py 是真实生产代码，必须语法正确才能用：
```bash
python3 -m py_compile /opt/data/organs/auto_healing.py && echo OK
```

常见 bug：
- 同一个 rule 有多个 `healthy_pattern` key（JSON 只取最后一个）
- rule 缺 severity（KeyError: 'severity'）
- 嵌套 dict 缺 `{` 或多 `}`

### 3. 补充系统真实守护进程检测

auto_healing 默认检测项不一定覆盖所有在跑进程。检查：
```bash
ps aux | grep -v grep | grep python
```

需要加入 DETECTION_RULES 的典型项（写在 ollama_model 规则后）：

```python
"hot_sync": {
    "name": "HotSync热同步进程",
    "check_cmd": "pgrep -f 'hot_sync.py' > /dev/null 2>&1 && echo RUNNING || echo STOPPED",
    "auto_fix": True,
    "fix_cmd": "cd /opt && nohup python3 /opt/data/scripts/hot_sync.py > /dev/null 2>&1 &",
    "severity": "high",
    "healthy_pattern": "^RUNNING$",
},
"cron_active": {
    "name": "Hermes Cron调度",
    "check_cmd": "pgrep -f 'hermes' > /dev/null 2>&1 && echo RUNNING || echo STOPPED",
    "severity": "critical",
    "healthy_pattern": "^RUNNING$",
},
"immune_cron": {
    "name": "免疫层定时检测",
    "check_cmd": "python3 -c \"import os, time; log='/opt/data/secretary/immune_health.log'; age=int((time.time()-os.path.getmtime(log))/60) if os.path.exists(log) else 999; print(age)\" 2>/dev/null || echo 999",
    "severity": "high",
    "healthy_pattern": "^[0-9]$",
},
```

### 4. 写 cron 包装器

❌ 错误做法：解析 CLI 文本输出（emoji 分割不可靠）

✅ 正确做法：直接 import 函数

```python
#!/usr/bin/env python3
"""免疫层定时检测 — 每10分钟触发auto_healing，异常时推送飞书"""
import sys
from pathlib import Path

ORGANS_DIR = Path("/opt/data/organs")
sys.path.insert(0, str(ORGANS_DIR))
from auto_healing import full_health_check
from unified_push import push_warning

def run():
    report = full_health_check()
    score = report.get("score", 0)
    failures = [r for r in report.get("infrastructure", {}).get("results", [])
                if not r.get("healthy")]
    organ_failures = [r for r in report.get("organs", {}).get("results", [])
                      if not r.get("healthy")]

    # 写日志
    from datetime import datetime
    log_file = Path("/opt/data/secretary/immune_health.log")
    log_file.write_text(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] "
        f"{'🔴' if failures else '🟢'} {score}%\n"
    )

    # 异常才推送（评分<80 且有失败项）
    if failures and score < 80:
        push_warning(
            f"⚠️ 系统健康预警 {score}%",
            f"基础设施层: {report['infrastructure']['score']}%\n"
            f"器官层: {report['organs']['score']}%\n"
            + "\n".join(f"❌ {r['name']}: {r['output']}" for r in failures[:5]),
            source="auto_healing_cron"
        )
    else:
        print(f"🟢 健康评分 {score}%（无需推送）")

if __name__ == "__main__":
    run()
```

保存到 `/opt/data/scripts/auto_healing_cron.py`

### 5. 安装 cron

```bash
crontab -e
# 添加：
*/10 * * * * /usr/bin/python3 /opt/data/scripts/auto_healing_cron.py
```

### 6. 验证

```bash
# 测试包装器
python3 /opt/data/scripts/auto_healing_cron.py

# 验证 cron 安装
crontab -l

# 验证日志
cat /opt/data/secretary/immune_health.log
```

## 关键教训

1. **先用现有系统**：auto_healing + organ_bus + unified_push 已经是完整的监控-告警闭环，只缺 cron 触发
2. **不解析 CLI 文本**：调用 `full_health_check()` 函数，而不是用 emoji 分割 stdout
3. **Hermes 不依赖系统 crond**：健康检查测 Hermes 进程即可，不用找 crond
4. **auto_healing 语法必须验证**：源文件可能是旧的/有bug的，首次使用前先 py_compile

## 验证命令汇总

```bash
# 1. 语法检查
python3 -m py_compile /opt/data/organs/auto_healing.py && echo OK

# 2. 手动跑检测
cd /opt/data/organs && python3 auto_healing.py full

# 3. 验证 cron 包装器
python3 /opt/data/scripts/auto_healing_cron.py

# 4. 确认 cron 安装
crontab -l | grep immune

# 5. 检查日志
cat /opt/data/secretary/immune_health.log
```
