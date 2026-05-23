---
name: brain-neural-network-builder
description: 构建机器猫大脑神经网络 — 把brain文档和skills接成语义图，实现自动推理路由。从目录重组→节点生成→连接构建→GitHub同步完整链路。
trigger: 同步brain文档到git / 构建神经网络 / brain+skill关联失效
triggers:
  - "brain神经网络"
  - "构建neural"
  - "brain连接"
  - "brain文档同步"
---

# Brain 神经网络构建器

## 核心价值
brain文档和skills再多，如果没连成网络就等于废铁。本skill把**孤立知识变成推理网络**。

## 完整流程

### Phase 1: 目录重组（一次性，之后增量）

```
git工作目录 (/root/hermes-skills)
├── principles/        # 核心原则（tdd/cron静默/安全等）
├── knowledge/         # 知识总结（模型分层/Ollama生态等）
├── reasoning_pattern/ # 推理模式（自进化/多Agent/VPO等）
├── workflow/          # 工作流（Git学习/原型分支等）
├── tool_templates/    # 工具模板（MCP集成/Agent Skills等）
└── architecture/      # 架构设计（大脑架构/团队协作等）
```

**原则：每个文档只放一个分类。如果内容跨越多类，选最主要的那个。**

### Phase 2: 生成 skill_neural.json

用keyword overlap + 手工核心连接：

```python
import os, json, re

neural = {"_meta": {"version": "1.0", "total_nodes": 0, "total_connections": 0}, "nodes": [], "connections": []}

def extract_keywords(text):
    cn = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    en = re.findall(r'[a-z][a-z0-9-]{2,20}', text)
    return list(set(cn + en))

# 添加brain_doc节点
for cat in ["principles","knowledge","reasoning_pattern","workflow","tool_templates","architecture"]:
    for fn in os.listdir(f"/root/hermes-skills/{cat}"):
        if not fn.endswith('.md'): continue
        with open(f"/root/hermes-skills/{cat}/{fn}") as f:
            content = f.read()
        neural["nodes"].append({
            "id": fn.replace('.md','').replace('-','_'),
            "type": "brain_doc",
            "keywords": extract_keywords(content)[:15],
            "description": content[:80],
            "confidence": 0.5, "usage_count": 0,
            "source": "brain"
        })

# 添加skill节点
for name in os.listdir("/opt/data/skills"):
    md = f"/opt/data/skills/{name}/SKILL.md"
    if os.path.exists(md):
        with open(md) as f: content = f.read()
        neural["nodes"].append({
            "id": name, "type": "skill",
            "keywords": extract_keywords(content)[:15],
            "description": content[:80],
            "confidence": 0.5, "usage_count": 0,
            "source": "skills"
        })

# 自动连接：共享关键词≥2个
for n1 in neural["nodes"]:
    for n2 in neural["nodes"]:
        if n1["id"] == n2["id"]: continue
        shared = set(n1["keywords"]) & set(n2["keywords"])
        if len(shared) >= 2:
            weight = min(1.0, len(shared)*0.2 + 0.3)
            neural["connections"].append({"from": n1["id"], "to": n2["id"], "weight": round(weight,2), "reason": f"共享: {list(shared)[:5]}"})

# 手工核心连接（高权重，核心推理链）
core = [
    ("brain_architecture_v2", "multi_agent_patterns", 0.95, "架构定义多Agent协作"),
    ("brain_architecture_v2", "self_evolution_pattern", 0.95, "架构包含自进化引擎"),
    ("brain-thinker", "brain_architecture_v2", 0.95, "brain-thinker实现三层思考"),
    ("brain-invoke", "brain_architecture_v2", 0.9, "brain-invoke是三层思考入口"),
    ("ollama-brain-teacher", "ollama_model_tiers", 0.9, "本地教师需理解模型分层"),
    ("ollama-auto-learning", "self_evolution_pattern", 0.9, "自动学习是自进化核心"),
    ("autonomous-ai-agents", "multi_agent_patterns", 0.9, "自主Agent对应多Agent模式"),
    ("mcp-builder", "mcp_integration", 0.9, "MCP builder实现MCP集成"),
    ("tdd", "tdd_engineering", 0.95, "TDD skill对应tdd-engineering原则"),
    ("security-auditor", "agent_behavior_guardrails", 0.85, "安全审计与行为护栏相关"),
]
for f,t,w,r in core:
    neural["connections"].append({"from": f, "to": t, "weight": w, "reason": r, "bidirectional": w>=0.7})

neural["_meta"]["total_nodes"] = len(neural["nodes"])
neural["_meta"]["total_connections"] = len(neural["connections"])
```

