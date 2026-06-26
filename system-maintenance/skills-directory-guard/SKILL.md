---
name: skills-directory-guard
description: Skills目录守护系统 — 防止skills/目录碎片化的长期机制。单skill目录自动归入knowledge/，空目录清理，新top-level目录预警。每周一自动跑。
triggers:
  - 审计skills/目录结构
  - 发现单skill目录散落在一级目录
  - 防止skills/持续碎片化
  - 每次挖宝/学习后检查
notes:
  - 核心代码：/opt/data/scripts/auto_integrator.py --guard
  - 白名单：20个合法一级分类（含methodology，2026-06-08更新）
  - 执行前先备份：cp -r /opt/data/skills/ /opt/data/backups/skills_pre_guard/
  - 实战：2026-06-04 从185个分类压缩到19个，489→488个skill，全过程无损
  - 已知Bug修复：DirEntry失效/跨设备EXDEV/幂等FileExistsError（2026-06-08）
version: 1.1
---

## ⚠️ auto_integrator.py --guard 的3个已知Bug（2026-06-08修复）

### Bug 1: DirEntry 路径缓存失效（严重）
- **症状**：`shutil.move(str(entry), ...)` 后 `FileNotFoundError: No such file or directory`
- **根因**：`os.scandir()` 返回的 `DirEntry` 对象在 `os.rename()` 成功后缓存失效，后续访问 `entry.path` 报错
- **修复**：循环开始时预捕获 `src_path = entry.path`，后续全部使用字符串路径
```python
src_path = entry.path   # 预先捕获
src_name = entry.name
# 后续用 src_path 而非 entry.path
shutil.move(src_path, str(dst))
```

### Bug 2: 跨设备移动 EXDEV 崩溃（严重）
- **症状**：`OSError: [Errno 18] Invalid cross-device link` 导致中途崩溃
- **根因**：Docker overlay 层与宿主机路径间移动触发 EXDEV（Unix跨文件系统移动限制）
- **修复**：
```python
try:
    shutil.move(src_path, str(dst))
except OSError as e:
    if e.errno == 18:  # EXDEV
        shutil.copytree(src_path, str(dst))
        shutil.rmtree(src_path)
    else:
        raise
```

### Bug 3: 幂等重复运行 FileExistsError（中等）
- **症状**：重复执行时报 `FileExistsError`（备份目标已存在）
- **根因**：跨 run 时同日期备份目录已存在，`copytree(dirs_exist_ok=False)`
- **修复**：空目录清理前检查备份目标是否已存在
```python
dst_backup = backup_dir / entry.name
if dst_backup.exists():
    shutil.rmtree(entry.path)  # 直接删除，已备份过
else:
    shutil.copytree(entry.path, dst_backup)
    shutil.rmtree(entry.path)
```

## 白名单管理要点

- `methodology/` 含3个有效skill（deep-source-analysis-workflow等），需加入白名单
- `version_history/` 可能含 `.md` 但非 `SKILL.md`，仍视为"空目录"清理
- 游离的 `.md` 单文件技能（如 `agent-zero.md`、`agenticSeek.md`）是 GitHub 挖宝产物，应保留在顶层或移入 `knowledge/`

# 三波融合工作流（2026-06-04实战）

## 第一波：清理无效skill

**操作**：删除 `_archived/` + `version_history/` + 25个散落根目录.md文件

**注意**：先扫描根目录散落文件，`.md`文件可能是知识沉淀（比如 `brain-core-principles.md`），只删收集癖残留

## 第二波：同名目录合并

**操作**：
- 5个brain相关目录 → 2个集中（brain-system-maintenance/integration → brain-system，brain-team-architecture → brain）
- 6个feishu skill → 1个统一的 `feishu-card-builder`
- 删前先 `shutil.copytree` 备份

## 第三波：分类压缩（最关键）

**扫描阶段**：
```python
# 统计每个一级分类的skill数量
for entry in os.scandir(skills_dir):
    cnt = sum(1 for r,d,f in os.walk(entry.path) for f in f if f == "SKILL.md")
```
结果：185个分类里167个只有1~2个skill → 全部移入 `knowledge/`

