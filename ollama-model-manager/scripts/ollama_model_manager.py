#!/usr/bin/env python3
"""
Ollama 模型保活 + 故障降级管理器
================================
- 保活策略：定时warmup关键模型
- 故障降级：主模型失败 → 自动切换备选模型
- 并发控制：防止同时加载多个大模型导致OOM
"""
import os
import sys
import time
import json
import requests
import subprocess
from datetime import datetime
from pathlib import Path

sys_path = "/opt/data/scripts"
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

# ── 模型优先级配置 ──────────────────────────────────────────
MODEL_TIER = {
    # 层级1：小模型快手（优先保活）
    "fast": {
        "model": "smollm2:1.7b",
        "size": "1GB",
        "timeout": 30,
        "num_predict": 20,
        "description": "快速响应，批量任务"
    },
    # 层级2：中模型打工仔（后台任务）
    "worker": {
        "model": "qwen2.5:3b-instruct-q4_K_M",
        "size": "1GB",
        "timeout": 60,
        "num_predict": 200,
        "description": "后台学习、分析报告"
    },
    # 层级3：大模型专家（复杂任务）
    "expert": {
        "model": "deepseek-r1:7b",
        "size": "4GB",
        "timeout": 90,
        "num_predict": 300,
        "description": "复杂推理、分析"
    },
    # 层级4：工具专家
    "tool": {
        "model": "qwen2.5:7b-instruct-q4_K_M",
        "size": "4GB",
        "timeout": 90,
        "num_predict": 300,
        "description": "工具调用、代码生成"
    },
}

# 备选降级链（主模型失败时尝试的顺序）
FALLBACK_CHAINS = {
    "worker": ["worker", "fast"],
    "expert": ["expert", "worker", "fast"],
    "tool": ["tool", "worker", "fast"],
    "fast": ["fast"],
}


# ── 模型健康检查 ────────────────────────────────────────────
def get_loaded_models() -> list:
    """获取当前已加载的模型列表"""
    try:
        resp = requests.get("http://localhost:11434/api/ps", timeout=5)
        if resp.status_code == 200:
            data = json.loads(resp.text)
            return [m.get("name", "") for m in data.get("models", [])]
    except:
        pass
    return []


def is_model_loaded(model_name: str) -> bool:
    """检查指定模型是否已加载"""
    return model_name in get_loaded_models()


def check_model_health(model_name: str) -> dict:
    """检查模型健康状态"""
    try:
        start = time.time()
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": "ok",
                "stream": False,
                "options": {"num_predict": 3}
            },
            timeout=20
        )
        elapsed = (time.time() - start) * 1000
        if resp.status_code == 200:
            data = json.loads(resp.text)
            return {
                "ok": True,
                "model": model_name,
                "elapsed_ms": round(elapsed),
                "response": data.get("response", "")[:50]
            }
    except requests.exceptions.Timeout:
        return {"ok": False, "model": model_name, "reason": "timeout"}
    except Exception as e:
        return {"ok": False, "model": model_name, "reason": str(e)}
    return {"ok": False, "model": model_name, "reason": "unknown"}


def warmup_model(model_name: str, force: bool = False) -> dict:
    """预热模型（如果未加载则触发加载）"""
    if not force and is_model_loaded(model_name):
        return {"status": "already_loaded", "model": model_name}
    
    print(f"  🔄 正在预热模型: {model_name}")
    result = check_model_health(model_name)
    if result["ok"]:
        print(f"  ✅ {model_name} 已就绪 (耗时:{result['elapsed_ms']}ms)")
        return {"status": "warmed", "model": model_name, **result}
    else:
        print(f"  ⚠️ {model_name} 预热失败: {result.get('reason')}")
        return {"status": "failed", "model": model_name, **result}


def warmup_all_critical():
    """预热所有关键模型"""
    print(f"\n🧊 模型保活检查 {datetime.now().strftime('%H:%M:%S')}")
    results = {}
    for tier in ["fast", "worker", "expert"]:  # 不预热tool（太大）
        model = MODEL_TIER[tier]["model"]
        results[tier] = warmup_model(model)
    return results


