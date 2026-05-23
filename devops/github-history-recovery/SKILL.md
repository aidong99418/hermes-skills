---
name: github-history-recovery
description: 从GitHub历史恢复被删文件 — 通过commit历史查询+Contents API找回已删除但已push的文件。触发：误删GitHub文件、从历史恢复、commit溯源。
version: 1.0.0
tags: [github, recovery, git-history, commits]
triggers: ["GitHub恢复", "历史恢复", "commit溯源", "文件找回"]
---

# GitHub历史恢复被删文件

## 核心场景

本地误删了某个已push到GitHub的文件，可以通过查commit历史找到该文件最后存在时的commit，从那个commit的Contents API重新下载。

## 完整脚本

```python
import urllib.request, json, base64

def restore_file(owner, repo, path, token=None):
    """
    从GitHub历史恢复被删文件
    思路：查所有修改过该文件的commit，从最新往最旧遍历，
          第一个能读出来的commit就是文件最后存在的版本
    """
    # 1. 查修改过该文件的commit历史
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?path={path}&per_page=100"
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    with urllib.request.urlopen(req) as r:
        commits = json.loads(r.read())
    
    print(f"找到{len(commits)}条commit历史")
    
    # 2. 从最新往最旧遍历，找到文件还存在时的commit
    for commit in commits:
        sha = commit['sha']
        try:
            url2 = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={sha}"
            req2 = urllib.request.Request(url2)
            if token:
                req2.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req2) as r2:
                data = json.loads(r2.read())
            
            if data.get('encoding') == 'base64':
                content = base64.b64decode(data['content']).decode('utf-8')
                return content, sha
        except Exception:
            continue
    
    return None, None

# 使用示例
content, commit_sha = restore_file(
    owner="aidong99418",
    repo="hermes-skills", 
    path="librechat/SKILL.md",
)
if content:
    print(f"✅ 从commit {commit_sha[:7]} 恢复成功，{len(content)}B")
```

## 原理

```
commit A (最新) ──→ 文件已被删 ──→ 404
    │
commit B ──→ 文件已删除 ──→ 404
    │
commit C (最旧) ──→ 文件存在 ──→ ✅ 返回内容
```

## 查某文件在哪个commit被删

```python
def find_when_deleted(owner, repo, path, token=None):
    """找到文件被删除的commit"""
    commits = json.loads(urllib.request.urlopen(
        f"https://api.github.com/repos/{owner}/{repo}/commits?path={path}&per_page=100"
    ).read())
    
    prev_exists = True
    for commit in commits:
        sha = commit['sha']
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={sha}"
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        
        try:
            urllib.request.urlopen(req)
            prev_exists = True
        except Exception:
            if prev_exists:
                return sha, commit['commit']['message'].split('\n')[0]
            prev_exists = False
    
    return None, None
```

## 坑/注意事项

1. **限流**：每查一个commit的Contents API就算一次请求，未认证60次/小时，多文件恢复要控速
2. **文件大小**：>100MB的文件Contents API不支持
3. **commit范围**：默认只查最新100条commit历史，如果文件很早被删可能需要加`page=2`
4. **权限**：公开仓库无需token，私有仓库需要token
5. **路径编码**：路径中含特殊字符需要URL编码
