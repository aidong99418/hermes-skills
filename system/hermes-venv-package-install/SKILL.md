---
name: hermes-venv-package-install
description: hermes venv 缺包时安装依赖的标准流程——当 cron 报 No module named 'xxx' 时，按此skill修复
trigger: cron报ModuleNotFoundError / hermes venv缺包 / pip install失败
tags: [hermes, venv, pip, dependency, cron]
created: 2026-06-19
---

# Hermes Venv 依赖包安装

## 触发场景
cron 任务报 `No module named 'xxx'`、hermes venv 缺包、pip install 失败（externally-managed-environment / No module named pip）

## 根因
hermes venv (`/opt/hermes/.venv/`) 配置为 `include-system-site-packages = false`，完全隔离。同时 venv 内 pip 缺失（损坏）。

## 安装步骤（按顺序尝试）

### Step 1：找备选 pip
```bash
# 按优先级找可用的 pip
/opt/data/scripts/venv/bin/pip           # 第1选择
/opt/data/venv/bin/pip
/usr/bin/pip
```
验证：`/opt/data/scripts/venv/bin/pip --version`

### Step 2：安装到 hermes venv site-packages
```bash
/opt/data/scripts/venv/bin/pip install <包名> \
  --target /opt/hermes/.venv/lib/python3.13/site-packages/ -q
```

### Step 3：验证
```bash
/opt/hermes/.venv/bin/python3 -c "import <包名>; print('<包名>', <包名>.__version__)"
```

### Step 4：验证完整导入链（可选，做更深验证）
```bash
cd /opt/data && /opt/hermes/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '/opt/data')
from brain.organs.evolution_engine import adopt_to_ae4
test_island = {'id': 'test', 'score': 0.8, 'type': 'fix_attempt', 'problem': 'test'}
result = adopt_to_ae4(test_island)
print('Result:', result)
"
```

## 已知损坏的 venv 信息
- 路径：`/opt/hermes/.venv/`
- Python：`/opt/hermes/.venv/bin/python3` → `/usr/bin/python3`
- venv pip：`/opt/hermes/.venv/bin/pip` → **不存在**
- 系统 pip：`/usr/bin/pip` → 有但装不进 venv（externally-managed）
- pyvenv.cfg：`include-system-site-packages = false`（隔离）

## 永久修复方案
用 uv 重建 hermes venv，从 requirements.txt 重新生成，可一劳永逸解决缺包问题：
```bash
/opt/uv/bin/uv venv /opt/hermes/.venv --python /usr/bin/python3.13
/opt/uv/bin/uv pip install -r /opt/hermes/requirements.txt \
  --python /opt/hermes/.venv/bin/python3
```
