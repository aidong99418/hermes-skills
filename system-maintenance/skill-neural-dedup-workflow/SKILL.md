---
name: skill-neural-dedup-workflow
description: skill_neural去重验证与修复——诊断重复skill、固化去重逻辑到build脚本、防止重建时恢复旧版本。触发：发现重复skill/自动重建后节点数异常/想去重验证。
triggers: ["工具", "skill", "技能"]
version: 1.0.0
created: 2026-06-05
tags: [skill-neural, dedup, bugfix, safety]
---

# skill_neural去重验证与修复工作流

## 症状
新会话忘记旧状态，重建skill_neural时把已删除的重复skill又恢复回去。

## 根因（2026-06-05实测）
build_neural_network.py只扫描skills/*顶层，漏掉所有子目录skill。重建后skill节点从123暴跌到37。

## 修复四步曲

### Step1: 找重复
```bash
python3 /opt/data/scripts/skill_dedup_check.py
```
输出：每个name的version/mtime对比，决定保留哪个。

### Step2: 删重复
保留原则：**version更新 > mtime更新**
- 删 loser path（SKILL.md所在目录）
- 备份到 skill_neural.snap/dedup_backup/{date}/ 再删

### Step3: 修build脚本
`/opt/data/scripts/build_neural_network.py` 必须递归扫描：
```python
skill_dirs = []
for p in Path("/opt/data/skills").glob("*"):
    if p.is_dir() and not p.name.startswith("."):
        skill_dirs.append(p)
# 递归找子目录
for p in Path("/opt/data/skills").glob("*/"):
    if p.is_dir() and not p.name.startswith("."):
        skill_dirs.append(p)
```

### Step4: 内置快照
build_neural_network.py 每次重建前自动快照：
```python
snap_dir = Path("/opt/data/skill_neural.snap")
snap_dir.mkdir(exist_ok=True)
ts = datetime.now().strftime("%m%d_%H%M%S")
shutil.copy(skill_neural_path, snap_dir / f"skill_neural_{ts}.json")
```

## 关键文件
- `/opt/data/skills/` — 顶层（漏扫根因）
- `/opt/data/skills/knowledge/` — 子目录（被漏）
- `/opt/data/skill_neural.snap/` — 快照目录
- `/opt/data/scripts/build_neural_network.py` — 需修复
- `/opt/data/scripts/skill_dedup_check.py` — 验证脚本
