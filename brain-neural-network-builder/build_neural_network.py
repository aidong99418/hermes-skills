#!/usr/bin/env python3
"""
Brain神经网络构建脚本 v3.0
===========================
扫描brain文档 + skills → 生成neural网络数据文件

用法:
    python3 build_neural_network.py          # 全量重建
    python3 build_neural_network.py --dry    # 预览不写入
"""
import json, re, datetime
from pathlib import Path

# ── 路径配置 ────────────────────────────────────────────────────
BRAIN_DIR      = Path("/opt/data/brain")
NEURAL_DIR     = Path("/opt/data/brain/neural")
SKILL_DIR      = Path("/opt/data/skills")
EXTERNAL_SKILLS= Path("/opt/data/external-skills")
DRY_RUN        = "--dry" in __import__("sys").argv

# ── 创建neural目录 ──────────────────────────────────────────────
NEURAL_DIR.mkdir(parents=True, exist_ok=True)

# ── Keywords噪音词表 ────────────────────────────────────────────
NOISE_KEYWORDS = {
    'api','url','http','https','tool','task','goal','result','file','path','dir',
    'true','false','none','null','void','test','impl','code','data','node','name',
    'type','desc','raw','help','root','sys','opt','tmp','var','src','lib','bin',
    'etc','run','pid','git','md','txt','json','yaml','yml','toml','env','cfg',
    'id','ref','idx','len','avg','min','max','sum','key','val','cnt',
    'num','str','int','bool','obj','arr','cls','fun','ret','arg','log',
    'req','res','err','msg','hdr','frm','to','db','sql','sqlite',
    'description','skill','skill.md','trigger','triggers',
    'from','this','that','which','with','have','has','been','being',
    'section','来源','完整内容','查询','常用','结果','changed',
    'operation','templates','manage','raw','source','sha',
    'version','created','updated',
    'div','and','the','for','use','when','you','are','can','not','but',
    'get','set','put','let','run','see','new','old','all','any','out',
    'one','two','top','end','big','say','ask','try','way',
}

# ── 工具函数 ────────────────────────────────────────────────────
def to_id(name: str) -> str:
    """统一转为 hyphen-separated lowercase ID"""
    return name.replace('_', '-').lower()

def safe_read(path: Path) -> str:
    """安全读取文件，自动处理编码"""
    for enc in ('utf-8', 'gbk', 'latin-1'):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return ""

def clean_keywords(text: str, max_kw: int = 10) -> list:
    """从文本提取清洗后的keywords"""
    chinese = re.findall(r'[\u4e00-\u9fff]{2,8}', text)
    english = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]{2,20}\b', text)
    seen, cleaned = set(), []
    for kw in chinese + english:
        k = kw.lower()
        if (k not in seen and k not in NOISE_KEYWORDS
            and not k.isdigit() and len(k) >= 2):
            seen.add(k)
            cleaned.append(kw if re.match(r'[\u4e00-\u9fff]', kw) else kw.lower())
        if len(cleaned) >= max_kw:
            break
    return cleaned

def extract_description(content: str, max_chars: int = 150) -> str:
    """提取前N个非markdown字符作为description"""
    lines, in_code = [], False
    for line in content.split('\n'):
        if line.strip().startswith('```'):
            in_code = not in_code
        if not in_code and line.strip() and not line.strip().startswith('#'):
            lines.append(line.strip())
        if len('\n'.join(lines)) > max_chars:
            break
    return re.sub(r'[#*_`>|\[\]()\-]', '', '\n'.join(lines)).strip()[:max_chars]

def extract_triggers(content: str, skill_name: str) -> list:
    """从frontmatter + 名称推断触发词"""
    triggers = []
    # frontmatter triggers字段
    for block in re.findall(r'triggers:\s*\n((?:\s*-\s*.+\n)+)', content):
        for line in block.strip().split('\n'):
            m = re.match(r'-\s*(.+)', line)
            if m:
                triggers.append(m.group(1).strip().rstrip(','))
    # 名称分词
    for w in re.findall(r'[a-z]{3,}', skill_name.lower()):
        if w not in {'the','for','and','you','are','can','not','but','get','set','out','new','old','all'}:
            triggers.append(w)
    return list(dict.fromkeys([t for t in triggers if len(t) >= 2]))[:8]

