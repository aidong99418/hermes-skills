---
name: brain-neural-network-builder
description: 机器猫Brain神经网络构建与自检技能 — 扫描brain文档+skills目录，一键重建neural网络三个JSON文件（skill_neural.json / connections.json / inference_paths.json），确保SkillMatcher触发词匹配和神经网络推理路径正常工作。
triggers:
  - 神经网络重建
  - neural网络重建
  - 重建neural
  - build neural
  - 神经网络修复
  - neural数据损坏
  - brain文档更新
  - skills目录变化
  - 检查neural网络
  - neural自检
  - neural健康检查
  - 验证neural连接
---

# Brain神经网络构建器 v3.0

## 功能概述

当brain文档或skills目录发生增删改时，运行本脚本一键重建neural网络三个核心数据文件：

| 文件 | 作用 | SkillMatcher读取字段 |
|------|------|---------------------|
| `skill_neural.json` | 节点库(brain_docs) + 技能触发词(skills) | `skills[].triggers` |
| `connections.json` | 突触权重（节点间关联强度） | — |
| `inference_paths.json` | 推理路径（tier→action路由） | — |

**当前状态**：74节点（32 brain_docs + 42 skills）/ 634条连接 / 9条推理路径

---

## 快速使用

### 全量重建（默认）
```bash
python3 /opt/data/brain/neural/build_neural_network.py
```

### 预览模式（不写入磁盘）
```bash
python3 /opt/data/brain/neural/build_neural_network.py --dry
```

---

## 构建逻辑

### Phase 1 — Brain文档扫描
- 扫描6个brain子目录（principles/knowledge/reasoning_pattern/workflow/tool_templates/architecture）
- 每个.md文件生成一个`brain_doc`类型节点
- **去重策略**：同名但不同目录的文件（如`git_learning_workflow.md`在principles和workflow同时存在），加category前缀区分
- ID统一用 hyphen 格式（`brain_thinker` → `brain-thinker`）

### Phase 2 — Skills扫描
- 扫描 `/opt/data/skills/` 和 `/opt/data/external-skills/` 下所有SKILL.md
- 每个skill生成一个`skill`类型节点，包含：
  - `triggers`：从frontmatter提取 + 名称分词
  - `activates_nodes`：根据skill名称关键词映射到目标brain节点
  - `keywords`：自动清洗（中英文噪音词过滤）

### Phase 3 — Connections自动推导
1. **同category全连接**（brain_doc间）：weight=0.6
2. **skill → activates_nodes**：weight=0.7
3. **同source全连接**（skills间）：weight=0.4
4. **核心手工连接**（高权重固定链路）：weight=0.7-0.9
5. **去重**：相同from-to对保留最高weight

### Phase 4 — 推理路径
- 9条预定义推理路径，引用实际存在的节点ID
- `valid()`过滤：路径节点不存在时自动跳过该节点
- 空路径（节点全缺失）会被过滤掉

---

## 数据文件格式

### skill_neural.json
```json
{
  "_meta": { "version": "3.0", "total_nodes": 74, "total_connections": 634 },
  "skills": [{            // ← SkillMatcher读取此字段！
    "id": "tdd",
    "name": "tdd",
    "triggers": ["tdd", "test"],    // 触发词
    "activates_nodes": ["tdd-engineering"],  // 激活节点
    "strengthens": [],
    "type": "skill"
  }],
  "nodes": [{             // Brain文档节点
    "id": "brain-thinker",
    "type": "brain_doc",
    "category": "knowledge",
    "keywords": ["brain", "thinker"],
    "source": "brain"
  }]
}
```

### connections.json
```json
{
  "_meta": { "version": "1.0", "description": "突触权重" },
  "connections": [
    {"from": "brain-thinker", "to": "brain-retriever", "weight": 0.9, "reason": "核心思考链路"}
  ]
}
```

---

## 常见问题

### Q: 推理路径显示"缺失节点"警告
**原因**：路径中引用了不存在的节点ID（可能skill被删除了）
**解决**：手动检查 `build_neural_network.py` 中的 `core` 列表或 `build_inference_paths()` 函数，更新为实际存在的ID

### Q: SkillMatcher仍然不工作
**原因**：schema不匹配。检查 `skill_neural.json` 顶层是否有 `skills` 字段（不是 `nodes`）
**验证**：
```bash
python3 -c "import json; d=json.load(open('/opt/data/brain/neural/skill_neural.json')); print('skills:', len(d.get('skills',[])), 'nodes:', len(d.get('nodes',[])))"
```

### Q: 增删一个skill后要重建吗？
**不需要全量重建**。skill触发词由frontmatter的`triggers`字段 + 名称分词自动生成，skill有增删改时运行一次build脚本即可。

### Q: 添加核心手工连接
编辑 `build_neural_network.py` 中 `core = [...]` 列表，格式：
```python
('from_node_id', 'to_node_id', 权重, '原因')
```

---

## 验证命令

```bash
# 1. 运行构建
python3 /opt/data/brain/neural/build_neural_network.py

# 2. 验证schema正确性（skills字段存在）
python3 -c "import json; d=json.load(open('/opt/data/brain/neural/skill_neural.json')); print('✅ skills:', len(d.get('skills',[])), '/ nodes:', len(d.get('nodes',[])))"

# 3. 模拟SkillMatcher查询测试
python3 -c "
import json
data = json.load(open('/opt/data/brain/neural/skill_neural.json'))
skills = data.get('skills', [])
q = 'tdd怎么做'
for s in skills:
    matched = [t for t in s.get('triggers',[]) if t.lower() in q.lower()]
    if matched:
        print(f'{s[\"name\"]}: {matched} → activates {s.get(\"activates_nodes\",[])}')
"
```

---

## 核心坑记录

- **ID命名不统一**：brain用`_`，skills用`-`，inference_paths用`_`，导致一个都匹配不上。修复：统一用hyphen格式
- **重复brain文档**：同一文件名在多个目录下出现（如`git_learning_workflow.md`在principles和workflow），加category前缀区分
- **Schema合同**：brain_retriever.py的SkillMatcher读取`skill_neural.json["skills"]`，不是`["nodes"]`，这是之前匹配全部失效的根因
- **关键词噪音**：从描述文本提取keywords时，短英文词（如`api`, `url`, `run`, `test`）占40%+，必须过滤
- **Slug规范化陷阱**：brain doc的ID是`brain_thinker`（原文件名），skill的ID是`brain-thinker`（目录名转hyphen），两者看似同一实体但字符串不相等。脚本早期用`if skill_id in seen_ids`判断时，`brain_thinker` ≠ `brain-thinker`，导致同一实体被当作两个独立节点或其中一个被静默丢弃。修复：`to_id()`统一转换
- **ID去重时机**：不能边扫描边去重（同一文件循环中无法预知后面是否还有同名），而应该先完整扫描生成列表，再做去重判断

## 调试自检清单

构建后发现异常，按以下顺序排查：

1. **验证文件能读**：skills字段数>0，否则schema错了
   ```bash
   python3 -c "import json; d=json.load(open('/opt/data/brain/neural/skill_neural.json')); print('skills:', len(d.get('skills',[])), 'nodes:', len(d.get('nodes',[])))"
   ```
2. **查重复ID**：`[x for x in ids if ids.count(x) > 1]`
3. **查路径缺失节点**：paths中有节点不在node_ids中
4. **模拟SkillMatcher**：用查询词匹配triggers，确认有输出
5. **验证写盘后内容**：读取刚生成的文件，检查实际内容是否与内存一致
