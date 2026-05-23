#!/usr/bin/env python3
"""
Multi-Agent Crew 调度框架 v1.0
===============================
基于 Ollama 的本地多Agent并行/串行调度。
零外部依赖，只用标准库 + requests。

用法:
    python3 multi_agent_crew.py --demo           # 运行演示
    python3 multi_agent_crew.py --demo-parallel  # 并行演示
    python3 multi_agent_crew.py --benchmark      # 内存/速度基准测试
    # 或作为模块导入使用（见 SKILL.md）
"""
import json
import time
import copy
import uuid
import queue
import signal
import inspect
import concurrent.futures as cf
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum
import requests

# ── 全局配置 ──────────────────────────────────────────────
OLLAMA_BASE = "http://localhost:11434"
KEEP_ALIVE = "5m"
REQUEST_TIMEOUT = 60

# ── 内置 ModelStrategy ─────────────────────────────────────
DEFAULT_STRATEGY = {
    "quick":    "smollm2:1.7b",
    "normal":   "qwen2.5:3b",
    "heavy":    "qwen2.5:7b",
    "critical": "deepseek-r1:7b",
}

# ── 内存基准（估算值，MB）──────────────────────────────────
MODEL_MEMORY = {
    "smollm2:1.7b":    1200,
    "qwen2.5:3b":      3500,
    "qwen2.5:7b":      7500,
    "deepseek-r1:7b":  7500,
    "llama3.2":        2000,
}

# ══════════════════════════════════════════════════════════
# 数据模型
# ══════════════════════════════════════════════════════════

