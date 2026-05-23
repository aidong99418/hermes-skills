---
name: github-repo-mining
description: GitHub高星仓库挖掘与静默同步工作流 — 从发现到推送到hermes-skills完整链路。触发：挖宝、GitHub学习、同步新项目。
version: 1.0.0
tags: [github, mining, sync, learning, workflow]
triggers: ["GitHub挖宝", "同步仓库", "发现新项目", "hermes-skills"]
---

# GitHub Repo Mining 工作流

## 核心定位
从GitHub高星仓库发现 → 分析 → 同步到本地hermes-skills的完整链路，用于持续扩展Agent技能库。

## 工作流

```
发现高星仓库
    ├── 星标筛选（>1k⭐）
    ├── 语言过滤（Python/JS/Go）
    └── 主题匹配（AI/Agent/DevOps）

内容分析（GitHub API）
    ├── 读README.md
    ├── 查源码结构
    └── 评估价值

筛选写入
    ├── 写SKILL.md
    └── 注册neural网络

推送GitHub
    ├── git add/commit/push
    └── neural重建
```

## 核心脚本逻辑

### 发现仓库（API查询）
```python
# 按星标+语言搜索
url = "https://api.github.com/search/repositories"
params = {
    "q": "stars:>5000 language:python",  # Python >5k星
    "sort": "stars",
    "per_page": 30,
}
```

### 读README（认证API防限流）
```python
import base64, os

token = os.environ.get("GITHUB_TOKEN")

def read_file(owner, repo, path):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    return base64.b64decode(data['content']).decode()
```

### 限流处理
```python
# 未认证: 60次/小时
# 认证后: 5000次/小时
# 超过限额sleep等待
X-RateLimit-Remaining: 0 → time.sleep(3600)
```

## 筛选标准

| 维度 | 标准 |
|------|------|
| 星标 | >1k（热门）/ >5k（顶级）|
| 主题 | AI/Agent/DevOps/云原生 |
| 活跃度 | 6个月内有更新 |
| 文档 | 有README.md |
| 复用性 | 可转化为skill |

## 坑/注意事项

1. **API限流是最大瓶颈**：未认证60次/小时，批量查询要控速
2. **README可能为空**：检查`size > 100`再下载
3. **base64编码**：GitHub API文件内容是base64，需要decode
4. **分支确认**：查`default_branch`字段，不一定是master/main
5. **嵌套目录**：skill写到子目录（如`ai-frameworks/cowagent/`）需同步父目录状态
