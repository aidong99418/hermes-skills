#!/usr/bin/env python3
"""
skill_neural去重验证脚本
触发：skills目录守护cron / 手动诊断 / 自动修复

逻辑：
1. 扫描所有skills/下的SKILL.md，提取name+version+mtime
2. 同名skill只保留：version最新 > mtime最新 的优先版本
3. 输出去重决策报告
4. 对skill_neural.json做同样检查
"""

import os
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

SKILLS_ROOT = Path("/opt/data/skills")
SKILL_NEURAL = Path("/opt/data/skill_neural.json")
SNAP_DIR = Path("/opt/data/skill_neural.snap")


def extract_skill_info(skill_dir: Path) -> dict:
    """从skill目录提取name和version"""
    meta = {
        "name": None,
        "version": None,
        "path": str(skill_dir),
        "mtime": 0,
    }
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        meta["mtime"] = skill_md.stat().st_mtime
        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception:
            content = ""
        # 提取name
        n = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
        if n:
            meta["name"] = n.group(1).strip()
        # 提取version
        v = re.search(r"^version:\s*(.+)$", content, re.MULTILINE)
        if v:
            meta["version"] = v.group(1).strip()
    return meta


def scan_all_skills():
    """递归扫描所有skill目录（顶层+子目录）"""
    skills = {}
    # 顶层
    for skill_dir in SKILLS_ROOT.glob("*"):
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            info = extract_skill_info(skill_dir)
            if info["name"]:
                skills.setdefault(info["name"], []).append(info)
    # 子目录（知识子目录）
    for skill_dir in SKILLS_ROOT.glob("*/*/"):
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            info = extract_skill_info(skill_dir)
            if info["name"]:
                skills.setdefault(info["name"], []).append(info)
    return skills


def get_version_score(v: str) -> int:
    """version分数：None=0, 数字越大越高"""
    if not v:
        return 0
    try:
        parts = [int(x) for x in v.lstrip("v").split(".")]
        return sum(p * (10 ** (2 - i)) for i, p in enumerate(parts))
    except Exception:
        return 0


def find_duplicates():
    """找出所有重复skill，返回去重决策"""
    all_skills = scan_all_skills()
    decisions = {}
    for name, instances in all_skills.items():
        if len(instances) == 1:
            continue
        # 排序：version降序 > mtime降序
        instances.sort(
            key=lambda x: (get_version_score(x["version"]), x["mtime"]),
            reverse=True,
        )
        winner = instances[0]
        losers = instances[1:]
        decisions[name] = {
            "winner": winner,
            "losers": losers,
            "count": len(instances),
        }
    return decisions


def verify_skill_neural_dedup():
    """检查skill_neural.json是否有重复的skill节点"""
    if not SKILL_NEURAL.exists():
        return {"error": "skill_neural.json不存在"}
    try:
        data = json.loads(SKILL_NEURAL.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"读取失败: {e}"}
    nodes = data.get("nodes", [])
    skill_nodes = [n for n in nodes if n.get("type") == "skill"]

    # 同名skill节点计数
    name_count = {}
    for n in skill_nodes:
        name = n.get("name")
        if name:
            name_count.setdefault(name, []).append(n)

    duplicates = {name: ns for name, ns in name_count.items() if len(ns) > 1}
    return {
        "total_skill_nodes": len(skill_nodes),
        "total_nodes": len(nodes),
        "duplicates": duplicates,
    }


def auto_backup_and_remove(loser_paths: list, dry_run: bool = False) -> dict:
    """
    备份并删除loser skill目录
    返回：{"backup_dir": str, "removed": list, "failed": list}
    """
    date_str = datetime.now().strftime("%Y%m%d")
    backup_dir = SNAP_DIR / "dedup_backup" / date_str
    backup_dir.mkdir(parents=True, exist_ok=True)

    removed = []
    failed = []
    for path_str in loser_paths:
        p = Path(path_str)
        if not p.exists():
            failed.append({"path": path_str, "reason": "目录不存在"})
            continue
        skill_name = p.name
        dest = backup_dir / skill_name
        try:
            if not dry_run:
                shutil.move(str(p), str(dest))
            removed.append(path_str)
        except Exception as e:
            failed.append({"path": path_str, "reason": str(e)})
    return {"backup_dir": str(backup_dir), "removed": removed, "failed": failed}


def main():
    print("=" * 60)
    print("🔍 skill_neural 去重验证报告")
    print("=" * 60)

    # 检查重复skill
    decisions = find_duplicates()
    if not decisions:
        print("\n✅ skills目录：无重复")
    else:
        print(f"\n⚠️  发现 {len(decisions)} 对重复skill：\n")
        for name, d in decisions.items():
            print(f"  【{name}】共 {d['count']} 个版本:")
            print(f"  ✅ 保留: {d['winner']['path']}")
            print(
                f"     version={d['winner']['version'] or '无'}, "
                f"mtime={datetime.fromtimestamp(d['winner']['mtime']).strftime('%m-%d %H:%M')}"
            )
            for loser in d["losers"]:
                print(f"  ❌ 删除: {loser['path']}")
                print(
                    f"     version={loser['version'] or '无'}, "
                    f"mtime={datetime.fromtimestamp(loser['mtime']).strftime('%m-%d %H:%M')}"
                )
            print()

        # 自动修复选项
        all_losers = []
        for d in decisions.values():
            all_losers.extend([l["path"] for l in d["losers"]])

        result = auto_backup_and_remove(all_losers)
        print(f"  📦 备份目录: {result['backup_dir']}")
        print(f"  ✅ 已移除: {len(result['removed'])} 个")
        if result["failed"]:
            print(f"  ❌ 失败: {len(result['failed'])} 个")
            for f in result["failed"]:
                print(f"     {f['path']}: {f['reason']}")

    # 检查skill_neural.json
    neural = verify_skill_neural_dedup()
    if "error" in neural:
        print(f"\n⚠️  skill_neural: {neural['error']}")
    elif not neural["duplicates"]:
        print(
            f"\n✅ skill_neural.json：{neural['total_skill_nodes']} 个skill节点 / "
            f"{neural['total_nodes']} 总节点，无重复"
        )
    else:
        print(
            f"\n⚠️  skill_neural.json：{neural['total_skill_nodes']} skill节点，"
            f"发现 {len(neural['duplicates'])} 个重复：\n"
        )
        for name, nodes in neural["duplicates"].items():
            print(f"  【{name}】出现 {len(nodes)} 次:")
            for n in nodes:
                nid = n.get("id", "unknown")
                npath = n.get("path", "")
                print(f"    - id={nid} path={npath}")

    print("\n" + "=" * 60)
    print("✅ 检查完成")


if __name__ == "__main__":
    main()
