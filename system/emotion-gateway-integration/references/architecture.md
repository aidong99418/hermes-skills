# 情绪感知 → LLM 流水线接入标准

## 架构全貌

```
用户消息
   ↓
emotion_sense hook (agent:start)
   → neural_emotion_sense.analyze_emotion() 分析情绪
   → 写入 /opt/data/state/emotion_state.json (10条历史)
   → 写入 /opt/data/state/emotion_inject.txt (当前情绪提示)
   ↓
brain_thinker.think() 被派工板触发
   → 读取 emotion_inject.txt
   → _emotion_ctx 注入到三路并行team_tasks的prompt前缀
   ↓
Ollama LLM 收到带情绪上下文的提示词 → 情绪感知响应
```

## 接入标准接口

### 文件约定

| 路径 | 用途 | 格式 |
|------|------|------|
| `/opt/data/state/emotion_state.json` | 情绪状态持久化 | JSON，含current/history/prompt字段 |
| `/opt/data/state/emotion_inject.txt` | 动态注入文本 | 纯文本，直接拼接在prompt前 |
| `/opt/data/state/emotion_history.jsonl` | 归档历史（未来扩展） | JSONL，每条对话一行 |

### 情绪类型与提示映射

```python
EMOTION_PROMPTS = {
    "impatient": "【情绪感知】董哥情绪急迫，请优先给出确定答案，不要模糊表述。",
    "frustrated": "【情绪感知】董哥感到受挫，请态度温和鼓励，肯定已有成果，再给方案。",
    "excited": "【情绪感知】董哥情绪积极，可以适当展开讨论，分享相关洞见。",
    "tired": "【情绪感知】董哥可能累了，回答要简洁直接，减少冗余，直击要点。",
    "curious": "【情绪感知】董哥有好奇心，可以适当展开细节，鼓励探索。",
    "focused": "【情绪感知】董哥状态专注，适合深度分析，可以提供详细论证。",
    "satisfied": "【情绪感知】董哥满意当前状态，保持稳定输出即可。",
    "neutral": None,  # 不额外注入
}
```

### 标准注入代码

任何调用LLM的脚本，读取情绪上下文的规范写法：

```python
from pathlib import Path

_emotion_ctx = ""
try:
    _ef = Path("/opt/data/state/emotion_inject.txt")
    if _ef.exists():
        _emotion_ctx = _ef.read_text(encoding="utf-8").strip()
        if _emotion_ctx:
            _emotion_ctx = "\n" + _emotion_ctx
except Exception:
    _emotion_ctx = ""

# 使用
prompt = f"{_emotion_ctx}你的系统提示：{question}..."
# 或 messages 数组模式
messages[0]["content"] = _emotion_ctx + "\n" + messages[0]["content"]
```

## 新功能接入Hook流水线规范

### 标准Hook目录结构

```
/opt/data/hooks/<hook_name>/
├── HOOK.yaml      # 元数据：name/description/version/events
└── handler.py     # async def handle(event_type, context) -> None
```

### HOOK.yaml 格式

```yaml
name: my_organ_hook
description: 我的器官Gateway接入Hook
version: 1.0
events:
  - agent:start    # 用户消息开始处理
  - agent:end      # 响应发送完成后
```

### 可用事件类型

| 事件 | 时机 | context字段 |
|------|------|------------|
| `gateway:startup` | Gateway进程启动 | `{}` |
| `session:start` | 新会话创建 | `platform, user_id, session_id` |
| `agent:start` | 消息开始处理 | `platform, user_id, session_id, message` |
| `agent:end` | 响应发送完成 | `platform, user_id, session_id, response` |
| `command:*` | 任意slash命令 | `command, args` |

**重要**：agent:start 的 context 不含 `system_prompt` 字段，无法直接注入。如需影响LLM输出，请通过**状态文件**中转。

### handler.py 标准模板

```python
"""
器官接入Hook — <hook_name>
"""
import json
from pathlib import Path
from datetime import datetime

STATE_FILE = Path("/opt/data/state/<state_name>.json")

async def handle(event_type: str, context: dict) -> None:
    """
    处理事件。
    注意：永远不阻塞主流程，所有异常内部捕获。
    """
    try:
        # 1. 提取需要的数据
        message = (
            context.get("message")
            or context.get("user_message")
            or ""
        )
        if not message:
            return

        # 2. 执行逻辑（如调用器官/分析/写入）
        result = ...

        # 3. 写入状态文件（供其他模块读取）
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        # 永远不阻塞主流程
        print(f"[<hook_name>] 处理异常: {e}", flush=True)
```

## 故障排查

### 情绪未注入
1. 检查 `/opt/data/state/emotion_inject.txt` 是否存在且非空
2. 检查 `/opt/data/state/emotion_state.json` 的 `confidence` 是否 >= 0.6
3. 检查 emotion_sense hook 是否在 `agent:start` 事件列表中

### Hook未加载
1. 检查 `/opt/data/hooks/<name>/HOOK.yaml` 是否存在且格式正确
2. 检查 `/opt/data/hooks/<name>/handler.py` 是否有 `async def handle(event_type, context)` 函数
3. 查看 gateway 日志中是否有 `[hooks] Loaded hook` 字样

### 状态文件路径不一致
- emotion_state.json 写入路径：`/opt/data/state/`（hook内部常量）
- 读取路径：各消费模块自行读取 `/opt/data/state/` 下对应文件
- 不要在 hook目录内读写状态文件（除非是hook私有状态）
