---
name: config-guardian
description: config.yaml配置守护者，自动检测并修复wisemodel等关键配置丢失。触发：Unknown provider、cron失败、config被意外修改。
triggers:
  - Unknown provider wisemodel
  - config.yaml配置丢失
  - 云端模型崩
  - cron任务provider报错
version: 1.0
---

# Config Guardian

## 脚本路径
/opt/data/scripts/config_guardian.py

## 命令
- dry run: python3 /opt/data/scripts/config_guardian.py --dry
- 修复: python3 /opt/data/scripts/config_guardian.py

## 检查项
1. providers.wisemodel（新格式dict）
2. custom_providers[wisemodel]（旧格式list）
3. 根model区（provider/default/context_length）
4. cron jobs与config一致性
5. Provider Resolution双重验证

## 设计原则
- 零云端依赖，纯Python stdlib
- 修复前自动备份到 /opt/data/backups/guardian_YYYYMMDD_HHMMSS/

## 关键教训：值存在 ≠ 值正确
2026-06-07 实踩：凌晨确认了3个配置，但重启后一查发现：
- `gateway_timeout_warning: 900`（应该是 1500）
- `busy_input_mode: interrupt`（应该是 queue）
- `smart_model_routing.enabled: false`（应该是 true）

教训：**说"配好了"和"真的配好了"是两回事**。必须用 yaml.safe_load 读出实际值比对，不只是 grep 找字段是否存在。

排查方法：
```python
import yaml
cfg = yaml.safe_load(open('/opt/data/config.yaml'))
# 找真实路径（值可能在嵌套层级）
def find_key(d, key):
    for k, v in flatten.items():
        if key in k.lower():
            print(f"{k} = {v}")

# 重点检查嵌套路径
cfg.get('agent', {}).get('gateway_timeout_warning')
cfg.get('display', {}).get('busy_input_mode')
cfg.get('smart_model_routing', {}).get('enabled')
```

---

## 已修复的 Bug（2026-06-08）

### Bug 1: verify_end_to_end 只接受 minimax-cn/minimax（已修复）
**症状**：guardian 修复完成后，verify 仍报 `❌ 根 model.provider`，但 config.yaml 的 provider 值是合法值 `custom`

**根因**：`verify_end_to_end()` 第 540 行硬编码了 provider 白名单为 `("minimax-cn", "minimax")`，而实际系统支持 `custom / auto / wisemodel` 等多种 provider，且 `check_root_model()` 校验的也是这五个值，两者不一致

**修复**：`verify_end_to_end` 的 checks 列表扩展为 `("minimax-cn", "minimax", "custom", "auto", "wisemodel")`，与 `check_root_model()` 逻辑对齐

### Bug 2: missing_providers 虚假报告"恢复成功"（已修复）
**症状**：日志显示 `✅ 恢复 providers.xxx`，但 baseline 中该条目是空的（baseline 本来就没有这个历史数据），结果写入了空 dict

**根因**：`apply_fixes` 中处理 `missing_providers` 时，无条件执行 `cfg["providers"][name] = dict(item["entry"])`，没有检查 entry 是否为空

**修复**：添加空条目检查，baseline 无历史数据时跳过而非虚假报告"恢复成功"：
```python
entry = item.get("entry") or {}
if not entry or not any(entry.values()):
    logger.warning("⚠️ 跳过 providers.%s：baseline 为空，无历史数据可恢复", name)
    continue
```

### Bug 3: restore_root_model 不覆盖 falsy 值
**症状**：`model.context_length` 为 0（而非缺失），修复日志没出现"恢复 model.context_length"

**根因**：`restore_root_model` 逻辑是 `if v and not cfg["model"].get(k)`，只有当 baseline 有值且 config 当前为空时才恢复。如果 config 当前是 `context_length: 0`（falsy），条件 `not cfg["model"].get(k)` 为 False，跳过恢复

**说明**：这个行为是设计上的。当用户手动删除了某个字段（如 context_length），guardian 能从 baseline 恢复。但如果用户显式将某字段设为 `0`（如 `context_length: 0`），guardian 认为这是有意行为，不会覆盖

### Bug 4: guardian_state的providers基准线覆盖config（2026-06-08）
**症状**：系统用custom_providers不需要顶级providers字段，但guardian_state.json里baseline.providers存了历史数据，每次扫描都"恢复"providers字段为空{}，导致路由混乱。

