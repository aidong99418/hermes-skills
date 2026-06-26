---
name: secretary-architecture-bug-hunting
version: 2026-06-03
description: 秘书处架构深度Bug排查与修复方法论——系统诊断→根因追踪→批量修复→验证闭环。触发：result_board积压/推送异常/多文件联动bug/架构审计。
triggers: ["秘书", "协调"]
tags: [secretary, debug, architecture, bug-fix]
---

# 秘书处架构深度Bug排查与修复方法论

## 适用场景
- result_board 异常积压（大量 pending_push）
- 推送链路不通 / 格式混乱
- 多文件协同逻辑不一致（deputy_worker / deputy_result / queue_worker_cron）
- 架构审计（装备/工具/配饰检查）

## 核心原则
**先验证问题存在，再诊断根因，最后修复。** 不能假设文件内容——直接读文件验证最新状态。

## 排查步骤

### 第1步：环境检查 — 摸清数据流全貌
- 读派工板 dispatch_board.json：task结构、status分布、唯一id数
- 读成果板 result_board.json：结果数、状态分布、格式一致性
- 查cron job：谁在派任务？什么频率？什么触发条件？
- 找所有写result_board的脚本

**关键诊断指标：**
- `instruction`字段是否为空（核心bug指标）
- `action`字段是否为空（无实质行动=不该推送）
- 时间戳是否集中（同一批任务=架构问题）
- `from_dispatch_id`是否全为空（追不到派工板原始任务）

### 第2步：分析 — 判断是否需要修复
- 200条积压但全无action → 不该全推，提炼或归档
- instruction全空 → 建任务方没填，执行方也没normalize
- 同一task_id产生200条结果 → 执行器写结果时未做内容过滤

### 第3步：查漏 — 找所有相关文件
```bash
find /opt/data/secretary -name "*.py"
grep -l "result_board\|dispatch_board\|from_secretary\|collected"
```

### 第4步：深挖 — 追踪因果链
任务是如何产生的（谁写dispatch_board）？↓ 什么触发deputy_worker执行？↓ 执行后结果写哪？↓ deputy_result如何发现done任务（collected标记）？↓ 特秘推理后写result_board什么字段？↓ queue_worker_cron读哪些字段推送？

### 第5步：修正方案 — 列出所有bug
典型bug模式：
1. 重复normalize（两处各normalize一遍，导致不一致）
2. 重复写入（worker和result都写result_board，格式冲突）
3. 过滤逻辑不完整（has_substance只看原始字段，忽略预存字段）
4. 过滤逻辑作用域错误（在函数内改外层变量，没写回派工板）
5. counter字段不统一（result_counter vs counter）
6. collected标记未持久化

### 第6步：验证 — 模拟所有场景
4个关键场景必须覆盖：
- spam任务(无purpose无instruction无normalized) → 跳过
- 有purpose的auto_triggered任务 → 通过（purpose算内容）
- 有instruction_normalized的任务 → 通过
- 正常有instruction的任务 → 通过

### 第7步：执行修复
修复顺序（按依赖关系）：
1. 先修复被调用方（deputy_worker的normalize预存）
2. 再修复调用方（deputy_result的normalize读取）
3. 最后删重复逻辑（worker写result_board）
每改一个文件立即 py_compile 验证语法

### 第8步：验证修复后逻辑完整正确
- py_compile 所有修改文件
- 模拟4个场景确认行为正确
- 验证无重复调用（normalize_task只调用一次）
- 验证无重复写入（result_board只有一处写）
- 验证collected标记正确持久化

### 第9步：归档
记录修复内容：fix_id, 时间, 根因, 文件列表, 修复内容, 验证结果
路径：/opt/data/secretary/logs/fix_YYYYMMDD_描述.json

## 已知Bug模式速查

| Bug | 症状 | 根因 | 修复 |
|-----|------|------|------|
| result_board 200条积压全无action | 推送刷屏 | worker写空instruction，result不过滤 | has_substance过滤+normalize_instruction |
| instruction字段全空 | 成果无法追溯原始问题 | 建任务时没填，执行器没normalize | normalize_instruction补全 |
| 两种格式混在result_board | 推送读不到summary/detail | worker写{content}，result写{summary/detail} | 删worker写result_board，只留result |
| auto_triggered任务被错误跳过 | 好任务没推送 | has_substance不看instruction_normalized | 添加normalized检查 |
| 同一批任务重复处理 | 重复写成果板 | collected标记未写回 | skipped任务立即write_json |
| normalize_task重复调用 | CPU浪费 | 两处都调normalize_task | 复用第一次结果 |

## 关键文件路径
- 派工板: `/opt/data/secretary/dispatch_board.json`
- 成果板: `/opt/data/secretary/result_board.json`
- 执行器: `/opt/data/secretary/deputy_worker.py`
- 成果收集: `/opt/data/secretary/deputy_result.py`
- 推送cron: `/opt/data/scripts/queue_worker_cron.py`
- 秘书基类: `/opt/data/secretary/secretary_base.py`