def infer_activates(skill_name: str) -> list:
    """根据skill名称推断激活的brain节点"""
    maps = {
        'brain': ['brain-retriever', 'brain-core-principles', 'brain-thinker'],
        'ollama': ['ollama-model-tiers', 'ollama-platform-ecosystem'],
        'tdd': ['tdd-engineering'],
        'security': ['lcguard-multiagent-security', 'security-auditor'],
        'video': ['theme-factory'],
        'creative': ['taste-design-principles'],
        'research': ['deer-flow-harness', 'external-fetcher'],
        'github': ['git-learning-workflow'],
        'cron': ['cron-silent-mode'],
        'mcp': ['mcp-integration'],
        'model': ['model-tier-system', 'ollama-python-sdk'],
        'auto-learning': ['auto-learning'],
    }
    for cat, targets in maps.items():
        if cat in skill_name.lower():
            return targets
    return ['brain-retriever', 'brain-core-principles']

# ── Phase 1: 扫描Brain文档 ──────────────────────────────────────
def scan_brain_docs():
    nodes = []
    seen_ids = {}  # id -> first occurrence
    cat_map = {
        'principles': 'principle', 'knowledge': 'knowledge',
        'reasoning_pattern': 'reasoning_pattern', 'workflow': 'workflow',
        'tool_templates': 'tool_template', 'architecture': 'architecture',
    }
    for subdir, cat_type in cat_map.items():
        dp = BRAIN_DIR / subdir
        if not dp.exists(): continue
        for mf in dp.glob("*.md"):
            raw_id = mf.stem
            node_id = to_id(raw_id)
            content = safe_read(mf)
            desc = extract_description(content)
            name_text = raw_id.replace('-', ' ').replace('_', ' ')
            kw = clean_keywords(desc + ' ' + name_text)

            # 同ID不同目录：加category前缀去重
            if node_id in seen_ids:
                node_id = f"{cat_type}-{node_id}"

            seen_ids[node_id] = True
            nodes.append({
                'id': node_id, 'type': 'brain_doc', 'name': node_id,
                'file': f'{subdir}/{mf.name}', 'keywords': kw,
                'description': desc, 'category': cat_type,
                'confidence': 0.5, 'usage_count': 0, 'last_used': None,
                'source': 'brain',
            })
    return nodes

# ── Phase 2: 扫描Skills ─────────────────────────────────────────
def scan_skills():
    nodes = []
    seen_ids = set()
    for base_dir, src in [(SKILL_DIR, 'skills'), (EXTERNAL_SKILLS, 'external-skills')]:
        if not base_dir.exists(): continue
        for sp in base_dir.glob("*"):
            if not sp.is_dir(): continue
            sm = sp / "SKILL.md"
            if not sm.exists(): continue
            raw_name = sp.name
            node_id = to_id(raw_name)
            if node_id in seen_ids:
                node_id = f"{src[:3]}-{node_id}"
            seen_ids.add(node_id)
            content = safe_read(sm)
            desc = extract_description(content)
            trig = extract_triggers(content, raw_name)
            act = infer_activates(node_id)
            kw = clean_keywords(desc + ' ' + raw_name)
            nodes.append({
                'name': node_id, 'triggers': trig, 'activates_nodes': act,
                'strengthens': [], 'file': f'{src}/{raw_name}/SKILL.md',
                'source': src, 'min_tier': 1, 'description': desc, 'keywords': kw,
                'id': node_id, 'type': 'skill',
            })
    return nodes