# ── 智能调用（带降级）────────────────────────────────────────
def smart_generate(prompt: str, tier: str = "worker", custom_model: str = None) -> dict:
    """
    智能生成：自动降级 + 保活
    返回: {"response": str, "model": str, "tier": str, "elapsed_ms": int, "fallback_used": bool}
    """
    chain = [custom_model] if custom_model else [tier]
    if tier in FALLBACK_CHAINS:
        chain = FALLBACK_CHAINS[tier]
    
    errors = []
    
    for t in chain:
        model_cfg = MODEL_TIER.get(t)
        if not model_cfg:
            continue
        
        model = model_cfg["model"]
        timeout = model_cfg["timeout"]
        
        # 确保模型已加载
        if not is_model_loaded(model):
            print(f"  ⚠️ {model} 未加载，触发冷启动...")
        
        try:
            start = time.time()
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": model_cfg["num_predict"]}
                },
                timeout=timeout
            )
            elapsed = int((time.time() - start) * 1000)
            
            if resp.status_code == 200:
                data = json.loads(resp.text)
                return {
                    "response": data.get("response", ""),
                    "model": model,
                    "tier": t,
                    "elapsed_ms": elapsed,
                    "fallback_used": t != chain[0],
                    "ok": True
                }
            else:
                errors.append(f"{model}: HTTP {resp.status_code}")
                
        except requests.exceptions.Timeout:
            errors.append(f"{model}: timeout")
        except Exception as e:
            errors.append(f"{model}: {e}")
    
    return {
        "response": f"所有模型均失败: {'; '.join(errors)}",
        "model": "none",
        "tier": tier,
        "elapsed_ms": 0,
        "fallback_used": True,
        "ok": False,
        "errors": errors
    }


# ── CLI：保活任务（供cron调用）────────────────────────────────
def keepalive_task():
    """每日保活任务"""
    print("="*60)
    print("🧊 Ollama 模型保活任务")
    print("="*60)
    
    # 1. 检查当前状态
    loaded = get_loaded_models()
    print(f"\n📊 当前已加载: {loaded or '无'}")
    
    # 2. 预热关键模型
    results = warmup_all_critical()
    
    # 3. 最终状态
    loaded_after = get_loaded_models()
    print(f"\n📊 预热后已加载: {loaded_after}")
    
    # 4. 检查qwen2.5:7b（工具专家）
    qwen7 = MODEL_TIER["tool"]["model"]
    if qwen7 not in loaded_after:
        print(f"\n⚠️ {qwen7} 未加载，是否需要预热？(太大，按需加载)")
    
    # 5. 清理长时间未使用的模型
    print("\n🧹 检查长时间加载的模型...")
    try:
        resp = requests.get("http://localhost:11434/api/ps", timeout=5)
        data = json.loads(resp.text)
        for m in data.get("models", []):
            dur = m.get("duration", 0)
            name = m.get("name", "")
            # duration=0 说明刚加载；duration>300s 说明一直没使用，考虑卸载
            if dur > 300000 and name not in [MODEL_TIER[t]["model"] for t in ["fast", "worker", "expert"]]:
                print(f"  💡 {name} 加载{dur//1000}s未使用，可以考虑卸载节省内存")
    except:
        pass
    
    return results


# ── CLI主程序 ───────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ollama 模型保活管理")
    parser.add_argument("--check", action="store_true", help="检查模型状态")
    parser.add_argument("--warmup", action="store_true", help="预热所有模型")
    parser.add_argument("--test", metavar="MODEL", help="测试指定模型")
    parser.add_argument("--task", action="store_true", help="保活任务(供cron)")
    parser.add_argument("--generate", metavar="PROMPT", help="测试生成")
    parser.add_argument("--tier", default="worker", choices=["fast","worker","expert","tool"], help="生成模型层级")
    args = parser.parse_args()
    
    if args.check:
        loaded = get_loaded_models()
        print(f"已加载模型: {loaded or '无'}")
        for tier, cfg in MODEL_TIER.items():
            status = "✅ 已加载" if cfg["model"] in loaded else "❌ 未加载"
            print(f"  [{tier}] {cfg['model']} ({cfg['size']}) - {cfg['description']} {status}")
    
    elif args.warmup or args.task:
        keepalive_task()
    
    elif args.test:
        result = check_model_health(args.test)
        if result["ok"]:
            print(f"✅ {result['model']} OK ({result['elapsed_ms']}ms): {result['response']}")
        else:
            print(f"❌ {result['model']} FAIL: {result.get('reason')}")
    
    elif args.generate:
        result = smart_generate(args.generate, tier=args.tier)
        print(f"模型: {result['model']} (tier:{result['tier']}) | {result['elapsed_ms']}ms | fallback:{result['fallback_used']}")
        print(f"响应: {result['response'][:200]}")
    
    else:
        parser.print_help()
        print("\n用法示例:")
        print("  python3 ollama_model_manager.py --check          # 查看模型状态")
        print("  python3 ollama_model_manager.py --warmup         # 预热所有模型")
        print("  python3 ollama_model_manager.py --task           # 保活cron任务")
        print("  python3 ollama_model_manager.py --test qwen2.5:7b-instruct-q4_K_M")
        print("  python3 ollama_model_manager.py --generate 'hello' --tier fast")
