import json, os, urllib.request, re

SEASON_2026 = "e88b4e43-2209-47aa-8e83-0e0b1cedde6e"
CAT_MOTOGP = "e8c110ad-64aa-4e8e-8a86-f2f152f6a942"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActions-EventUpdater/1.0)"}

def http_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)

def clean_name(name):
    if not name: return "Rider"
    clean = name.strip()
    if "Vinales" in clean or "Vi.ales" in clean: return "Maverick Viñales"
    if "Munoz" in clean or "Mu.oz" in clean: return "Daniel Muñoz"
    if "Oncu" in clean or ".ncu" in clean: return "Deniz Öncü"
    return clean

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

def main():
    event_html_path = "event.html"
    if not os.path.exists(event_html_path):
        print(f"File {event_html_path} non trovato.")
        return

    with open(event_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    events_url = f"https://api.motogp.pulselive.com/motogp/v1/results/events?seasonUuid={SEASON_2026}&categoryUuid={CAT_MOTOGP}"
    events = http_get(events_url)
    finished_events = [
        ev for ev in events
        if isinstance(ev, dict) and ev.get('status') == 'FINISHED'
        and not str(ev.get('short_name', '')).endswith(('1', '2', '3'))
    ]

    updated = False

    for ev in finished_events:
        short = ev.get('short_name')
        ev_id = ev.get('id')
        if not short or not ev_id: continue

        # Check if already populated with real data in STATIC_EVENT_DATA
        marker = f'"{short}":'
        if marker in html_content:
            idx = html_content.find(marker)
            sample = html_content[idx:idx+200]
            if '"grid":  [' in sample and '"pos":' in sample:
                print(f"Evento {short} già popolato con dati in event.html.")
                continue

        print(f"Estrazione e popolamento evento {short} ({ev.get('name')})...")

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

        # Build grid: P1..P12 from Q2 (Pole), P13..P22 from Q1 excluding promoted top 2
        grid = []
        promoted = set()
        if len(q1) >= 2:
            promoted.add(q1[0]['rider'])
            promoted.add(q1[1]['rider'])

        p = 1
        for r in q2:
            grid.append({
                "pos": p,
                "rider": r['rider'],
                "laps": r['laps'],
                "time": r['time'],
                "status": "INSTND",
                "pts": None
            })
            p += 1

        for r in q1:
            if r['rider'] not in promoted:
                grid.append({
                    "pos": p,
                    "rider": r['rider'],
                    "laps": r['laps'],
                    "time": r['time'],
                    "status": "INSTND",
                    "pts": None
                })
                p += 1

        static_obj = {
            "fp1": fp1, "pr": pr, "fp2": fp2, "q1": q1, "q2": q2,
            "grid": grid, "sprint": spr, "wup": wup, "race": rac
        }
        static_json = json.dumps(static_obj, separators=(',', ':'))

        empty_pattern = rf'"{short}":\s*\{{\s*"grid":\s*\[\s*\],\s*"race":\s*\{{[\s\S]*?"q1":\s*\{{[\s\S]*?\}}'
        if re.search(empty_pattern, html_content):
            html_content = re.sub(empty_pattern, f'"{short}": {static_json}', html_content)
            updated = True
            print(f"✓ Sostituito placeholder vuoto {short} in STATIC_EVENT_DATA!")
        elif 'const STATIC_EVENT_DATA = {' in html_content:
            html_content = html_content.replace(
                'const STATIC_EVENT_DATA = {',
                f'const STATIC_EVENT_DATA = {{\n    "{short}": {static_json},'
            )
            updated = True
            print(f"✓ Inserito {short} in STATIC_EVENT_DATA!")

    if updated:
        with open(event_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✓ event.html aggiornato con successo!")
    else:
        print("Nessun nuovo evento da aggiungere a event.html.")

if __name__ == '__main__':
    main()
