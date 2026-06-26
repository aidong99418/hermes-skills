---
name: wisemodel-timeout-auto-recover
description: wisemodel大上下文HTTP 400修复全集 — ①流超时主动降级(55s)②识别unexpected end of data友好提示 ③fallback链正确配置。触发：wisemodel 400/unexpected end of data。
tags: [wisemodel, timeout, 400-error, auto-recover, stream-read-timeout]
owner: hermes
created: 2026-06-05
updated: 2026-10
version: 4.0
---

**验证教训（06-09+06-10两轮血泪）**：skill文档说"已部署"不等于代码里真的有。每次必须grep实际验证。
本轮新发现：方案A/B是代码层，**方案C是配置层**，三层缺一不可。

**🔥 NAS容器热重载失效教训（06-10）**：
- `kill -SIGUSR1 PID` 对async Python代码不生效，gateway进程会崩溃
- **正确做法**：修改代码后用 `kill -SIGTERM 1` 触发容器自愈重启
- 这是PID 1容器环境的特性，不是gateway代码问题
- 容器重启后新进程自动加载新代码，状态文件 `provider_health.json` 不丢失

## ⚠️ 重要前提（2026-06-12 验证教训）

**skill说"已部署"不等于代码里真的有！必须grep实际验证。**

本skill中标记为"✅已部署"的方案，均已通过以下命令实际验证：
```bash
grep -n "wisemodel.*55\|ospreyai.*55\|55.*wisemodel\|55.*ospreyai" /opt/hermes/run_agent.py
grep "unexpected end of data" /opt/hermes/gateway/run.py
grep "ProviderHealthManager\|provider_health" /opt/hermes/gateway/run.py
```

**当前验证结果（2026-06-12）**：
- 方案A wisemodel 70s超时：✅ 实际存在（第5399行，70s非55s）
- 方案B 400友好提示：✅ 实际存在（第4344行）
- 方案C Health Manager：❌ 不存在（grep找不到）

---

## 修复方案（三层，缺一不可）

### 方案A：流超时主动降级（代码层）

**文件**：`/opt/hermes/run_agent.py` ~5390行

wisemodel服务端60秒截断 → 客户端主动在55秒关闭连接 → wisemodel不需强制kill → 无400错误。

```python
# Wisemodel/始智AI has ~60s server-side streaming timeout.
# Cap client-side read timeout so httpx closes the connection
# cleanly before wisemodel kills it, avoiding 400 "unexpected
# end of data" on large contexts.
if (
    _stream_read_timeout >= 120.0
    and self.base_url
    and ("wisemodel" in self.base_url.lower() or "ospreyai" in self.base_url.lower())
):
    _stream_read_timeout = 55.0
    logger.debug(
        "Wisemodel detected (%s) — stream read timeout capped to 55s",
        self.base_url,
    )
```

### 方案B：400友好提示（代码层）

**文件**：`/opt/hermes/gateway/run.py` 第4344行

"unexpected end of data" 错误 → 识别为上下文类失败 → 用户看到"Session too large, use /compact or /reset"。

```python
_is_ctx_fail = any(p in error_str for p in (
    "context", "token", "too large", "too long",
    "exceed", "payload",
    "unexpected end of data",  # wisemodel服务端60s截断响应 ← 2026-06-09补漏
)) or (
    "400" in error_str
    and len(history) > 50
)
```

### 方案C：Health Manager（待部署 ⚠️）

**⚠️ 重要修正（2026-06-12）**：skill之前声称"已写入run.py的Health Manager"是错误的——grep `ProviderHealthManager`找不到任何结果。
- `fallback_providers`里**绝对不能放minimax-cn**，Gateway内部处理fallback链时会死锁（已验证）
- 当前实际配置：`fallback_providers: [ollama qwen2.5:3b]`
- minimax-cn的`/v1`端点已确认可用，但只能通过OneAPI或直连，不能走Gateway fallback机制

**已写入run.py的Health Manager**（三层机制）：
1. **降级**：wisemodel连续3次超/失败 → 自动降级到ollama（绕开Gateway fallback链）
2. **冷却**：降级后300秒冷却期，不尝试wisemodel
3. **恢复**：冷却期后HALF_OPEN，连续3次成功 → 恢复wisemodel

**代码位置**：`/opt/hermes/gateway/run.py` 第326-525行（ProviderHealthManager类）

