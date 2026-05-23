---
name: github-repo-mining
description: GitHub高星仓库挖掘与同步工作流 — 挖宝→分析→同步到本地hermes-skills完整链路。触发：挖宝/GitHub/学习新项目。
version: 1.0.0
tags: [github, mining, sync, skills, arxiv]
triggers: ["GitHub挖宝", "学习新项目", "高星仓库", "同步skill"]
---

# GitHub 仓库挖掘工作流

## 核心定位
从 GitHub 大规模挖宝高价值项目 → 分析内容 → 筛选 → 同步到 hermes-skills 仓库。

## 完整链路

```
发现高星项目 → 读README分析价值 → 判断是否值得写skill
                                              ↓
                                    ✅值得 → 写SKILL.md → commit/push
                                    ❌放弃 → 跳过
```

## 工具选择

| 方式 | 优点 | 缺点 |
|------|------|------|
| GitHub API | 精确过滤，可编程 | 未认证60次/小时，需Token |
| `gh` 命令 | 官方CLI，用Token无限制 | sandbox网络隔离时不可用 |
| 第三方API | 可能有缓存 | 不稳定 |

**当前环境**：GitHub API 可用（API直连），`gh` 不可用（sandbox隔离）

## GitHub API 查询示例

### 按星标+语言筛选
```python
import urllib.request, json

def search_repos(query, token=None, per_page=30):
    """搜索GitHub仓库"""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    q = urllib.request.quote(query)  # 如 "stars:>10000 language:Python"
    url = f"https://api.github.com/search/repositories?q={q}&sort=stars&per_page={per_page}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())
```

### 获取README内容
```python
def get_readme(owner, repo, token=None):
    """获取仓库README"""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        import base64
        return base64.b64decode(data['content']).decode()
```

## 筛选标准

| 维度 | 标准 |
|------|------|
| 星标 | >10k⭐（主流框架门槛）|
| 语言 | Python/TypeScript/Go 优先 |
| 更新 | 近半年有活跃提交 |
| License | 非GPL限制型 |
| 实用性 | 有SDK/API/CLI等可集成点 |

## 批量查询脚本示例

```python
# 查询AI/Agent框架高星仓库
repos = search_repos("stars:>30000 language:Python topic:artificial-intelligence", token=TOKEN)
for item in repos['items'][:10]:
    print(f"⭐{item['stargazers_count']:,} | {item['full_name']}")
    print(f"   {item['description']}")
    print(f"   {item['html_url']}")
    print()
```

## 挖宝优先级排序

1. **T0**：Agent框架（AutoGen/CrewAI/OpenManus/CowAgent）
2. **T1**：RAG/向量库（Qdrant/Chroma）| 平台（LangGraph/Airflow/Dify/n8n）
3. **T2**：工具类（Portainer/Dozzle/Glances/UptimeKuma）
4. **T3**：SDK类（OpenAI Python SDK / Vercel AI SDK）

## push流程（当前目录结构）

```bash
cd /opt/data/skills
# 假设已写好 new-skill/SKILL.md
git add new-skill/
git commit -m "feat: add new-skill"
git pull origin master --rebase
git push
# 同时更新brain/neural网络注册
```
