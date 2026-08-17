#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chelsea FC 情报站抓取脚本（含中英对照翻译）
数据源：chelseafc.com 官方 JSON API（零破解，无需登录）
翻译：Google 免费翻译接口（client=gtx，零 key，零付费）
用法：python3 scripts/fetch.py
产出：data/news.json + images/（图集图片）
"""
import json, re, os, sys, time, urllib.request, urllib.parse, datetime

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
BASE = "https://www.chelseafc.com"
LISTING_URL = BASE + "/en/api/news/listing/7rJyiGvKIDGe6kNF0jRwJ5?pageSize=50&pageNum=0"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
IMG_DIR = os.path.join(ROOT, "images")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

GALLERY_KEYS = ["training gallery", "gallery", "match gallery",
                "open training", "behind the scenes", "colney",
                "in pictures", "best pictures", "day as a blue"]

# 翻译配置
TRANSLATE_DELAY = 0.25   # 免费接口节流，避免 429
MAX_SEG_LEN = 4500       # 单次翻译最大字符（超出则分段）

def fetch_text(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'replace')

def fetch_json(url):
    return json.loads(fetch_text(url))

def g_translate(text, tl='zh-CN'):
    """Google 免费翻译（无 key）。失败返回 None。"""
    text = text.strip()
    if not text:
        return None
    url = ("https://translate.googleapis.com/translate_a/single"
           "?client=gtx&sl=en&tl=" + tl + "&dt=t&q=" + urllib.parse.quote(text))
    req = urllib.request.Request(url, headers=UA)
    r = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
    data = json.loads(r)
    parts = [seg[0] for seg in data[0] if seg and seg[0]]
    return "".join(parts)

def translate_long(text, tl='zh-CN'):
    """长文本分段翻译，容错。"""
    if not text:
        return None
    if len(text) <= MAX_SEG_LEN:
        return g_translate(text, tl)
    # 按句子分段
    segs = re.split(r'(?<=[.!?])\s+', text)
    out, buf = [], ""
    for s in segs:
        if len(buf) + len(s) > MAX_SEG_LEN:
            if buf:
                t = g_translate(buf, tl)
                if t: out.append(t)
            buf = s
        else:
            buf += (" " if buf else "") + s
    if buf:
        t = g_translate(buf, tl)
        if t: out.append(t)
    return " ".join(out) if out else None

def is_gallery(item):
    t = item.get('type', '').lower()
    title = item.get('title', '').lower()
    if t == 'gallery':
        return True
    return any(k in title for k in GALLERY_KEYS)

def clean_path(p):
    return p.split('&quot;')[0].split('\\u0026')[0].split('\\"')[0].split('"')[0]

def extract_gallery_images(html):
    blacklist = ['logo', 'sponsor', 'badge', 'crest', 'cfc%20plus', 'cfc-plus',
                 'marketing/', 'site%20chelsea', 'app', 'qrcode', 'nike_header',
                 'bingx_header', 'cfc_phone', 'stadion']
    found = {}
    for m in re.finditer(r'https?://img\.chelseafc\.com/image/upload/([^"\s\\)]+)', html):
        p = clean_path(m.group(1))
        low = p.lower()
        if any(b in low for b in blacklist):
            continue
        if not re.search(r'\.(jpe?g|png|webp)(\?|$)', low):
            continue
        if p not in found:
            found[p] = "http://img.chelseafc.com/image/upload/" + p
    return list(found.values())

def extract_body(html):
    """提取新闻正文（<p> 段落拼接），图集文章通常无正文返回 None。"""
    paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.S)
    def clean(p):
        p = re.sub(r'<[^>]+>', '', p)
        p = (p.replace('&amp;', '&').replace('&nbsp;', ' ')
              .replace('&#39;', "'").replace('&quot;', '"')
              .replace('&hellip;', '…').replace('&ndash;', '–').replace('&mdash;', '—'))
        return p.strip()
    cleaned = [clean(p) for p in paras if len(clean(p)) > 30]
    if not cleaned:
        return None
    return " ".join(cleaned)

def cloudinary_compress(url, w=1200):
    return url.replace('/image/upload/', f'/image/upload/w_{w},q_auto,f_auto/')

def download(url, path):
    try:
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=30).read()
        with open(path, 'wb') as f:
            f.write(data)
        return len(data)
    except Exception as e:
        print(f"  [下载失败] {e}")
        return 0

def slugify(s, n=60):
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s[:n]

def main():
    print("== Chelsea FC 情报站抓取（含中英翻译）==")
    listing = fetch_json(LISTING_URL)
    items = listing.get('items', [])
    print(f"抓到 {len(items)} 条新闻\n")

    news = []
    g_down = 0
    total_bytes = 0

    for idx, it in enumerate(items):
        title = it.get('title', '(无标题)')
        itype = it.get('type', 'Article')
        url = it.get('url', '')
        full_url = BASE + url if url.startswith('/') else url
        cat = it.get('category', {})
        category = cat.get('title', '') if isinstance(cat, dict) else ''
        thumb = it.get('thumbnail', {})
        thumb_url = ''
        if isinstance(thumb, dict):
            f = thumb.get('file', {})
            thumb_url = f.get('url', '') if isinstance(f, dict) else ''

        entry = {
            'title': title, 'title_zh': None,
            'type': itype, 'category': category,
            'url': full_url, 'thumbnail': thumb_url,
            'is_gallery': is_gallery(it),
            'body_en': None, 'body_zh': None,
            'images': [],
        }

        # 1. 抓详情页（图集提取图，文章提取正文）
        html = None
        try:
            html = fetch_text(full_url)
        except Exception as e:
            print(f"[{idx+1}] 详情失败 {title[:40]} -> {e}")

        if html:
            if entry['is_gallery']:
                # 方案1：图片走官方 Cloudinary 直链，不落地 repo
                imgs = extract_gallery_images(html)
                entry['images'] = imgs
                entry['images_local'] = [cloudinary_compress(u) for u in imgs]
            else:
                entry['body_en'] = extract_body(html)

        # 2. 翻译标题
        try:
            entry['title_zh'] = g_translate(title)
            time.sleep(TRANSLATE_DELAY)
        except Exception as e:
            print(f"  [标题翻译失败] {e}")

        # 3. 翻译正文（非图集）
        if entry['body_en']:
            try:
                entry['body_zh'] = translate_long(entry['body_en'])
                time.sleep(TRANSLATE_DELAY)
            except Exception as e:
                print(f"  [正文翻译失败] {e}")

        mark = "🖼" if entry['is_gallery'] else ("✓" if entry['title_zh'] else "✗")
        print(f"[{idx+1}] {mark} {itype}: {title[:55]}")
        news.append(entry)

    out = {
        'updated': datetime.datetime.now().isoformat(timespec='seconds'),
        'count': len(news),
        'gallery_count': sum(1 for n in news if n['is_gallery']),
        'translated_count': sum(1 for n in news if n['title_zh']),
        'news': news,
    }
    outpath = os.path.join(DATA_DIR, 'news.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完成：{len(news)} 条 | 图集 {out['gallery_count']} 篇 | 翻译成功 {out['translated_count']} 条标题")
    print(f"   图集图片 {g_down} 张，共 {total_bytes/1024/1024:.1f} MB")
    print(f"   写入 {outpath}")

if __name__ == '__main__':
    main()
