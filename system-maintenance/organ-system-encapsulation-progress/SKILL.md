---
name: organ-system-encapsulation-progress
description: 器官系统封装进度追踪 — 2026-06-05融合完成（物理迁移+验证）
triggers: ["系统", "架构"]
tags: [organ, encapsulation, in-progress]
created: 2026-06-05
updated: 2026-06-05
---

# 器官系统封装进度追踪

## 状态：融合阶段一完成 ✅

### ✅ 已完成
1. 现状摸底：14个器官脚本，逐一扫描完成
2. 14个器官文件迁移到 `/opt/data/brain/organs/`（物理统一）
3. 7个文件内部导入路径修复（`from organs.` → `from .` 相对导入）
4. organ_bus 自动注册路径更新为新位置
5. organ_registry.json 10条路径全部更新
6. 14/14 器官健康验证通过

### 🔑 关键架构发现
**"两层皮架构"**：器官系统（organ_bus+14器官）和神经脉络（AE4进化图谱）是通过 ae4_bridge 单向连接，
organ_bus只能"透视"脉络，脉络完全不知道器官存在。
融合核心不是搬文件，而是让脉络激活后主动通过 organ_bus 通知器官（双向闭环）。

### ✅ 融合阶段二完成（2026-06-06）
**双向事件闭环已打通：**
1. 新建 `/opt/data/brain/organs/organ_gateway_bridge.py`（247行）— OrganGatewayBridge 单例
   - Gateway HookRegistry → Organ Bus（gateway事件同步到器官）
   - Organ Bus → Gateway Hook（器官事件同步到网关）
   - 自动加载14个器官 health_check
2. gateway/run.py start() L1815 接入桥接 init()
3. gateway/run.py stop() L2499 接入桥接 shutdown()
4. 新建 `/opt/data/scripts/organ_health_daemon.py`（4492字节）— 正确路径统一守护脚本
5. cron 自愈器全链路检查改用 organ_health_daemon.py
6. 新注册器官系统全链路监控 cron（每5分钟）
7. 验证：13/14 器官健康（neural_safe 缺 psutil）

**调用链现状（2026-06-06）：**
```
gateway.start() → organ_gateway_bridge.init(hooks)
  → 注册 gateway hook 事件监听器
  → 加载14个器官 health_check
  → organ_bus 双向订阅

cron/5min → organ_health_daemon.py
  → 读 organ_registry.json
  → 逐个器官 health_check
  → 写 organ_alert.json（如需）
```

### ⚠️ 迁移踩坑记录
- alert_sender.py / task_board.py：health_check()函数内用 `time.time()` 但未 import time（原有bug，迁移后验证才发现）
- system_health.py：无 health_check 函数（需补全）
- evolution_engine.py：原本不存在，需创建存根

### 迁移标准流程（可复用）
```
1. mkdir -p /opt/data/brain/organs
2. cp /opt/data/organs/*.py /opt/data/brain/organs/
3. sed "s/from organs\./from ./g" *.py（批量相对导入）
4. 修 organ_bus._auto_register 路径
5. 更新 organ_registry.json 所有 file 路径
6. 逐个验证 health_check()
```

### ⏳ 待做
1. ~~**双向事件闭环**：脉络激活后 emit("neural.activated") → organ_bus 订阅触发器官反应~~ ✅ (2026-06-06 OrganGatewayBridge)
2. **统一 health_check 格式**：剩余器官补 organ_type/version 字段
3. **三套 activation_engine 合一**：/opt/data/brain/core/activation_engine.py（1224行最新）保留，其他废弃
4. **evolution_engine 完整实现**：岛屿遗传算法（当前是存根）
5. **ae4_bridge 悬空路径**：V35_BASE 指向不存在的目录，需修复
6. **neural_safe psutil 依赖**：给 hermes venv 装 psutil，让 14/14 器官全部健康
