#!/usr/bin/env python3
"""
Motorsport News Fetcher Script (Pure Python 3, zero third-party dependencies)
Fetches RSS feeds for F1, MotoGP, Moto2, Moto3, SBK, MXGP, MX2, WEC.
Generates Italian summaries, extracts images, and writes to data/news.json and js/news.js.
"""

import os
import re
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import html

FEEDS = [
    {"name": "Motorsport.com F1", "category": "F1", "url": "https://www.motorsport.com/rss/f1/news/"},
    {"name": "Motorsport.com MotoGP", "category": "MotoGP", "url": "https://www.motorsport.com/rss/motogp/news/"},
    {"name": "Motorsport.com WSBK", "category": "SBK", "url": "https://www.motorsport.com/rss/wsbk/news/"},
    {"name": "Motorsport.com WEC", "category": "WEC", "url": "https://www.motorsport.com/rss/wec/news/"},
    {"name": "Crash MotoGP", "category": "MotoGP", "url": "https://www.crash.net/rss/motogp"},
    {"name": "Crash WSBK", "category": "SBK", "url": "https://www.crash.net/rss/wsbk"},
    {"name": "Crash F1", "category": "F1", "url": "https://www.crash.net/rss/f1"},
    {"name": "Autosport F1", "category": "F1", "url": "https://www.autosport.com/rss/f1/news/"},
    {"name": "RaceFans F1", "category": "F1", "url": "https://www.racefans.net/feed/"},
    {"name": "GateDrop MXGP", "category": "MXGP", "url": "https://gatedrop.com/feed/"},
    {"name": "Vurbmoto MX", "category": "MXGP", "url": "https://vurbmoto.com/feed/"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def clean_text(raw):
    if not raw:
        return ""
    text = re.sub(r'<[^>]+>', ' ', raw)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_ai_summary(title, raw_desc):
    source_text = raw_desc if raw_desc and len(raw_desc) > 30 else title
    clean = clean_text(source_text)
    if len(clean) > 400:
        clean = clean[:397].rsplit(' ', 1)[0] + '...'

    # Fast Italian translation attempt via MyMemory API
    try:
        encoded = urllib.parse.quote(clean[:450])
        req = urllib.request.Request(
            f"https://api.mymemory.translated.net/get?q={encoded}&langpair=en|it",
            headers=HEADERS
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            if data and data.get("responseData") and data["responseData"].get("translatedText"):
                trans = data["responseData"]["translatedText"].strip()
                if trans and "MYMEMORY WARNING" not in trans and len(trans) > 5:
                    return trans
    except Exception:
        pass

    return clean

def detect_category(title, desc, default_cat):
    combined = f"{title} {desc}".lower()

    if re.search(r'\bmoto2\b|arbolino|vietti|canet|ogura|garcia|lopez|dixon|chantra', combined):
        return "Moto2"
    if re.search(r'\bmoto3\b|david alonso|ortola|veijer|holgado|mu[nñ]oz|piqueras|rueda', combined):
        return "Moto3"
    if re.search(r'\b(sbk|worldsbk|superbike)\b|razgatlioglu|bulega|bautista|rea|locatelli|iannone|petrucci', combined):
        return "SBK"
    if re.search(r'\bmx2\b|motocross mx2', combined):
        return "MX2"
    if re.search(r'\bmxgp\b|fim motocross|gajser|herlings|prado|febvre|coenen|de wolf|adamo', combined):
        return "MXGP"
    if re.search(r'\bwec\b|le mans|hypercar|499p|toyota gazoo|porsche 963', combined):
        return "WEC"
    if re.search(r'\bf1\b|formula 1|verstappen|hamilton|leclerc|norris|piastri|ferrari f1|mercedes f1|red bull racing', combined):
        return "F1"
    if re.search(r'\bmotogp\b|marquez|bagnaia|martin|ducati corse|aprilia racing|yamaha motogp|ktm motogp', combined):
        return "MotoGP"

    return default_cat

def extract_image(item_elem, desc_raw):
    # 1. Enclosure
    enclosure = item_elem.find('enclosure')
    if enclosure is not None and enclosure.get('url'):
        return enclosure.get('url')

    # 2. media:content or media:thumbnail
    for child in item_elem:
        tag = child.tag.lower()
        if 'content' in tag or 'thumbnail' in tag:
            url = child.get('url')
            if url:
                return url

    # 3. img tag inside description
    if desc_raw:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_raw, re.IGNORECASE)
        if m:
            return m.group(1)

    return ""

def parse_date(date_str):
    if not date_str:
        return datetime.now(timezone.utc)
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except Exception:
            continue
    return datetime.now(timezone.utc)

def main():
    print("=" * 60)
    print("Avvio estrazione Notizie Motorsport...")
    print("=" * 60)

    all_items = []
    seen_links = set()

    for feed in FEEDS:
        name = feed["name"]
        cat = feed["category"]
        url = feed["url"]
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_content = resp.read()

            root = ET.fromstring(xml_content)
            channel = root.find('channel')
            if channel is None:
                continue

            items = channel.findall('item')
            count = 0
            for it in items:
                title_node = it.find('title')
                link_node = it.find('link')
                desc_node = it.find('description')
                date_node = it.find('pubDate')

                title = clean_text(title_node.text) if title_node is not None else ""
                link = link_node.text.strip() if link_node is not None and link_node.text else ""
                raw_desc = desc_node.text if desc_node is not None and desc_node.text else ""
                date_str = date_node.text if date_node is not None and date_node.text else ""

                if not title or not link or link in seen_links:
                    continue
                seen_links.add(link)

                category = detect_category(title, raw_desc, cat)
                image = extract_image(it, raw_desc)
                dt = parse_date(date_str)
                ai_sum = get_ai_summary(title, raw_desc)

                all_items.append({
                    "id": f"{hash(link) & 0xffffffff:08x}",
                    "title": title,
                    "link": link,
                    "pubDate": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "pubDateISO": dt.isoformat(),
                    "aiSummary": ai_sum,
                    "source": name,
                    "category": category,
                    "image": image
                })
                count += 1

            print(f"✓ {name}: {count} notizie estratte.")
        except Exception as e:
            print(f"✗ Errore {name} ({url}): {e}")

    # Group by category, limit each to max 40 items
    grouped = {}
    for item in all_items:
        grouped.setdefault(item["category"], []).append(item)

    final_list = []
    for cat_name, cat_items in grouped.items():
        cat_items.sort(key=lambda x: x["pubDateISO"], reverse=True)
        final_list.extend(cat_items[:40])

    final_list.sort(key=lambda x: x["pubDateISO"], reverse=True)

    output = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalItems": len(final_list),
        "items": final_list
    }

    # Ensure output directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("js", exist_ok=True)

    json_raw = json.dumps(output, indent=2, ensure_ascii=False)

    with open("data/news.json", "w", encoding="utf-8") as f:
        f.write(json_raw)

    with open("js/news.js", "w", encoding="utf-8") as f:
        f.write("window.NEWS_DATA = " + json.dumps(output, separators=(',', ':'), ensure_ascii=False) + ";\n")

    print("\n✓ File generati con successo:")
    print(f"  - data/news.json ({len(final_list)} notizie)")
    print(f"  - js/news.js")
    for cat_name in sorted(grouped.keys()):
        print(f"    • {cat_name}: {len(grouped[cat_name])} notizie")

if __name__ == "__main__":
    main()
