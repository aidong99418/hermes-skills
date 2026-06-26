---
name: system-architecture-version-diagnosis
description: 系统架构版本诊断与旧版本清理工作流——多轮迭代排查、版本交叉验证、归档而非粗暴删除。触发：用户问"当前版本是什么"/"旧版本清理了吗"/全面系统盘点。
triggers: ["系统", "架构", "用户问"]
tags: ["architecture", "diagnosis", "cleanup", "version-tracker", "system-audit"]
updated: 2026-05-31
version: 1.0
---

# 系统架构版本诊断与旧版本清理工作流

## 核心原则

1. **证据链>文档**：文档说v3.5，但代码里evolution_state标记v4.0 → 以代码为准
2. **先诊断后行动**：不要根据文件名猜测版本，逐文件验证
3. **归档而非删除**：设计文档废止后移到 `brain/backup/` 而非直接删，防止误删有价值内容
4. **检查引用链**：删除前必须grep确认没有外部引用

## 诊断步骤

### 第1轮：定位架构文档
```bash
find /opt/data -type f \( -name "*ARCHITECTURE*.md" -o -name "*architecture*.md" -o -name "*设计*.md" -o -name "*架构*.md" -o -name "*人体架构*.md" \) 2>/dev/null
```

### 第2轮：验证真实运行版本（代码版本>文档版本）
```python
import json
with open('/opt/data/brain/neural/activation_engine_data/evolution_state.json') as f:
    es = json.load(f)
print(f"version: {es['version']}")  # v4.0 → 当前真实运行版本
print(f"nodes: {len(es['nodes'])}")
```

### 第3轮：器官落地检查
- 真实器官：`/opt/data/organs/*.py`（v4.0，8个文件）
- 模拟器官：`/opt/data/neural_network/organs/*.py`（v2.0遗留，仅示例）

### 第4轮：清理前验证
- 0B文件：先os.stat验证size，不靠ls的印象
- 文档重复：用内容相似度判断，不靠文件名猜
- 外部引用：grep全库搜索确认后再删

## 已知版本对照表（2026-05-31）

| 版本 | 路径 | 状态 | 证据 |
|------|------|------|------|
| **v4.0** | evolution_state.json | **✅ 生产运行** | version=4.0, 23948节点, 7器官落地 |
| v3.0/v3.5 | skill/brain-system里 | ❌ 从未实现 | blood_vessel.py等0B |
| v2.0 | neural_network/ARCHITECTURE.md | ❌ 已归档 | brain/backup/ |
| 机器猫v3.0 | brain/MASTER_ARCHITECTURE.md | ✅ 仍在参考 | 实际运行大脑系统 |

## 清理优先级

| 优先级 | 操作 | 注意 |
|--------|------|------|
| ⭐⭐⭐ 高 | 删除0B空壳文件 | 先验证size==0 |
| ⭐⭐⭐ 高 | 删除未实现版本目录 | 先迁移有价值的.py文件 |
| ⭐⭐ 中 | 清理重复文档 | 先比较内容确认重复 |
| ⭐⭐ 中 | 删除空目录 | 逐层确认无文件 |
| ⭐ 低 | 归档废弃设计文档 | 移入brain/backup/ |

## 关键教训

1. **文档说v3.5，代码说v4.0** → 始终以代码运行状态为准
2. **0B文件不一定被删了** → 可能是文件存在但未写入，需要os.stat验证
3. **相似度≠重复** → 25.6%相似的文档内容可能不同，需读头尾判断
4. **器官有两个位置** → /opt/data/organs/是真实器官，/opt/data/neural_network/organs/是示例模拟
5. **删前必查引用** → organ_immune.py在cron中引用organ_feishu.py，贸然删除会断链