**移动策略**：
- 有.py脚本的可执行skill → 融入对应分类
- 办公/ML/基础设施 → 对应已有分类
- 其余 → `knowledge/`

**空目录陷阱**：空目录可能有 DESCRIPTION.md，先 `os.listdir` 再判断

## 真实影响点

只有 `auto_integrator.py` 的 DOMAINS.target_files 硬编码路径需要修：
```python
# 之前
"/opt/data/skills/auto-learning/SKILL.md"
"/opt/data/skills/skill-creator/SKILL.md"
# 之后
"/opt/data/skills/knowledge/auto-learning/SKILL.md"
"/opt/data/skills/knowledge/skill-creator/SKILL.md"
```

## 最终结果（2026-06-04）

```
185个分类 → 19个分类
488个skill无损
0个空目录
0个旧路径引用
备份：1.6MB /opt/data/backups/skills_cleanup_20260604_013831/
```

## 最终结果（2026-06-08）

```
20个分类，494个skill
单skill目录归位3个（秘书处架构升级工作流引擎等）
空目录清理5个（domain/inference-sh/smart-home/social-media/version_history）
methodology 纳入白名单
✅ Skills目录结构健康，无需干预
备份：/opt/data/backups/skills_guard_2026-06-08/
```

## 长期守护

每周一 08:00 自动跑 `--guard`，单skill目录自动归位，空目录自动清理，新目录预警。

# Skills目录守护系统

## 核心问题

每次挖宝/学习都会在 `/opt/data/skills/` 新建目录，日积月累导致185个一级分类，大部分只有1~2个skill。

## 解决方案

在 `auto_integrator.py` 里加守护规则，3个动作：

| 情况 | 处理 |
|------|------|
| 单skill目录（≤2个SKILL.md） | **自动**移入 `knowledge/` |
| 不在白名单的新top-level目录 | 预警记录，等人工确认 |
| 空目录 | 备份后删除 |

## 白名单（20个合法一级分类，2026-06-08更新）

```python
ALLOWED_TOP_LEVEL = {
    "apple", "brain", "brain-system", "creative", "debug",
    "devops", "everos", "gaming", "github", "knowledge",
    "mcp", "media", "methodology",  # 2026-06-08 新增
    "mlops", "productivity", "research",
    "software-development", "system", "system-maintenance", "workflow",
}
```

## 使用方法

```bash
# 手动运行
python3 /opt/data/scripts/auto_integrator.py --guard

# 每周一自动跑（已配置cron job_id: a33cfd69dc90）
```

## 关键教训（融合必读）

### 融合前必须做的事

1. **先扫描** — `os.walk` 统计每个分类的 SKILL.md 数量
2. **先备份** — `cp -r /opt/data/skills/ /opt/data/backups/`
3. **扫空目录隐藏文件** — 空目录可能有 DESCRIPTION.md
4. **找硬编码路径** — `auto_integrator.py` 里 DOMAINS.target_files 可能引用旧路径
5. **验证cron** — jobs.json 不应引用skill目录路径

### 融合中的陷阱

| 陷阱 | 发现方式 | 解决方案 |
|------|----------|----------|
| execute_code sandbox 看不到文件 | 输出为空/无输出 | 用 `terminal` 命令 |
| 散落.md不是skill | 目录0 skill但有.md | 检查 os.listdir |
| 空目录有隐藏文件 | 目录0 skill但无法rmdir | 逐个文件检查 |
| skill_view 用 name 字段 | 目录重组不破坏 skill_view | 不需要改 |
| auto_integrator 硬编码路径 | grep target_files | 手动修 |
| cron用skill名不路径 | jobs.json无skills/路径引用 | 安全 |
| version_history含.md非SKILL.md | 统计只看SKILL.md | 视为空目录清理 |
| DirEntry在move后失效 | 重复执行第2次报错 | 预捕获src_path字符串 |
| 跨设备EXDEV | Docker overlay场景 | copytree+rmtree兜底 |
| 幂等重跑FileExistsError | 第二次执行崩溃 | 检查dst_backup.exists() |

### 融合后的真实影响点

只有 `auto_integrator.py` 里的 `DOMAINS["target_files"]` 是危险区，其他（器官/脚本/cron）都安全。
