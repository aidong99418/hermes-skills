---
name: github-api
description: GitHub REST API 完整参考 — 认证/限流/搜索/仓库/文件/Commits/Issues/PRs，覆盖挖宝workflow所需全部端点。触发：GitHub API/Token/限流/挖宝/同步/搜索仓库/读文件。
version: 1.0.0
tags: [github, api, rest, rate-limit, authentication, search]
triggers: ["GitHub API", "Token认证", "限流", "仓库搜索", "API挖宝"]
---

# GitHub REST API 完整参考

## 认证方式

### 1. Personal Access Token（推荐）
```bash
# 环境变量方式
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# curl认证
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/octocat/Hello-World
```

### 2. GitHub CLI（最简单）
```bash
# 认证
gh auth login

# 用API（自动带Token）
gh api repos/octocat/Hello-World
gh api /search/repositories?q=stars:>5000+language:python
```

### 3. gh auth token（提取已存Token）
```bash
gh auth token  # 输出当前Token，可用于curl/Python脚本
```

## 限流规则

| 资源 | 未认证 | 认证后 |
|------|--------|--------|
| `core`（大部分API） | 60次/小时 | **5,000次/小时** |
| `search`（仓库/Issues搜索） | 10次/分钟 | **30次/分钟** |
| `code_search`（代码搜索） | 更少 | 9次/分钟 |
| GraphQL | 独立计算 | 独立计算 |

### 关键规则
- **查限流状态不扣次数**：`GET /rate_limit` 完全免费
- **搜索限流独立**：和core分开算
- **超过限流**：读取响应头`X-RateLimit-Remaining`，为0时等`X-RateLimit-Reset`秒

### 实时查限流
```python
import urllib.request

def check_rate_limit(token=None):
    req = urllib.request.Request("https://api.github.com/rate_limit")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    core = data['resources']['core']
    search = data['resources']['search']
    print(f"core: {core['remaining']}/{core['limit']} (reset {core['reset']})")
    print(f"search: {search['remaining']}/{search['limit']} (reset {search['reset']})")
    return core['remaining'] > 0
```

### 智能限流装饰器
```python
import time, json, urllib.request
from functools import wraps

def rate_limit_aware(token=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 1. 先查剩余次数
            req = urllib.request.Request("https://api.github.com/rate_limit")
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
            remaining = data['resources']['core']['remaining']
            reset_time = data['resources']['core']['reset']
            
            if remaining == 0:
                wait = max(0, reset_time - time.time()) + 1
                print(f"限流了，等{wait:.0f}秒...")
                time.sleep(wait)
            elif remaining < 10:
                wait = max(0, reset_time - time.time()) + 1
                print(f"剩余{remaining}次，谨慎使用，等{wait:.0f}秒...")
                time.sleep(1)  # 等1秒
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

## 搜索仓库（挖宝核心）

### 按星标+语言搜索
```python
# 搜索 Python >5000星 的AI相关仓库
url = "https://api.github.com/search/repositories"
params = {
    "q": "stars:>5000 language:python topic:artificial-intelligence",
    "sort": "stars",
    "order": "desc",
    "per_page": 30,
}

# curl
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/repositories?q=stars:>5000+language:python&sort=stars&per_page=30"
```

### 搜索过滤条件
| 条件 | 语法 | 示例 |
|------|------|------|
| 星标 | `stars:>N` | `stars:>1000` |
| 语言 | `language:XXX` | `language:python` |
| 创建时间 | `created:>YYYY-MM-DD` | `created:>2020-01-01` |
| 更新时间 | `pushed:>YYYY-MM-DD` | `pushed:>2024-01-01` |
| 主题 | `topic:XXX` | `topic:machine-learning` |
| README含词 | `README:XXX` | `README:openai` |
| 用户 | `user:XXX` | `user:openai` |
| 组织 | `org:XXX` | `org:anthropics` |

### 分页遍历所有结果
```python
import math, time

