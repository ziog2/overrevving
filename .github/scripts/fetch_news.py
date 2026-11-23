#!/usr/bin/env python3
"""
Motorsport News Fetcher Script (Pure Python 3, zero third-party dependencies)
Fetches RSS feeds for F1, MotoGP, Moto2, Moto3, SBK, MXGP, MX2, WEC.
Generates Italian summaries, extracts images, and writes to data/news.json and js/news.js.
"""

import os
import re
import json
import unicodedata
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import html

VALID_CATEGORIES = ("MotoGP", "Moto2", "Moto3", "SBK", "MXGP", "MX2", "F1")

STANDINGS_KEY_TO_CAT = {
    "motogp": "MotoGP",
    "moto2": "Moto2",
    "moto3": "Moto3",
    "sbk": "SBK",
    "mxgp": "MXGP",
    "mx2": "MX2",
    "f1": "F1",
}

FEEDS = [
    {"name": "Motorsport.com F1", "category": "F1", "url": "https://www.motorsport.com/rss/f1/news/"},
    {"name": "Motorsport.com MotoGP", "category": "MotoGP", "url": "https://www.motorsport.com/rss/motogp/news/"},
    {"name": "Motorsport.com Moto2", "category": "Moto2", "url": "https://www.motorsport.com/rss/moto2/news/"},
    {"name": "Motorsport.com Moto3", "category": "Moto3", "url": "https://www.motorsport.com/rss/moto3/news/"},
    {"name": "Motorsport.com WSBK", "category": "SBK", "url": "https://www.motorsport.com/rss/wsbk/news/"},
    {"name": "Crash MotoGP", "category": "MotoGP", "url": "https://www.crash.net/rss/motogp"},
    {"name": "Crash Moto2", "category": "Moto2", "url": "https://www.crash.net/rss/moto2"},
    {"name": "Crash Moto3", "category": "Moto3", "url": "https://www.crash.net/rss/moto3"},
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

# Cognomi troppo generici o parole comuni da non usare da soli per il matching
SURNAME_STOPLIST = {
    "martin", "garcia", "lopez", "miller", "smith", "taylor", "wright",
    "walker", "turner", "cooper", "parker", "carter", "porter",
    "hunter", "fisher", "baker", "clark", "brown", "white", "black", "green",
    "young", "power", "speed", "cross", "stone", "woods", "price", "grant",
    "scott", "lewis", "wilson", "thomas", "roberts", "johnson",
    "williams", "jones", "davis", "moore", "jackson", "harris", "campbell",
    "stewart", "morris", "rogers", "morgan", "murphy", "bailey", "rivera",
    "howard", "ward", "torres", "peterson", "ramirez", "james", "watson",
    "brooks", "kelly", "sanders", "bennett", "barnes", "ross", "henderson",
    "coleman", "jenkins", "perry", "powell", "patterson", "hughes", "flores",
    "butler", "simmons", "foster", "gonzales", "bryant", "alexander", "griffin",
    "russell", "alonso", "fernandez", "marquez", "binder", "lowes", "coenen",
    "espargaro", "dixon", "sanchez", "martinez", "rodriguez", "hernandez",
    "gonzalez", "perez", "gomez", "ruiz", "diaz", "moreno", "munoz", "alvarez",
    "romero", "navarro", "dominguez", "vazquez", "ramos", "serrano", "blanco",
    "molina", "morales", "ortega", "delgado", "castro", "ortiz", "rubio",
    "marin", "sanz", "iglesias", "medina", "cortes", "garrido", "castillo",
    "santos", "lozano", "guerrero", "cano", "prieto", "mendez", "calvo",
    "gallego", "vidal", "leon", "herrera", "pena", "cabrera",
    "ferrari", "honda", "yamaha", "suzuki", "ducati", "aprilia", "kawasaki",
    "france", "spain", "italy", "qatar", "japan", "brazil", "austria",
    "winner", "second", "finish", "season", "racing", "riders", "driver",
}

def strip_accents(text):
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def normalize_text(text):
    return strip_accents(text or "").lower()

def clean_text(raw):
    if not raw:
        return ""
    text = re.sub(r'<[^>]+>', ' ', raw)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def load_rosters(standings_path="data/standings_latest.json"):
    """
    Carica dinamicamente i roster della stagione corrente da data/standings_latest.json
    per evitare liste di piloti hardcoded obsolete.
    Restituisce (full_name_map, unique_surname_map) con sole voci univoche per categoria.
    """
    full_cats = {}
    surname_cats = {}

    if not os.path.exists(standings_path):
        return {}, {}

    try:
        with open(standings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}, {}

    for key, cat in STANDINGS_KEY_TO_CAT.items():
        entries = data.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            raw_name = entry.get("name", "") if isinstance(entry, dict) else ""
            norm = re.sub(r'\s+', ' ', normalize_text(raw_name)).strip()
            if not norm or len(norm) < 4:
                continue
            full_cats.setdefault(norm, set()).add(cat)

            parts = [p for p in re.split(r'[\s\-]+', norm) if p]
            if len(parts) >= 2:
                surname = parts[-1]
                if len(surname) >= 6 and surname not in SURNAME_STOPLIST:
                    surname_cats.setdefault(surname, set()).add(cat)

    full_map = {name: next(iter(cats)) for name, cats in full_cats.items() if len(cats) == 1}
    surname_map = {s: next(iter(cats)) for s, cats in surname_cats.items() if len(cats) == 1}
    return full_map, surname_map

_translation_disabled = False

def load_summary_cache(news_path="data/news.json"):
    cache = {}
    if not os.path.exists(news_path):
        return cache
    try:
        with open(news_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("items", []):
            link = item.get("link")
            summary = item.get("aiSummary")
            if link and summary:
                cache[link] = summary
    except Exception:
        pass
    return cache

def get_ai_summary(title, raw_desc):
    global _translation_disabled
    source_text = raw_desc if raw_desc and len(raw_desc) > 30 else title
    clean = clean_text(source_text)
    if len(clean) > 400:
        clean = clean[:397].rsplit(' ', 1)[0] + '...'

    if _translation_disabled:
        return clean

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
                if "MYMEMORY WARNING" in trans:
                    _translation_disabled = True
                    return clean
                if trans and len(trans) > 5:
                    return trans
    except urllib.error.HTTPError as e:
        if e.code == 429:
            _translation_disabled = True
    except Exception:
        pass

    return clean

# Pattern per campionati esclusi dal sito (non presenti tra le 7 categorie attive)
EXCLUDED_URL_RE = re.compile(
    r'/(?:fia-f2|formula2|formula-2|f2|fia-f3|formula3|formula-3|f3|'
    r'indycar|nascar|wec|formula-e|wrc|dtm|imsa|supercars|'
    r'f1-academy|f1academy|motoe|btcc|gt-world|gtworld|elms|super-formula)/',
    re.IGNORECASE,
)

EXCLUDED_TITLE_SUFFIX_RE = re.compile(
    r'\|\s*(?:formula\s*2|f2|formula\s*3|f3|indycar|formula\s*e|wec|nascar|wrc|f1\s*academy|motoe)\s*$',
    re.IGNORECASE,
)

EXCLUDED_SERIES_RE = re.compile(
    r'\b(?:formula\s*2|fia\s*f2|f2|formula\s*3|fia\s*f3|f3|indycar|nascar|'
    r'formula\s*e|wec|world\s+endurance|motoe|f1\s*academy)\b',
    re.IGNORECASE,
)

ACTIVE_SERIES_FRAMING_RE = re.compile(
    r'\b(?:(?:in|for|to|joins?|keeps?|stay(?:s|ing)?\s+in|rac(?:e|es|ing)\s+in|debut(?:s|ing)?\s+in|finish(?:es|ing)?)\s+'
    r'(?:f1|formula\s*1|motogp|moto2|moto3|wsbk|worldsbk|sbk)|'
    r'(?:f1|formula\s*1|motogp)\s+(?:season|race|races|seat|drive|grid|debut|test|team|contract|deal|title))\b',
    re.IGNORECASE,
)

def should_exclude(title_norm, link_norm, rss_tags_norm):
    if link_norm and EXCLUDED_URL_RE.search(link_norm):
        return True

    if EXCLUDED_TITLE_SUFFIX_RE.search(title_norm):
        return True

    # Se i tag RSS indicano solo una serie esclusa e nessuna delle 7 valide
    if rss_tags_norm:
        has_excl_tag = any(EXCLUDED_SERIES_RE.search(t) for t in rss_tags_norm)
        has_valid_tag = any(
            re.search(r'\b(?:f1|formula\s*1|motogp|moto2|moto3|sbk|wsbk|worldsbk|superbike|bsb|mxgp|mx2|sx2)\b', t)
            for t in rss_tags_norm
        )
        if has_excl_tag and not has_valid_tag:
            return True

    # Se il titolo parla esplicitamente di F2/F3/IndyCar/WEC/ecc. senza un ruolo attivo in una delle 7 categorie
    if EXCLUDED_SERIES_RE.search(title_norm) and not ACTIVE_SERIES_FRAMING_RE.search(title_norm):
        return True

    return False

# Regole esplicite per URL path
URL_RULES = [
    ("F1",     re.compile(r'/(?:f1|formula-?1)/', re.IGNORECASE), 6.0),
    ("MotoGP", re.compile(r'/motogp/', re.IGNORECASE), 6.0),
    ("Moto2",  re.compile(r'/moto2/', re.IGNORECASE), 6.0),
    ("Moto3",  re.compile(r'/moto3/', re.IGNORECASE), 6.0),
    ("SBK",    re.compile(r'/(?:wsbk|worldsbk|sbk|superbike|bsb)/', re.IGNORECASE), 6.0),
    ("MX2",    re.compile(r'(?:/(?:mx2|sx2)/|\b(?:mx2|sx2|250-?sx|250-?prosport)\b)', re.IGNORECASE), 6.0),
    ("MXGP",   re.compile(r'/mxgp/', re.IGNORECASE), 5.0),
]

# Regole esplicite per keyword di campionato (sempre con word boundary \b)
TITLE_KEYWORDS = {
    "F1":     re.compile(r'\b(?:f1|formula\s*1|formula\s*one)\b', re.IGNORECASE),
    "MotoGP": re.compile(r'\b(?:motogp|moto\s*gp)\b', re.IGNORECASE),
    "Moto2":  re.compile(r'\bmoto2\b', re.IGNORECASE),
    "Moto3":  re.compile(r'\bmoto3\b', re.IGNORECASE),
    "SBK":    re.compile(r'\b(?:wsbk|worldsbk|sbk|world\s+superbike|superbike|worldssp|bsb|british\s+superbike)\b', re.IGNORECASE),
    "MX2":    re.compile(r'\b(?:mx2|sx2|250\s*sx|250sx|250\s*pro\s*sport|250\s*prosport|250\s*class|250\s*[ab]|250cc|emx250)\b', re.IGNORECASE),
    "MXGP":   re.compile(r'\b(?:mxgp|sx1|450\s*sx|450sx|450\s*class|450\s*pro|450cc|wmx|women\'?s\s+motocross|fim\s+motocross|british\s+motocross|paris\s+supercross|ama\s+motocross|supercross|motocross)\b', re.IGNORECASE),
}

# Menzioni secondarie/passate nel titolo (es. "Ex-MotoGP", "after losing MotoGP ride", "after Moto2 snub", "Moto3 champion")
SECONDARY_MENTION_PATTERNS = {
    "F1":     re.compile(r'\b(?:(?:ex[-\s]+|former\s+|after\s+losing\s+|losing\s+)(?:f1|formula\s*1))\b', re.IGNORECASE),
    "MotoGP": re.compile(r'\b(?:(?:ex[-\s]+|former\s+|after\s+losing\s+|losing\s+)(?:motogp|moto\s*gp))\b', re.IGNORECASE),
    "Moto2":  re.compile(r'\b(?:(?:ex[-\s]+|former\s+|after\s+|after\s+losing\s+|losing\s+)moto2|moto2\s+(?:snub|graduate|champion|winner))\b', re.IGNORECASE),
    "Moto3":  re.compile(r'\b(?:(?:ex[-\s]+|former\s+|after\s+|after\s+losing\s+|losing\s+)moto3|moto3\s+(?:snub|graduate|champion|winner))\b', re.IGNORECASE),
    "SBK":    re.compile(r'\b(?:(?:ex[-\s]+|former\s+|after\s+losing\s+|losing\s+)(?:wsbk|worldsbk|sbk|world\s+superbike|superbike))\b', re.IGNORECASE),
}

def detect_category(title, desc_raw, default_cat, link="", rss_tags=None, rosters=None):
    """
    Classifica una notizia in una delle 7 categorie del sito:
      MotoGP, Moto2, Moto3, SBK, MXGP, MX2, F1
    oppure restituisce None se l'articolo appartiene a un campionato non coperto (es. F2, WEC, IndyCar).
    """
    title_norm = normalize_text(title)
    desc_norm = normalize_text(clean_text(desc_raw))
    link_norm = (link or "").lower()
    rss_tags_norm = [normalize_text(t) for t in (rss_tags or []) if t]

    if should_exclude(title_norm, link_norm, rss_tags_norm):
        return None

    scores = {cat: 0.0 for cat in VALID_CATEGORIES}

    # 1. Baseline dal feed di origine (più leggera su MX generici così MX2/250cc può prevalere)
    if default_cat in scores:
        scores[default_cat] += 2.0 if default_cat == "MXGP" else 2.5

    # 2. Segnale dal percorso URL
    for cat, pat, weight in URL_RULES:
        if link_norm and pat.search(link_norm):
            scores[cat] += weight

    # 3. Segnale dai tag <category> del feed RSS
    for cat, pat in TITLE_KEYWORDS.items():
        if any(pat.search(t) for t in rss_tags_norm):
            scores[cat] += 4.0

    # 4. Segnale dalle keyword esplicite nel titolo
    for cat, pat in TITLE_KEYWORDS.items():
        if pat.search(title_norm):
            sec_pat = SECONDARY_MENTION_PATTERNS.get(cat)
            if sec_pat and sec_pat.search(title_norm):
                scores[cat] += 2.0
            elif cat == "MX2":
                # MX2 / SX2 / 250cc è una sottoclasse specifica rispetto al generico "Supercross"/"Motocross"
                scores[cat] += 9.0
            elif cat == "MXGP":
                scores[cat] += 6.0
            else:
                scores[cat] += 7.0

    # 5. Segnale dalle keyword esplicite nella descrizione pulita
    for cat, pat in TITLE_KEYWORDS.items():
        if pat.search(desc_norm):
            if cat == "MX2":
                scores[cat] += 4.0
            elif cat == "MXGP":
                scores[cat] += 2.0
            else:
                scores[cat] += 3.0

    # 6. Segnale di supporto dai roster aggiornati (data/standings_latest.json)
    if rosters:
        full_map, surname_map = rosters
        matched_title_cats = set()
        matched_desc_cats = set()

        for full_name, cat in full_map.items():
            if full_name in title_norm and re.search(rf'\b{re.escape(full_name)}\b', title_norm):
                if cat not in matched_title_cats:
                    scores[cat] += 3.0
                    matched_title_cats.add(cat)
            elif full_name in desc_norm and re.search(rf'\b{re.escape(full_name)}\b', desc_norm):
                if cat not in matched_desc_cats:
                    scores[cat] += 1.0
                    matched_desc_cats.add(cat)

        for surname, cat in surname_map.items():
            if cat not in matched_title_cats and surname in title_norm and re.search(rf'\b{re.escape(surname)}\b', title_norm):
                scores[cat] += 2.0
                matched_title_cats.add(cat)
            elif cat not in matched_desc_cats and surname in desc_norm and re.search(rf'\b{re.escape(surname)}\b', desc_norm):
                scores[cat] += 0.5
                matched_desc_cats.add(cat)

    best_cat = max(
        VALID_CATEGORIES,
        key=lambda c: (scores[c], 1 if c == default_cat else 0)
    )
    if scores[best_cat] <= 0:
        return default_cat if default_cat in VALID_CATEGORIES else None
    return best_cat

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
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            continue
    return datetime.now(timezone.utc)

def main():
    print("=" * 60)
    print("Avvio estrazione Notizie Motorsport...")
    print("=" * 60)

    rosters = load_rosters()
    summary_cache = load_summary_cache()
    print(f"✓ Roster dinamici caricati: {len(rosters[0])} nomi completi, {len(rosters[1])} cognomi univoci.")
    print(f"✓ Cache riassunti caricata: {len(summary_cache)} articoli esistenti.")

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
            skipped = 0
            for it in items:
                title_node = it.find('title')
                link_node = it.find('link')
                desc_node = it.find('description')
                date_node = it.find('pubDate')

                title = clean_text(title_node.text) if title_node is not None else ""
                link = link_node.text.strip() if link_node is not None and link_node.text else ""
                raw_desc = desc_node.text if desc_node is not None and desc_node.text else ""
                date_str = date_node.text if date_node is not None and date_node.text else ""
                rss_tags = [clean_text(c.text) for c in it.findall('category') if c.text]

                if not title or not link or link in seen_links:
                    continue
                seen_links.add(link)

                category = detect_category(title, raw_desc, cat, link=link, rss_tags=rss_tags, rosters=rosters)
                if not category:
                    skipped += 1
                    continue

                image = extract_image(it, raw_desc)
                dt = parse_date(date_str)

                all_items.append({
                    "id": f"{hash(link) & 0xffffffff:08x}",
                    "title": title,
                    "link": link,
                    "pubDate": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "pubDateISO": dt.isoformat(),
                    "_raw_desc": raw_desc,
                    "source": name,
                    "category": category,
                    "image": image
                })
                count += 1

            print(f"✓ {name}: {count} notizie estratte ({skipped} escluse).")
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

    # Traduci / genera riassunto solo per gli articoli finali non già presenti in cache
    translated_new = 0
    for item in final_list:
        raw_desc = item.pop("_raw_desc", "")
        cached = summary_cache.get(item["link"])
        if cached:
            item["aiSummary"] = cached
        else:
            item["aiSummary"] = get_ai_summary(item["title"], raw_desc)
            translated_new += 1

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
    print(f"  - data/news.json ({len(final_list)} notizie, {translated_new} nuovi riassunti)")
    print(f"  - js/news.js")
    for cat_name in sorted(grouped.keys()):
        print(f"    • {cat_name}: {min(len(grouped[cat_name]), 40)} notizie (estratte: {len(grouped[cat_name])})")

if __name__ == "__main__":
    main()
