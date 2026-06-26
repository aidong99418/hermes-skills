#!/usr/bin/env python3
"""
Blueprint report pusher — sends report to 董哥 via gateway weixin platform.
已验证可用：2026-06-11
"""
import asyncio
import json
import sys
import os

# Add hermes to path (cron env has no hermes_tools)
sys.path.insert(0, "/opt/hermes")
os.chdir("/opt/hermes")

async def push_report():
    from gateway.platforms.weixin import send_weixin_direct

    # Read the report
    report_path = "/opt/data/cron/output/blueprint_report.json"
    try:
        with open(report_path) as f:
            data = json.load(f)
        report_text = data.get("report", "无报告内容")
    except Exception as e:
        report_text = f"读取报告失败: {e}"

    # Resolve chat_id
    extra, token, chat_id = {}, None, None

    # Priority 1: channel_directory.json
    try:
        ch_dir = os.path.expanduser("~/.hermes/channel_directory.json")
        with open(ch_dir) as f:
            cd = json.load(f)
        for name, info in cd.items():
            if "weixin" in name.lower() or "wechat" in name.lower():
                chat_id = info.get("chat_id") or info.get("id")
                if chat_id:
                    break
    except Exception:
        pass

    # Priority 2: bot.json glob
    if not chat_id:
        import glob
        for bot_cfg in glob.glob("/opt/data/weixin/accounts/*@im.bot.json"):
            try:
                data = json.loads(open(bot_cfg).read())
                token = data.get("token")
                chat_id = data.get("user_id", "").split("@")[0]
                break
            except Exception:
                continue

    # Priority 3: filehelper (always works)
    if not chat_id:
        chat_id = "filehelper"

    result = await send_weixin_direct(
        extra=extra,
        token=token,
        chat_id=chat_id,
        message=report_text,
    )
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    asyncio.run(push_report())
