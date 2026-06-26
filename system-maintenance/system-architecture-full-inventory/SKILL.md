---
name: system-architecture-full-inventory
description: 系统全量架构盘点工作流——扫描所有子系统、找真实板子文件、找系统间断点。触发：系统重构/诊断/摸清家底/打通系统。
triggers:
  - 系统重构
  - 摸清家底
  - 系统有多少套
  - 打通系统
  - 架构诊断
version: 1.0
---

# 系统全量架构盘点工作流

## 何时用
系统有多套独立组件跑着，但不知道它们之间的关系、哪些该保留、哪些该打通。先做全量盘点再动手，不要边做边修。

## 标准步骤

### 1. 列清单——扫描6大系统
- `/opt/data/brain/` → Brain系统
- `/opt/data/scripts/` → 学习系统 + 健康系统 + 记忆系统
- 推送系统（单独找）

### 2. 找真实板子文件（不要相信文件名）
**关键教训**：`secretary/` 下的才是真正的派工板（`dispatch_board.json`）。

排查方法：
```python
import re, json
# board_utils.py 里真正读写的文件
bu = open("/opt/data/secretary/dispatch_board.json").read()
files = re.findall(r'["\'](/[^"\']*\.json)["\']', bu)
```

检查 secretary/ 目录（容易遗漏）：
- `/opt/data/secretary/dispatch_board.json` ← 派工板
- `/opt/data/secretary/result_board.json` ← 结果板

**板子文件类型判断**：
- 活动日志：`{'at', 'from', 'level', 'message'}` — 只记录事件
- 派工板：`{'pending_tasks', 'completed_tasks', 'failed_tasks'}` — 真正任务流转
- 结果板：`{'results', 'unread', 'result_counter'}` — 任务执行结果

### 3. 找断点
```
检测脚本 → 写派工板？ → 修复脚本在监听？
Health检测 → 有没有修的环节？
Brain → 秘书处？有无数据流？
```

## 核心教训
> 文件名不一定是功能名。要追代码，看实际 `read/write` 操作。`secretary/dispatch_board.json` 是派工板，`secretary/result_board.json` 是成果板。