def search_all_repos(query, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    all_items = []
    page = 1
    per_page = 100  # 最大100
    
    while True:
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page={per_page}&page={page}"
        req = urllib.request.Request(url)
        for k, v in headers.items():
            req.add_header(k, v)
        
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        
        items = data.get('items', [])
        all_items.extend(items)
        total = data.get('total_count', 0)
        
        print(f"第{page}页: {len(items)}条, 累计{len(all_items)}/{total}")
        
        if len(items) < per_page or len(all_items) >= min(total, 1000):
            break
        
        page += 1
        time.sleep(1)  # 防止超限
    
    return all_items
```

## 读仓库文件（base64解码）

### 读README/单个文件
```python
import base64, json, urllib.request

def read_file(owner, repo, path, ref="main", token=None):
    """读仓库任意文件，自动base64解码"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    
    if data.get('encoding') == 'base64':
        content = base64.b64decode(data['content']).decode('utf-8')
    else:
        content = data.get('content', '')
    
    return content, data.get('sha')

# 使用
readme, sha = read_file("openai", "openai-python", "README.md", token=TOKEN)
```

### 批量读多个文件（并发）
```python
import concurrent.futures

def batch_read_files(owner, repo, files, token=None):
    """并发读多个文件"""
    def _read(path):
        return path, read_file(owner, repo, path, token=token)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        results = dict(ex.map(_read, files))
    return results

# 并发读
files = ["README.md", "setup.py", "pyproject.toml"]
content_map = batch_read_files("openai", "openai-python", files, token=TOKEN)
```

### 读目录列表
```python
def list_dir(owner, repo, path="", ref="main", token=None):
    """列出目录内容"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    with urllib.request.urlopen(req) as r:
        items = json.loads(r.read())
    
    # 文件列表
    return [(item['name'], item['type'], item.get('size', 0)) for item in items]
```

## 查Commits历史
```python
def get_commits(owner, repo, path=None, token=None, per_page=30):
    """查仓库commit历史，可过滤路径"""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = f"?per_page={per_page}"
    if path:
        params += f"&path={path}"
    
    req = urllib.request.Request(url + params)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    with urllib.request.urlopen(req) as r:
        commits = json.loads(r.read())
    
    return [{
        'sha': c['sha'][:7],
        'date': c['commit']['author']['date'],
        'msg': c['commit']['message'].split('\n')[0],
        'author': c['commit']['author']['name'],
    } for c in commits]
```

## Issues & Pull Requests
```python
# 列出Issues
GET /repos/{owner}/{repo}/issues?state=open&labels=bug

# 创建Issue
POST /repos/{owner}/{repo}/issues
{"title": "Bug fix", "body": "Description", "labels": ["bug"]}

# 列出PRs
GET /repos/{owner}/{repo}/pulls?state=open&sort=updated
```

## GraphQL API（高级）

查询示例（比REST更灵活）：
```bash
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ viewer { login name } rateLimit { remaining limit } }"}' \
  https://api.github.com/graphql
```

## 挖宝Workflow完整脚本
```python
#!/usr/bin/env python3
"""GitHub高星仓库挖宝脚本"""
import os, json, base64, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {"Accept": "application/vnd.github.v3+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def api(url, params=None):
    """带限流处理的API请求"""
    full_url = "https://api.github.com" + url
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        full_url += "?" + qs
    
    req = urllib.request.Request(full_url)
    for k, v in HEADERS.items():
        req.add_header(k, v)
    
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def search_repos(query, min_stars=5000):
    """搜索高星仓库"""
    data = api("/search/repositories", {
        "q": f"{query}+stars:>{min_stars}",
        "sort": "stars",
        "per_page": 30,
    })
    return data.get('items', [])

def get_readme(owner, repo):
    """获取README内容"""
    try:
        data = api(f"/repos/{owner}/{repo}/contents/README.md")
        if data.get('encoding') == 'base64':
            return base64.b64decode(data['content']).decode('utf-8', errors='ignore')
    except:
        pass
    return ""

# 挖宝
repos = search_repos("machine learning agent framework", min_stars=5000)
for r in repos:
    readme = get_readme(r['owner']['login'], r['name'])
    print(f"⭐{r['stargazers_count']:,} | {r['full_name']} | {r.get('description','')}")
```

## 重要限制

| 限制 | 值 |
|------|------|
| 搜索结果上限 | 1,000条（1000个结果或100页） |
| 目录最多文件 | 1,000个 |
| 单文件最大 | 100MB |
| 下载URL有效期 | 一次性的，用完即失效 |
| 搜索查询长度 | ≤256字符 |
| 搜索AND/OR/NOT | ≤5个运算符 |

## 响应头限流信息
```python
# 每次响应都有这些头
X-RateLimit-Limit:      # 总次数
X-RateLimit-Remaining:  # 剩余次数
X-RateLimit-Reset:      # 重置时间戳(Unix)
X-RateLimit-Used:       # 本次用了几次
```

## 与本项目契合点

| GitHub API能力 | 用途 |
|---------------|------|
| 搜索仓库 | 挖宝高星项目 |
| 读文件(Contents) | 下载SKILL.md/RAME |
| 读Commit历史 | 恢复被删文件 |
| Issues/PR | 项目管理自动化 |
| GraphQL | 复杂关联查询 |
| Rate Limit API | 智能限流控制 |
