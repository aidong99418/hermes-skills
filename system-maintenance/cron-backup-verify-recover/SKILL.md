---
name: cron-backup-verify-recover
description: Cron备份任务验证 + MEMORY.md空文件检测恢复 + RAG断链修复。触发：每日备份cron后检查、执行备份脚本后验证、发现文件丢失。自动恢复+修复jobs.json配置。
triggers: ["恢复", "定时", "cron", "调度", "备份"]
tags: [备份, 恢复, MEMORY.md, RAG, cron, 断链]
related_skills: [system-full-audit, dispatcher-cleanup-workflow]
version: 1.0
---

# Cron 备份任务验证与恢复

## 触发场景

- 每日 03:00 备份 cron 执行后
- 手动执行备份脚本后
- 发现 MEMORY.md / RAG 异常时

## 快速诊断脚本

```python
#!/opt/hermes/.venv/bin/python3
"""快速验证备份完整性 + MEMORY.md空文件检测"""
import os, shutil, glob

BACKUP_DIR = "/volume2/数据备份/memory_backup"
MEMORY_SRC = "/opt/data/memories/MEMORY.md"
RAG_DIR = "/opt/data/rag_index"

def check():
    issues = []
    warnings = []

    # 1. MEMORY.md 空文件检测（critical）
    size = os.path.getsize(MEMORY_SRC)
    if size < 100:  # 正常应该几KB
        warnings.append(f"MEMORY.md 异常小: {size} bytes，需要从备份恢复")

    # 2. manifest 日期是否为今天
    manifest = f"{BACKUP_DIR}/manifest.json"
    if os.path.exists(manifest):
        import json
        with open(manifest) as f:
            m = json.load(f)
        if m.get("date") != os.popen("date +%Y-%m-%d").read().strip():
            issues.append(f"manifest日期过时: {m.get('date')}")
    else:
        issues.append("manifest.json 不存在")

    # 3. 检查 RAG 断链
    broken_links = []
    for root, dirs, files in os.walk(RAG_DIR):
        for d in dirs:
            path = os.path.join(root, d)
            if os.path.islink(path) and not os.path.exists(path):
                broken_links.append(path)
    if broken_links:
        issues.append(f"RAG存在 {len(broken_links)} 个断链: {broken_links[:3]}")

    return issues, warnings

issues, warnings = check()
for w in warnings:
    print(f"⚠️  {w}")
for i in issues:
    print(f"🚨  {i}")
if not issues and not warnings:
    print("✅ 备份状态正常")
```

## MEMORY.md 恢复流程

```bash
# 1. 找到最新的备份
ls -lt "/volume2/数据备份/memory_backup/" | grep "MEMORY_" | head -5

# 2. 检查候选备份大小
wc -c "/volume2/数据备份/memory_backup/MEMORY_2026-05-29_001206.md"

# 3. 确认恢复
cp "/volume2/数据备份/memory_backup/MEMORY_2026-05-29_001206.md" \
   /opt/data/memories/MEMORY.md

# 4. 验证
wc -c /opt/data/memories/MEMORY.md
```

## 备份脚本修复（RAG断链导致copytree失败）

**问题**：`shutil.copytree` 遇到 broken symlink 直接抛异常，cron 静默失败，manifest 停滞在前一天

**修复**：在 jobs.json 的备份 prompt 中修改 `shutil.copytree` 调用

```python
# 修复前
shutil.copytree(RAG_DIR, rag_bak)

# 修复后（添加 dirs_exist_ok + symlinks）
shutil.copytree(RAG_DIR, rag_bak, dirs_exist_ok=True, symlinks=True)
```

```bash
# 同时修复已存在的断链
find /opt/data/rag_index -type l ! -exec test -e {} \; -print 2>/dev/null
# 逐个删除断链（确认是broken symlink后）
rm "/opt/data/rag_index/brain/trigger_config.md"
```

## 手动重新执行备份（修复后）

```python
import shutil, json, os
from datetime import datetime

BACKUP_DIR = "/volume2/数据备份/memory_backup"
MEMORY_SRC = "/opt/data/memories/MEMORY.md"
RAG_DIR = "/opt/data/rag_index"
PROTECTED_SRC = "/opt/data/memories/protected_archive.json"

date = datetime.now().strftime("%Y-%m-%d")
os.makedirs(BACKUP_DIR, exist_ok=True)

# 备份 MEMORY.md
mem_bak = f"{BACKUP_DIR}/MEMORY_{date}.md"
shutil.copy2(MEMORY_SRC, mem_bak)

# 备份 RAG（关键：dirs_exist_ok=True, symlinks=True）
rag_bak = f"{BACKUP_DIR}/rag_index_{date}"
if os.path.exists(rag_bak):
    shutil.rmtree(rag_bak)
shutil.copytree(RAG_DIR, rag_bak, dirs_exist_ok=True, symlinks=True)

# 备份 protected_archive
prot_bak = f"{BACKUP_DIR}/protected_archive_{date}.json"
if os.path.exists(PROTECTED_SRC):
    shutil.copy2(PROTECTED_SRC, prot_bak)

# 写入 manifest
manifest = f"{BACKUP_DIR}/manifest.json"
manifest_data = {
    "date": date,
    "memory_backup": f"MEMORY_{date}.md",
    "rag_backup": f"rag_index_{date}",
    "protected_backup": f"protected_archive_{date}.json" if os.path.exists(PROTECTED_SRC) else None,
}
with open(manifest, 'w') as f:
    json.dump(manifest_data, f, ensure_ascii=False, indent=2)

# 清理30天前旧备份
import glob, time
cutoff = time.time() - 30 * 86400
cleaned = 0
for bak in glob.glob(f"{BACKUP_DIR}/*"):
    if os.path.getmtime(bak) < cutoff:
        if os.path.isfile(bak):
            os.remove(bak)
        else:
            shutil.rmtree(bak)
        cleaned += 1

print(f"✅ 备份完成: {date}")
print(f"   MEMORY: {mem_bak} ({os.path.getsize(mem_bak)} bytes)")
print(f"   RAG: {rag_bak}/")
print(f"   清理旧备份: {cleaned} 个")
```

## 验证清单

| 检查项 | 命令 | 预期结果 |
|--------|------|---------|
| MEMORY.md 大小 | `wc -c /opt/data/memories/MEMORY.md` | > 1000 bytes |
| manifest 日期 | `cat /volume2/数据备份/memory_backup/manifest.json` | 今天日期 |
| 今日 MEMORY 备份 | `ls -lt /volume2/数据备份/memory_backup/ | grep "MEMORY_$(date +%Y-%m-%d)"` | 有文件且 > 1KB |
| 今日 RAG 备份 | `du -sh /volume2/数据备份/memory_backup/rag_index_$(date +%Y-%m-%d)/` | 有内容 |
| RAG 断链 | `find /opt/data/rag_index -type l ! -exec test -e {} \; -print` | 无输出 |

## 已知 RAG 断链来源

- `/opt/data/rag_index/brain/trigger_config.md` → `/opt/data/brain/trigger_config.md`（已删除，/opt/data/brain/ 下无此文件）
- 发现新断链时：确认目标文件是否存在，如不存在则删除 symlink
