---
name: hermes-cron-script-execution-model
description: Hermes cron scheduler 强制用 Python 执行 script 字段，完全忽略 shebang。用于诊断 cron job script 类型错误。
triggers: ["调度", "cron", "定时"]
trigger: cron script SyntaxError / .sh wrapper 失效 / script 字段配置问题
version: 1.0
---

# Hermes Cron Script 执行模型

## 核心发现

Hermes cron scheduler 的 `_run_job_script` 函数（`/opt/hermes/cron/scheduler.py`）**强制用 `sys.executable` 执行 script 文件**：

```python
result = subprocess.run(
    [sys.executable, str(path)],  # 用Python运行任何扩展名！
    capture_output=True,
    text=True,
    timeout=script_timeout,
    cwd=str(path.parent),
)
```

**shebang 完全被忽略**，`.sh` 文件会被当作 Python 代码解析，导致 `SyntaxError`。

## 正确做法

### Script 字段只支持 Python 脚本（`.py`）

如果需要在 cron job 中执行 shell 命令，必须用 Python wrapper：

```python
#!/usr/bin/env python3
"""my_wrapper.py — 在 hermes cron job 中执行 shell 命令"""
import subprocess, sys, pathlib

# 执行实际的 shell 脚本/命令
result = subprocess.run(
    [sys.executable, "/opt/data/scripts/real_script.py"],
    capture_output=True, text=True,
)
# 可选：追加日志
LOG = pathlib.Path("/opt/data/some/log.log")
with LOG.open("a") as f:
    if result.stdout: f.write(result.stdout)
    if result.stderr: f.write(result.stderr)
sys.exit(result.returncode)
```

### jobs.json 配置要点

```json
{
  "script": "my_wrapper.py",   // ← 必须是 .py，放在 ~/.hermes/scripts/
  "prompt": "检查上方输出是否包含错误，如有错误请报告。"
  // 不要再把命令写在 prompt 里 — script 已执行
}
```

### 路径规则

- scripts 必须放在 `~/.hermes/scripts/`（通过 `get_hermes_home() / "scripts"` 解析）
- 支持相对路径（`brain_backup_wrapper.py`）和绝对路径（`~/scripts/xxx.py`）
- **不支持**绝对路径如 `/opt/data/scripts/xxx.py`（会被安全校验拦截）

## 诊断命令

```bash
# 查看当前 cron scheduler 的 script 执行逻辑
grep -n "subprocess\|sys.executable\|run_job_script" /opt/hermes/cron/scheduler.py

# 查看 hermes home
python3 -c "from hermes_constants import get_hermes_home; print(get_hermes_home())"

# 列出当前 scripts
ls -la ~/.hermes/scripts/
```

## 常见错误模式

| 错误 | 原因 | 修复 |
|------|------|------|
| `SyntaxError: invalid syntax` on shebang line | `.sh` 文件被 Python 执行 | 改用 `.py` wrapper |
| `Script not found: /opt/data/scripts/xxx.sh` | 路径不在 `~/.hermes/scripts/` | 复制到正确位置 |
| `Blocked: script path resolves outside` | 绝对路径超出 HERMES_HOME | 用相对路径 |

## 批量扫描脚本字段（防止同类问题）

```bash
# 检查所有 cron job 的 script 字段，排查 bash 脚本和绝对路径
python3 -c "
import json
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)
for job in data['jobs']:
    script = job.get('script')
    if script:
        is_bash = script.startswith('#!/bin') or (isinstance(script, str) and script.endswith('.sh'))
        print(f\"{'⚠️ BASH' if is_bash else '✅ PY'} [{job['id']}] {job['name']}: {repr(script[:60])}")
"
```

**本次修复的3个问题：**
- `brain_backup_wrapper.sh` → `brain_backup_trigger.py`（Brain系统触发式备份）
- `self_observer_wrapper.sh` → `/opt/data/brain/performance/self_observer.py`（自进化每日报告）
- bash代码内嵌 → `learning_engine.py`（learning-engine-v2）

## 绝对路径支持情况

skill 旧版说"不支持绝对路径"，实测：绝对路径（`/opt/data/...`）可以生效，前提是文件存在且 hermes 有权限读取。相对路径（`brain_backup_trigger.py`）会自动在 `$HERMES_HOME/scripts/` 下查找。

## 发现历程

2026-05-30：整点 cron 触发 brain_backup 报错 SyntaxError on line 2 of brain_backup_wrapper.sh。
深入 scheduler.py 源码发现 `_run_job_script` 用 `subprocess.run([sys.executable, path])` 执行，
shebang 对 Hermes cron 完全无效。修复：用 Python wrapper + 改 jobs.json script 字段为 `.py`。

本次会话额外发现：排查过程中扫描全部 jobs.json，发现 self_observer_wrapper.sh 和 learning-engine-v2
也有同类问题（bash 代码被当作 Python 执行），一并修复。建议定期运行批量扫描命令防止类似问题积压。
