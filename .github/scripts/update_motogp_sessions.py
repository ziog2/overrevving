#!/usr/bin/env python3
"""
update_motogp_sessions.py
=========================
Unified MotoGP Live Session & Analysis Automation Engine.

Automates the ingestion of:
1. Official Dorna Classification PDFs (instant classification + official weather).
2. Dorna Analysis PDFs (stints, tyre compounds, flying laps, sector times T1-T4).
3. Moto2 and Moto3 session and lap chart synchronization.
4. Export database (CSV & Excel) synchronization.

Ensures the website updates immediately as soon as Dorna publishes session PDFs
or PulseLive API updates.
"""

import os
import sys
import re
import io
import json
import urllib.request
import urllib.error
import pypdf

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(os.path.join(BASE_DIR, ".github", "scripts"))

# Import existing helpers from update_event_data
from update_event_data import (
    find_matching_object,
    clean_name,
    normalize_rider_name,
    FULL_NUM_TO_RIDER,
    SHORT_TO_CAL_NAME,
    update_file_calendar_weather,
    format_class,
    format_cond,
    update_moto2,
    update_moto3,
    extract_sectors_from_pdf,
    compute_lap_chart_from_sectors
)

ALL_ROUNDS = [
    'THA', 'BRA', 'USA', 'SPA', 'FRA', 'CAT', 'ITA', 'HUN', 'CZE', 'NED',
    'GER', 'GBR', 'ARA', 'RSM', 'AUT', 'JPN', 'INA', 'AUS', 'MAL', 'QAT',
    'POR', 'VAL'
]

MOTOGP_RIDER_NUMBERS = {
    'Francesco Bagnaia': '63',
    'Marc Marquez': '93',
    'Jorge Martin': '89',
    'Marco Bezzecchi': '72',
    'Fabio Di Giannantonio': '49',
    'Franco Morbidelli': '21',
    'Pedro Acosta': '37',
    'Brad Binder': '33',
    'Ai Ogura': '79',
    'Raul Fernandez': '25',
    'Luca Marini': '10',
    'Joan Mir': '36',
    'Alex Marquez': '73',
    'Fermin Aldeguer': '54',
    'Enea Bastianini': '23',
    'Maverick Viñales': '12',
    'Maverick Vinales': '12',
    'Fabio Quartararo': '20',
    'Alex Rins': '42',
    'Jack Miller': '43',
    'Toprak Razgatlioglu': '07',
    'Diogo Moreira': '11',
    'Johann Zarco': '5',
    'Somkiat Chantra': '35',
    'Aleix Espargaro': '41',
    'Pol Espargaro': '44',
    'Augusto Fernandez': '37',
    'Lorenzo Savadori': '32',
    'Michele Pirro': '51',
    'Iker Lecuona': '27',
    'Jake Dixon': '96',
    'Remy Gardner': '87',
    'Dani Pedrosa': '26',
    'Stefan Bradl': '6',
    'Andrea Iannone': '29',
    'Andrea Dovizioso': '04',
    'Cal Crutchlow': '35',
    'Takaaki Nakagami': '30',
    'Jonas Folger': '94'
}

def get_rider_code(name, fallback_num):
    num = MOTOGP_RIDER_NUMBERS.get(name, fallback_num)
    parts = name.strip().split()
    first_init = parts[0][0].upper() if parts else "X"
    last_init = parts[-1][0].upper() if parts else "X"
    return f"{first_init}{last_init}{num}", str(num)

