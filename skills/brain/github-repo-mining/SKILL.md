---
name: github-repo-mining
description: GitHub高星仓库挖掘与静默同步工作流——从发现到推送到hermes-skills完整链路
version: 1.0.0
tags: [github, workflow, mining]
---

# GitHub高星仓库挖掘工作流

## 核心结论

github.com(git协议/HTTPS git)被防火墙阻断 → 用api.github.com REST API绕过

推送流程：blob → tree → commit → PATCH ref（5步）

## 执行步骤

### Step 1: 发现目标

```bash
curl -s "https://api.github.com/search/repositories?q=stars:>100+language:python&sort=stars&per_page=20"
```

### Step 2: 下载文件

```bash
# 策略：不能bulk scan，会超时。用subagent并行下5-7个文件
curl -sL --max-time 15 "https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/main/README.md" -o /tmp/gems/{name}.md
```

注意：`refs/heads/`前缀必须加，raw.githubusercontent.com下载路径要对应分支名（main/master）

### Step 3: 判断内容类型

| 文件类型 | 处理方式 |
|---------|---------|
| SKILL.md | 评估是否优于现有 → 覆盖external-skills |
| README/AGENTS/CLAUDE | 提炼核心原则 → brain/principles |
| best-practices目录 | 全读 → 精华入brain |
| prototype/zoom-out | 工程实践 → brain/principles |

### Step 4: 更新brain/index.json

```python
with open('/opt/data/brain/index.json') as f:
    idx = json.load(f)
# 添加entry: {path, category, keywords, summary}
```

### Step 5: 推送hermes-skills（GitHub REST API）

```python
def github_push_via_api(token, repo_owner, repo_name, files: dict, commit_msg, branch='master'):
    base = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    # 1. 获取当前SHA
    ref = requests.get(f"{base}/git/ref/heads/{branch}", headers=headers).json()
    current_sha = ref["object"]["sha"]
    
    # 2. 上传各文件blob
    blob_shas = {}
    for path, content in files.items():
        r = requests.post(f"{base}/git/blobs", headers=headers,
            json={"content": content, "encoding": "utf-8"}).json()
        blob_shas[path] = r["sha"]
    
    # 3. 构建树
    tree = [{"path": p, "mode": "100644", "type": "blob", "sha": s} for p, s in blob_shas.items()]
    new_tree = requests.post(f"{base}/git/trees", headers=headers,
        json={"base_tree": current_sha, "tree": tree}).json()
    
    # 4. 创建commit
    commit = requests.post(f"{base}/git/commits", headers=headers,
        json={"message": commit_msg, "tree": new_tree["sha"], "parents": [current_sha]}).json()
    
    # 5. 更新ref
    requests.patch(f"{base}/git/refs/heads/{branch}", headers=headers,
        json={"sha": commit["sha"]})
```

### Step 6: 删除文件用sha=None

```python
tree_item = {"path": "path/to/delete", "mode": "100644", "type": "blob", "sha": None}
```

## 高价值仓库参考清单（2026-05-23已验证）

| 仓库 | Stars | 产出 |
|------|-------|------|
| obra/superpowers | 203K | 流水线+Agent规范 |
| anthropics/skills | 139K | docx/pdf/pptx/xlsx/mcp-builder |
| mattpocock/skills | 101K | TDD/prototype/grill-with-docs |
| addyosmani/agent-skills | 45K | 五维code-review |
| Leonxlnx/taste-skill | 3.4K | 前端审美防Slop原则 |
| Donchitos/Claude-Code-Game-Studios | 700 | 49 Agent三层架构 |

## 坑

1. **不要bulk scan** → 超时，改subagent选择性下
2. **README 404** → 仓库路径不对，实际文件在子目录或不同分支
3. **推送超时** → 用REST API代替git push
4. **删除文件** → 树中sha=None，不是省略该path
5. **14字节下载** → 失败占位符，不是真实内容，改用GitHub API `Accept: application/vnd.github.v3.raw` 下载
6. **delegate_task中断** → 大批量任务(~8+文件)在~400-700秒后必被中断，改用execute_code直接推API
7. **subagent写入brain后未推GitHub** → 总是需要人工补推步骤

## 新增验证通过仓库

| 仓库 | Stars | 产出 |
|------|-------|------|
| bytedance/deer-flow | 12K | 超级Agent harness架构 |
| anthropics/claude-code | 1200 | Plugin开发7阶段/命令模板 |
| vercel/ai | 23K | AI SDK模式 |
| microsoft/playwright | 65K | 测试工作流 |
| anthropic/anthropic-cookbook | 9K | AI cookbook模式 |
| open-interpreter/open-interpreter | 20K | 代码执行沙箱模式 |
| ollama/ollama | 50K | 本地模型平台生态 |
| ollama/ollama-python | - | Python SDK集成 |

## 批量Brain推送最佳实践

```python
# Step 1: 先从GitHub拿当前index.json，避免重复推送
current = gh_api("GET", f"/repos/{REPO}/contents/brain/index.json?ref={BRANCH}")
pushed_paths = {e['path'] for e in json.loads(base64.decode(current['content']))['integrated']['entries']}

# Step 2: 只推本地有且GitHub没有的文件
to_push = {gh_path: local for gh_path, local in local_files.items()
           if not any(gh_path.split('/')[-1] in p for p in pushed_paths)
           and os.path.exists(local) and os.path.getsize(local) > 500}

# Step 3: 全部blob→tree→commit→ref，一个commit推完
# Step 4: 推送完成后验证commit SHA
```

## delegate_task使用原则

- **适合**: 纯下载+安装（skill文件到/opt/data/skills/），无GitHub推送
- **不适合**: >5个文件的brain提炼写入+GitHub推送 → 改用execute_code直接API推
- **超时预警**: 看到"interrupted, waiting for model response" → 子任务被中断，立刻用execute_code补推
