---
name: iron-vein-consolidation-workflow
description: 将散落的铁律脉络脚本整合进机器猫器官系统的工作流。触发：发现独立进程/脚本功能重复但分散在各目录、或器官系统与独立脚本并存时。
version: 1.0
---

# 铁律脉络整合进器官系统工作流

## 触发条件
发现系统中有多个独立进程/脚本功能重复但分散在各目录、或器官系统与独立脚本并存时。

## 核心认知
**设计文档里的"整体" ≠ 实际部署的"整体"**。自然生长过程中，功能一个个加但架构没统一设计，就会从"1个器官"变成"4个散落脚本"。

碎片化的代价：
- 4个进程需要4次守护
- 5个健康检测点
- 无法被 auto_healing 统一管理
- 无法用 list_organs 看到
- learning_loop 学不到它的模式
- 系统升级可能被遗忘

## 路线决策矩阵

| 路线 | 做法 | 统一性 | 工作量 | 推荐 |
|------|------|--------|--------|------|
| 甲：只修cron | 恢复进程，不改架构 | ❌ 碎片依旧 | 30min | 不推荐 |
| 乙：打包进器官 | 1个器官但内部还是多个模块 | ⚠️ 形式统一 | 45min | 假统一 |
| 丙：完全融合 | 1个器官，规则写死在代码里 | ✅ 真正统一 | 60min | 最彻底 |
| 丁：混合统一 | 1个器官 + 1个可热加载规则JSON | ✅ 真正统一+可配置 | 60min | **推荐** |

**判断标准**：如果原系统有独立配置文件需求（如规则可热改），选丁；否则选丙。

## 工作流（丁：混合统一）

### 第一步：清点现有组件
```python
# 检查所有相关文件是否存在、进程是否在跑
components = {
    "iron_watcher": "/opt/data/scripts/iron_watcher.py",
    "iron_rule_engine": "/opt/data/scripts/iron_rule_engine.py",
    "iron_write": "/opt/data/scripts/iron_write.py",
    "iron_watchdog": "/opt/data/scripts/iron_watchdog.py",
}
```

### 第二步：提取核心逻辑
- 从每个脚本提取：函数定义、规则、配置
- 合并进 organ.py 基类的子类
- 原文件移动到 `_archived/` 而非删除

### 第三步：设计新器官
```
/opt/data/organs/
├── iron_vein.py        ← 器官主体（继承 organ.Organ）
│   ├── register_rules()     # 加载 iron_rules.json
│   ├── scan_files()         # 文件扫描（原 iron_watcher）
│   ├── execute_rule(rule)   # 规则执行（原 iron_rule_engine）
│   ├── safe_write()         # 安全写入（原 iron_write）
│   └── health_check()       # 统一自检
└── iron_rules.json     ← 规则配置（可热加载）
```

### 第四步：接入器官系统
- 在 `organ.py` 注册表添加 iron_vein
- auto_healing 的8项检测加入 iron_vein 检测
- learning_loop 记录 iron_vein 的异常模式

### 第五步：废弃原文件
```bash
# 不删除，归档
mv iron_watcher.py /opt/data/_archived/iron_vein_consolidation_YYYYMMDD/
mv iron_rule_engine.py ...
mv iron_write.py ...
mv iron_watchdog.py ...
mv iron_rules_registry.json ...
```

## 验证清单
- [ ] `list_organs()` 能看到 iron_vein
- [ ] `auto_healing` 能检测 iron_vein 健康
- [ ] iron_vein.health_check() 返回 ok=True
- [ ] 修改 iron_rules.json 后重新加载生效
- [ ] 原脚本进程全部停止（无残留）

## 关键教训
1. **分析根因时不只看症状，要看架构关系** — 本次问题表面是cron丢了，实际根因是铁律脉络是"外挂租客"，不是"器官公民"
2. **假统一 vs 真统一** — 把5个文件打包进1个器官只是形式统一，内部还是碎片。真正的统一是合并逻辑到1个进程
3. **先分析再行动** — 本次花了30分钟分析，方案确定后60分钟执行，比直接修cron然后反复修要好