def download_url(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read()
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  [HTTP {e.code}] {url}")
    except Exception as e:
        print(f"  [Network] {url} -> {e}")
    return None

def parse_classification_pdf(pdf_bytes):
    """
    Parses official Dorna Classification.pdf:
    Returns list of dicts:
      [{'pos': 1, 'rider': 'Marc Marquez', 'laps': 16, 'time': '01:52.278', 'status': 'INSTND', 'pts': None}, ...]
    and weather string:
      "Dry | Air: 34°C | Track: 42°C"
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
    except Exception as e:
        print(f"  Error reading Classification PDF with pypdf: {e}")
        return [], ""

    # Extract weather from footer
    weather_str = ""
    w_match = re.search(r'Air:\s*(\d+)°\s*(?:Ground|Track):\s*(\d+)°(?:\s*Condition:\s*([A-Za-z]+))?', full_text, re.IGNORECASE)
    if w_match:
        air = w_match.group(1)
        track = w_match.group(2)
        cond = w_match.group(3) or "Dry"
        if 'condition: wet' in full_text.lower():
            cond = "Wet"
        weather_str = f"{cond.capitalize()} | Air: {air}°C | Track: {track}°C"

    # Line parsing: e.g.
    # DUCATI 93 Marc MARQUEZ SPA 354.0 1 1'52.278 15 16 Ducati Lenovo Team
    lines = full_text.split('\n')
    results = []

    for line in lines:
        m = re.search(r'\b(\d{1,2})\s+(\d+\'\d{2}\.\d{3})\s+(\d+)\s+(\d+)\b', line)
        if m:
            pos = int(m.group(1))
            time_raw = m.group(2)
            m_part, s_part = time_raw.split("'")
            formatted_time = f"{int(m_part):02d}:{s_part}"
            total_laps = int(m.group(4))

            pre = line[:m.start()].strip()
            # Clean trailing speed and nation
            pre = re.sub(r'\s+\d{2,3}\.\d\s*$', '', pre)
            pre = re.sub(r'\s+[A-Z]{3}\s*$', '', pre)
            # Remove leading bike manufacturer
            pre = re.sub(r'^(?:DUCATI|APRILIA|KTM|HONDA|YAMAHA)\s+', '', pre, flags=re.IGNORECASE)
            # Remove rider number
            pre = re.sub(r'^\d{1,2}\s+', '', pre)

            canonical_name = normalize_rider_name(pre.strip())

            results.append({
                'pos': pos,
                'rider': canonical_name,
                'laps': total_laps,
                'time': formatted_time,
                'status': 'INSTND',
                'pts': None
            })

    results.sort(key=lambda x: x['pos'])
    return results, weather_str

def parse_analysis_pdf_all(pdf_bytes):
    """
    Parses Dorna Analysis.pdf and extracts:
    1. Stints data (runs, tyre compounds, flying laps, fastest laps).
    2. Sector data (T1, T2, T3, T4 for every lap).
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
    except Exception as e:
        print(f"  Error reading Analysis PDF with pypdf: {e}")
        return {}, {}

    # Rider headers: e.g. "93 Ducati Lenovo Team\nSPA Marc MARQUEZ\n1st\nRuns=3 Total laps=15"
    matches = list(re.finditer(
        r'(?m)^(\d{1,2})\s+[^\n]+\n[A-Z]{3}\s+([^\n]+)\n(?:\d+(?:st|nd|rd|th)|NC|unfinished)[^\n]*\nRuns=(\d+)',
        full_text
    ))

    riders_stints = {}
    riders_sectors = {}

    for idx, m in enumerate(matches):
        num = m.group(1).strip()
        raw_name = m.group(2).strip()
        canonical_name = normalize_rider_name(raw_name)
        code, official_num = get_rider_code(canonical_name, num)

        start_pos = m.end()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
        rider_block = full_text[start_pos:end_pos]

        runs_stints = []
        runs_sectors = []
        current_run_stint = None
        current_run_sector = None

        total_laps_so_far = 0

        for line in rider_block.split('\n'):
            # Detect new run
            run_m = re.search(r'Run\s*#.*?(\d+)\s+Slick-([A-Za-z]+)\s+Slick-([A-Za-z]+)', line)
            if run_m:
                r_num = int(run_m.group(1))
                f_tyre = run_m.group(2)[0].upper()
                r_tyre = run_m.group(3)[0].upper()

                if current_run_stint and current_run_stint['laps']:
                    runs_stints.append(current_run_stint)
                if current_run_sector and current_run_sector['laps']:
                    runs_sectors.append(current_run_sector)

                current_run_stint = {
                    'run': r_num,
                    'front': f_tyre,
                    'rear': r_tyre,
                    'laps': []
                }
                current_run_sector = {
                    'run': r_num,
                    'front': f_tyre,
                    'rear': r_tyre,
                    'laps': []
                }
                continue

            # Detect lap time & sectors
            # Format: 1'52.278 15 28.537 29.593 25.041 354.0 29.107
            # or with P for pit: 1'58.234 16 28.900 30.123 25.400 P 33.811
            lap_m = re.search(
                r"(\d+'\d{2}\.\d{3})\s+(\d+)\s+(\d{1,2}\.\d{3})\s+(\d{1,2}\.\d{3})\s+(\d{1,2}\.\d{3})(?:\s+[\d\.]+)?\s*(P)?\s*(\d{1,2}\.\d{3})",
                line
            )
            if lap_m:
                time_str = lap_m.group(1)
                lap_num = int(lap_m.group(2))
                t1 = float(lap_m.group(3))
                t2 = float(lap_m.group(4))
                t3 = float(lap_m.group(5))
                is_pit = bool(lap_m.group(6))
                t4 = float(lap_m.group(7))

                m_part, s_part = time_str.split("'")
                sec = round(int(m_part) * 60 + float(s_part), 3)

                if current_run_stint is None:
                    current_run_stint = {'run': 1, 'front': 'M', 'rear': 'M', 'laps': []}
                if current_run_sector is None:
                    current_run_sector = {'run': 1, 'front': 'M', 'rear': 'M', 'laps': []}

                current_run_stint['laps'].append({
                    'time': time_str,
                    'sec': sec,
                    'pit': is_pit
                })

                current_run_sector['laps'].append({
                    'lap': lap_num,
                    'time': time_str,
                    'sec': sec,
                    't1': t1,
                    't2': t2,
                    't3': t3,
                    't4': t4,
                    'pit': is_pit
                })

        if current_run_stint and current_run_stint['laps']:
            runs_stints.append(current_run_stint)
        if current_run_sector and current_run_sector['laps']:
            runs_sectors.append(current_run_sector)

        # Process stints summary
        processed_runs = []
        total_laps_count = 0
        for r in runs_stints:
            laps = r['laps']
            laps_count = len(laps)
            start_lap = total_laps_count + 1
            end_lap = total_laps_count + laps_count
            total_laps_count += laps_count

            valid_secs = [l['sec'] for l in laps if not l['pit']]
            if valid_secs:
                min_sec = min(valid_secs)
                flying = [l for l in laps if l['sec'] <= min_sec * 1.15 and l['sec'] < 180.0]
                if flying:
                    best = min(flying, key=lambda x: x['sec'])
                    fastest_str = best['time']
                    fastest_sec = best['sec']
                    flying_secs = sorted([round(l['sec'], 3) for l in flying])
                else:
                    fastest_str = laps[0]['time']
                    fastest_sec = laps[0]['sec']
                    flying_secs = []
            else:
                fastest_str = laps[0]['time'] if laps else "-"
                fastest_sec = laps[0]['sec'] if laps else 0
                flying_secs = []

            processed_runs.append({
                'front': r['front'],
                'rear': r['rear'],
                'lapsCount': laps_count,
                'startLap': start_lap,
                'endLap': end_lap,
                'fastest': fastest_str,
                'fastestSec': fastest_sec,
                'flying': flying_secs,
                'laps': laps
            })

        riders_stints[canonical_name] = {
            'number': official_num,
            'code': code,
            'totalLaps': total_laps_count,
            'runs': processed_runs
        }

        riders_sectors[canonical_name] = {
            'number': official_num,
            'name': canonical_name,
            'runs': runs_sectors
        }

    return riders_stints, riders_sectors

def update_session_datasets(session_name):
    """
    Checks all rounds for Dorna Analysis.pdf for `session_name` (FP1, PR, FP2)
    and updates JSON and JS files.
    """
    sess_lower = session_name.lower()
    full_path = os.path.join(BASE_DIR, 'data', f'motogp_{sess_lower}_stints.json')
    compact_path = os.path.join(BASE_DIR, 'data', f'motogp_{sess_lower}_compact.json')
    js_data_path = os.path.join(BASE_DIR, 'js', f'motogp_{sess_lower}_data.js')
    sectors_path = os.path.join(BASE_DIR, 'data', f'motogp_{sess_lower}_sectors.json')
    js_sectors_path = os.path.join(BASE_DIR, 'js', f'motogp_{sess_lower}_sectors.js')

    # Load existing datasets
    stints_data = {}
    if os.path.exists(full_path):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                stints_data = json.load(f)
        except Exception:
            stints_data = {}

    sectors_data = {}
    if os.path.exists(sectors_path):
        try:
            with open(sectors_path, 'r', encoding='utf-8') as f:
                sectors_data = json.load(f)
        except Exception:
            sectors_data = {}

    any_updated = False

    for rnd in ALL_ROUNDS:
        # Check if already present and has riders
        if rnd in stints_data and len(stints_data[rnd]) > 0 and rnd in sectors_data and len(sectors_data[rnd]) > 0:
            # If round is not the current one (e.g. past rounds), skip re-download
            if rnd != 'QAT':
                continue

        url = f"https://resources.motogp.com/files/results/2026/{rnd}/MotoGP/{session_name}/Analysis.pdf"
        pdf_bytes = download_url(url)
        if not pdf_bytes:
            continue

        r_stints, r_sectors = parse_analysis_pdf_all(pdf_bytes)
        if r_stints and len(r_stints) > 0:
            stints_data[rnd] = r_stints
            sectors_data[rnd] = r_sectors
            any_updated = True
            print(f"  ✓ {rnd} {session_name}: parsed {len(r_stints)} riders from Analysis.pdf!")

    if any_updated:
        # Save full stints JSON
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(stints_data, f, indent=2, ensure_ascii=False)

        # Build compact stints
        compact = {}
        for rnd, riders in stints_data.items():
            compact[rnd] = {}
            for r_name, r_info in riders.items():
                valid_runs = []
                for r in r_info.get('runs', []):
                    if r.get('lapsCount', 0) <= 0:
                        continue
                    valid_runs.append({
                        'front': r['front'],
                        'rear': r['rear'],
                        'lapsCount': r['lapsCount'],
                        'startLap': r['startLap'],
                        'endLap': r['endLap'],
                        'fastest': r['fastest'],
                        'fastestSec': r['fastestSec'],
                        'flying': r.get('flying', [])
                    })
                if valid_runs:
                    compact[rnd][r_name] = {
                        'number': r_info['number'],
                        'code': r_info['code'],
                        'totalLaps': r_info['totalLaps'],
                        'runs': valid_runs
                    }

        compact_json = json.dumps(compact, separators=(',', ':'), ensure_ascii=False)
        with open(compact_path, 'w', encoding='utf-8') as f:
            f.write(compact_json)

        js_var_name = f"EVENT_{session_name.upper()}_STINTS_DATA"
        with open(js_data_path, 'w', encoding='utf-8') as f:
            f.write(f"const {js_var_name} = {compact_json};\n")
            f.write(f"if (typeof window !== 'undefined') window.{js_var_name} = {js_var_name};\n")

        # Save sectors JSON and JS
        sectors_json = json.dumps(sectors_data, separators=(',', ':'), ensure_ascii=False)
        with open(sectors_path, 'w', encoding='utf-8') as f:
            f.write(sectors_json)

        js_sec_var = f"EVENT_{session_name.upper()}_SECTORS_DATA"
        with open(js_sectors_path, 'w', encoding='utf-8') as f:
            f.write(f"const {js_sec_var} = {sectors_json};\n")
            f.write(f"if (typeof window !== 'undefined') window.{js_sec_var} = {js_sec_var};\n")

        print(f"  ✓ Saved updated {session_name} stint and sector datasets.")
    return any_updated

def update_event_html_results():
    """
    Checks Dorna Classification PDFs and PulseLive API to update STATIC_EVENT_DATA
    and SESSION_WEATHER_DATA in event.html.
    """
    event_path = os.path.join(BASE_DIR, 'event.html')
    if not os.path.exists(event_path):
        return False

    with open(event_path, 'r', encoding='utf-8') as f:
        html = f.read()

    orig_html = html
    updated = False

    # Extract STATIC_EVENT_DATA
    idx_s_start = html.find('const STATIC_EVENT_DATA = {')
    idx_s_end = html.find('function getQueryParams()', idx_s_start) if idx_s_start != -1 else -1
    if idx_s_start == -1 or idx_s_end == -1:
        print("  Error: Cannot find STATIC_EVENT_DATA in event.html")
        return False

    s_slice = html[idx_s_start:idx_s_end]

    # Extract SESSION_WEATHER_DATA
    idx_w_start = html.find('const SESSION_WEATHER_DATA = {')
    idx_w_end = html.find('const STATIC_EVENT_DATA =', idx_w_start) if idx_w_start != -1 else -1
    w_slice = html[idx_w_start:idx_w_end] if idx_w_start != -1 and idx_w_end != -1 else ""

    sessions_map = [
        ('FP1', 'fp1'),
        ('PR', 'pr'),
        ('FP2', 'fp2'),
        ('Q1', 'q1'),
        ('Q2', 'q2'),
        ('SPR', 'sprint'),
        ('WUP', 'wup'),
        ('RAC', 'race'),
    ]

    for rnd in ALL_ROUNDS:
        s_start, s_end, s_parsed = find_matching_object(s_slice, rnd)
        static_obj = s_parsed if isinstance(s_parsed, dict) else {}

        w_start, w_end, w_parsed = find_matching_object(w_slice, rnd) if w_slice else (None, None, None)
        weather_obj = w_parsed if isinstance(w_parsed, dict) else {}

        round_static_changed = False
        round_weather_changed = False

        for sess_code, sess_key in sessions_map:
            # Check Dorna Classification PDF
            class_url = f"https://resources.motogp.com/files/results/2026/{rnd}/MotoGP/{sess_code}/Classification.pdf"
            pdf_b = download_url(class_url)
            if pdf_b:
                results, weather = parse_classification_pdf(pdf_b)
                if results and len(results) > 0:
                    current_res = static_obj.get(sess_key, [])
                    # Check if missing, empty, or has corrupted placeholder (like Deniz Öncü anywhere in MotoGP)
                    is_corrupt = any(('Öncü' in str(r.get('rider', '')) or 'Oncu' in str(r.get('rider', ''))) for r in current_res)
                    should_update = (not current_res or len(current_res) == 0 or is_corrupt)
                    if not should_update and len(results) >= len(current_res) and current_res != results:
                        if any(c.get('rider') != d.get('rider') for c, d in zip(current_res, results)):
                            should_update = True
                    if should_update:
                        static_obj[sess_key] = results
                        round_static_changed = True
                        print(f"  ✓ {rnd} {sess_code}: Updated classification from Dorna PDF ({len(results)} riders)!")

                if weather and ('°C' in weather):
                    if weather_obj.get(sess_key) != weather:
                        weather_obj[sess_key] = weather
                        round_weather_changed = True
                        print(f"  ✓ {rnd} {sess_code}: Updated weather from Dorna PDF ({weather})!")

        # If Q1 and Q2 are present but grid is missing
        if static_obj.get('q2') and static_obj.get('q1') and (not static_obj.get('grid') or len(static_obj['grid']) == 0):
            promoted = set(r['rider'] for r in static_obj['q1'][:2])
            new_grid = []
            p = 1
            for r in static_obj['q2']:
                new_grid.append({'pos': p, 'rider': r['rider'], 'laps': r.get('laps', '-'), 'time': r.get('time', '-'), 'status': 'INSTND', 'pts': None})
                p += 1
            for r in static_obj['q1']:
                if r['rider'] not in promoted:
                    new_grid.append({'pos': p, 'rider': r['rider'], 'laps': r.get('laps', '-'), 'time': r.get('time', '-'), 'status': 'INSTND', 'pts': None})
                    p += 1
            static_obj['grid'] = new_grid
            round_static_changed = True
            print(f"  ✓ {rnd}: Computed starting grid from Q1 & Q2!")

        if round_static_changed:
            new_json = json.dumps(static_obj, separators=(',', ':'), ensure_ascii=False)
            if s_start is not None and s_end is not None:
                new_entry = f'"{rnd}": {new_json}'
                s_slice = s_slice[:s_start] + new_entry + s_slice[s_end:]
            else:
                m_ins = re.search(r'const STATIC_EVENT_DATA\s*=\s*\{', s_slice)
                pos = m_ins.end()
                s_slice = s_slice[:pos] + f'\n  "{rnd}": {new_json},' + s_slice[pos:]
            html = html[:idx_s_start] + s_slice + html[idx_s_end:]
            idx_s_end = idx_s_start + len(s_slice)
            updated = True

        if round_weather_changed and w_slice:
            new_w_json = json.dumps(weather_obj, separators=(',', ':'), ensure_ascii=False)
            if w_start is not None and w_end is not None:
                new_w_entry = f'"{rnd}": {new_w_json}'
                w_slice = w_slice[:w_start] + new_w_entry + w_slice[w_end:]
            else:
                m_ins = re.search(r'const SESSION_WEATHER_DATA\s*=\s*\{', w_slice)
                pos = m_ins.end()
                w_slice = w_slice[:pos] + f'\n  "{rnd}": {new_w_json},' + w_slice[pos:]
            html = html[:idx_w_start] + w_slice + html[idx_w_end:]
            idx_w_end = idx_w_start + len(w_slice)
            # Re-locate idx_s_start since w_slice modified text before it
            idx_s_start = html.find('const STATIC_EVENT_DATA = {')
            idx_s_end = html.find('function getQueryParams()', idx_s_start)
            s_slice = html[idx_s_start:idx_s_end]
            updated = True

    if updated:
        with open(event_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ event.html successfully updated with official Dorna results and weather!")
    return updated

def main():
    print("==================================================")
    print("MotoGP Automated Results & Analysis Update Engine")
    print("==================================================")

    # 1. Update event.html with official Dorna classification and weather
    print("\n[Step 1/5] Checking Dorna Classification PDFs for MotoGP...")
    class_updated = update_event_html_results()

    # 2. Update FP1, PR, and FP2 Analysis datasets (stints, tyres, sectors)
    print("\n[Step 2/5] Checking Dorna Analysis PDFs for FP1, PR, and FP2...")
    fp1_up = update_session_datasets('FP1')
    pr_up  = update_session_datasets('PR')
    fp2_up = update_session_datasets('FP2')

    # 3. Update Moto2 results and lap charts
    print("\n[Step 3/5] Updating Moto2 sessions & lap charts...")
    try:
        update_moto2()
    except Exception as e:
        print(f"  Moto2 update notice: {e}")

    # 4. Update Moto3 results and lap charts
    print("\n[Step 4/5] Updating Moto3 sessions & lap charts...")
    try:
        update_moto3()
    except Exception as e:
        print(f"  Moto3 update notice: {e}")

    # 5. Export multi-year and 2026 database
    print("\n[Step 5/5] Refreshing exports and database...")
    try:
        import export_database
        export_database.main()
    except Exception as e:
        print(f"  Database export notice: {e}")

    print("\n==================================================")
    print("Update complete!")
    print("==================================================")

if __name__ == '__main__':
    main()
