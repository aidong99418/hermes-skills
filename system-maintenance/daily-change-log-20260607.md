# 日常改动日志 2026-06-07

## 日期：2026-06-07
## 改动类型：模型配置大整理（wisemodel废弃 → MiniMax-M2.7）

---

## 1. 模型配置变更

### 变更前
- 云端主模型：minimax-m2.5-highspeed via wisemodel（始智AI/ospreyai.cn）
- wisemodel API key：`wisemodel-gbngcikewhrtirhoamio`
- wisemodel API base：`https://open.ospreyai.cn/v1`

### 变更后
- 云端主模型：**MiniMax-M2.7** via **minimax-cn**
- MiniMax API key：环境变量 `MINIMAX_API_KEY`
- MiniMax API base：`https://api.minimaxi.com/anthropic`
- context_length：192000

---

## 2. 文件清理清单

### brain/ 目录
| 文件 | 改动 |
|------|------|
| `brain/memory_bank/system_facts.json` | wisemodel段→minimax-cn，dispatch_rules/user_interaction更新 |

### scripts/ 目录（20个文件）
| 文件 | 改动 |
|------|------|
| `scripts/model_router.py` | MODEL_CLOUD=MinMax-M2.7，provider=minimax-cn，check函数修复，v3.0→v4.0 |
| `scripts/context_compressor.py` | WISEMODEL_*→MINIMAX_*，API_BASE改api.minimaxi.com |
| `scripts/adaptive_router.py` | 2处minimax-m2.5-highspeed→MiniMax-M2.7 |
| `scripts/self_upgrade.py` | 去掉litellm依赖，改urllib直调MiniMax-M2.7，v2.0→v2.1 |
| `scripts/multi_model_call.py` | minimax条目改MiniMax-M2.7+api.minimaxi.com |
| `scripts/wps_learn.py` | wisemodel_generate→minimax_generate，API全换 |
| `scripts/brain_dream_maker.py` | call_wisemodel_safe→call_siliconflow_deepseek（改走硅基流动DeepSeek-V3） |
| `scripts/config_guardian.py` | wisemodel检查改为minimax-cn检查 |
| `scripts/hermes_code_guard.py` | fallback切换从wisemodel互切改为minimax-cn↔siliconflow |
| `scripts/model_health.py` | check_wisemodel→check_minimax，API/Key/常量全改，v2.0→v2.1 |
| `scripts/quota_watcher.py` | wisemodel→minimax-cn，API_BASE改，v2.0→v2.1 |
| `scripts/quota_monitor.py` | 重写为v2.1，清理所有wisemodel残留 |
| `scripts/quota_tracker.py` | wisemodel→minimax-cn |
| `scripts/cron_recovery_watchdog.py` | 3处wisemodel引用→minimax-cn |
| `scripts/hermes_health_guard.py` | default改为MiniMax-M2.7 |
| `scripts/translate_tips_batch.py` | wisemodel→MiniMax-M2.7，API改api.minimaxi.com |
| `scripts/memory_loader.py` | 示例搜索词改为minimax-cn |

### auth.json
- 删除 `credential_pool.custom:wisemodel` 条目
- 剩余有效provider：minimax-cn, custom:siliconflow, custom:始智ai, minimax

---

## 3. LiteLLM相关（已删除/废弃）
- `/opt/data/configs/litellm_config.yaml` — 已删除
- `/opt/data/config/litellm_config.json` — 已删除
- `/opt/data/litellm_env/` — 已删除
- `self_upgrade.py` — 不再依赖litellm包，直接urllib调用

---

## 4. 模型路由现状（最终）

| 用途 | 模型 | provider | 说明 |
|------|------|----------|------|
| 云端主模型（用户交互） | MiniMax-M2.7 | minimax-cn | 192K context |
| 便宜简单任务 | Qwen/Qwen2.5-7B-Instruct | siliconflow | ¥0.001/1K tokens |
| 本地后台任务 | qwen2.5:3b | ollama | http://127.0.0.1:11434/v1 |
| 本地代码 | qwen2.5-coder:7b | ollama | |
| 本地知识问答 | qwen2.5:7b | ollama | |

---

## 5. 待验证（未完成检查）
- [ ] brain/thinking/thinker.py — 可能残留wisemodel引用
- [ ] MEMORY.md — 可能有wisemodel残留
- [ ] IRON_RULES.md — 可能有wisemodel残留

---

## 6. 下次启动需确认
- Gateway发消息时用的是config.yaml里的minimax-cn配置
- 所有派工板结果推送走feishu/weixin双通道
- 微信webhook配置在config.yaml的notification.weixin段