**诊断**：查guardian_state.json里baseline字段，若有providers子字典说明存了错误的基准线。

**修复**：
```python
state = json.load(open('/opt/data/config/guardian_state.json'))
if 'baseline' in state and 'providers' in state['baseline']:
    del state['baseline']['providers']
with open('/opt/data/config/guardian_state.json', 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
```

**验证**：`python3 /opt/data/scripts/config_guardian.py` 应输出"检查通过，无异常"。

### Bug 5: 模型层面备用 vs provider双通道切换（2026-06-08）
**双provider切换风险**：通过providers/fallback_providers字段切换provider，minimax-cn会触发系统崩溃死锁。

**正确方案**：通过custom_providers多入口做模型备用，失败时路由层自动切，不触发guardian误报：
```yaml
custom_providers:
- name: 始智Ai
  base_url: https://open.ospreyai.cn/v1
  api_key: wisemodel-xxx
  model: minimax-m2.5-highspeed
  models:
    minimax-m2.5-highspeed:
      context_length: 192000
- name: MiniMax-CN  # 备用模型，不走provider切换
  base_url: https://open.minimaxi.com/v1
  api_key: minimax-xxx
  model: MiniMax-M2.7
  models:
    MiniMax-M2.7:
      context_length: 100000
```

**铁律**：不动providers/fallback_providers字段，只用custom_providers做多入口。

### Bug 7: _is_config_intact() 硬性要求所有 provider 有 api_key（误报根因）
**发现时间**：2026-06-10

**症状**：guardian 每次运行都输出 `🔧 检测到配置损坏，开始修复` → `✅ config.yaml 检查通过，无异常`，日志每15分钟重复一次，形成持续误报。

**根因**：`_is_config_intact()` 第201行：
```python
if not entry.get("api_key") or len(entry.get("api_key", "")) < 10:
    return False  # key 被清空
```
这段逻辑无差别检查所有 baseline providers 的 api_key，但 `guardian_state.json` 里 `ollama` 和 `siliconflow` 的 api_key 本身就是空字符串 `""`（本地/免费平台无需 key）。这导致 `cfg_providers.get("ollama")` 的 api_key 为空时条件为真，触发"配置损坏"误报。

**修复**：
```python
# 修复前（有 bug）
if not entry.get("api_key") or len(entry.get("api_key", "")) < 10:
    return False  # 导致 ollama/siliconflow 每次都误报

# 修复后
if bl_entry.get("api_key") and bl_entry["api_key"] not in ("", "...", "***"):
    if not entry.get("api_key") or len(entry.get("api_key", "")) < 10:
        return False  # key 被清空
```
仅当基准线本身有有效 api_key 时才检查；无 key 的 provider（Ollama/siliconflow）跳过此检查。

**诊断方法**：
```python
# 查 guardian_state.json 中各 provider 的 api_key
cat /opt/data/config/guardian_state.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for k,v in d['baseline']['providers'].items():
    print(f'{k}: api_key={repr(v.get(\"api_key\").strip() if v.get(\"api_key\") else \"\")}')"
```

---

### Bug 6: providers字段格式与代码预期不一致（list vs dict双方向）
**背景**：providers 字段在不同时期可能是 dict 或 list，代码必须双向兼容：
- dict格式: `{id: {...}}`（当前生产环境就是这个格式）
- list格式: `[{id, ...}, ...]`

**Bug 6a（已修复）：config从dict变为list → 代码需适配list**
- 症状：`AttributeError: 'str' object has no attribute 'get'` 在 `_is_config_intact()` 行192 和 `check_all_providers()` 行284
- 修复：加 `isinstance` 判断后归一化为 dict 再查询（见上方原始描述）

**Bug 6b（2026-06-08新发现）：check_api_key_validity() 误用list遍历dict**
- 症状：`AttributeError: 'str' object has no attribute 'get'`
- 发生位置：`check_api_key_validity()` 行432，`for entry in (cfg.get("providers") or [])`
- 根因：该函数从未应用 Bug 6a 的修复，仍然假设 providers 是 list。实际 config.yaml 中 providers 是 dict：`{'minimax-cn': {...}, 'ollama': {...}, 'siliconflow': {...}}`，迭代 dict 得到的是字符串键（如 `'minimax-cn'`），不是 dict，调用 `.get()` 即崩溃
- 修复：
```python
# 修复前（假设list）
for entry in (cfg.get("providers") or []):
    name = entry.get('id') or entry.get('name', 'unknown')
    if entry.get("api_key"):
        locations.append((f"providers.{name}", entry.get("api_key", "")))

# 修复后（兼容dict）
for name, entry in (cfg.get("providers") or {}).items():
    if entry.get("api_key"):
        locations.append((f"providers.{name}", entry.get("api_key", "")))
```

