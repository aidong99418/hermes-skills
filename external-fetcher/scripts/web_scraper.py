#!/usr/bin/env python3
"""
🕷️ Hermes Web Scraper v2 — 本地化数据抓取技能（权威源版）
严格筛选：只收录能验证、可访问、质量可靠的权威来源
覆盖：学术论文、安全漏洞、科技媒体、AI资讯、代码社区、国内技术圈
100%本地，无需任何外部 API Key
"""

import requests
import feedparser
import json
import re
import os
import ssl
import urllib.request
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/html, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
TIMEOUT = 12

# ─────────────────────────────────────────────────────────
# 数据源配置（全部经过验证，可正常访问）
# format: (url, params_dict, parser, category, label)
# parser: xml/rss/json/html_text/html_links
# category: paper/security/tech/ai/code/social
# ─────────────────────────────────────────────────────────
SOURCES = [
    # ═══ 学术论文（国际权威）═════════════════════════════
    ('http://export.arxiv.org/api/query',
     {'search_query': 'cat:cs.AI', 'max_results': 12, 'sortBy': 'submittedDate', 'sortOrder': 'descending'},
     'xml', 'paper', '📚 ArXiv — AI/机器学习'),
    ('http://export.arxiv.org/api/query',
     {'search_query': 'cat:cs.CL', 'max_results': 8, 'sortBy': 'submittedDate', 'sortOrder': 'descending'},
     'xml', 'paper', '📚 ArXiv — 自然语言处理'),
    ('http://export.arxiv.org/api/query',
     {'search_query': 'cat:cs.LG', 'max_results': 8, 'sortBy': 'submittedDate', 'sortOrder': 'descending'},
     'xml', 'paper', '📚 ArXiv — 生成模型/深度学习'),
    ('http://export.arxiv.org/api/query',
     {'search_query': 'cat:cs.CR', 'max_results': 8, 'sortBy': 'submittedDate', 'sortOrder': 'descending'},
     'xml', 'paper', '📚 ArXiv — 网络安全'),
    ('http://export.arxiv.org/api/query',
     {'search_query': 'cat:cs.SE', 'max_results': 6, 'sortBy': 'submittedDate', 'sortOrder': 'descending'},
     'xml', 'paper', '📚 ArXiv — 软件工程'),
    ('http://export.arxiv.org/api/query',
     {'search_query': 'cat:cs.PL', 'max_results': 6, 'sortBy': 'submittedDate', 'sortOrder': 'descending'},
     'xml', 'paper', '📚 ArXiv — 编程语言'),

    # ═══ 安全漏洞（官方+社区权威）═════════════════════════
    ('https://services.nvd.nist.gov/rest/json/cves/2.0',
     {'cvssV3Severity': 'CRITICAL', 'resultsPerPage': 10},
     'cve_nvd', 'security', '🔴 NVD CVE — 严重漏洞'),
    ('https://services.nvd.nist.gov/rest/json/cves/2.0',
     {'cvssV3Severity': 'HIGH', 'resultsPerPage': 10},
     'cve_nvd', 'security', '🟠 NVD CVE — 高危漏洞'),
    ('https://www.exploit-db.com/rss.xml',
     {}, 'rss', 'security', '💀 Exploit-DB — 漏洞利用'),
    ('https://www.freebuf.com/feed',
     {}, 'rss', 'security', '🛡️ FreeBuf — 安全资讯'),
    ('https://xz.aliyun.com/feed',
     {}, 'rss', 'security_cn', '🎯 先知社区 — 安全资讯（阿里云）'),
    ('https://www.secpulse.com/rss',
     {}, 'rss', 'security_cn', '🎯 安全脉搏 — 安全资讯'),
    ('https://www.technologyreview.com/feed/',
     {}, 'rss', 'tech', '🔬 MIT Tech Review'),
    ('https://www.wired.com/feed/rss',
     {}, 'rss', 'tech', '⚡ Wired'),
    ('https://www.theverge.com/rss/index.xml',
     {}, 'rss', 'tech', '📱 The Verge'),

    # ═══ AI/代码社区（国际）═══════════════════════════════
    ('https://hn.algolia.com/api/v1/search',
     {'tags': 'front_page', 'hitsPerPage': 20}, 'hn', 'ai', '📰 Hacker News — 热门'),
    ('https://hn.algolia.com/api/v1/search',
     {'query': 'artificial intelligence machine learning LLM', 'tags': 'story', 'hitsPerPage': 15},
     'hn', 'ai', '🤖 Hacker News — AI相关'),
    ('https://hn.algolia.com/api/v1/search',
     {'query': 'security vulnerability exploit CVE zero-day', 'tags': 'story', 'hitsPerPage': 15},
     'hn', 'ai', '🔐 Hacker News — 安全相关'),
    ('https://api.github.com/search/repositories',
     {'q': 'AI OR LLM OR GPT OR language-model language:python', 'sort': 'stars', 'order': 'desc', 'per_page': 10},
     'github', 'code', '⭐ GitHub — AI热门项目'),
    ('https://api.github.com/search/repositories',
     {'q': 'vulnerability security exploit language:python', 'sort': 'stars', 'order': 'desc', 'per_page': 10},
     'github', 'code', '🔐 GitHub — 安全热门项目'),

    # ═══ 国内技术/AI 媒体（权威中文源）═════════════════════
    ('https://36kr.com/feed',
     {}, 'rss', 'ai_cn', '📡 36氪 — 科技创业'),
    ('https://www.oschina.net/news/rss',
     {}, 'rss', 'ai_cn', '🔧 OSCHINA — 开源中国'),
    ('https://www.tmtpost.com/rss',
     {}, 'rss', 'ai_cn', '🚀 钛媒体 — 科技媒体'),
    ('https://www.ithome.com/rss/',
     {}, 'rss', 'ai_cn', '🖥️ IT之家 — IT资讯'),
    ('https://feed.infoq.com/',
     {}, 'rss', 'ai_cn', '🎯 InfoQ — 国际技术深度报道'),
]