# ── Phase 3: 生成Connections ────────────────────────────────────
def generate_connections(all_nodes: list) -> list:
    node_ids = {n['id'] for n in all_nodes}
    connections = []

    # 同category全连接
    for cat in set(n.get('category','') for n in all_nodes if n['type'] == 'brain_doc'):
        cat_ids = [n['id'] for n in all_nodes if n.get('category') == cat]
        for i, a in enumerate(cat_ids):
            for b in cat_ids[i+1:]:
                connections.append({'from': a, 'to': b, 'weight': 0.6, 'reason': f'同类别{cat}'})

    # skill → activates_nodes
    for s in all_nodes:
        if s['type'] != 'skill': continue
        for target in s.get('activates_nodes', []):
            if target in node_ids:
                connections.append({'from': s['id'], 'to': target, 'weight': 0.7, 'reason': 'skill激活'})

    # 同source skill全连接
    skill_by_source = {}
    for s in all_nodes:
        if s['type'] == 'skill':
            skill_by_source.setdefault(s['source'], []).append(s['id'])
    for src, names in skill_by_source.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                connections.append({'from': a, 'to': b, 'weight': 0.4, 'reason': f'skill同源'})

    # 核心手工连接
    core = [
        ('brain-thinker', 'brain-retriever', 0.9, '核心思考链路'),
        ('brain-retriever', 'brain-core-principles', 0.9, '检索→原则'),
        ('ollama-model-tiers', 'ollama-platform-ecosystem', 0.9, '模型体系'),
        ('ollama-model-tiers', 'ollama-python-sdk', 0.8, '模型→SDK'),
        ('tdd-engineering', 'prototype-branching', 0.8, 'TDD→原型分支'),
        ('collaborative-protocol', 'hook-automation', 0.8, '协作→钩子'),
        ('deer-flow-harness', 'external-fetcher', 0.8, 'DeerFlow→外部获取'),
        ('mcp-integration', 'mcp-builder', 0.9, 'MCP集成'),
        ('cron-silent-mode', 'git-learning-workflow', 0.7, '静默→学习流'),
        ('machine-cat-guardian', 'ollama-brain-teacher', 0.7, '守护→教学'),
        ('lcguard-multiagent-security', 'multi-agent-patterns', 0.8, '安全→多Agent'),
        ('brain-system-integration', 'brain-team-architecture', 0.9, '系统→团队架构'),
        ('skill-creator', 'tdd', 0.7, '创建→TDD'),
        ('taste-design-principles', 'frontend-design', 0.8, '审美→前端'),
        ('auto-learning', 'external-fetcher', 0.8, '自动学习→外部获取'),
        ('ollama-auto-learning-debug', 'ollama-model-tiers', 0.8, '学习调试→模型层'),
    ]
    for from_, to, w, reason in core:
        if from_ in node_ids and to in node_ids:
            connections.append({'from': from_, 'to': to, 'weight': w, 'reason': reason})

    # 去重（相同from-to只留最高权重）
    conn_seen = {}
    for c in connections:
        key = (c['from'], c['to'])
        if key not in conn_seen or c['weight'] > conn_seen[key]['weight']:
            conn_seen[key] = c
    return list(conn_seen.values())

