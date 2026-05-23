---
name: herrmes-skills-push
description: herrmes-skills GitHub仓库日常维护工作流 — 单仓库结构、直接clone、智能恢复、GitHub API认证。触发：推skill到GitHub、恢复误删skill、GitHub API限流处理。
version: 2.0.0
tags: [github, skills, git, backup]
triggers: ["推skill", "hermes-skills", "恢复skill", "GitHub API限流", "GitHub认证"]
category: github
author: 打工仔
date: 2026-05-23
---

# herrmes-skills 仓库维护规范

## 仓库信息
- **GitHub**: https://github.com/aidong99418/hermes-skills
- **本地路径**: `/opt/data/skills/`（直接就是Git仓库，不再是external-skills）
- **分支名**: `master`（不是 `main`）
- **远程**: `origin` = `https://github.com/aidong99418/hermes-skills.git`

## 当前目录结构（2026-05-23 重构）

```
/opt/data/skills/          ← 就是Git仓库本体，git clone到这里
├── .git/                  ← Git元数据
├── SKILL.md/              ← skill目录（54个）
├── brain/                 ← 文档目录
├── architecture/
├── knowledge/
├── principles/
├── reasoning_pattern/
├── tool_templates/
└── workflow/
```

**旧结构（已废弃）**：
- `/opt/data/external-skills/` — 已不再使用
- 双目录 cp 流程 — 已废弃

## 标准工作流（当前）

### 首次设置（新机器）
```bash
cd /opt/data
mv skills skills_backup
git clone https://github.com/aidong99418/hermes-skills.git skills
# skills/ 现在就是仓库，备份旧目录
# 如果旧目录有未同步的skill，对比后补充
```

### 每次写新skill
```bash
# Step 1: 直接写入本地仓库
vim /opt/data/skills/my-new-skill/SKILL.md

# Step 2: git add + commit + push（三步，不是三地）
cd /opt/data/skills
git add my-new-skill/
git commit -m "feat: add my-new-skill"
git pull origin master --rebase    # 远程有新提交要先拉
git push
```

### 推新skill到GitHub后
```bash
# 不要忘了同步neural注册
# 编辑 /opt/data/brain/neural/build_neural_network.py
# 添加新skill的关联映射
# 然后git add/commit/push neural变更
```

## 从GitHub恢复误删的skill

### 场景
误删了skill目录，但之前已push到GitHub。

### 方法：从历史commit找
```python
import urllib.request, json, base64

def get_commits_with_file(owner, repo, filename, token=None):
    """查哪个commit包含该文件"""
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=20"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        commits = json.loads(r.read())
    
    for c in commits:
        sha = c['sha']
        detail_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
        req2 = urllib.request.Request(detail_url, headers=headers)
        with urllib.request.urlopen(req2) as r2:
            detail = json.loads(r2.read())
        files = [f['filename'] for f in detail.get('files', [])]
        if any(filename in f for f in files):
            print(f"Found in {sha[:7]}: {[f for f in files if filename in f]}")

get_commits_with_file('aidong99418', 'hermes-skills', 'librechat')
```

### 方法：直接下载历史文件
```python
def download_from_commit(owner, repo, path, ref, token=None):
    """从指定commit下载文件"""
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    return base64.b64decode(data['content']).decode()

# 用commit SHA
content = download_from_commit('aidong99418', 'hermes-skills',
                                'ai-frameworks/librechat/SKILL.md', '6fd6431')
with open('/opt/data/skills/librechat/SKILL.md', 'w') as f:
    f.write(content)
```

## GitHub API 认证配置

### 未认证 vs Token认证
| 方式 | 次数/小时 | 建议 |
|------|---------|------|
| 未认证 | 60次 | 测试用 |
| Token认证 | 5,000次 | 挖宝/批量操作必配 |

### Token创建步骤
1. GitHub → 头像 → **Settings** → **Developer settings** → **Personal access tokens** → **Generate new token (Classic)**
2. 名字随便填，如 `hermes-agent`
3. 只勾 **`repo`** 一个scope（Full control of private repositories）
4. Generate，把token发给我配置

### Token使用方式
```python
import urllib.request

token = "ghp_xxxx"  # 董哥提供
headers = {'Authorization': f'Bearer {token}'}

url = "https://api.github.com/repos/aidong99418/hermes-skills/contents"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as r:
    print(json.loads(r.read()))
```

## 踩坑记录

### ⚠️ 分支名是 master 不是 main
所有 `git` 和 `API` 操作中涉及分支名都用 `master`

### ⚠️ 不要在 skills/ 内再创建嵌套 skills/ 目录
之前误建了 `/opt/data/skills/skills/` 子目录，导致 skill 被重复嵌套。
检查：`ls /opt/data/skills/` 确保没有 nested `skills/` 子目录。

### ⚠️ GitHub API 限流
- 未认证：60次/小时
- 并行请求会瞬间打满 → 改串行或配Token
- 限流后等待1小时自动恢复，或配Token

### ⚠️ 删除占位符skill
- `ai-frameworks/` 和 `nas-monitoring-suite/` 只是占位符（README指向子目录）
- 子skill（cowagent/portainer/dozzle/glances/uptime-kuma/librechat）直接放根目录
- 不要再创建二级嵌套skill目录