# ─────────────────────────────────────────────────────────
# 解析器
# ─────────────────────────────────────────────────────────

def parse_arxiv(raw: str) -> List[Dict]:
    items = []
    for e in re.findall(r'<entry>(.*?)</entry>', raw, re.DOTALL):
        title = re.search(r'<title>(.*?)</title>', e, re.DOTALL)
        summary = re.search(r'<summary>(.*?)</summary>', e, re.DOTALL)
        link = re.search(r'<id>(.*?)</id>', e)
        authors = re.findall(r'<name>(.*?)</name>', e)
        published = re.search(r'<published>(.*?)</published>', e)
        if title:
            items.append({
                'title': ' '.join(title.group(1).split()),
                'summary': ' '.join(summary.group(1).split())[:400] if summary else '',
                'url': link.group(1).strip() if link else '',
                'authors': ', '.join(authors[:3]),
                'published': published.group(1)[:10] if published else '',
                'type': 'paper'
            })
    return items


def parse_cve_nvd(raw: str) -> List[Dict]:
    data = json.loads(raw)
    results = []
    for v in data.get('vulnerabilities', []):
        cve = v.get('cve', {})
        metrics = cve.get('metrics', {})
        cvss = (metrics.get('cvssMetricV31') or metrics.get('cvssMetricV30') or [{}])[0]
        cvss_data = cvss.get('cvssData', {}) if cvss else {}
        results.append({
            'title': cve.get('id', ''),
            'summary': cve.get('descriptions', [{}])[0].get('value', '')[:400],
            'url': f"https://nvd.nist.gov/vuln/detail/{cve.get('id','')}",
            'cvss': cvss_data.get('baseScore', 'N/A'),
            'severity': cvss_data.get('baseSeverity', 'UNKNOWN'),
            'published': cve.get('published', '')[:10],
            'type': 'security'
        })
    return results


def parse_rss(raw: str, limit: int = 15) -> List[Dict]:
    feed = feedparser.parse(raw)
    items = []
    for entry in feed.entries[:limit]:
        content = ''
        if hasattr(entry, 'summary'):
            content = entry.summary
        elif hasattr(entry, 'description'):
            content = entry.description
        content = re.sub(r'<[^>]+>', ' ', content)
        content = ' '.join(content.split())
        items.append({
            'title': entry.get('title', ''),
            'summary': content[:400],
            'url': entry.get('link', ''),
            'published': entry.get('published', entry.get('updated', ''))[:10],
            'type': 'tech'
        })
    return items


def parse_hn(raw: dict) -> List[Dict]:
    results = []
    for item in raw.get('hits', []):
        results.append({
            'title': item.get('title', ''),
            'summary': item.get('excerpt', '')[:300],
            'url': item.get('url', item.get('objectID', '')),
            'points': item.get('points', 0),
            'comments': item.get('num_comments', 0),
            'author': item.get('author', ''),
            'published': item.get('created_at', '')[:10],
            'type': 'news'
        })
    return results


def parse_github(raw: dict) -> List[Dict]:
    results = []
    for item in raw.get('items', []):
        results.append({
            'title': f"{item.get('full_name', '')} ⭐{item.get('stargazers_count', 0)}",
            'summary': item.get('description', '')[:300],
            'url': item.get('html_url', ''),
            'stars': item.get('stargazers_count', 0),
            'language': item.get('language', ''),
            'type': 'code'
        })
    return results


