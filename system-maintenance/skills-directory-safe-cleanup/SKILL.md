---
name: skills-directory-safe-cleanup
description: 安全清理与盘点 /opt/data/skills/ 嵌套目录的标准工作流。核心：skill藏在子目录，用rglob不用iterdir。
triggers: ["工具", "skill", "技能"]
---

# Skill目录安全清理工作流
======================================
**触发场景**：需要盘点/清理/归档 `/opt/data/skills/` 下的内容

## 核心原则
**skill全部藏在嵌套目录里**。`skills_dir.iterdir()` 只看顶层，无法发现子目录中的真实skill。
- 588个真实skill全部在子目录（层级2-10）
- 用 `rglob('SKILL.md')` 才是正确的扫描方法

## 标准流程

### 1. 先摸底（正确方法）
```python
from pathlib import Path

skills_dir = Path('/opt/data/skills')

# 找所有含SKILL.md的目录——用rglob，递归扫描
skill_md_files = list(skills_dir.rglob('SKILL.md'))
print(f'含SKILL.md的目录: {len(skill_md_files)}个')

# 按一级分类统计
top_dirs = {}
for f in skill_md_files:
    parts = f.parent.relative_to(skills_dir).parts
    top_dirs.setdefault(parts[0], []).append(str(f.parent.relative_to(skills_dir)))

for top, paths in sorted(top_dirs.items(), key=lambda x: -len(x[1])):
    print(f'  {top}: {len(paths)}个skill')
```

### 2. 识别纯文档目录
```python
# 所有含md文件的子目录
all_md_dirs = {}
for md in skills_dir.rglob('*.md'):
    p = md.parent
    if p == skills_dir:
        continue
    all_md_dirs.setdefault(p, []).append(md.name)

# 分离
has_skill = {d for d, files in all_md_dirs.items() if 'SKILL.md' in files}
doc_only  = {d: files for d, files in all_md_dirs.items() if 'SKILL.md' not in files}
print(f'真实skill: {len(has_skill)}个，纯文档: {len(doc_only)}个')
```

### 3. 安全归档（移动策略）
```python
import shutil
from pathlib import Path

archive_dir = Path('/opt/data/skills-archive')
archive_dir.mkdir(exist_ok=True)

moved = skipped = 0
for src_dir in sorted(doc_only.keys()):
    rel = src_dir.relative_to(skills_dir)
    dst = archive_dir / rel
    
    # 处理重名冲突
    counter = 1
    while dst.exists():
        dst = dst.parent / (dst.name + f'_v{counter}')
        counter += 1
    
    if src_dir.exists():
        shutil.move(str(src_dir), str(dst))
        moved += 1
    else:
        skipped += 1  # 已经被其他操作移走了

print(f'移动: {moved}个, 跳过: {skipped}个')
```

### 4. 验证结果
```python
# 最终验证
remaining_skills = list(skills_dir.rglob('SKILL.md'))
print(f'skills/: {len(remaining_skills)}个真实skill')

archived_skills = list(archive_dir.rglob('SKILL.md'))
print(f'archive/: {len(archived_skills)}个（含skill的误清理）')

# 检查skills/里还有无纯文档目录
doc_in_skills = [d for d in skills_dir.rglob('*') 
                 if d.is_dir() 
                 and list(d.glob('*.md'))
                 and not list(d.rglob('SKILL.md'))]
print(f'skills/剩余纯文档: {len(doc_in_skills)}个')
```

## 避坑要点
1. **永远不要用 `iterdir()` 判断skill数量**——它只扫顶层，会把深层skill误判为纯文档
2. **移动前先copy测试**——`shutil.move()` 遇重名直接报错，`dirs_exist_ok`只在copy时有效
3. **回滚策略**——误清理了有SKILL.md的目录时，从archive复制回skills/
4. **别删everos/、system/、system-maintenance/、brain-system/、mlops/**——这些分类有深层SKILL.md，顶层扫描会漏掉

## 已知真实skill数量基线（2026-06-08）
| 分类 | 数量 |
|------|------|
| system | 123 |
| knowledge | 100 |
| brain-system | 54 |
| everos | 59 |
| mlops | 57 |
| workflow | 25 |
| brain | 21 |
| devops | 19 |
| productivity | 16 |
| creative | 10 |
| debug | 10 |
| software-development | 10 |
| github | 7 |
| research | 7 |
| apple | 5 |
| media | 5 |
| mcp | 4 |
| gaming | 3 |
| methodology | 3 |
| wps-office | 1 |
| **总计** | **588** |
