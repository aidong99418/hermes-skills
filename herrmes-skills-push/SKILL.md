---
name: herrmes-skills-push
description: 往GitHub herrmes-skills仓库推送skill的标准流程。包含：目录结构规范、git身份配置、PAT凭证、批量推送步骤。董哥自己的skill仓库，每6小时自动同步回NAS external-skills目录。
triggers:
  - "推skill到github"
  - "herrmes-skills"
  - "skill推送"
category: github
version: 1.0
author: 打工仔
date: 2026-05-23
---

# herrmes-skills 推送规范

## 仓库信息
- **GitHub**: https://github.com/aidong99418/herrmes-skills
- **本地同步目录**: `/opt/data/external-skills/`
- **分支名**: `master`（不是 `main`，之前踩过坑）
- **自动同步**: 每6小时cron自动git pull（job_id: 402c591a41d9）
- **本地路径配置**: `/opt/data/config.yaml` 第251行 `external_dirs: [/opt/data/external-skills]`

## skill目录结构规范

每个skill必须包含：
```
skill-name/
├── SKILL.md              # 必须：skill元数据+使用说明
└── scripts/              # 可选：配套脚本
    └── *.py
```

**SKILL.md 必须包含YAML frontmatter：**
```yaml
---
name: skill-name           # 必须，唯一标识
description: 简短描述      # 必须，<100字
triggers:                  # 可选，触发条件关键词
  - "关键词1"
  - "关键词2"
category: xxx              # 分类：brain/devops/productivity等
version: 1.0               # 版本号
author: 打工仔
date: 2026-05-23
---
```

## 目录结构（2026-05-23纠正）

| 目录 | 作用 | 是否Git仓库 |
|------|------|------------|
| `/opt/data/skills/` | 实时层（37个skill），Agent实际加载这里 | ❌ 不是 |
| `/opt/data/external-skills/` | git仓库（16个skill），GitHub同步目录 | ✅ 是 |

**关键认知**：`/opt/data/skills/` 就是你看到的技能列表，但直接在这里 `git` 无效。

### 写入流程（标准步骤）
```bash
# Step 1: 写技能到实时层
vim /opt/data/skills/my-new-skill/SKILL.md

# Step 2: 同步到git仓库
cp -r /opt/data/skills/my-new-skill /opt/data/external-skills/

# Step 3: 提交并推送（远程有新提交要先pull）
cd /opt/data/external-skills
git add my-new-skill/
git commit -m "feat: add my-new-skill"
git pull origin master --rebase    # ← 必做，否则push被rejected
git push
```

### push被rejected的解决方法
```bash
git pull origin master --rebase
# 如果有冲突，解决后：
git add .
git rebase --continue
git push
```

## 推送流程（简洁版）

### 1. 首次配置（只做一次）
```bash
# 配置git身份
git config --global user.email "aidong99418@users.noreply.github.com"
git config --global user.name "打工仔"

# 配置remote（含PAT）
git remote set-url origin https://ghp_<TOKEN>@github.com/aidong99418/hermes-skills.git
```

### 2. 每次推送
```bash
# 假设新写了 /opt/data/skills/some-skill/
cp -r /opt/data/skills/some-skill /opt/data/external-skills/
cd /opt/data/external-skills
git add some-skill/
git commit -m "feat: add some-skill"
git pull origin master --rebase   # ← 每次都要
git push
```

## 踩坑记录

### ⚠️ 关键：分支名是 `master` 不是 `main`
**现象**：`git push origin main` 失败，报 `error: src refspec main does not match any`
**原因**：仓库创建时用 `master` 分支，而非 GitHub 默认的 `main`
**解决**：所有涉及分支名的地方都要用 `master`
```bash
# 错误的（踩坑写法）
git push origin main
git pull origin main

# 正确的
git push origin master
git pull origin master
```
涉及的文件：`brain_backup_trigger.py`、`brain_backup.py`、`sync_hermes_skills.sh`

## brain系统双保险备份策略（2026-05-23建立）

### 触发式备份（文件变更即备份）
脚本：`/opt/data/scripts/brain_backup_trigger.py`
- 监控14个brain核心文件（脚本+数据+配置）
- 检测到变更 → 立即备份到 `/volume2/数据备份/brain_backup/YYYYMMDD/triggered/`
- 同时复制到hermes-skills仓库对应目录 → 自动git commit + push
- 无变更时跳过，零浪费

### 定时完整备份（每小时整点）
cron job_id: `6b64ab11c8c3`，`0 * * * *`
- 整点检测14个文件，任一有变更则完整快照
- 保留7天，自动清理旧版本

### GitHub自动同步（每6小时）
- 任何本地变更的文件，自动推送到 `master` 分支
- GitHub就是云端容灾+版本历史

### 备份文件清单
核心脚本：`brain_invoke.py / brain_retriever.py / brain_thinker.py / dialog_watchdog.py / external_fetcher.py / web_scraper.py`
数据配置：`connections.json / inference_paths.json / working_memory.json / confidence_tracking.json / feedback_tracking.json / behavior_log.jsonl`
架构文档：`brain_architecture_v2.md / keyword_index.json`

## 同步验证
```bash
# 确认GitHub有内容
curl -s "https://api.github.com/repos/aidong99418/herrmes-skills/contents"

# 确认本地已同步
curl -s "https://github.com/aidong99418/herrmes-skills"

# 手动触发同步
cd /opt/data/external-skills && git pull origin master
```
