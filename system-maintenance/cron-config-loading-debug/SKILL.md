---
name: cron-config-loading-debug
description: Cron调度器config.yaml加载返回None导致所有任务崩溃的诊断与修复（2026-06-09）
triggers: ["调试", "定时", "配置", "错误", "bug", "cron", "调度", "config"]
---
# Cron调度器配置加载Bug诊断与修复

## 触发条件
cron任务全部静默（最后活跃2026-06-01），scheduler_cron.py任务无法执行。

## 根因（2026-06-09凌晨实测）

**链路：**
```
scheduler_cron.py → load_yaml('/opt/hermes/config.yaml') → 文件不存在/格式错 → 返回None
↓
_cfg = None（不是{}）
↓
cron任务运行 → cron_util.py 第31行 _cfg["gateway"]["url"]
↓
TypeError: 'NoneType' object is not subscriptable → 任务直接崩溃退出
```

- gateway.py 的 load_config() 实际调用 config_guardian.py，能正常工作
- 但 scheduler_cron.py 直接用 load_yaml() 读 /opt/hermes/config.yaml，绕过了兼容层
- /opt/hermes/ 路径大概率是错的，应该是 /opt/data/hermes/

## 修复步骤

### Step 1：确认配置文件实际位置
```bash
ls -la /opt/hermes/config.yaml 2>/dev/null && echo "存在" || echo "不存在"
ls -la /opt/data/hermes/config.yaml 2>/dev/null && echo "存在" || echo "不存在"
```

### Step 2：修复scheduler_cron.py路径 + None保护
找到 scheduler_cron.py 中的 load_yaml 调用，修改为：
```python
# 兼容路径
import os
_config_path = '/opt/hermes/config.yaml'
if not os.path.exists(_config_path):
    _config_path = '/opt/data/hermes/config.yaml'
_cfg = load_yaml(_config_path) or {}
```

### Step 3：验证
```bash
cd /opt/data && python3 -c "
from scheduler_cron import _cfg
print('配置:', type(_cfg), 'OK' if _cfg else 'NONE-需修复')
"
```

## 预防
任何新cron脚本读配置，禁止直接 `load_yaml('/opt/hermes/xxx.yaml')`，统一走 `/opt/data/hermes/` + None兜底。
