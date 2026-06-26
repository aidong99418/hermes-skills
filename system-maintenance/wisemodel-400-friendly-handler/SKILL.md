---
name: wisemodel-400-friendly-handler
description: wisemodel 400后gateway友好处理——立即停typing+直接推送中文错误消息，对话不卡死
trigger: wisemodel 400 / unexpected end of data / 对话卡死
---
created: 2026-05-30
version: 2.1
---
## 触发条件
wisemodel 代理响应超时（~60秒限制）导致 HTTP 400：`unexpected end of data`

## 问题现象
- typing 指示器卡死（"正在输入..."一直显示）
- 错误消息没推给用户
- 对话完全卡死，必须开新会话才能恢复

---

## v2.1 实际落地：stream超时截断（2026-06-06实测）

**问题根因**：wisemodel服务端~60秒截断流，Hermes客户端傻等120秒才超时 → wisemodel强制kill连接 → 400 "unexpected end of data"

**修复1 — stream_read_timeout裁到55秒（run_agent.py:5390）**
```python
# Wisemodel/始智AI has a ~60s server-side streaming timeout.
# Cap the client-side stream read timeout so httpx closes the
# connection cleanly before wisemodel kills it, avoiding a
# 400 "unexpected end of data" on long contexts.
if _stream_read_timeout >= 120.0 and self.base_url and "wisemodel" in self.base_url.lower():
    _stream_read_timeout = 55.0
    logger.debug(
        "Wisemodel detected (%s) — stream read timeout capped to 55s (server limit)",
        self.base_url,
    )
```
**插入位置**：`stream_kwargs = {...}` 之前，与"Local provider detected"并列

**修复2 — 400友好提示（gateway/run.py:4083）**
```python
_is_ctx_fail = any(p in error_str for p in (
    "context", "token", "too large", "too long",
    "exceed", "payload",
    "unexpected end of data",  # wisemodel/始智AI 超时截断响应
)) or (
    "400" in error_str
    and len(history) > 50
)
```
→ 用户看到"Session too large, use /compact or /reset"而非原始400

**防御层级**：
1. 55秒cap → 预防：提前收网，wisemodel干净关闭连接，无400
2. 友好提示 → 兜底：万一还400，用户知道怎么办

---

## v2.0 checkpoint续传设计（待落地）

```
超时 → retry x2 → 耗尽 →
  ① 保存断点（partial → checkpoint JSON文件）
  ② 重置session（干净上下文，同session_key换session_id）
  ③ 注入续传提示到context_prompt
  ④ 自动重跑agent
  ⑤ 推"🔄 正在续传..."通知
  ⑥ 推送最终结果
```

**关键变量（run.py）**：
```python
_auto_recover_pending = False   # 初始化
_send_error_to_user = True      # 初始化，防止错误消息抢先
_is_wisemodel_timeout = False   # 初始化

# retry耗尽后
_auto_recover_pending = bool(_is_wisemodel_timeout)
_send_error_to_user = not _auto_recover_pending  # 超时时不发错误
```

**流程守卫（4307行）**：
```python
# 错误消息块 + _send_error_to_user 守卫
if not response and agent_result.get("failed") and _send_error_to_user:
    # 只在非超时时执行，超时走下面recovery
```

**核心恢复逻辑（4499行+）**：
```python
_do_auto_recover = (
    agent_result.get("compression_exhausted")
    or _auto_recover_pending  # wisemodel超时时也为True
) and session_entry and session_key
if _do_auto_recover:
    # 1. 提取最后一条assistant消息作为partial
    _partial_result = ""
    for _msg in reversed(agent_result.get("messages", [])):
        if _msg.get("role") == "assistant" and _msg.get("content"):
            _partial_result = _msg["content"]
            break

    # 2. 保存断点文件
    _ckpt_file.write_text(json.dumps({
        "partial": _partial_result,
        "original_message": message_text,
        "session_id": session_entry.session_id,
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False, indent=2))

    # 3. 重置session
    self.session_store.reset_session(session_key)
    self._evict_cached_agent(session_key)
    self._session_model_overrides.pop(session_key, None)

    # 4. 注入续传提示
    _recovery_hint = (
        f"\n[系统续传] 上一次处理因大上下文超时被中断。"
        f"以下是已生成的部分内容（不完整），请在此基础上继续完成：\n"
        f"---\n{_partial_result}\n---\n"
    )
    context_prompt = _recovery_hint + context_prompt

    # 5. 重跑
    agent_result = await self._run_agent(
        message=message_text,
        context_prompt=context_prompt,
        history=[],  # 干净空历史
        source=source,
        session_id=session_entry.session_id,
        session_key=session_key,
        event_message_id=event.message_id,
        channel_prompt=event.channel_prompt,
    )

    # 6. 续传成功 → 推通知
    if not agent_result.get("failed"):
        _resume_notice = (
            "🔄 上一条消息因大上下文超时被自动续传。\n"
            "结果正在处理中，请稍候...\n"
        )
        await _typing_adapter.send(source.chat_id, _resume_notice)
        _auto_recovered = True  # 绕过错误处理块
```

**覆盖场景**：
- wisemodel 60秒截断 → 自动续传 ✅
- 500/502/503服务错误 → 自动续传 ✅
- 压缩耗尽 → 自动续传（原有逻辑升级）✅
- 续传自身也失败 → fallback正常错误处理 ✅

**为什么不用派工板**：派工板链路多一个依赖，开新会话更稳更直接。

## 验证方法
触发一次 wisemodel 400 → 观察是否自动收到"🔄 正在续传"通知、最终是否出结果、typing是否正常消失。
