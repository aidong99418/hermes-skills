---
name: system-upgrade-verification-framework
description: NAS系统升级决策框架——先验证实际状态再给推荐，避免根据文件列表推测。触发：需要评估升级方案、诊断系统薄弱点、推荐新工具。
triggers: ["系统", "架构"]
version: 1.0
---

# System Upgrade Decision Framework

## 核心原则
**先验证，再推荐**。严禁基于文件列表或目录大小做推测性判断。

## 评估步骤（顺序不可跳过）

### 第0步：GitHub下载源可用性测试
在尝试任何安装前，先测试代理是否可用：

```bash
# 测试GitHub访问方式（避开API限流）
git ls-remote https://gitee.com/mirrors/{repo}.git HEAD
curl -sI https://ghproxy.net/https://github.com/{user}/{repo}/releases/download/v{ver}/file 2>/dev/null | head -1
# jsDelivr CDN
curl -sI https://cdn.jsdelivr.net/gh/{user}/{repo}/ 2>/dev/null | head -1
```

**已验证可用的免费代理**：
- `https://gitee.com/mirrors/{repo}` — 官方维护，无限速
- `https://ghproxy.net/` — 公益代理，格式：`https://ghproxy.net/https://github.com/{user}/{repo}/releases/download/{tag}/{file}`
- `https://cdn.jsdelivr.net/gh/` — Cloudflare CDN，无限速

### 第1步：实际运行测试（不可跳过）
```python
# ❌ 错误做法：根据文件大小/目录列表推测
du -sh /opt/data/brain/memory/  # 可能误导

# ✅ 正确做法：实际运行并观察输出
cd /opt/data/scripts && python3 -c "
from brain_retriever import BrainRetriever
r = BrainRetriever()
res = r.search('测试', top_k=3)
print(f'Results: {len(res)}')
# 观察实际输出和耗时
"
```

### 第2步：追踪调用链（不可跳过）
```python
# ❌ 错误做法：只看静态文件
grep -r "BM25" /opt/data/scripts/  # 只看到import语句

# ✅ 正确做法：追踪实际数据流
grep -n "def search\|def retrieve\|def fetch" brain_retriever.py
grep -n "brain_retriever\|bm25\|semantic\|search_arxiv" brain_thinker.py
```

### 第3步：性能基准（不可跳过）
```bash
# 内存
free -h | grep Mem

# 磁盘
df -h /opt/data | tail -1

# 实际索引数据量（不是目录大小）
find /opt/data/brain -name "*.jsonl" -exec wc -l {} \; 2>/dev/null
# 关键：wc -l是原始行数，索引后实际chunks可能差10-100倍
```

### 第4步：告警路径验证（不可跳过）
```bash
# 找所有告警代码
grep -rn "alert\|warning\|critical\|send\|push\|notify" system_heartbeat.py
# 关键验证：告警有没有推送路径？只是print还是真的推？
```

## 常见误区

| 误区 | 真相 |
|------|------|
| "目录大小=数据量" | neural目录43MB，但全是Python代码文件 |
| "jsonl行数=检索数据量" | 原始3个jsonl文件，但索引后有122K chunks |
| "文件存在=功能正常" | brain_retriever运行时在首次构建索引，无输出≠不工作 |
| "有告警=会通知" | system_heartbeat有告警，但只是print不推送 |
| "模块多=系统强" | 65个agent脚本不代表65个活跃功能，大量是废弃/备份 |

## 推荐公式
```
升级价值 = (现有系统的真实薄弱点) × (升级方案的实际匹配度) / (改动风险)
```
不是选星最多的工具，而是找实际影响最大的那个短板。
