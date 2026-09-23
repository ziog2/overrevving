import json, os, urllib.request, re, zlib

SEASON_2026 = "e88b4e43-2209-47aa-8e83-0e0b1cedde6e"
CAT_MOTOGP = "e8c110ad-64aa-4e8e-8a86-f2f152f6a942"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActions-EventUpdater/2.0)"}

FULL_NUM_TO_RIDER = {
    93: "Marc Marquez",
    89: "Jorge Martin",
    63: "Francesco Bagnaia",
    79: "Ai Ogura",
    49: "Fabio Di Giannantonio",
    37: "Pedro Acosta",
    25: "Raul Fernandez",
    54: "Fermin Aldeguer",
    11: "Diogo Moreira",
    33: "Brad Binder",
    36: "Joan Mir",
    10: "Luca Marini",
    21: "Franco Morbidelli",
    43: "Jack Miller",
    7:  "Toprak Razgatlioglu",
    76: "Toprak Razgatlioglu",
    12: "Maverick Viñales",
    20: "Fabio Quartararo",
    23: "Enea Bastianini",
    42: "Alex Rins",
    30: "Takaaki Nakagami",
    35: "Somkiat Chantra",
    73: "Alex Marquez",
    8:  "Alex Marquez",
    72: "Marco Bezzecchi",
    44: "Pol Espargaro",
    47: "Augusto Fernandez",
    27: "Iker Lecuona",
    51: "Michele Pirro",
    5:  "Johann Zarco",
}

def http_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)