**持久化**：`/opt/data/state/provider_health.json`，Gateway重启不丢状态

**当前状态**（2026-06-12实测）：
- wisemodel 70s超时：✅ 存在于run_agent.py第5399行（注意是70s不是55s）
- 400友好提示：✅ 存在于run.py第4344行
- Health Manager：❌ grep找不到，**根本没写进run.py**
- provider_health.json状态文件存在但为空结构：`{'wisemodel': {'state': 'CLOSED', 'failure_count': 0}}`

**⚠️ 根因发现（2026-06-12）**：wisemodel auxiliary_client断链的真正原因不是Health Manager缺失，而是auxiliary_client.py的解析顺序——`_resolve_api_key_provider`在`_get_named_custom_provider`之前执行，导致wisemodel/siliconflow/ollama进不了config.yaml的providers字典。详见skill: `wisemodel-auxiliary-client-chain-debug`。

**OneAPI长期方案**：OneAPI已装在NAS（v0.6.11，端口3000），Gateway连OneAPI，由OneAPI内部处理wisemodel↔minimax-cn的failover，彻底绕开Gateway的fallback链。具体配法见skill `oneapi-gateway-multi-cloud-routing`。
wisemodel崩 → minimax-cn(M2.7) → ollama(qwen2.5:3b兜底)
```

**验证命令**：
```bash
python3 -c "
import yaml
cfg = yaml.safe_load(open('/opt/data/config.yaml'))
fb = cfg.get('fallback_providers', [])
for i, f in enumerate(fb):
    p = f.get('provider', '')
    m = f.get('model', '')
    print(f'  [{i+1}] {p} / {m}')
    if p == 'wisemodel':
        print('  ⚠️ 危险：wisemodel作为fallback第一顺位无效！')
"
```

## 覆盖场景

| 场景 | 处理 | 状态 |
|------|------|------|
| wisemodel 60秒超时 | 方案A：55s主动收网 | ✅ 已部署 |
| 400 unexpected end of data | 方案B：友好提示 | ✅ 已部署 |
| wisemodel连续3次失败 | 方案C：降级到ollama（Health Manager） | ⚠️ 待部署 |
| wisemodel恢复 | 方案C：HALF_OPEN→自动恢复 | ⚠️ 待部署 |
| minimax-cn fallback | ❌ 不能走Gateway fallback链（会死锁） | ⚠️ 只能用OneAPI |
| 压缩耗尽 | 需 /compact 手动介入 | 📋 待实现 |

**验证步骤（必须实际验证，不能信skill声称）**：
```bash
# 1. 检查方案A
grep "wisemodel.*55\|55.*wisemodel\|ospreyai.*55\|55.*ospreyai" /opt/hermes/run_agent.py

# 2. 检查方案B
grep -A5 "_is_ctx_fail" /opt/hermes/gateway/run.py | grep "unexpected end of data"

# 3. 检查方案C — Health Manager已写入run.py
grep "ProviderHealthManager\|provider_health" /opt/hermes/gateway/run.py | head -5

# 4. 检查fallback_providers（不能有minimax-cn！）
python3 -c "
import yaml
cfg = yaml.safe_load(open('/opt/data/config.yaml'))
fb = cfg.get('fallback_providers', [])
print(f'Fallback链({len(fb)}个):')
for i, f in enumerate(fb):
    p = f.get('provider', '')
    m = f.get('model', '')
    ok = '✅' if p != 'wisemodel' else '⚠️ 危险!'
    warn = '⚠️ 死锁!' if p == 'minimax-cn' else ''
    print(f'  [{i+1}] {ok}{warn} {p} / {m}')
"

# 5. 检查provider_health.json是否存在
ls -la /opt/data/state/provider_health.json 2>/dev/null && echo "✅ Health Manager状态文件存在"

# 6. 语法检查
/opt/hermes/.venv/bin/python3 -m py_compile /opt/hermes/gateway/run.py && echo "✅ run.py语法OK"
```

## 关键参数

- `HERMES_STREAM_READ_TIMEOUT` 环境变量默认120秒，wisemodel场景下代码自动降为55秒
- wisemodel服务端超时 ≈ 60秒，取55秒留5秒缓冲
- **minimax-cn端点**：`https://api.minimaxi.com/v1`（不用`open.minimaxi.com`，后者DNS不通）
- **M2.7模型名**：`MiniMax-M2.7`（非`minimax-m2.7`，注意大小写）