class Process(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HYBRID = "hybrid"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class Agent:
    id: str
    role: str
    system: str = ""
    model: str = ""
    strategy: dict = field(default_factory=lambda: DEFAULT_STRATEGY)
    tier: str = "normal"
    max_retries: int = 2
    timeout: int = 30

    def get_model(self) -> str:
        if self.model:
            return self.model
        return self.strategy.get(self.tier, "qwen2.5:3b")

@dataclass
class Task:
    id: str
    description: str
    agent_id: str
    depends_on: list = field(default_factory=list)
    context_template: dict = field(default_factory=dict)
    on_fail: str = "retry"          # retry | skip | abort
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""

# ══════════════════════════════════════════════════════════
# 核心引擎
# ══════════════════════════════════════════════════════════

class Crew:
    """
    多Agent调度器。

    参数:
        agents:         Agent 实例列表
        tasks:          Task 实例列表
        process:        Process.PARALLEL | SEQUENTIAL | HYBRID
        ollama_base:    Ollama 服务地址
        keep_alive:     模型常驻时间
        max_workers:    并行线程数
        verbose:        是否打印日志
        on_task_start:  任务开始回调 (task_id -> None)
        on_task_result: 任务完成回调 (task_id, result -> None)
        on_complete:    全部完成回调 (dict -> None)
    """

    def __init__(
        self,
        agents: list,
        tasks: list,
        process: Process = Process.PARALLEL,
        ollama_base: str = OLLAMA_BASE,
        keep_alive: str = KEEP_ALIVE,
        max_workers: int = 3,
        verbose: bool = True,
        on_task_start: Optional[Callable] = None,
        on_task_result: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
    ):
        self.agents = {a.id: a for a in agents}
        self.tasks = {t.id: t for t in tasks}
        self.process = process
        self.base = ollama_base
        self.keep_alive = keep_alive
        self.max_workers = max_workers
        self.verbose = verbose
        self._hooks = {
            "on_task_start": on_task_start or (lambda _: None),
            "on_task_result": on_task_result or (lambda _, __: None),
            "on_complete": on_complete or (lambda _: None),
        }
        # 运行时状态
        self._results: dict[str, Any] = {}
        self._active_models: set[str] = set()
        self._executor: Optional[cf.ThreadPoolExecutor] = None

    # ── Ollama 调用 ─────────────────────────────────────────
    def _call_llm(self, agent: Agent, prompt: str) -> str:
        """调用 Ollama，返回文本响应"""
        model = agent.get_model()
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 2048},
            "keep_alive": self.keep_alive,
        }

        for attempt in range(agent.max_retries + 1):
            try:
                r = requests.post(
                    f"{self.base}/api/generate",
                    json=payload,
                    timeout=agent.timeout,
                )
                r.raise_for_status()
                return r.json().get("response", "").strip()

            except requests.exceptions.Timeout:
                if attempt < agent.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"[{agent.id}] 超时 ({agent.timeout}s)")

            except requests.exceptions.ConnectionError:
                # Ollama 未启动
                raise RuntimeError(f"[{agent.id}] Ollama 连接失败，请检查服务")

            except Exception as e:
                if attempt < agent.max_retries:
                    time.sleep(1)
                    continue
                raise RuntimeError(f"[{agent.id}] 请求失败: {e}")

        return ""

    def _build_prompt(self, task: Task, agent: Agent, context: dict) -> str:
        """组装完整 prompt"""
        # 1. 插入依赖结果
        deps_context = ""
        for dep_id in task.depends_on:
            dep_result = self._results.get(dep_id, "")
            if dep_result:
                deps_context += f"\n\n[上游任务 '{dep_id}' 的结果]\n{dep_result}\n"

        # 2. 模板插值
        template_vars = {**context, **task.context_template}
        desc = task.description
        for key, val in template_vars.items():
            desc = desc.replace(f"{{{key}}}", str(val))

        # 3. 组装完整 prompt
        parts = []
        if agent.system:
            parts.append(f"<system>{agent.system}</system>")
        if deps_context:
            parts.append(f"<context>{deps_context}</context>")
        parts.append(f"<task>{desc}</task>")
        return "\n".join(parts)

    # ── 单任务执行 ─────────────────────────────────────────
    def _execute_task(self, task: Task, context: dict) -> tuple[str, Any]:
        """执行单个任务，返回 (task_id, result)"""
        self._hooks["on_task_start"](task.id)
        task.status = TaskStatus.RUNNING

        agent = self.agents.get(task.agent_id)
        if not agent:
            raise ValueError(f"Agent '{task.agent_id}' 不存在")

        if self.verbose:
            model = agent.get_model()
            print(f"  ▶ [{task.id}] → {agent.role} ({model})")

        prompt = self._build_prompt(task, agent, context)
        result = self._call_llm(agent, prompt)

        task.result = result
        task.status = TaskStatus.DONE
        self._results[task.id] = result
        self._hooks["on_task_result"](task.id, result)

        return task.id, result

    # ── 任务拓扑排序 ───────────────────────────────────────
    def _topo_sort(self) -> list[Task]:
        """Kahn算法拓扑排序，检测循环依赖"""
        in_deg = {tid: 0 for tid in self.tasks}
        for t in self.tasks.values():
            for dep in t.depends_on:
                in_deg[t.id] += 1

        queue = [tid for tid, deg in in_deg.items() if deg == 0]
        sorted_ids = []

        while queue:
            tid = queue.pop(0)
            sorted_ids.append(tid)
            for other in self.tasks.values():
                if tid in other.depends_on:
                    in_deg[other.id] -= 1
                    if in_deg[other.id] == 0:
                        queue.append(other.id)

        # 检测循环
        if len(sorted_ids) != len(self.tasks):
            raise ValueError("任务存在循环依赖！")

        return [self.tasks[tid] for tid in sorted_ids]

    # ── 依赖就绪判断 ───────────────────────────────────────
    def _deps_ready(self, task: Task) -> bool:
        return all(
            self.tasks.get(dep_id, Task(id=dep_id, description="", agent_id="")).status == TaskStatus.DONE
            for dep_id in task.depends_on
        )

    # ── 主要入口 ───────────────────────────────────────────
    def kickoff(self, context: dict = None) -> dict[str, Any]:
        """
        执行所有任务，返回 {task_id: result} 字典。

        参数:
            context: 全局上下文变量，用于模板插值
        """
        context = context or {}
        self._results = {}
        sorted_tasks = self._topo_sort()

        if self.verbose:
            print(f"\n{'='*50}")
            print(f"🚀 Crew 启动 | Process: {self.process.value}")
            print(f"   Agents: {list(self.agents.keys())}")
            print(f"   Tasks:  {list(self.tasks.keys())}")
            print(f"{'='*50}")

        start_time = time.time()

        if self.process == Process.PARALLEL:
            self._run_parallel(sorted_tasks, context)
        else:
            self._run_sequential(sorted_tasks, context)

        elapsed = time.time() - start_time

        if self.verbose:
            done = sum(1 for t in self.tasks.values() if t.status == TaskStatus.DONE)
            failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
            print(f"\n{'='*50}")
            print(f"✅ 完成 | 耗时 {elapsed:.1f}s | 成功 {done} | 失败 {failed}")
            print(f"{'='*50}")

        self._hooks["on_complete"](self._results)
        return self._results

    def _run_sequential(self, tasks: list[Task], context: dict):
        """串行执行（尊重依赖顺序）"""
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]

        while pending:
            ready = [t for t in pending if self._deps_ready(t)]
            if not ready:
                # 没有就绪任务但还有pending → 死锁（不应发生）
                break

            for task in ready:
                self._execute_task_safe(task, context)
                pending.remove(task)

    def _run_parallel(self, tasks: list[Task], context: dict):
        """并行执行（自动等待依赖完成）"""
        pending = list(tasks)
        running = []
        completed = set()

        while pending or running:
            # 找就绪任务
            for task in pending[:]:
                if self._deps_ready(task):
                    # 提交到线程池
                    future = self._executor_submit(task, context)
                    running.append((task, future))
                    pending.remove(task)

            # 收集完成的任务
            still_running = []
            for task, future in running:
                if future.done():
                    try:
                        _, _ = future.result()
                        completed.add(task.id)
                    except Exception as e:
                        self._handle_task_error(task, e, context)
                else:
                    still_running.append((task, future))
            running = still_running

            # 防止忙等待
            if pending and not running:
                time.sleep(0.1)

    def _executor_submit(self, task: Task, context: dict):
        if self._executor is None:
            self._executor = cf.ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor.submit(self._execute_task, task, context)

    def _execute_task_safe(self, task: Task, context: dict):
        try:
            self._execute_task(task, context)
        except Exception as e:
            self._handle_task_error(task, e, context)

    def _handle_task_error(self, task: Task, error: Exception, context: dict):
        task.status = TaskStatus.FAILED
        task.error = str(error)
        if self.verbose:
            print(f"  ❌ [{task.id}] 失败: {error}")

        if task.on_fail == "abort":
            raise error
        elif task.on_fail == "skip":
            task.status = TaskStatus.SKIPPED
            self._results[task.id] = None
        # on_fail == "retry" → 在下次机会重试（此处简化为打印）

    def kickoff_final(self, context: dict = None) -> str:
        """只返回最后一个任务的结果"""
        results = self.kickoff(context)
        done = [t for t in self.tasks.values() if t.status == TaskStatus.DONE]
        if done:
            return done[-1].result or ""
        return ""

    def memory_snapshot(self) -> dict:
        """当前内存使用快照"""
        import resource
        import os
        mem = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "rss_mb": mem.ru_maxrss / 1024,
            "page_size": os.sysconf("SC_PAGE_SIZE") if hasattr(os, 'sysconf') else 4096,
        }

    def __del__(self):
        if self._executor:
            self._executor.shutdown(wait=False)


