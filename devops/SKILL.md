---
name: devops
description: DevOps工具集目录 — 包含github-history-recovery等GitHub历史恢复工具。触发：Git历史恢复、仓库备份、commit溯源。
version: 1.0.0
tags: [devops, github, recovery, git]
triggers: ["Git历史恢复", "commit溯源", "仓库备份"]
---

# DevOps 工具集

## 子技能

| 子技能 | 说明 |
|--------|------|
| [github-history-recovery](./github-history-recovery/) | GitHub历史文件恢复 — 从commit历史中恢复被删或误覆盖的文件 |

## github-history-recovery 详情

从GitHub仓库的历史commit中恢复被删除或修改的文件。

### 使用方式
```bash
# 查看子技能目录
ls /opt/data/skills/devops/github-history-recovery/
```

### 核心功能
- 根据commit SHA查找历史版本
- 恢复被误删的文件
- 读取任意历史commit的文件内容
- base64解码GitHub API返回的文件内容