def download_bytes(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status == 200:
                return resp.read()
    except Exception as e:
        print(f"  [PDF Download] Info: {url} -> {e}")
    return None

def clean_name(name):
    if not name: return "Rider"
    clean = name.strip()
    if "Vinales" in clean or "Vi.ales" in clean: return "Maverick Viñales"
    if "Munoz" in clean or "Mu.oz" in clean: return "Daniel Muñoz"
    if "Oncu" in clean or ".ncu" in clean: return "Deniz Öncü"
    return clean

def normalize_rider_name(raw_name):
    if not raw_name: return "Rider"
    n = raw_name.upper()
    if "MARQUEZ" in n and "MARC" in n: return "Marc Marquez"
    if "MARQUEZ" in n and ("ALEX" in n or r"A\EX" in n): return "Alex Marquez"
    if "BEZZECCHI" in n: return "Marco Bezzecchi"
    if "MARTIN" in n: return "Jorge Martin"
    if "GIANNANTONIO" in n: return "Fabio Di Giannantonio"
    if "ACOSTA" in n: return "Pedro Acosta"
    if "FERNANDEZ" in n or "FERNAN" in n: return "Raul Fernandez"
    if "EGUER" in n: return "Fermin Aldeguer"
    if "MARINI" in n: return "Luca Marini"
    if "ZARCO" in n: return "Johann Zarco"
    if "MOREIRA" in n: return "Diogo Moreira"
    if "MORBI" in n: return "Franco Morbidelli"
    if "BAGNAIA" in n: return "Francesco Bagnaia"
    if "BIN" in n: return "Brad Binder"
    if "BASTIANINI" in n: return "Enea Bastianini"
    if "ESPARGARO" in n: return "Pol Espargaro"
    if "MILLER" in n: return "Jack Miller"
    if "RINS" in n: return "Alex Rins"
    if "MIR" in n: return "Joan Mir"
    if "QUARTARARO" in n: return "Fabio Quartararo"
    if "VIÑALES" in n or "VINALES" in n or "VI.ALES" in n: return "Maverick Viñales"
    if "OGURA" in n: return "Ai Ogura"
    if "RAZGATLIOGLU" in n: return "Toprak Razgatlioglu"
    if "CHANTRA" in n: return "Somkiat Chantra"
    if "PIRRO" in n: return "Michele Pirro"
    if "NAKAGAMI" in n: return "Takaaki Nakagami"
    return clean_name(raw_name)

def format_class(sess_id):
    if not sess_id: return []
    url = f"https://api.motogp.pulselive.com/motogp/v1/results/session/{sess_id}/classification?categoryUuid={CAT_MOTOGP}"
    try:
        data = http_get(url)
        classification = data.get('classification', [])
        formatted = []
        for idx, c in enumerate(classification, start=1):
            r_name = clean_name(c.get('rider', {}).get('full_name') if c.get('rider') else 'Rider')
            pos_val = c.get('position', idx)
            laps_val = c.get('total_laps') if c.get('total_laps') is not None else (c.get('laps') if c.get('laps') is not None else "-")
            time_val = c.get('time') if c.get('time') else (c.get('best_lap', {}).get('time') if c.get('best_lap') else "-")
            pts_val = c.get('points', None)
            status_val = c.get('status', 'INSTND')
            formatted.append({
                "pos": pos_val,
                "rider": r_name,
                "laps": laps_val,
                "time": time_val if time_val else "-",
                "status": status_val,
                "pts": pts_val
            })
        return formatted
    except Exception as e:
        print(f"Error fetching session {sess_id}: {e}")
        return []

def format_cond(sess):
    if not sess or not sess.get('condition'):
        return "Dry | Air: 20°C | Track: 25°C"
    c = sess.get('condition', {})
    tr = c.get('track', 'Dry')
    air_raw = str(c.get('air', '20'))
    air_num = re.sub(r'[^0-9\-]', '', air_raw) or '20'
    ground_raw = str(c.get('ground', '25'))
    ground_num = re.sub(r'[^0-9\-]', '', ground_raw) or '25'
    return f"{tr} | Air: {air_num}°C | Track: {ground_num}°C"

# --- PDF PARSING HELPERS (PURE PYTHON, NO DEPENDENCIES) ---

def decompress_stream(data):
    if not data: return None
    try:
        return zlib.decompress(data)
    except Exception:
        pass
    try:
        return zlib.decompress(data, -zlib.MAX_WBITS)
    except Exception:
        pass
    try:
        return zlib.decompress(data[2:], -zlib.MAX_WBITS)
    except Exception:
        return None

def parse_cmap_clean(raw_bytes):
    if not raw_bytes: return {}
    cmap = {}
    try:
        txt = raw_bytes.decode('utf-8', errors='ignore')
    except Exception:
        txt = str(raw_bytes)

    range_blocks = re.findall(r'beginbfrange(.*?)endbfrange', txt, re.DOTALL)
    for rb in range_blocks:
        r_matches = re.findall(r'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', rb)
        for s_hex, e_hex, d_hex in r_matches:
            s_start = int(s_hex, 16)
            s_end = int(e_hex, 16)
            d_start = int(d_hex, 16)
            for i in range(s_end - s_start + 1):
                cmap[s_start + i] = chr(d_start + i)

    char_blocks = re.findall(r'beginbfchar(.*?)endbfchar', txt, re.DOTALL)
    for cb in char_blocks:
        c_matches = re.findall(r'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', cb)
        for s_hex, d_hex in c_matches:
            src = int(s_hex, 16)
            dst = int(d_hex, 16)
            cmap[src] = chr(dst)
    return cmap

def parse_dorna_analysis_pdf(pdf_bytes):
    ascii_str = pdf_bytes.decode('latin-1', errors='ignore')
    cmaps = {}
    stream_matches = list(re.finditer(r'(\d+)\s+0\s+obj\s*<<([^>]*)>>\s*stream', ascii_str))

    for m in stream_matches:
        obj_num = int(m.group(1))
        s_start = m.end()
        if s_start < len(pdf_bytes) and pdf_bytes[s_start] == 13: s_start += 1
        if s_start < len(pdf_bytes) and pdf_bytes[s_start] == 10: s_start += 1
        end_idx = ascii_str.find("endstream", s_start)
        if end_idx > s_start:
            s_bytes = pdf_bytes[s_start:end_idx]
            dec_bytes = decompress_stream(s_bytes)
            if dec_bytes:
                try:
                    dec_text = dec_bytes.decode('utf-8', errors='ignore')
                    if "beginbfrange" in dec_text or "beginbfchar" in dec_text:
                        cmaps[obj_num] = parse_cmap_clean(dec_bytes)
                except Exception:
                    pass

    font_to_cmap = {}
    for fm in re.finditer(r'(\d+)\s+0\s+obj\s*<<[^>]*?/ToUnicode\s+(\d+)\s+0\s+R', ascii_str):
        f_obj = int(fm.group(1))
        c_obj = int(fm.group(2))
        if c_obj in cmaps:
            font_to_cmap[f_obj] = cmaps[c_obj]

    rname_to_cmap = {}
    for rm in re.finditer(r'/([A-Za-z0-9_]+)\s+(\d+)\s+0\s+R', ascii_str):
        r_name = rm.group(1)
        f_obj = int(rm.group(2))
        if f_obj in font_to_cmap:
            rname_to_cmap[r_name] = font_to_cmap[f_obj]

    decoded_pages = []
    for m in stream_matches:
        s_start = m.end()
        if s_start < len(pdf_bytes) and pdf_bytes[s_start] == 13: s_start += 1
        if s_start < len(pdf_bytes) and pdf_bytes[s_start] == 10: s_start += 1
        end_idx = ascii_str.find("endstream", s_start)
        if end_idx > s_start:
            s_bytes = pdf_bytes[s_start:end_idx]
            dec_bytes = decompress_stream(s_bytes)
            if not dec_bytes: continue
            content_str = dec_bytes.decode('latin-1', errors='ignore')
            if "BT" in content_str and "ET" in content_str:
                cur_cmap = None
                page_text = ""
                for line in re.split(r'[\r\n]+', content_str):
                    tf_m = re.search(r'/([A-Za-z0-9_]+)\s+[\d\.]+\s+Tf', line)
                    if tf_m and tf_m.group(1) in rname_to_cmap:
                        cur_cmap = rname_to_cmap[tf_m.group(1)]

                    tj_m = re.search(r'\[(.*)\]\s*TJ', line) or re.search(r'\((.*)\)\s*Tj', line)
                    if tj_m:
                        raw_arr = tj_m.group(1)
                        str_matches = re.findall(r'\((.*?)\)', raw_arr)
                        decoded_str = ""
                        for sm in str_matches:
                            val = sm.replace(r'\n', '\n').replace(r'\r', '\r').replace(r'\t', '\t').replace(r'\(', '(').replace(r'\)', ')').replace(r'\\', '\\')
                            for ch in val:
                                b_code = ord(ch)
                                if cur_cmap and b_code in cur_cmap:
                                    decoded_str += cur_cmap[b_code]
                                else:
                                    decoded_str += ch
                        if decoded_str.strip():
                            page_text += decoded_str + " "
                    if "Tm" in line or "Td" in line or "T*" in line:
                        page_text += "\n"
                decoded_pages.append(page_text)
    return "\n=== PAGE ===\n".join(decoded_pages)

def unpack_numbers(text):
    res = text
    for _ in range(4):
        res = re.sub(r'(\d{2}\.\d{3})(\d{2}\.\d{3})', r'\1 \2', res)
        res = re.sub(r'(\d{2}\.\d{3})(\d{3}\.\d{1})', r'\1 \2', res)
        res = re.sub(r'(\d{3}\.\d{1})(\d{2}\.\d{3})', r'\1 \2', res)
        res = re.sub(r'(\d+\'\d{2}\.\d{3})(\d{2}\.\d{3})', r'\1 \2', res)
    return res

def extract_sectors_from_pdf(pdf_bytes, max_laps):
    raw_text = parse_dorna_analysis_pdf(pdf_bytes)
    clean = re.sub(r'(?s)Fastest Lap:.*? MotoGP Sports Entertainment Group, 2026', '', raw_text)
    clean = re.sub(r'(?m)^Official MotoGP Timing.*$', '', clean)
    clean = re.sub(r'(?m)^These data/results.*$', '', clean)
    clean = re.sub(r'(?m)^Page \d+ of \d+.*$', '', clean)
    clean = re.sub(r'(?m)^.*?, (?:Sunday|Saturday).*$', '', clean)
    clean = clean.replace('=== PAGE ===', '')
    clean = unpack_numbers(clean)

    pat = r'(?m)^(?:ITA|SPA|FRA|RSA|AUS|JPN|GER|GBR|POR|USA|THA|BRA|HUN|CZE|NED|INA|MAL|QAT)\s*\n([^\n]+)\s*\n(?:\d+(?:st|nd|rd|th|t\\)|NC)'
    matches = list(re.finditer(pat, clean))
    result = {}

    for i, m in enumerate(matches):
        raw_name = m.group(1).strip()
        canonical_name = normalize_rider_name(raw_name)
        start_idx = m.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(clean)
        block = clean[start_idx:end_idx]

        l_matches = list(re.finditer(r'(\d+\'\d{2}\.\d{3})\s*([\s\S]*?)(?=\d+\'\d{2}\.\d{3}|$)', block))
        laps = []
        lap_num = 1

        for lm in l_matches:
            if lap_num > max_laps: break
            lap_time = lm.group(1)
            sub_block = lm.group(2)
            s_toks = re.findall(r'\b\d{2}\.\d{3}\b', sub_block)
            spd_toks = re.findall(r'\b\d{3}\.\d\b', sub_block)

            if len(s_toks) >= 4:
                laps.append({
                    "lap": lap_num,
                    "time": lap_time,
                    "t1": float(s_toks[0]),
                    "t2": float(s_toks[1]),
                    "t3": float(s_toks[2]),
                    "t4": float(s_toks[3]),
                    "speed": float(spd_toks[0]) if spd_toks else 300.0
                })
                lap_num += 1

        if laps:
            result[canonical_name] = laps
    return result

def extract_lap_chart_from_pdf(pdf_bytes):
    ascii_str = pdf_bytes.decode('latin-1', errors='ignore')
    
    def get_stream(obj_num):
        m = re.search(rf'(?m)^{obj_num}\s+0\s+obj[\s\S]*?stream', ascii_str)
        if m:
            s_start = m.end()
            if s_start < len(pdf_bytes) and pdf_bytes[s_start] == 13: s_start += 1
            if s_start < len(pdf_bytes) and pdf_bytes[s_start] == 10: s_start += 1
            end_idx = ascii_str.find("endstream", s_start)
            if end_idx > s_start:
                return decompress_stream(pdf_bytes[s_start:end_idx])
        return None

    f_to_cmap = {}
    for fm in re.finditer(r'(\d+)\s+0\s+obj[\r\n\s]+<<((?:(?!endobj)[\s\S])*?)/ToUnicode\s+(\d+)\s+0\s+R', ascii_str):
        f_num = int(fm.group(1))
        c_num = int(fm.group(3))
        f_to_cmap[f_num] = parse_cmap_clean(get_stream(c_num))

    r_to_cmap = {}
    for ro in re.finditer(r'(\d+)\s+0\s+obj[\r\n\s]+<<((?:(?!endobj)[\s\S])*?)>>[\r\n\s]*endobj', ascii_str):
        r_dict = ro.group(2)
        for fr in re.finditer(r'/([A-Za-z0-9_]+)\s*(\d+)\s+0\s+R', r_dict):
            r_name = fr.group(1)
            f_num = int(fr.group(2))
            if f_num in f_to_cmap:
                r_to_cmap[r_name] = f_to_cmap[f_num]

    m_cont = re.search(r'/Contents\s+(\d+)\s+0\s+R', ascii_str)
    c_obj = int(m_cont.group(1)) if m_cont else 5
    raw_bytes = get_stream(c_obj)
    if not raw_bytes: return {"totalLaps": 0, "riders": {}}

    tokens = []
    cur_x, cur_y = 0.0, 0.0
    cur_font = ""
    i, blen = 0, len(raw_bytes)

    while i < blen:
        if raw_bytes[i] == 0x2F: # '/'
            f_start = i + 1
            while i < blen and raw_bytes[i] not in (0x20, 0x0A, 0x0D): i += 1
            f_name = raw_bytes[f_start:i].decode('ascii', errors='ignore')
            remain = raw_bytes[i:min(blen, i+30)].decode('ascii', errors='ignore')
            if re.match(r'^\s*[\d\.]+\s+Tf', remain):
                cur_font = f_name

        if i + 1 < blen and raw_bytes[i] == 0x54 and raw_bytes[i+1] == 0x6D: # 'Tm'
            back_str = raw_bytes[max(0, i-80):i].decode('ascii', errors='ignore')
            tm_m = re.search(r'([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s*$', back_str)
            if tm_m:
                cur_x = float(tm_m.group(5))
                cur_y = float(tm_m.group(6))

        if i + 1 < blen and raw_bytes[i] == 0x54 and raw_bytes[i+1] == 0x64: # 'Td'
            back_str = raw_bytes[max(0, i-40):i].decode('ascii', errors='ignore')
            td_m = re.search(r'([\d\.\-]+)\s+([\d\.\-]+)\s*$', back_str)
            if td_m:
                cur_x += float(td_m.group(1))
                cur_y += float(td_m.group(2))

        if i + 1 < blen and raw_bytes[i] == 0x54 and raw_bytes[i+1] == 0x4A: # 'TJ'
            b_idx = i - 1
            while b_idx >= 0 and raw_bytes[b_idx] != 0x5B: b_idx -= 1
            if b_idx >= 0:
                cmap = r_to_cmap.get(cur_font, {})
                local_x = cur_x
                p = b_idx + 1
                while p < i:
                    if raw_bytes[p] == 0x28: # '('
                        p += 1
                        d_str = ""
                        while p < i and raw_bytes[p] != 0x29:
                            b = raw_bytes[p]
                            if b == 0x5C: # '\'
                                p += 1
                                if p >= i: break
                                next_b = raw_bytes[p]
                                if 0x30 <= next_b <= 0x37:
                                    oct_str = chr(next_b)
                                    if p + 1 < i and 0x30 <= raw_bytes[p+1] <= 0x37:
                                        p += 1; oct_str += chr(raw_bytes[p])
                                        if p + 1 < i and 0x30 <= raw_bytes[p+1] <= 0x37:
                                            p += 1; oct_str += chr(raw_bytes[p])
                                    b = int(oct_str, 8)
                                elif next_b == 0x6E: b = 10
                                elif next_b == 0x72: b = 13
                                elif next_b == 0x74: b = 9
                                elif next_b == 0x62: b = 8
                                elif next_b == 0x66: b = 12
                                else: b = next_b
                            d_str += cmap.get(b, chr(b))
                            p += 1
                        if d_str.strip():
                            tokens.append({"x": round(local_x, 2), "y": round(cur_y, 2), "text": d_str.strip()})
                        local_x += (len(d_str) * 5.5)
                    elif (0x30 <= raw_bytes[p] <= 0x39) or raw_bytes[p] == 0x2D:
                        n_start = p
                        while p < i and raw_bytes[p] not in (0x20, 0x28, 0x5D): p += 1
                        n_str = raw_bytes[n_start:p].decode('ascii', errors='ignore')
                        try:
                            kern = float(n_str)
                            local_x -= (kern / 1000.0 * 8.0)
                        except Exception: pass
                        continue
                    p += 1
        i += 1

    table_tokens = [t for t in tokens if 30 <= t["x"] <= 450 and 120 <= t["y"] <= 680]
    grouped = {}
    for t in table_tokens:
        y_key = round(t["y"] / 10.0) * 10.0
        grouped.setdefault(y_key, []).append(t)

    sorted_y = sorted(grouped.keys(), reverse=True)
    lap_table = []

    for yk in sorted_y:
        row_toks = sorted(grouped[yk], key=lambda t: t["x"])
        lap_label_toks = [t for t in row_toks if t["x"] < 55]
        lap_label_str = "".join(t["text"] for t in lap_label_toks).strip()
        has_lap_label = lap_label_str.isdigit()
        lap_label = int(lap_label_str) if has_lap_label else -1

        rider_toks = [t for t in row_toks if t["x"] >= 55]
        if len(rider_toks) < 5: continue

        cells = []
        cur_num = ""
        last_x = -999

        for tok in rider_toks:
            clean_tok = re.sub(r'[^0-9]', '', tok["text"])
            if not clean_tok: continue
            for ch in clean_tok:
                gap = tok["x"] - last_x
                if len(cur_num) == 2 or gap > 5.8:
                    if cur_num:
                        cells.append(int(cur_num))
                        cur_num = ""
                cur_num += ch
                last_x = tok["x"]
        if cur_num:
            cells.append(int(cur_num))

        if len(cells) >= 8:
            if (has_lap_label and lap_label == 0) or (not has_lap_label and len(lap_table) == 0):
                continue
            lap_table.append(cells)

    rider_positions = {}
    num_laps = len(lap_table)

    for l_idx in range(num_laps):
        lap_riders = lap_table[l_idx]
        for p_idx, r_num in enumerate(lap_riders):
            r_name = FULL_NUM_TO_RIDER.get(r_num, f"Rider #{r_num}")
            if r_name not in rider_positions:
                rider_positions[r_name] = [None] * l_idx
            rider_positions[r_name].append(p_idx + 1)
        for r_name in rider_positions:
            while len(rider_positions[r_name]) <= l_idx:
                rider_positions[r_name].append(None)

    return {"totalLaps": num_laps, "riders": rider_positions}

def find_matching_object(text, search_key):
    """
    Finds '"{search_key}": {' and returns (full_start, full_end, parsed_dict_or_raw)
    using depth-balanced brace matching within `text`.
    """
    pattern = rf'"{search_key}"\s*:\s*\{{'
    m = re.search(pattern, text)
    if not m:
        return None, None, None
    full_start = m.start()
    brace_start = text.find('{', full_start)

    depth = 0
    in_string = False
    escape = False
    full_end = None

    for i in range(brace_start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    full_end = i + 1
                    break

    if full_end is None:
        return None, None, None

    json_str = text[brace_start:full_end]
    parsed = None
    try:
        parsed = json.loads(json_str)
    except Exception:
        pass

    return full_start, full_end, parsed

SHORT_TO_CAL_NAME = {
    'THA': 'Thailand', 'BRA': 'Brazil', 'USA': 'USA', 'SPA': 'Spain',
    'FRA': 'France', 'CAT': 'Catalonia', 'ITA': 'Italy', 'HUN': 'Hungary',
    'CZE': 'Czechia', 'NED': 'Netherlands', 'GER': 'Germany', 'GBR': 'Great Britain',
    'ARA': 'Aragon', 'RSM': 'San Marino', 'AUT': 'Austria', 'JPN': 'Japan',
    'INA': 'Indonesia', 'AUS': 'Australia', 'MAL': 'Malaysia', 'QAT': 'Qatar',
    'POR': 'Portugal', 'VAL': 'Valencia'
}

def get_track_cond(sess):
    if not sess:
        return None
    cond = sess.get('condition')
    if isinstance(cond, dict):
        track = cond.get('track', '')
        if track:
            return 'Wet' if 'wet' in str(track).lower() else 'Dry'
    return 'Dry'

def update_file_calendar_weather(file_path, cal_name, weather_str):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if weather is already present with the desired string
    if re.search(rf"name:\s*'{cal_name}'[^\}}]*weather:\s*'{re.escape(weather_str)}'", content):
        return

    # If weather is already present with a partial string (e.g. SPR only), update it
    if re.search(rf"name:\s*'{cal_name}'[^\}}]*weather:\s*'[^']*'", content):
        content = re.sub(rf"(name:\s*'{cal_name}'[^\}}]*weather:\s*)'[^']*'", rf"\1'{weather_str}'", content)
    else:
        # Append weather
        content = re.sub(rf"(name:\s*'{cal_name}',\s*date:\s*'[^']+')(?!\s*,\s*weather:)(\s*\}})", rf"\1, weather: '{weather_str}'\2", content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Aggiornato meteo calendario per {cal_name} in {file_path}: {weather_str}")

# --- MAIN AUTOMATION FUNCTION ---

def main():
    event_html_path = "event.html"
    if not os.path.exists(event_html_path):
        print(f"File {event_html_path} non trovato.")
        return

    with open(event_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    orig_len = len(html_content)

    events_url = f"https://api.motogp.pulselive.com/motogp/v1/results/events?seasonUuid={SEASON_2026}&categoryUuid={CAT_MOTOGP}"
    try:
        events = http_get(events_url)
    except Exception as e:
        print(f"Errore caricamento lista eventi: {e}")
        return

    # Filter events: FINISHED or currently ongoing (RUNNING, LIVE, IN_PROGRESS)
    relevant_events = [
        ev for ev in events
        if isinstance(ev, dict)
        and ev.get('status') in ('FINISHED', 'RUNNING', 'LIVE', 'IN_PROGRESS')
        and not str(ev.get('short_name', '')).endswith(('1', '2', '3'))
    ]

    updated = False

    for ev in relevant_events:
        short = ev.get('short_name')
        ev_id = ev.get('id')
        ev_status = ev.get('status')
        if not short or not ev_id: continue

        print(f"\n==========================================")
        print(f"Controllo evento {short} ({ev.get('name')}) [Status: {ev_status}]")

        sessions_url = f"https://api.motogp.pulselive.com/motogp/v1/results/sessions?eventUuid={ev_id}&categoryUuid={CAT_MOTOGP}"
        try:
            sessions = http_get(sessions_url)
        except Exception as e:
            print(f"Errore caricamento sessioni {short}: {e}")
            continue

        fp_sess = [s for s in sessions if s.get('type') == 'FP']
        pr_sess = next((s for s in sessions if s.get('type') == 'PR'), None)
        q_sess  = sorted([s for s in sessions if s.get('type') == 'Q'], key=lambda s: s.get('date', ''))
        spr_sess = next((s for s in sessions if s.get('type') == 'SPR'), None)
        wup_sess = next((s for s in sessions if s.get('type') == 'WUP'), None)
        rac_sess = next((s for s in sessions if s.get('type') == 'RAC'), None)

        fp1 = format_class(fp_sess[0]['id']) if len(fp_sess) >= 1 else []
        pr  = format_class(pr_sess['id']) if pr_sess else []
        fp2 = format_class(fp_sess[1]['id']) if len(fp_sess) >= 2 else []

        q1_sess = q_sess[0] if len(q_sess) >= 1 else None
        q2_sess = q_sess[1] if len(q_sess) >= 2 else None

        q1 = format_class(q1_sess['id']) if q1_sess else []
        q2 = format_class(q2_sess['id']) if q2_sess else []
        spr = format_class(spr_sess['id']) if spr_sess else []
        wup = format_class(wup_sess['id']) if wup_sess else []
        rac = format_class(rac_sess['id']) if rac_sess else []

        # Build grid if Q1 & Q2 are available
        grid = []
        if q2:
            promoted = set()
            if len(q1) >= 2:
                promoted.add(q1[0]['rider'])
                promoted.add(q1[1]['rider'])
            p = 1
            for r in q2:
                grid.append({"pos": p, "rider": r['rider'], "laps": r['laps'], "time": r['time'], "status": "INSTND", "pts": None})
                p += 1
            for r in q1:
                if r['rider'] not in promoted:
                    grid.append({"pos": p, "rider": r['rider'], "laps": r['laps'], "time": r['time'], "status": "INSTND", "pts": None})
                    p += 1

        # 1. Update STATIC_EVENT_DATA using bounded brace matching
        idx_s_start = html_content.find('const STATIC_EVENT_DATA = {')
        idx_s_end = html_content.find('function getQueryParams()', idx_s_start) if idx_s_start != -1 else -1

        if idx_s_start != -1 and idx_s_end != -1:
            s_slice = html_content[idx_s_start:idx_s_end]
            s_start, s_end, s_parsed = find_matching_object(s_slice, short)

            if s_start is not None and s_end is not None:
                has_race = False
                has_spr = False
                if isinstance(s_parsed, dict):
                    has_race = bool(s_parsed.get("race") and isinstance(s_parsed["race"], list) and len(s_parsed["race"]) > 0)
                    has_spr = bool(s_parsed.get("sprint") and isinstance(s_parsed["sprint"], list) and len(s_parsed["sprint"]) > 0)

                needs_update = False
                if not has_race and rac:
                    needs_update = True
                elif not has_spr and spr:
                    needs_update = True

                if needs_update:
                    existing = s_parsed if isinstance(s_parsed, dict) else {}
                    static_obj = {
                        "fp1": fp1 if fp1 else (existing.get("fp1") if isinstance(existing.get("fp1"), list) else []),
                        "pr": pr if pr else (existing.get("pr") if isinstance(existing.get("pr"), list) else []),
                        "fp2": fp2 if fp2 else (existing.get("fp2") if isinstance(existing.get("fp2"), list) else []),
                        "q1": q1 if q1 else (existing.get("q1") if isinstance(existing.get("q1"), list) else []),
                        "q2": q2 if q2 else (existing.get("q2") if isinstance(existing.get("q2"), list) else []),
                        "grid": grid if grid else (existing.get("grid") if isinstance(existing.get("grid"), list) else []),
                        "sprint": spr if spr else (existing.get("sprint") if isinstance(existing.get("sprint"), list) else []),
                        "wup": wup if wup else (existing.get("wup") if isinstance(existing.get("wup"), list) else []),
                        "race": rac if rac else (existing.get("race") if isinstance(existing.get("race"), list) else [])
                    }
                    static_json = json.dumps(static_obj, separators=(',', ':'))
                    new_s_entry = f'"{short}": {static_json}'
                    new_s_slice = s_slice[:s_start] + new_s_entry + s_slice[s_end:]
                    html_content = html_content[:idx_s_start] + new_s_slice + html_content[idx_s_end:]
                    updated = True
                    label = "Gara Domenica" if rac else ("Sprint Sabato" if spr else "Qualifiche")
                    print(f"✓ Aggiornato blocco {short} in STATIC_EVENT_DATA ({label})!")

        # 2. Update SESSION_WEATHER_DATA using bounded brace matching
        idx_w_start = html_content.find('const SESSION_WEATHER_DATA = {')
        idx_w_end = html_content.find('const STATIC_EVENT_DATA =', idx_w_start) if idx_w_start != -1 else -1

        if idx_w_start != -1 and idx_w_end != -1:
            w_slice = html_content[idx_w_start:idx_w_end]
            w_start, w_end, w_parsed = find_matching_object(w_slice, short)

            if w_start is not None and w_end is not None:
                weather_obj = {
                    "grid": format_cond(rac_sess or q2_sess),
                    "race": format_cond(rac_sess),
                    "sprint": format_cond(spr_sess),
                    "fp1": format_cond(fp_sess[0] if len(fp_sess) >= 1 else None),
                    "fp2": format_cond(fp_sess[1] if len(fp_sess) >= 2 else None),
                    "wup": format_cond(wup_sess),
                    "pr": format_cond(pr_sess),
                    "q2": format_cond(q2_sess),
                    "q1": format_cond(q1_sess)
                }
                has_w = any(isinstance(v, str) and ('°C' in v or 'Wet' in v) for v in weather_obj.values())
                if has_w:
                    merged_w = dict(w_parsed) if isinstance(w_parsed, dict) else weather_obj
                    for k, v in weather_obj.items():
                        if '°C' in v or 'Wet' in v:
                            merged_w[k] = v
                    if merged_w != w_parsed:
                        merged_w_json = json.dumps(merged_w, separators=(',', ':'))
                        new_w_entry = f'"{short}": {merged_w_json}'
                        new_w_slice = w_slice[:w_start] + new_w_entry + w_slice[w_end:]
                        html_content = html_content[:idx_w_start] + new_w_slice + html_content[idx_w_end:]
                        updated = True
                        print(f"✓ Aggiornato meteo per {short} in SESSION_WEATHER_DATA!")

        # Update calendar badges in category.html and motogp.html
        cal_name = SHORT_TO_CAL_NAME.get(short)
        if cal_name:
            spr_cond = get_track_cond(spr_sess) if spr_sess else ('Dry' if spr else None)
            rac_cond = get_track_cond(rac_sess) if rac_sess else ('Dry' if rac else None)
            if spr_cond and rac_cond:
                cal_badge = f"SPR: {spr_cond} RACE: {rac_cond}"
            elif spr_cond:
                cal_badge = f"SPR: {spr_cond}"
            elif rac_cond:
                cal_badge = f"RACE: {rac_cond}"
            else:
                cal_badge = None

            if cal_badge:
                update_file_calendar_weather("category.html", cal_name, cal_badge)
                update_file_calendar_weather("motogp.html", cal_name, cal_badge)

        # 3. LAP CHARTS & SECTOR TELEMETRY

        # 3.1 SPRINT (Available Saturday evening)
        if spr:
            idx_spr_charts = html_content.find('const EVENT_LAP_CHARTS_DATA =')
            idx_rac_in_charts = html_content.find('"RAC":', idx_spr_charts) if idx_spr_charts != -1 else -1
            spr_chart_present = (f'"{short}":' in html_content[idx_spr_charts:idx_rac_in_charts]) if idx_rac_in_charts != -1 else False

            if not spr_chart_present:
                spr_lap_pdf_url = f"https://resources.motogp.com/files/results/2026/{short}/MotoGP/SPR/LapChart.pdf"
                spr_lap_bytes = download_bytes(spr_lap_pdf_url)
                if spr_lap_bytes:
                    print(f"  Estrazione LapChart Sprint per {short}...")
                    spr_lap_data = extract_lap_chart_from_pdf(spr_lap_bytes)
                    if spr_lap_data and spr_lap_data.get("riders"):
                        spr_lap_json = json.dumps(spr_lap_data, separators=(',', ':'))
                        m_spr_c = re.search(r'"SPR":\s*\{', html_content[idx_spr_charts:idx_rac_in_charts])
                        if m_spr_c:
                            pos = idx_spr_charts + m_spr_c.end()
                            html_content = html_content[:pos] + f'\n        "{short}": ' + spr_lap_json + ',' + html_content[pos:]
                            updated = True
                            print(f"  ✓ Inserito LapChart Sprint {short} ({spr_lap_data['totalLaps']} giri)!")

            idx_spr_sec_start = html_content.find('const EVENT_SPR_LAPS_DATA =')
            idx_rac_sec_start = html_content.find('const EVENT_LAPS_DATA =')
            spr_sec_present = (f'"{short}":' in html_content[idx_spr_sec_start:idx_rac_sec_start]) if (idx_spr_sec_start != -1 and idx_rac_sec_start != -1) else False

            if not spr_sec_present:
                spr_ana_pdf_url = f"https://resources.motogp.com/files/results/2026/{short}/MotoGP/SPR/Analysis.pdf"
                spr_ana_bytes = download_bytes(spr_ana_pdf_url)
                if spr_ana_bytes:
                    print(f"  Estrazione Settori Sprint per {short}...")
                    spr_sectors_data = extract_sectors_from_pdf(spr_ana_bytes, max_laps=15)
                    if spr_sectors_data:
                        spr_sec_json = json.dumps(spr_sectors_data, separators=(',', ':'))
                        m_spr_sec = re.search(r'const EVENT_SPR_LAPS_DATA\s*=\s*\{', html_content)
                        if m_spr_sec:
                            pos = m_spr_sec.end()
                            html_content = html_content[:pos] + f'\n    "{short}": ' + spr_sec_json + ',' + html_content[pos:]
                            updated = True
                            print(f"  ✓ Inseriti Settori Sprint {short} ({len(spr_sectors_data)} piloti)!")

        # 3.2 MAIN RACE (Available Sunday evening)
        if rac:
            idx_rac_charts = html_content.find('"RAC":')
            idx_spr_sec = html_content.find('const EVENT_SPR_LAPS_DATA =', idx_rac_charts) if idx_rac_charts != -1 else -1
            rac_chart_present = (f'"{short}":' in html_content[idx_rac_charts:idx_spr_sec]) if idx_spr_sec != -1 else False

            if not rac_chart_present:
                rac_lap_pdf_url = f"https://resources.motogp.com/files/results/2026/{short}/MotoGP/RAC/LapChart.pdf"
                rac_lap_bytes = download_bytes(rac_lap_pdf_url)
                if rac_lap_bytes:
                    print(f"  Estrazione LapChart Gara per {short}...")
                    rac_lap_data = extract_lap_chart_from_pdf(rac_lap_bytes)
                    if rac_lap_data and rac_lap_data.get("riders"):
                        rac_lap_json = json.dumps(rac_lap_data, separators=(',', ':'))
                        m_rac_c = re.search(r'"RAC":\s*\{', html_content[idx_rac_charts:idx_spr_sec])
                        if m_rac_c:
                            pos = idx_rac_charts + m_rac_c.end()
                            html_content = html_content[:pos] + f'\n        "{short}": ' + rac_lap_json + ',' + html_content[pos:]
                            updated = True
                            print(f"  ✓ Inserito LapChart Gara {short} ({rac_lap_data['totalLaps']} giri)!")

            idx_rac_sec = html_content.find('const EVENT_LAPS_DATA =')
            rac_sec_present = (f'"{short}":' in html_content[idx_rac_sec:]) if idx_rac_sec != -1 else False

            if not rac_sec_present:
                rac_ana_pdf_url = f"https://resources.motogp.com/files/results/2026/{short}/MotoGP/RAC/Analysis.pdf"
                rac_ana_bytes = download_bytes(rac_ana_pdf_url)
                if rac_ana_bytes:
                    print(f"  Estrazione Settori Gara per {short}...")
                    rac_sectors_data = extract_sectors_from_pdf(rac_ana_bytes, max_laps=30)
                    if rac_sectors_data:
                        rac_sec_json = json.dumps(rac_sectors_data, separators=(',', ':'))
                        m_rac_sec = re.search(r'const EVENT_LAPS_DATA\s*=\s*\{', html_content)
                        if m_rac_sec:
                            pos = m_rac_sec.end()
                            html_content = html_content[:pos] + f'\n    "{short}": ' + rac_sec_json + ',' + html_content[pos:]
                            updated = True
                            print(f"  ✓ Inseriti Settori Gara {short} ({len(rac_sectors_data)} piloti)!")

    if updated:
        # Integrity verification before writing
        if len(html_content) < orig_len * 0.95:
            raise RuntimeError(f"ABORT: html_content shrunk suspiciously from {orig_len} to {len(html_content)}")
        for req_tag in ("const SESSION_WEATHER_DATA =", "const STATIC_EVENT_DATA =", "const EVENT_LAP_CHARTS_DATA =", "const EVENT_SPR_LAPS_DATA =", "const EVENT_LAPS_DATA =", "function initEventPage()"):
            if req_tag not in html_content:
                raise RuntimeError(f"ABORT: Missing required section '{req_tag}' in html_content")

        with open(event_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print("\n✓ event.html aggiornato e validato con successo!")
    else:
        print("\nNessun nuovo dato da aggiornare in event.html.")

if __name__ == '__main__':
    main()