# ── Phase 4: 推理路径 ───────────────────────────────────────────
def build_inference_paths(node_ids: set) -> list:
    """构建推理路径（引用实际存在的节点ID）"""
    valid = lambda n: n in node_ids
    paths = [
        {'trigger': 'Ollama模型调用失败', 'tier': 2,
         'path': [n for n in ['ollama-model-tiers', 'ollama-python-sdk', 'ollama-auto-learning-debug'] if valid(n)],
         'action': '1.检查服务 2.端口11434 3.pull模型 4.ERROR日志'},
        {'trigger': '脚本KeyError崩溃', 'tier': 1,
         'path': [n for n in ['tdd', 'tdd-engineering', 'prototype-branching'] if valid(n)],
         'action': '1..get()安全访问 2.try/except 3.写进brain'},
        {'trigger': '需要写新脚本', 'tier': 1,
         'path': [n for n in ['skill-creator', 'tdd', 'tdd-engineering'] if valid(n)],
         'action': '1.skill-creator模板 2.tdd流程 3.存进brain'},
        {'trigger': '架构选型问题', 'tier': 3,
         'path': [n for n in ['brain-team-architecture', 'brain-system-integration', 'deer-flow-harness'] if valid(n)],
         'action': '1.列约束 2.查brain架构 3.建议+原因 4.存brain'},
        {'trigger': '学习新知识', 'tier': 2,
         'path': [n for n in ['external-fetcher', 'auto-learning', 'brain-thinker'] if valid(n)],
         'action': '1.外部获取 2.Ollama分析 3.写进brain 4.更新neural'},
        {'trigger': '安全/漏洞相关', 'tier': 3,
         'path': [n for n in ['lcguard-multiagent-security', 'security-auditor', 'brain-thinker'] if valid(n)],
         'action': '1.查CVE/HN 2.分析影响 3.给建议 4.写进brain'},
        {'trigger': '多模型协作任务', 'tier': 3,
         'path': [n for n in ['collaborative-protocol', 'hook-automation', 'brain-thinker'] if valid(n)],
         'action': '1.拆解子问题 2.派发 3.汇总 4.整合'},
        {'trigger': '主题/设计需求', 'tier': 1,
         'path': [n for n in ['theme-factory', 'taste-design-principles', 'frontend-design'] if valid(n)],
         'action': '1.theme-factory 2.审美原则参考 3.前端实现'},
        {'trigger': 'debug报错问题', 'tier': 1,
         'path': [n for n in ['ollama-auto-learning-debug', 'tdd-engineering'] if valid(n)],
         'action': '1.查错误日志 2.定位根因 3.修复 4.验证'},
    ]
    # 过滤空路径
    return [p for p in paths if len(p['path']) >= 2]

# ── 主函数 ──────────────────────────────────────────────────────
def main():
    today = datetime.date.today().isoformat()
    print(f"[{today}] Brain Neural Builder v3.0")
    print("=" * 50)

    # 扫描
    brain_nodes = scan_brain_docs()
    skill_nodes = scan_skills()
    all_nodes = brain_nodes + skill_nodes
    node_ids = {n['id'] for n in all_nodes}

    print(f"  Brain文档: {len(brain_nodes)}个")
    print(f"  Skills: {len(skill_nodes)}个")
    print(f"  总节点: {len(all_nodes)}个")

    # 生成connections
    connections = generate_connections(all_nodes)
    print(f"  连接数: {len(connections)}条")

    # 推理路径
    paths = build_inference_paths(node_ids)
    missing_paths = {n for p in paths for n in p['path'] if n not in node_ids}
    print(f"  推理路径: {len(paths)}条" + (f" ⚠️缺失节点: {missing_paths}" if missing_paths else " ✅"))

    # 去重验证
    all_ids = [n['id'] for n in all_nodes]
    dups = [x for x in set(all_ids) if all_ids.count(x) > 1]
    if dups:
        print(f"  ⚠️ 重复ID: {dups}")
    else:
        print(f"  ✅ 无重复ID")

    if DRY_RUN:
        print("\n[DRY RUN] 未写入文件")
        return

    # 写 skill_neural.json
    neural_data = {
        '_meta': {'version': '3.0', 'created': today,
                  'total_nodes': len(all_nodes), 'total_connections': len(connections),
                  'description': f'机器猫神经网络v3 - {len(brain_nodes)}brain+{len(skill_nodes)}skill'},
        'skills': skill_nodes, 'nodes': all_nodes,
    }
    with open(NEURAL_DIR / 'skill_neural.json', 'w', encoding='utf-8') as f:
        json.dump(neural_data, f, ensure_ascii=False, indent=2)

    # 写 connections.json
    with open(NEURAL_DIR / 'connections.json', 'w', encoding='utf-8') as f:
        json.dump({'_meta': {'version': '1.0', 'description': '突触权重'},
                   'connections': connections}, f, ensure_ascii=False, indent=2)

    # 写 inference_paths.json
    with open(NEURAL_DIR / 'inference_paths.json', 'w', encoding='utf-8') as f:
        json.dump({'version': '3.0', 'updated': today, 'inference_paths': paths}, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已写入 {NEURAL_DIR}/")
    print(f"   skill_neural.json     (nodes + skills字段)")
    print(f"   connections.json      (突触权重)")
    print(f"   inference_paths.json  (推理路径)")

if __name__ == "__main__":
    main()
