import json, os, urllib.request, io, re

SEASON_2026 = "e88b4e43-2209-47aa-8e83-0e0b1cedde6e"
CAT_MOTOGP = "e8c110ad-64aa-4e8e-8a86-f2f152f6a942"

RIDER_NUMBERS = {
    "Marc Marquez": 93, "Jorge Martin": 89, "Francesco Bagnaia": 63, "Ai Ogura": 79,
    "Fabio Di Giannantonio": 49, "Pedro Acosta": 37, "Raul Fernandez": 25, "Fermin Aldeguer": 54,
    "Diogo Moreira": 11, "Brad Binder": 33, "Joan Mir": 36, "Luca Marini": 10,
    "Franco Morbidelli": 21, "Jack Miller": 43, "Toprak Razgatlioglu": 7, "Maverick Viñales": 12,
    "Fabio Quartararo": 20, "Enea Bastianini": 23, "Alex Rins": 42, "Somkiat Chantra": 30,
    "Alex Marquez": 73, "Marco Bezzecchi": 72, "Johann Zarco": 5, "Iker Lecuona": 27,
    "Michele Pirro": 51, "Pol Espargaro": 44, "Augusto Fernandez": 47, "Miguel Oliveira": 88
}
NUM_TO_RIDER = {v: k for k, v in RIDER_NUMBERS.items()}
NUM_TO_RIDER[76] = "Toprak Razgatlioglu"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActions-EventUpdater/1.0)"}

def http_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)

def download_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()

def get_class(sess_id):
    if not sess_id: return []
    url = f"https://api.motogp.pulselive.com/motogp/v1/results/session/{sess_id}/classification?categoryUuid={CAT_MOTOGP}"
    try:
        data = http_get(url)
        return data.get('classification', [])
    except Exception:
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

        # Check if already present in STATIC_EVENT_DATA
        if f'"{short}":' in html_content and f'STATIC_EVENT_DATA' in html_content:
            print(f"Evento {short} già presente in event.html.")
            continue

        print(f"Estrazione nuovo evento concluso: {short} ({ev.get('name')})...")

        sessions_url = f"https://api.motogp.pulselive.com/motogp/v1/results/sessions?eventUuid={ev_id}&categoryUuid={CAT_MOTOGP}"
        try:
            sessions = http_get(sessions_url)
        except Exception as e:
            print(f"Errore caricamento sessioni {short}: {e}")
            continue

        fp_sess = [s for s in sessions if s.get('type') == 'FP']
        pr_sess = next((s for s in sessions if s.get('type') == 'PR'), None)
        q_sess  = [s for s in sessions if s.get('type') == 'Q']
        spr_sess = next((s for s in sessions if s.get('type') == 'SPR'), None)
        wup_sess = next((s for s in sessions if s.get('type') == 'WUP'), None)
        rac_sess = next((s for s in sessions if s.get('type') == 'RAC'), None)

        fp1 = get_class(fp_sess[0]['id']) if len(fp_sess) >= 1 else []
        pr  = get_class(pr_sess['id']) if pr_sess else []
        fp2 = get_class(fp_sess[1]['id']) if len(fp_sess) >= 2 else []

        q1 = []
        q2 = []
        for qs in q_sess:
            c = get_class(qs['id'])
            if len(c) <= 12 and not q2:
                q2 = c
            else:
                q1 = c

        spr = get_class(spr_sess['id']) if spr_sess else []
        wup = get_class(wup_sess['id']) if wup_sess else []
        rac = get_class(rac_sess['id']) if rac_sess else []

        # Build grid
        grid = []
        q2_ids = set()
        p = 1
        for r in q2:
            r_id = r.get('rider', {}).get('id', str(p))
            q2_ids.add(r_id)
            grid.append({
                "position": p,
                "rider": r.get('rider'),
                "name": r.get('rider', {}).get('full_name', 'Rider'),
                "time": r.get('best_lap', {}).get('time', '-') if r.get('best_lap') else '-'
            })
            p += 1

        for r in q1:
            r_id = r.get('rider', {}).get('id', str(p))
            if r_id not in q2_ids:
                grid.append({
                    "position": p,
                    "rider": r.get('rider'),
                    "name": r.get('rider', {}).get('full_name', 'Rider'),
                    "time": r.get('best_lap', {}).get('time', '-') if r.get('best_lap') else '-'
                })
                p += 1

        static_obj = {
            "fp1": fp1, "pr": pr, "fp2": fp2, "q1": q1, "q2": q2,
            "grid": grid, "sprint": spr, "wup": wup, "race": rac
        }
        static_json = json.dumps(static_obj, separators=(',', ':'))

        # Insert into STATIC_EVENT_DATA
        if 'const STATIC_EVENT_DATA = {' in html_content:
            html_content = html_content.replace(
                'const STATIC_EVENT_DATA = {',
                f'const STATIC_EVENT_DATA = {{\n    "{short}": {static_json},'
            )
            updated = True
            print(f"✓ Aggiunto {short} in STATIC_EVENT_DATA!")

    if updated:
        with open(event_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✓ event.html aggiornato con successo!")
    else:
        print("Nessun nuovo evento da aggiungere a event.html.")

if __name__ == '__main__':
    main()
