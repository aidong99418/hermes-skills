---
name: pgrep-cron-false-positive-fix
version: "2026-06-03"
tags: [cron, pgrep, process-detection, watchdog, debugging]
trigger: cron/watcher脚本误报进程存活，或pgrep结果与ps aux不一致
---

# pgrep 在 Cron 环境下的误报陷阱与修复

## 核心问题

在 cron 调度环境中，`pgrep -f "process_name.py"` 会**匹配 cron shell 命令本身**，因为 cron wrapper 的命令包含脚本路径字符串：

```bash
# cron 实际执行的 shell 命令：
bash -c '... pgrep -f "deputy_dispatch.py" ...'

# pgrep -f 会匹配到上面这整行 bash -c 命令（它包含 "deputy_dispatch.py" 字符串）
```

这导致：
- **误报为存活**：shell 命令字面量被当作进程
- **检测失效**：如果脚本名恰好被排除，反而漏报

## 修复方案（3层过滤）

```python
import subprocess, os

def is_running(name: str) -> bool:
    pattern = f"{name}.py"
    r = subprocess.run(
        ["pgrep", "-a", "-f", pattern],
        capture_output=True, text=True
    )
    for line in r.stdout.strip().split("\n"):
        if not line.strip():
            continue
        pid_str = line.split()[0]
        try:
            pid = int(pid_str)
        except (ValueError, IndexError):
            continue

        # 排除1：自身PID（watchdog 自身）
        if pid == os.getpid():
            continue
        # 排除2：父shell进程（cron wrapper bash）
        if pid == os.getppid():
            continue
        # 排除3：包含 -c 或 source 的 cron shell 命令行
        if " -c " in line or line.startswith("bash") or "source " in line:
            continue
        # 确认必须是 python 进程
        if "python" in line.lower() and pattern in line:
            return True
    return False
```

## 验证命令

```bash
# 对比测试：pgrep vs 真实进程
pgrep -a -f "deputy_worker.py" | grep -v grep

# 应该只看到 python 进程，不应有 bash -c 行
```

## 关键教训

| 错误方法 | 问题 |
|---------|------|
| `pgrep -f pattern` 直接用 | 匹配 cron shell 命令本身（命令里包含 pattern 字符串）|
| `ps aux \| grep pattern \| grep -v grep` | 同样会匹配 shell 命令中的字面量 |
| 读锁文件 `/tmp/*.lock` | daemon 未正确写锁时完全失效 |

| 正确方法 | 说明 |
|---------|------|
| `pgrep -a -f pattern` + PID过滤 | 最可靠，排除自身和父进程 |
| `ps auxww \| grep "[x]pattern"` | [x] 技巧在管道模式下有效 |

## 应用场景

- 秘书处 watchdog 脚本（每5分钟检查 daemon 存活）
- cron 调用的进程自愈脚本
- 任何通过 cron/agent 调度检测其他进程是否存活的场景