**教训**：config_guardian.py 有多个函数分散读取 `providers`，Bug 6a 的修复只修了 `_is_config_intact()` 和 `check_all_providers()`，漏掉了 `check_api_key_validity()`。全面排查需要用 `grep -n "providers" config_guardian.py` 逐行确认所有遍历点都已加 `isinstance` 保护。

**全面排查命令**：
```bash
grep -n "cfg.get. providers" /opt/data/scripts/config_guardian.py
# 所有返回结果都应做 isinstance 判断，不能假设单一格式
```
**症状**：`AttributeError: 'list' object has no attribute 'get'` 发生在：
- `_is_config_intact()` 行 192: `cfg.get("providers", {}).get(name)`
- `check_all_providers()` 行 284: `providers.get(name)`

**根因**：config.yaml 的 `providers` 字段已从 dict 结构（`{id: {...}}`）改为 list 结构（`[{id, ...}, ...]`），但 config_guardian.py 代码未同步更新，只调用 `.get(name)` 不兼容 list。

**修复**（2处）：
```python
# _is_config_intact() 中
raw_providers = cfg.get("providers") or {}
if isinstance(raw_providers, list):
    cfg_providers = {p.get("id"): p for p in raw_providers if isinstance(p, dict)}
else:
    cfg_providers = raw_providers
for name, bl_entry in bl_providers.items():
    entry = cfg_providers.get(name) or {}

# check_all_providers() 中同样处理
raw_providers = cfg.get("providers") or []
if isinstance(raw_providers, list):
    providers = {p.get("id"): p for p in raw_providers if isinstance(p, dict)}
else:
    providers = raw_providers or {}
```

**教训**：config.yaml 的 providers 字段格式在不同版本间可能从 dict 变为 list，代码必须同时兼容两种格式。用 `isinstance(raw_providers, list)` 判断后归一化为 dict 再查询。

---

## 已知的无法自动修复场景

| 场景 | 原因 | 建议 |
|---|---|---|
| fallback_providers 为空 | baseline 中 fallback_providers 也为空，无历史数据 | 手动在 config.yaml 中配置 fallback 列表 |
| delegation 字段全为空字符串 | baseline 中 delegation 各字段本来就是空字符串 | 无需修复（delegation 本身可为空） |

## 排查方法：运行 + 读日志 + 读 state
```bash
# 1. 运行（自动修复）
python3 /opt/data/scripts/config_guardian.py

# 2. 检查日志（关注 ❌ 和 ⚠️）
tail -20 /opt/data/logs/guardian.log

# 3. 查看状态文件（含 broken_count + baseline）
cat /opt/data/config/guardian_state.json

# 4. 快速诊断：guardian_state 中各 provider api_key 是否为空（Bug 7 误报根因）
cat /opt/data/config/guardian_state.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for k,v in d['baseline']['providers'].items():
    klen = len(v.get('api_key','')) if v.get('api_key') else 0
    print(f'{k}: api_key长度={klen}')"

# 5. 验证实际 config 值（"值存在 ≠ 值正确"）
# 用 python 而非 grep，确保值真的被写入
```

## 历史教训
**值存在 ≠ 值正确**（2026-06-07）：确认了3个配置，但重启后发现 gateway_timeout_warning/busy_input_mode/smart_model_routing 都是错的。说"配好了"和"真的配好了"是两回事。必须用 yaml.safe_load 读出实际值比对，不只是 grep 找字段是否存在。

### model.provider = minimax 误报（2026-06-07）
**症状**：guardian 报错 `model.provider 应为 wisemodel / custom / auto，当前: minimax`

**根因**：config.yaml 根 `model:` 段的 `provider` 与 `base_url` 语义不一致。当 `base_url: https://open.ospreyai.cn/v1`（wisemodel/始智AI平台）时，`provider` 应为 `wisemodel`，不能用模型名 `minimax`。

**修复**：手动 patch 将 `config.yaml` 中 `provider: minimax` 改为 `provider: wisemodel`，然后重新跑验证。

**为何无法自动修复**：guardian `check_root_model()` 用 baseline 对比恢复，但 baseline 里也存了旧值，无法自我修正。