def parse_freebuf_articles(raw: str) -> List[Dict]:
    """从 FreeBuf HTML 页面提取文章标题和链接"""
    soup = BeautifulSoup(raw, 'html.parser')
    items = []
    for art in soup.select('div.article-item')[:15]:
        title_el = art.select_one('h2 a, h3 a, .title a')
        summary_el = art.select_one('.item-info p, .summary, .desc')
        link_el = art.select_one('a[href]')
        if title_el:
            items.append({
                'title': title_el.get_text(strip=True),
                'summary': summary_el.get_text(strip=True)[:300] if summary_el else '',
                'url': link_el['href'] if link_el else '',
                'type': 'security'
            })
    return items


def parse_t00ls(raw: str) -> List[Dict]:
    """解析 T00ls 页面"""
    soup = BeautifulSoup(raw, 'html.parser')
    items = []
    for row in soup.select('table tbody tr, div.article-list li, .news-list li')[:15]:
        title_el = row.select_one('a')
        if title_el:
            items.append({
                'title': title_el.get_text(strip=True),
                'summary': row.get_text(strip=True)[:200],
                'url': title_el['href'] if title_el else '',
                'type': 'security_cn'
            })
    return items


def fetch_all(categories: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """
    抓取所有源
    categories: None=全部, 或 ['paper','security','tech','ai','code','ai_cn','security_cn']
    """
    results = {}
    cat_map = {'paper','security','tech','ai','code','ai_cn','security_cn'}
    active = [(url, params, p, cat, label)
              for url, params, p, cat, label in SOURCES
              if not categories or cat in categories]

    def fetch_one(url, params, parser, cat, label):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            if parser == 'xml':
                return label, parse_arxiv(r.text)
            elif parser == 'cve_nvd':
                return label, parse_cve_nvd(r.text)
            elif parser == 'rss':
                return label, parse_rss(r.text)
            elif parser == 'hn':
                return label, parse_hn(r.json())
            elif parser == 'github':
                return label, parse_github(r.json())
            elif parser == 'html_articles':
                return label, parse_freebuf_articles(r.text)
            elif parser == 't00ls':
                return label, parse_t00ls(r.text)
            return label, []
        except Exception as e:
            return label, [{'error': str(e)[:80], 'type': 'error'}]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_one, *s) for s in active]
        for f in as_completed(futures):
            label, data = f.result()
            results[label] = data
            good = [x for x in data if 'error' not in x]
            print(f'  {"✅" if good else "⚠️"} {label}: {len(good)}条')

    return results


def format_markdown(results: Dict) -> str:
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    md = f"""# 🕷️ Hermes Web Scraper Report
> 生成时间: {now} | 数据源: {len(results)}个 | 总条目: {sum(len(v) for v in results.values())}条

"""

    order = [
        ('📚', 'paper', '── 学术论文 ──'),
        ('🔴🟠', 'security', '── 安全漏洞 ──'),
        ('🔐', 'security_cn', '── 国内安全 ──'),
        ('📰🤖🔐', 'ai', '── Hacker News ──'),
        ('⭐🔐', 'code', '── GitHub 项目 ──'),
        ('🔬⚡📱', 'tech', '── 国际科技媒体 ──'),
        ('📡💬🔧🚀🖥️', 'ai_cn', '── 国内技术媒体 ──'),
    ]
    for icon, cat_key, section_title in order:
        matching = [(label, items) for label, items in results.items()
                    if any(s[3] == cat_key for s in SOURCES if s[4] == label)]
        if not matching: continue
        md += f'\n## {section_title}\n\n'
        for label, items in matching:
            md += f'### {label}\n\n'
            for item in items[:10]:
                if 'error' in item: continue
                md += f"- **{item.get('title','')}**\n"
                s = item.get('summary','')
                if s: md += f"  {s[:200]}\n"
                if item.get('url'): md += f"  🔗 {item.get('url','')[:80]}\n"
                extra = []
                for k in ['cvss','severity','stars','language','points','authors','published']:
                    if k in item and item[k]: extra.append(f"{k}={item[k]}")
                if extra: md += f"  {' | '.join(extra)}\n"
                md += '\n'

    return md


if __name__ == '__main__':
    import sys
    os.makedirs('/opt/data/cron/output', exist_ok=True)

    categories = None
    if len(sys.argv) > 1:
        categories = sys.argv[1].split(',')

    print(f'🕷️ 开始抓取权威数据源... (分类: {categories or "全部"})\n')
    results = fetch_all(categories)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = f"/opt/data/cron/output/scraper_{ts}.json"
    md_path = f"/opt/data/cron/output/scraper_{ts}.md"

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\n✅ JSON: {json_path}')

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(format_markdown(results))
    print(f'✅ Markdown: {md_path}')

    total = sum(len(v) for v in results.values())
    print(f'✅ 共抓取 {total} 条数据，来自 {len(results)} 个权威源')
