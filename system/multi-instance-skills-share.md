# 技能名称
multi-instance-skills-share

# 触发场景
任何涉及多Agent实例/子代理/分身共享skills库的场景：
- 启动新子代理/分身任务
- 评估分身间skills一致性
- 优化skills同步机制
- 设计新的分身架构

# 核心架构

## 当前问题
子代理(subagent)隔离上下文，不知道去哪读skills库，导致每个子代理各自为战，无法复用已有skill。

## 解决方案：共享skills库
所有实例共用同一个物理目录 `/opt/data/skills/`：

```
/opt/data/skills/           ← 共享skills库（所有实例同一物理路径）
  ├── knowledge/            ← 知识类skills（95个）
  ├── system/               ← 系统类skills（111个）
  ├── workflow/             ← 工作流skills（30个）
  ├── brain/                ← 大脑类skills（23个）
  └── ...                   ← 其他分类

主实例（PID 1）             子代理（delegate_task）         秘书处守护进程
/hermes/gateway/run.py      /hermes/tools/delegate_tool.py  /opt/data/scripts/secretary_daemon.py
    ↓                            ↓                              ↓
get_skills_dir() → /opt/data/skills/ ← ← ← ← ← ← ← ← ← ← ←
    所有进程读同一目录，天然共享
```

## 关键改动记录（2026-06-09）

### 1. 子代理system prompt注入
文件：`/opt/hermes/tools/delegate_tool.py`

改动：在 `_build_child_system_prompt()` 函数里注入skills路径信息。

子代理现在收到的system prompt末尾包含：
```
SKILLS LIBRARY PATH:
/opt/data/skills
Your system has a shared skills library at this path. Before starting, check if there's a relevant skill for your task:
  1. Use skills_list() to browse available skills
  2. Use skill_view(name='xxx') to load a specific skill and follow its instructions
  3. Skills are organized by category (knowledge/, system/, workflow/, etc.)
  4. Prefer using existing skills over improvising -- they encode proven workflows
```

效果：子代理知道去哪读skill，能主动调用 `skill_view()` 加载特定skill执行任务。

### 2. 主实例skills路径
路径：`/opt/data/skills/`（由 `hermes_constants.get_skills_dir()` 返回）
配置：`config.yaml` 里 `skills.external_dirs: []`（空 = 只读内置目录）

## 实例类型与skills访问

| 实例类型 | 启动方式 | skills访问方式 | 备注 |
|---------|---------|---------------|------|
| 主实例（gateway） | hermes gateway run | get_skills_dir() → /opt/data/skills/ | 直接读 |
| 子代理（delegate） | delegate_task tool | system prompt注入路径 + skill_view() | 2026-06-09修复 |
| 秘书处守护进程 | Python daemon | 读 /opt/data/skills/ | 需验证是否主动用skills |
| Ollama本地模型 | API调用 | 不直接读skills | 通过我（主实例）间接调用skill |

## 共享机制原理
NAS上所有进程共用同一个文件系统命名空间：
- `/opt/data/` 是NAS持久化存储路径
- 无论哪个进程（主实例/子代理/守护进程），访问 `/opt/data/skills/` 看到同一套文件
- 无需额外同步机制，天然共享

## 验证方法
```bash
# 1. 验证主实例能读skills
hermes skills list

# 2. 验证子代理system prompt包含skills路径
grep -n "SKILLS LIBRARY PATH" /opt/hermes/tools/delegate_tool.py

# 3. 验证语法正确
/opt/hermes/.venv/bin/python -c "from tools.delegate_tool import _build_child_system_prompt; print('OK')"
```

## 架构补充：子代理禁止写NAS
子代理的 `execute_code` 工具被blocked（DELEGATE_BLOCKED_TOOLS），只能读skills、读文件、执行命令，但禁止写NAS文件。这是有意设计，防止子代理污染共享skills库。

写入skills的正确方式：
1. 我（主实例）收到董哥指令 → 写skill到 /opt/data/skills/XXX/
2. 所有分身/子代理 下次读到同一份文件

## 未来扩展方向
1. **skills版本管理**：每个skill加版本号，避免不同分身读到不同版本
2. **skills增量同步**：秘书处/子代理新增skill后自动同步到共享目录
3. **skills热加载**：修改skill后无需重启gateway立即生效
