# 模型切换器

在微信/飞书对话中直接输入模型切换指令，识别 → 配置 → 重启全自动完成。

## 触发关键词

| 用户输入 | 切换到 |
|---------|--------|
| `切到M2.7` `用M2.7` `换M2.7` `m2.7` | MiniMax-M2.7（官方主模型） |
| `切到wisemodel` `用wisemodel` `始智AI` | wisemodel + MiniMax-M2.7 |
| `切到硅基` `硅基流动` `siliconflow` `SF` | siliconflow + Qwen/Qwen3-8B |
| `切到minimax` `官方模型` | minimax + MiniMax-M2.7 |

## 执行流程

1. 解析模型名称（支持多种表达）
2. 更新 config.yaml（`hermes config set`）
3. 发送 SIGUSR1 触发 Gateway 优雅重启
4. 告知用户切换完成

## 完整代码

```python
import subprocess, re, os, signal, sys

# 模型名映射
MODEL_MAP = {
    "m2.7":         {"provider": "minimax",       "model": "MiniMax-M2.7"},
    "minimax-m2.7": {"provider": "minimax",       "model": "MiniMax-M2.7"},
    "wisemodel":    {"provider": "wisemodel",      "model": "MiniMax-M2.7"},
    "始智ai":        {"provider": "wisemodel",      "model": "MiniMax-M2.7"},
    "硅基":         {"provider": "siliconflow",    "model": "Qwen/Qwen3-8B"},
    "siliconflow":  {"provider": "siliconflow",    "model": "Qwen/Qwen3-8B"},
    "sf":           {"provider": "siliconflow",    "model": "Qwen/Qwen3-8B"},
    "minimax":      {"provider": "minimax",        "model": "MiniMax-M2.7"},
}

def parse_intent(text: str) -> dict | None:
    """从用户输入提取模型切换意图"""
    text = text.lower().strip()
    for keyword, config in MODEL_MAP.items():
        if keyword in text:
            return {"keyword": keyword, **config}
    return None

def switch_model(provider: str, model: str, config_path: str) -> tuple[bool, str]:
    """用 hermes config set 更新模型配置"""
    try:
        # 1. 写 model.default
        r = subprocess.run(
            ["/opt/hermes/.venv/bin/hermes", "config", "set",
             f"model.provider", provider],
            capture_output=True, text=True, timeout=10
        )
        # 2. 写 model.default
        r2 = subprocess.run(
            ["/opt/hermes/.venv/bin/hermes", "config", "set",
             f"model.default", model],
            capture_output=True, text=True, timeout=10
        )
        return True, f"✅ 配置已更新: {provider} / {model}"
    except Exception as e:
        return False, f"配置更新失败: {e}"

def restart_gateway() -> tuple[bool, str]:
    """发送 SIGUSR1 触发 Gateway 优雅重启"""
    pid = 1  # Gateway 固定 PID 1
    try:
        os.kill(pid, signal.SIGUSR1)
        return True, "✅ Gateway 正在优雅重启（预计 30s 内完成）"
    except ProcessLookupError:
        return False, "Gateway 进程不存在"
    except PermissionError:
        return False, "无权限发送信号"
    except OSError as e:
        return False, f"信号发送失败: {e}"

# 主流程
def handle_model_switch(user_text: str) -> str:
    intent = parse_intent(user_text)
    if not intent:
        return None  # 不匹配，返回None让调用方处理

    provider = intent["provider"]
    model = intent["model"]

    ok, msg = switch_model(provider, model, "")
    if not ok:
        return f"❌ {msg}"

    ok2, msg2 = restart_gateway()
    return f"{msg}\n{msg2}"
```

## 注意事项

- Gateway 运行在容器 PID 1，普通 kill 无法重启，必须用 SIGUSR1
- SIGUSR1 触发优雅重启：先排空当前对话，再重启，0丢失
- wisemodel 需要确认 api_key 已配置在 config.yaml custom_providers 里
- siliconflow key 已在 smart_model_routing.cheap_model.api_key 配置