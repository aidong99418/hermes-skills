---
name: memory-tool-discipline
description: MEMORY工具使用纪律——双层架构，MEMORY只存铁律，大数据走外部。触发：MEMORY满了/忘事了/想往MEMORY里写东西时激活。
version: 1.0
---

# MEMORY 工具使用纪律

## 核心原则

MEMORY 工具是 **2,200 字符硬上限**，不是通用记忆库。填满是必然，不是故障。

## 双层架构

| 层级 | 工具 | 容量 | 用途 |
|------|------|------|------|
| 核心记忆 | `memory` 工具 | 2,200 字符，上限固定 | 绝对不能忘的铁律/关键决策规则 |
| 扩展记忆 | MEMORY.md + Chroma + mem0ai | 无限 | 语义知识/会话记录/技术细节 |

## 写入规则

### MEMORY 工具（只有两种情况才写）

1. **新规则首次踩坑**：某个问题修好后，要把根因+解法固化进去
2. **用户明确强调的偏好/铁律**：用户说"记住这个"、"以后不要这样"

### MEMORY 工具写入时

- **先问要不要删旧记录再写**，避免堆积
- 合并同主题记录，用一条长记录代替多条短记录
- 格式：`主体内容 + 日期标签`（如 `(2026-05-30)`），方便识别时效

### 禁止写入 MEMORY 工具的内容

- 会话结束自动同步记录（写 MEMORY.md）
- 排雷教训/技术细节（写 MEMORY.md）
- 重复记录同一类问题（合并，不是叠加）
- 任何可以用文件存储的内容

## 压缩 MEMORY 的标准流程

当 MEMORY 满了需要压缩时：

1. 列出所有记录，识别重复主题
2. 同主题合并为一条 consolidated 记录
3. 删除所有"会话结束同步"类垃圾记录
4. 确认最终 ≤4 条核心记录
5. 写新规则前先确认能替换/合并哪条旧记录

## 外部记忆使用

- **MEMORY.md**：/opt/data/MEMORY.md，文本格式，可无限追加
- **Chroma + mem0ai**：语义检索，适合跨会话记忆搜索
- **brain_bm25_cache.json**：结构化缓存数据
- **Skills 文件**：可执行技能/操作流程，存在 /opt/data/skills/

## 平台 MEMORY 的 replace/remove 行为陷阱

**关键发现（2026-05-30）**：`memory replace` 和 `memory remove` 在匹配到内容时仍可能返回 `No entry matched`。
原因：平台内部对 old_text 的规范化处理与显示文本存在差异。

**正确做法**：用 `memory add` 添加新条目（自动置顶或追加到末尾），再直接写外部文件。不要依赖 `replace/remove`。

**例外**：首次初始化空的 MEMORY 时，`replace` 可以用于完全覆写。

## 写完后的验证

```bash
# 验证外部文件
wc -c /opt/data/memories/MEMORY.md
head -3 /opt/data/memories/MEMORY.md

# 验证平台MEMORY
# 调用记忆后观察返回的 usage 和 entry_count
```

写完后要 **两层同步验证**：平台 MEMORY 和 MEMORY.md 都要更新，且内容顺序/结构对应。

## 常见错误

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 会话结束写大量同步记录 | MEMORY 快速填满 | 写 MEMORY.md |
| 每个问题修完都写一条 | 重复记录堆积 | 合并，不是叠加 |
| 技术细节写 MEMORY | 2,200 字符被垃圾占满 | MEMORY 只存铁律 |
| MEMORY 满了继续追加 | 报错：反复压缩-忘事循环 | 先删/合并再添加 |
| 用 replace/remove 改 MEMORY | 静默失败，旧内容仍在 | 用 add + 外部文件同步 |
| 只更新一个层 | 两层不一致，下次读错 | 改铁律时两层同步更新 |

## 验证

写完 MEMORY 后调用 `memory(action='list')` 确认记录数 ≤4，总字符 ≤1,800。
