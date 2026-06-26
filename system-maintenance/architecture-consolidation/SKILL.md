---
name: architecture-consolidation
description: 多版本架构系统清理与合并工作流——当NAS上存在多个架构版本时，如何诊断真实状态、合并重复、清理废弃。触发：用户说"版本混乱"/"架构问题"/"升级还是删除"。
triggers:
  - 版本混乱
  - 架构问题
  - 升级最新版
  - 删除旧版本
  - 多版本并存
version: 1.0
---

# 多版本架构系统清理与合并工作流

## 典型症状

NAS上存在多个架构版本（v1/v2/v3/v3.5/v4），版本之间功能重叠但依赖不清，有大量重复文件，废弃目录和活跃目录混在一起。

## 工作流

### 第一步：全面扫描（不假设，知道实际情况）

扫描范围：
- `/opt/data/brain/` — 机器猫大脑系统（通常是最活跃的）
- `/opt/data/neural_network/` — 人体架构系统
- `/root/hermes-skills/brain-*` — skill组件
- `/opt/data/scripts/` — 核心执行脚本

每个目录检查：
1. 文件列表 + 最后修改时间
2. 是否有cron任务在调用
3. 配置文件中有无引用

### 第二步：分类存活状态

每个组件标记为三态之一：
- 🟢 **活跃** — 有cron/脚本在调用，输出被消费
- 🟡 **半活跃** — 有文档/设计但无执行层
- 🔴 **废弃** — 无人引用，无执行，无cron

### 第三步：识别真实数据（踩过的坑）

**教训1：不要相信目录名是"空"的判断**
- `vessel/`, `discovery/`, `evolution/` 目录看起来是"未实现空目录"
- 实际上有Python文件（blood_vessel.py, organ_scanner.py, precision_expansion.py）
- 这些是 auto_integrator 自动扫描进来的执行脚本，从未被集成到主系统
- 处理：备份到 `/opt/data/backup/architecture_YYYYMMDD/` 后移除

**教训2：organ_registry 可能有169条，但真实器官可能只有10个**
- auto_integrated=true 条目是 auto_integrator 扫描产物，是噪声不是信号
- 真实器官是业务核心器官（感官_飞书/大脑皮层_路由/线粒体_推理/海马体_热层等）
- 过滤后 organ_registry 从169条压缩到10条

**教训3：重复文档多处存在（brain_architecture_v2.md在8处）**
- 这些是设计文档的遗留副本
- 保留一个主源（如 `/opt/data/neural_network/ARCHITECTURE.md`），删除其余

**教训4：/opt/data/brain/ 与 /opt/data/skills/ 高度重叠**
- brain/ 目录下有15+个skill子目录（algorithmic-art/tdd/docx/pdf/pptx等）
- 正确处理：用 `diff -rq` 对比两边同名目录内容
  - **完全相同** → 删除brain/下的，保留skills/源
  - **存在差异** → 检查brain/版本是否有独特内容，有则保留
  - 常见情况：skills/版本更完整（有scripts/references子目录），brain/版本是旧副本

**教训5：scripts/ 目录是重灾区**
- 常见杂物：20+个过期.log文件、.bak备份、测试文件(.xlsx/.docx)、旧版本脚本(queue_worker_v2.py)
- 清理前先确认cron依赖：检查 `/var/spool/cron/crontabs/` 和 cronjob list
- 非脚本文件（.md/.json/.docx）混杂在脚本目录中是常见问题

**教训6：cron依赖检查不可跳过**
- 即使skill目录被删，也要确认cron任务是否引用它
- 用 `cronjob list` 查看所有job，检查prompt中是否有skill引用
- 删了活跃cron依赖的skill会导致定时任务失败

### 第四步：执行清理（备份先行）

关键原则：
- 所有删除操作前先 mv 到 backup 目录
- 删除重复文档：保留一个主源
- 删除废弃skill目录：确认无cron引用
- 移除空目录：备份后再删除

### 第五步：合并两套架构

当存在理论层（设计文档）+ 执行层（生产系统）两套架构时：

1. 从理论层提取真实核心节点（过滤auto_integrated）
2. 保留执行层不动（brain_doc/skill神经网络是生产系统）
3. 将真实节点作为新节注入到生产系统的神经网络JSON中

注入格式：
```python
skill_neural['organs'] = organ_nodes           # 器官节点列表
skill_neural['organ_connections'] = edges       # 器官间连接
skill_neural['_meta']['merged'] = True          # 标记合并
```

结果示例：skill_neural.json v3.0 → v3.5，节点从206增加到216（含10个器官节点）

### 验证完整性

三项验证必须全部通过：

1. **语法检查** — 所有核心脚本
```bash
find /opt/data/brain/ /opt/data/neural_network/ -name "*.py" | xargs python3 -m py_compile
```
2. **JSON完整性** — 所有JSON文件
```bash
find /opt/data/neural_network/ -name "*.json" -exec python3 -c "import json,json;f=open('{}');json.load(f);print('OK: '+f.name)" \;
```
3. **清理验证** — 确认重复文件已删除
```bash
# 检查重复skill目录是否清理
for d in /opt/data/brain/*/; do name=$(basename "$d"); [ -d "/opt/data/skills/$name" ] && echo "DUPLICATE: $name in brain/ vs skills/"; done
# 检查scripts/是否有非脚本文件混入
find /opt/data/scripts/ -maxdepth 1 ! -name "*.py" ! -name "." ! -name ".." | head -20
```
4. **最终目录大小**
```bash
du -sh /opt/data/brain/ /opt/data/neural_network/ /opt/data/scripts/ /opt/data/skills/
```

## 关键教训总结

1. **不要假设空目录真的是空的** — 必须 `ls` 进去验证
2. **auto_integrated 是噪声** — 自动集成系统会产生大量无价值的脚本条目
3. **备份永远在删除之前** — 用 mv 到 backup 而非直接 rm
4. **版本号不代表优先级** — v2.0的器官体系哲学 + v3.0执行层 = 完整系统
5. **diff比对brain/和skills/** — 避免误删有差异的版本
6. **cron依赖检查不可跳过** — 删除skill前必须确认无活跃定时任务依赖
