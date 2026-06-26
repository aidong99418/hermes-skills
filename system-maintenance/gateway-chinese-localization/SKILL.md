---
name: gateway-chinese-localization
description: Hermes Gateway 中文本地化批量改造 — 翻译所有用户可见消息为中文，含缩进陷阱修复。
trigger: 需要翻译 gateway 推送给用户的消息 / 中文友好改造
version: 1.0
---

# Hermes Gateway 中文本地化批量改造

## 触发条件
需要对 `/opt/hermes/gateway/run.py` 中的所有用户可见消息进行中文翻译（系统弹窗、命令回复、进度通知）。

## 核心教训（踩坑总结）

### 缩进陷阱 ⚠️
**问题**：批量 patch 替换时，原始代码的 return 语句可能和上下文同缩进，替换后容易多出缩进。

**示例**：
```python
# 原始代码（return 正确缩进）
        if agent:
            if session_key in self._running_agents:
                del self._running_agents[session_key]
            return "message"  # ← 同级缩进
```

**中招后症状**：`IndentationError: unexpected indent`，报错行往往不是真正出问题的行。

**修复方法**：找到报错行附近，检查是否有上一轮 patch 引入了多余缩进，逐个修复。

### 标准工作流

1. **扫描所有用户消息**
   ```bash
   grep -n 'return f"\|return "\|adapter\.send' gateway/run.py | grep -v 'logger\.' | head -200
   ```

2. **按功能模块批量翻译**（从 grep 结果判断属于哪类命令）

3. **每批后立即语法验证**
   ```bash
   python3 -m py_compile gateway/run.py
   ```

4. **修复缩进错误**：
   - 报错行往往是被"挤歪"的行，不是真正的错误位置
   - 检查报错行附近的 return 语句是否有异常缩进
   - 用 `read_file` 查看上下文确认原始缩进

5. **验证完成后重启**
   ```bash
   hermes gateway restart
   ```

## 需翻译的消息类型清单

| 类型 | 示例 |
|------|------|
| 命令回复 | `/stop` → `⚡ 已停止` |
| 错误消息 | `Failed to...` → `❌ ...失败` |
| 进度通知 | `Still working...` → `正在处理...` |
| 工具名 | `terminal` → `终端` |
| 确认消息 | `✅ Command approved` → `✅ 已批准` |
| 警告消息 | `⚠️ YOLO mode...` → `⚠️ 危险模式...` |

## 翻译原则
- 只改用户可见消息，不改原始输出内容
- 保持 emoji 和格式不变
- 变量占位符 `{var}` 保留

## 批量快速替换脚本

```python
import re
content = open('/opt/hermes/gateway/run.py').read()

replacements = [
    ('**Session ID:**', '**会话ID:**'),
    ('**Title:**', '**标题:**'),
    ('**Created:**', '**创建时间:**'),
    ('**Last Activity:**', '**最后活跃:**'),
    ('**Agent Running:**', '**Agent状态:**'),
    ("**Agent Running:** {'Yes ⚡' if is_running else 'No'}",
     "**Agent状态:** {'运行中 ⚡' if is_running else '空闲'}"),
    ('**Connected Platforms:**', '**已连接平台:**'),
    ('⚡ **Skill Commands**', '⚡ **技能命令**'),
    ('skill is installed but disabled', '技能已安装但未启用'),
    ('Enable it with', '启用方法'),
    ('skill is available but not installed', '技能可用但未安装'),
    ('Install it with', '安装方法'),
    ("Hi~ I don't recognize you yet!", '你好！我还不认识你！'),
    ("Here's your pairing code:", '配对码是：'),
    ('Ask the bot owner to run:', '请让管理员运行：'),
    ('⚡ Priority Processing', '⚡ 优先处理已开启'),
    ('You can continue waiting or use /reset', '可以继续等待，或输入 /reset 重置'),
    ('... and ', '还有 '),
    ('more. Use `/commands` for the full paginated list.', '条。使用 /commands 查看完整列表。'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)

with open('/opt/hermes/gateway/run.py', 'w') as f:
    f.write(content)
```

### ⚠️ 换行符陷阱
`\n\n` 在 Python 字符串字面量中要写成 `\\n\\n`，直接写 `\n\n` 会触发 `SyntaxError: unterminated string literal`。例如：
```python
# ❌ 错误
'"⚡ 优先处理已开启\n\n"'
# ✅ 正确
'"⚡ 优先处理已开启\\n\\n"'
```

### 重启方式
SIGHUP 比完整重启更安全（保留 session 锁）：
```bash
kill -HUP $(pgrep -f 'gateway/run.py' | head -1)
```
或直接：
```bash
hermes gateway restart
```

## 关联文件
- `/opt/hermes/gateway/run.py` — 所有修改在此文件
- 工具名翻译字典 `_TOOL_NAME_CN`（模块级，约58行）

## 验证清单
- [ ] `python3 -m py_compile gateway/run.py` 通过
- [ ] SIGHUP 或 restart gateway
- [ ] 测试 /status 命令，确认输出全中文