### Phase 3: 部署

```bash
# 1. 放到正确位置（brain_retriever读这个路径）
mkdir -p /opt/data/brain/neural
cp skill_neural.json /opt/data/brain/neural/skill_neural.json

# 2. 初始化突触权重文件
python3 -c "import json; json.dump({'_meta':{'version':'1.0'},'connections':[]}, open('/opt/data/brain/neural/connections.json','w'), ensure_ascii=False, indent=2)"

# 3. 同步到runtime brain（按子目录结构）
for cat in principles knowledge reasoning_pattern workflow tool_templates architecture; do
    mkdir -p /opt/data/brain/$cat
    cp /root/hermes-skills/$cat/*.md /opt/data/brain/$cat/
done

# 4. 重建index.json
python3 -c "
import json, os
entries = []
for cat in ['principles','knowledge','reasoning_pattern','workflow','tool_templates','architecture']:
    for fn in sorted(os.listdir(f'/opt/data/brain/{cat}')):
        if fn.endswith('.md'):
            entries.append({'path': f'{cat}/{fn}', 'file': fn, 'category': cat, 'id': fn.replace('.md','')})
with open('/opt/data/brain/index.json','w') as f:
    json.dump({'_meta':{'version':'2.0','updated':'2026-05-23','total':len(entries)},'entries':entries}, f, ensure_ascii=False, indent=2)
"
```

### Phase 4: 验证检索

```python
# 测试neural检索
with open('/opt/data/brain/neural/skill_neural.json') as f:
    neural = json.load(f)

for query in ['模型', 'agent', 'brain', '学习']:
    results = [(n['id'], n['type'], sum(1 for k in n['keywords'] if query in str(k)))
               for n in neural['nodes']]
    results = [r for r in results if r[2] > 0]
    results.sort(key=lambda x: -x[2])
    print(f'"{query}" → {results[:3]}')
```

### Phase 5: GitHub同步

```bash
cd /root/hermes-skills
git add -A
git commit -m "feat: brain neural network vX - {N}nodes/{M}connections"
# 如果push被reject，先pull --rebase再push
git pull --rebase https://ghp_...@github.com/... HEAD
git push https://ghp_...@github.com/... HEAD
```

## 常见问题处理

### 发现重复文件（flat + 子目录都有）
不要手动删！从git工作目录重建runtime brain：
```bash
# git工作目录是clean source，重新同步即可
cp /root/hermes-skills/$cat/*.md /opt/data/brain/$cat/
```

### 文档太小（<500B）
用对应源文件（/tmp/gems/repos3/ 或仓库原文）重新生成结构化brain文档，不要留placeholder。

### GitHub push rejected
```bash
git pull --rebase <token>@github.com/<user>/<repo>.git HEAD
git push <token>@github.com/<user>/<repo>.git HEAD
```

## 关键原则
1. **git工作目录是clean source**：永远从git目录重建runtime，不从runtime反向同步
2. **每个文档一个分类**：避免跨类重复，训练检索的准确性
3. **手工核心连接 > 自动关键词**：核心推理链（架构→模式→实现）必须手工指定高权重
4. **先分析再执行**：被问"把没处理完的做好"时，先brain-retrieve判断优先级，不一定按用户说的顺序
