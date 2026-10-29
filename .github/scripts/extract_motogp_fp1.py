#!/usr/bin/env python3
"""
Extracts MotoGP FP1 Stints, tyres, and lap times from official Dorna Analysis PDFs.
Cleans all page headers, footers, and 'Fastest Lap:' artifacts to ensure only
genuine rider lap times are parsed.
"""
import sys
import os
import re
import json
import urllib.request
import urllib.error

sys.path.append(os.path.dirname(__file__))
from update_event_data import parse_dorna_analysis_pdf

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
    'Cal Crutchlow': '35',
    'Takaaki Nakagami': '30',
    'Jonas Folger': '94'
}

def get_code(name, fallback_num):
    num = MOTOGP_RIDER_NUMBERS.get(name, fallback_num)
    parts = name.strip().split()
    first_init = parts[0][0].upper()
    last_init = parts[-1][0].upper()
    return f"{first_init}{last_init}{num}", num

PATTERN_FOOTER = re.compile(
    r'Page\s+\d+\s+of\s+\d+.*?(?:©[^\n]*\n|Fastest Lap:[^\n]*\n)(?:.*?T4[^\n]*\n)?',
    re.DOTALL | re.IGNORECASE
)

REG_RIDER = re.compile(
    r'(\d{1,3})\s*\n([^\n]+?)\s*\n([A-Z]{3})\s*\n([^\n]+?)\s*\n(?:(?:\d+)(?:st|nd|rd|th)\s*\n)?Runs\s*=\s*(\d+)',
    re.MULTILINE
)

def parse_runs_for_rider(block):
    runs_parts = re.split(r'Run\s*#\s*\d*', block)
    runs_data = []
    total_laps_so_far = 0
    for part in runs_parts[1:]:
        tyre_matches = re.findall(r'Slick-(Soft|Medium|Hard)', part, re.IGNORECASE)
        front_tyre = tyre_matches[0][0].upper() if len(tyre_matches) >= 1 else 'M'
        rear_tyre = tyre_matches[1][0].upper() if len(tyre_matches) >= 2 else front_tyre
        
        lap_matches = re.findall(r"(\d+)'(\d+\.\d+)(\s*P)?", part)
        laps = []
        for m in lap_matches:
            mins = int(m[0])
            secs = float(m[1])
            tot = round(mins * 60 + secs, 3)
            is_pit = bool(m[2])
            laps.append({
                'time': f"{mins}'{m[1]}",
                'sec': tot,
                'pit': is_pit
            })
            
        laps_count = len(laps)
        start_lap = total_laps_so_far + 1
        end_lap = total_laps_so_far + laps_count
        total_laps_so_far += laps_count
        
        valid_secs = [l['sec'] for l in laps if not l['pit']]
        if valid_secs:
            min_stint = min(valid_secs)
            flying = [l for l in laps if l['sec'] <= min_stint * 1.15 and l['sec'] < 150.0]
            if flying:
                best = min(flying, key=lambda x: x['sec'])
                fastest_str = best['time']
                fastest_sec = best['sec']
            else:
                fastest_str = laps[0]['time'] if laps else "-"
                fastest_sec = laps[0]['sec'] if laps else 0
        else:
            fastest_str = laps[0]['time'] if laps else "-"
            fastest_sec = laps[0]['sec'] if laps else 0
            
        runs_data.append({
            'front': front_tyre,
            'rear': rear_tyre,
            'lapsCount': laps_count,
            'startLap': start_lap,
            'endLap': end_lap,
            'fastest': fastest_str,
            'fastestSec': fastest_sec,
            'laps': laps
        })
    return runs_data

def run_extraction():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, 'data', 'motogp_fp1_stints.json')
    compact_path = os.path.join(base_dir, 'data', 'motogp_fp1_compact.json')
    js_path = os.path.join(base_dir, 'js', 'motogp_fp1_data.js')

    # Load existing data so previous rounds are safely preserved
    if os.path.exists(full_path):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                all_events_fp1 = json.load(f)
        except Exception:
            all_events_fp1 = {}
    else:
        all_events_fp1 = {}

    updated_count = 0
    for rnd in ALL_ROUNDS:
        url = f"https://resources.motogp.com/files/results/2026/{rnd}/MotoGP/FP1/Analysis.pdf"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    pdf_bytes = resp.read()
                else:
                    continue
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Normal for future rounds not yet raced
                continue
            print(f"  {rnd}: HTTP error {e.code}")
            continue
        except Exception as e:
            print(f"  {rnd}: Network error ({e})")
            continue

        try:
            txt = parse_dorna_analysis_pdf(pdf_bytes)
            if not txt or len(txt) < 1000:
                continue

            cleaned_txt = PATTERN_FOOTER.sub('\n', txt)
            cleaned_txt = re.sub(r'Fastest Lap:.*?(?=\n|$)', '', cleaned_txt)
            cleaned_txt = re.sub(r'Official MotoGP Timing.*?(?=\n|$)', '', cleaned_txt)

            matches = list(REG_RIDER.finditer(cleaned_txt))
            if not matches:
                continue

            riders_dict = {}
            for i, m in enumerate(matches):
                start_pos = m.start()
                end_pos = matches[i+1].start() if i + 1 < len(matches) else len(cleaned_txt)
                block = cleaned_txt[start_pos:end_pos]

                num = m.group(1).strip()
                name_raw = m.group(4).strip()
                parts = name_raw.split()
                norm_name = " ".join([p.capitalize() if p.isupper() else p for p in parts])

                code, official_num = get_code(norm_name, num)
                runs = parse_runs_for_rider(block)
                total_laps = sum(r['lapsCount'] for r in runs)

                riders_dict[norm_name] = {
                    'number': official_num,
                    'code': code,
                    'totalLaps': total_laps,
                    'runs': runs
                }

            all_events_fp1[rnd] = riders_dict
            updated_count += 1
            print(f"  {rnd}: parsed {len(riders_dict)} riders from Analysis.pdf")
        except Exception as e:
            print(f"  {rnd}: Error parsing PDF -> {e}")

    # Write full JSON
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(all_events_fp1, f, indent=2, ensure_ascii=False)

    # Build compact JSON
    compact = {}
    for rnd, riders in all_events_fp1.items():
        compact[rnd] = {}
        for r_name, r_info in riders.items():
            valid_runs = [
                {
                    'front': r['front'],
                    'rear': r['rear'],
                    'lapsCount': r['lapsCount'],
                    'startLap': r['startLap'],
                    'endLap': r['endLap'],
                    'fastest': r['fastest'],
                    'fastestSec': r['fastestSec']
                }
                for r in r_info.get('runs', [])
                if r.get('lapsCount', 0) > 0
            ]
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

    # Write JS file
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(f"const EVENT_FP1_STINTS_DATA = {compact_json};\n")

    print(f"FP1 Stints extraction complete! Processed {len(all_events_fp1)} rounds.")

if __name__ == '__main__':
    run_extraction()
