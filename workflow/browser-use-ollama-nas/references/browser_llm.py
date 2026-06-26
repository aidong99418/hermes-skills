#!/usr/bin/env python3
"""
browser-use Ollama 适配器
create_browser_llm() — 给ChatOllama注入browser-use需要的provider/model_name属性
run_browser_task() — 同步入口，一行执行浏览器任务
"""
import asyncio, os
from langchain_ollama import ChatOllama


def create_browser_llm(model=None, base_url="http://localhost:11434", num_ctx=8192):
    """兼容browser-use的Ollama实例（属性注入）"""
    model = model or os.environ.get("BROWSER_MODEL", "qwen2.5:3b")
    llm = ChatOllama(model=model, base_url=base_url, num_ctx=num_ctx)
    object.__setattr__(llm, 'provider', 'ollama')
    object.__setattr__(llm, 'model_name', model)
    return llm


def run_browser_task(task, model=None, max_steps=10, **kwargs):
    """同步执行browser-use任务"""
    from browser_use import Agent
    from browser_use.browser.session import BrowserSession
    llm = create_browser_llm(model=model)
    session = BrowserSession(enable_default_extensions=False)

    async def _run():
        return await Agent(
            task=task, llm=llm, browser_session=session,
            max_steps=max_steps, use_vision=False,
            max_actions_per_step=3, enable_planning=False, **kwargs
        ).run()

    return asyncio.run(_run())


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python browser_llm.py \"任务描述\"")
        sys.exit(1)
    print(f"🚀 {sys.argv[1]}")
    print(run_browser_task(sys.argv[1]))