# ══════════════════════════════════════════════════════════
# 快捷函数（不用显式建 Crew 对象）
# ══════════════════════════════════════════════════════════

def quick_crew(
    tasks: list[dict],
    strategy: dict = None,
    process: Process = Process.PARALLEL,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    一行调用多Agent。

    tasks 格式:
    [
        {"id": "t1", "description": "任务描述", "role": "研究员",
         "system": "系统提示", "tier": "normal"},
        {"id": "t2", "description": "另一任务", "role": "编辑",
         "depends_on": ["t1"]},
    ]

    示例:
    results = quick_crew([
        {"id": "analyze", "description": "分析{topic}数据", "role": "分析师",
         "system": "你是一名数据分析师", "tier": "normal"},
        {"id": "report", "description": "写报告", "role": "编辑",
         "depends_on": ["analyze"], "tier": "heavy"},
    ], {"topic": "Q2销售"})
    """
    strategy = strategy or DEFAULT_STRATEGY

    agents_map = {}
    for t in tasks:
        rid = t["role"]
        if rid not in agents_map:
            agents_map[rid] = Agent(
                id=rid,
                role=rid,
                system=t.get("system", ""),
                tier=t.get("tier", "normal"),
                strategy=strategy,
                timeout=t.get("timeout", 30),
            )

    task_objs = []
    for t in tasks:
        task_objs.append(Task(
            id=t["id"],
            description=t["description"],
            agent_id=t["role"],
            depends_on=t.get("depends_on", []),
        ))

    crew = Crew(
        agents=list(agents_map.values()),
        tasks=task_objs,
        process=process,
        verbose=verbose,
    )
    return crew.kickoff()


# ══════════════════════════════════════════════════════════
# CLI / 演示
# ══════════════════════════════════════════════════════════

def demo_sequential():
    """演示：串行任务链（先搜→再分析→再写）"""
    print("\n" + "═"*60)
    print("📌 演示1: 串行任务链")
    print("═"*60)

    tasks = [
        {"id": "search", "description": "搜索关于AI大模型最新进展的新闻，列出5条",
         "role": "研究员", "system": "你是一名科技记者，收集最新资讯。", "tier": "normal"},
        {"id": "analyze", "description": "分析以下新闻，找出3个关键趋势：\n{search}",
         "role": "分析师", "system": "你是一名行业分析师，洞察趋势。", "tier": "heavy",
         "depends_on": ["search"]},
        {"id": "write", "description": "把以下分析写成一篇500字的科技报道：\n{analyze}",
         "role": "编辑", "system": "你是一名科技编辑，文笔通俗。", "tier": "heavy",
         "depends_on": ["analyze"]},
    ]

    results = quick_crew(tasks, process=Process.SEQUENTIAL)
    print("\n📄 最终报告:")
    print(results.get("write", "无结果"))


def demo_parallel():
    """演示：并行多Agent同时工作"""
    print("\n" + "═"*60)
    print("📌 演示2: 并行多Agent（3个研究员同时搜）")
    print("═"*60)

    tasks = [
        {"id": "tech", "description": "搜索AI领域的最新技术突破，列出3条",
         "role": "AI研究员", "system": "你专注于AI技术。", "tier": "quick"},
        {"id": "market", "description": "搜索AI市场投资动态，列出3条",
         "role": "市场研究员", "system": "你专注于AI投资市场。", "tier": "quick"},
        {"id": "policy", "description": "搜索AI监管政策新闻，列出3条",
         "role": "政策研究员", "system": "你专注于AI政策法规。", "tier": "quick"},
        {"id": "summarize", "description": "汇总以下三份研究报告，写成一篇综合摘要，每份一个重点：\ntech:{tech}\nmarket:{market}\npolicy:{policy}",
         "role": "总编辑", "system": "你擅长综合归纳。", "tier": "heavy",
         "depends_on": ["tech", "market", "policy"]},
    ]

    results = quick_crew(tasks, process=Process.SEQUENTIAL)
    print("\n📄 综合摘要:")
    print(results.get("summarize", "无结果"))


def benchmark():
    """内存/速度基准测试"""
    print("\n" + "═"*60)
    print("⚡ 基准测试")
    print("═"*60)

    import resource
    import os

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB

    # 单Agent任务
    start = time.time()
    r = quick_crew([{
        "id": "test",
        "description": "用3句话解释量子计算",
        "role": "专家",
        "system": "你是一名物理学家。",
        "tier": "normal",
    }], verbose=False)
    elapsed = time.time() - start

    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    print(f"  模型: qwen2.5:3b")
    print(f"  延迟: {elapsed:.1f}s")
    print(f"  内存增量: {after - before:.1f} MB")
    print(f"  结果: {r.get('test', '')[:100]}")


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "--demo"

    if cmd == "--demo":
        demo_sequential()
    elif cmd == "--demo-parallel":
        demo_parallel()
    elif cmd == "--benchmark":
        benchmark()
    else:
        print(f"用法: {sys.argv[0]} [--demo|--demo-parallel|--benchmark]")
