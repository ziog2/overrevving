#!/usr/bin/env python3
"""
Overrevving - Git-as-a-database & Multi-Championship Export Engine
Generates:
  - data/standings_latest.json
  - data/<category>/2026.json
  - exports/csv/season_standings.csv
  - exports/csv/race_results_points.csv
  - exports/csv/calendar_events.csv
  - exports/motorsport_database_2026.xlsx (if openpyxl available)
"""

import os
import sys
import json
import csv
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
CSV_DIR = os.path.join(EXPORTS_DIR, "csv")

CATEGORIES = ['motogp', 'moto2', 'moto3', 'sbk', 'f1', 'mxgp', 'mx2']

CALENDARS_2026 = {
    'motogp': [
        {'round': 1, 'name': 'Thailand', 'date': '2026-03-01', 'weather': 'Dry'},
        {'round': 2, 'name': 'Brazil', 'date': '2026-03-22', 'weather': 'Dry'},
        {'round': 3, 'name': 'USA', 'date': '2026-03-29', 'weather': 'Dry'},
        {'round': 4, 'name': 'Spain', 'date': '2026-04-26', 'weather': 'Dry'},
        {'round': 5, 'name': 'France', 'date': '2026-05-10', 'weather': 'Dry'},
        {'round': 6, 'name': 'Catalonia', 'date': '2026-05-17', 'weather': 'Dry'},
        {'round': 7, 'name': 'Italy', 'date': '2026-05-31', 'weather': 'Dry'},
        {'round': 8, 'name': 'Hungary', 'date': '2026-06-07', 'weather': 'Dry'},
        {'round': 9, 'name': 'Czechia', 'date': '2026-06-21', 'weather': 'Dry'},
        {'round': 10, 'name': 'Netherlands', 'date': '2026-06-28', 'weather': 'Dry'},
        {'round': 11, 'name': 'Germany', 'date': '2026-07-12', 'weather': 'Dry'},
        {'round': 12, 'name': 'Great Britain', 'date': '2026-08-09', 'weather': 'Dry'},
        {'round': 13, 'name': 'Aragon', 'date': '2026-08-30', 'weather': 'Dry'},
        {'round': 14, 'name': 'San Marino', 'date': '2026-09-13', 'weather': 'Dry'},
        {'round': 15, 'name': 'Austria', 'date': '2026-09-20', 'weather': 'Dry'},
        {'round': 16, 'name': 'Japan', 'date': '2026-10-04', 'weather': 'Dry'},
        {'round': 17, 'name': 'Indonesia', 'date': '2026-10-11'},
        {'round': 18, 'name': 'Australia', 'date': '2026-10-25'},
        {'round': 19, 'name': 'Malaysia', 'date': '2026-11-01'},
        {'round': 20, 'name': 'Qatar', 'date': '2026-11-08'},
        {'round': 21, 'name': 'Portugal', 'date': '2026-11-22'},
        {'round': 22, 'name': 'Valencia', 'date': '2026-11-29'}
    ],
    'moto2': [
        {'round': 1, 'name': 'Thailand', 'date': '2026-03-01'},
        {'round': 2, 'name': 'Brazil', 'date': '2026-03-22'},
        {'round': 3, 'name': 'USA', 'date': '2026-03-29'},
        {'round': 4, 'name': 'Spain', 'date': '2026-04-26'},
        {'round': 5, 'name': 'France', 'date': '2026-05-10'},
        {'round': 6, 'name': 'Catalonia', 'date': '2026-05-17'},
        {'round': 7, 'name': 'Italy', 'date': '2026-05-31'},
        {'round': 8, 'name': 'Hungary', 'date': '2026-06-07'},
        {'round': 9, 'name': 'Czechia', 'date': '2026-06-21'},
        {'round': 10, 'name': 'Netherlands', 'date': '2026-06-28'},
        {'round': 11, 'name': 'Germany', 'date': '2026-07-12'},
        {'round': 12, 'name': 'Great Britain', 'date': '2026-08-09'},
        {'round': 13, 'name': 'Aragon', 'date': '2026-08-30'},
        {'round': 14, 'name': 'San Marino', 'date': '2026-09-13'},
        {'round': 15, 'name': 'Austria', 'date': '2026-09-20'},
        {'round': 16, 'name': 'Japan', 'date': '2026-10-04'},
        {'round': 17, 'name': 'Indonesia', 'date': '2026-10-11'},
        {'round': 18, 'name': 'Australia', 'date': '2026-10-25'},
        {'round': 19, 'name': 'Malaysia', 'date': '2026-11-01'},
        {'round': 20, 'name': 'Qatar', 'date': '2026-11-08'},
        {'round': 21, 'name': 'Portugal', 'date': '2026-11-22'},
        {'round': 22, 'name': 'Valencia', 'date': '2026-11-29'}
    ],
    'moto3': [
        {'round': 1, 'name': 'Thailand', 'date': '2026-03-01'},
        {'round': 2, 'name': 'Brazil', 'date': '2026-03-22'},
        {'round': 3, 'name': 'USA', 'date': '2026-03-29'},
        {'round': 4, 'name': 'Spain', 'date': '2026-04-26'},
        {'round': 5, 'name': 'France', 'date': '2026-05-10'},
        {'round': 6, 'name': 'Catalonia', 'date': '2026-05-17'},
        {'round': 7, 'name': 'Italy', 'date': '2026-05-31'},
        {'round': 8, 'name': 'Hungary', 'date': '2026-06-07'},
        {'round': 9, 'name': 'Czechia', 'date': '2026-06-21'},
        {'round': 10, 'name': 'Netherlands', 'date': '2026-06-28'},
        {'round': 11, 'name': 'Germany', 'date': '2026-07-12'},
        {'round': 12, 'name': 'Great Britain', 'date': '2026-08-09'},
        {'round': 13, 'name': 'Aragon', 'date': '2026-08-30'},
        {'round': 14, 'name': 'San Marino', 'date': '2026-09-13'},
        {'round': 15, 'name': 'Austria', 'date': '2026-09-20'},
        {'round': 16, 'name': 'Japan', 'date': '2026-10-04'},
        {'round': 17, 'name': 'Indonesia', 'date': '2026-10-11'},
        {'round': 18, 'name': 'Australia', 'date': '2026-10-25'},
        {'round': 19, 'name': 'Malaysia', 'date': '2026-11-01'},
        {'round': 20, 'name': 'Qatar', 'date': '2026-11-08'},
        {'round': 21, 'name': 'Portugal', 'date': '2026-11-22'},
        {'round': 22, 'name': 'Valencia', 'date': '2026-11-29'}
    ],
    'sbk': [
        {'round': 1, 'name': 'Australia', 'date': '2026-02-22'},
        {'round': 2, 'name': 'Portugal', 'date': '2026-03-29'},
        {'round': 3, 'name': 'Netherlands', 'date': '2026-04-19'},
        {'round': 4, 'name': 'Hungary', 'date': '2026-05-03'},
        {'round': 5, 'name': 'Most', 'date': '2026-05-17'},
        {'round': 6, 'name': 'Aragon', 'date': '2026-05-31'},
        {'round': 7, 'name': 'Misano', 'date': '2026-06-14'},
        {'round': 8, 'name': 'Donington', 'date': '2026-07-12'},
        {'round': 9, 'name': 'Magny-Cours', 'date': '2026-09-27'},
        {'round': 10, 'name': 'Cremona', 'date': '2026-10-11'},
        {'round': 11, 'name': 'Estoril', 'date': '2026-10-18'},
        {'round': 12, 'name': 'Jerez', 'date': '2026-10-18'}
    ],
    'mxgp': [
        {'round': 1, 'name': 'Argentina', 'date': '2026-03-08'},
        {'round': 2, 'name': 'Andalucia', 'date': '2026-03-22'},
        {'round': 3, 'name': 'Switzerland', 'date': '2026-03-29'},
        {'round': 4, 'name': 'Sardegna', 'date': '2026-04-12'},
        {'round': 5, 'name': 'Trentino', 'date': '2026-04-19'},
        {'round': 6, 'name': 'France', 'date': '2026-05-24'},
        {'round': 7, 'name': 'Germany', 'date': '2026-05-31'},
        {'round': 8, 'name': 'Latvia', 'date': '2026-06-07'},
        {'round': 9, 'name': 'Italy', 'date': '2026-06-21'},
        {'round': 10, 'name': 'Portugal', 'date': '2026-06-28'},
        {'round': 11, 'name': 'South Africa', 'date': '2026-07-05'},
        {'round': 12, 'name': 'Great Britain', 'date': '2026-07-19'},
        {'round': 13, 'name': 'Czech Republic', 'date': '2026-07-26'},
        {'round': 14, 'name': 'Flanders', 'date': '2026-08-02'},
        {'round': 15, 'name': 'Sweden', 'date': '2026-08-16'},
        {'round': 16, 'name': 'Netherlands', 'date': '2026-08-23'},
        {'round': 17, 'name': 'Turkey', 'date': '2026-09-06'}
    ],
    'mx2': [
        {'round': 1, 'name': 'Argentina', 'date': '2026-03-08'},
        {'round': 2, 'name': 'Andalucia', 'date': '2026-03-22'},
        {'round': 3, 'name': 'Switzerland', 'date': '2026-03-29'},
        {'round': 4, 'name': 'Sardegna', 'date': '2026-04-12'},
        {'round': 5, 'name': 'Trentino', 'date': '2026-04-19'},
        {'round': 6, 'name': 'France', 'date': '2026-05-24'},
        {'round': 7, 'name': 'Germany', 'date': '2026-05-31'},
        {'round': 8, 'name': 'Latvia', 'date': '2026-06-07'},
        {'round': 9, 'name': 'Italy', 'date': '2026-06-21'},
        {'round': 10, 'name': 'Portugal', 'date': '2026-06-28'},
        {'round': 11, 'name': 'South Africa', 'date': '2026-07-05'},
        {'round': 12, 'name': 'Great Britain', 'date': '2026-07-19'},
        {'round': 13, 'name': 'Czech Republic', 'date': '2026-07-26'},
        {'round': 14, 'name': 'Flanders', 'date': '2026-08-02'},
        {'round': 15, 'name': 'Sweden', 'date': '2026-08-16'},
        {'round': 16, 'name': 'Netherlands', 'date': '2026-08-23'},
        {'round': 17, 'name': 'Turkey', 'date': '2026-09-06'}
    ],
    'f1': [
        {'round': 1, 'name': 'Australia', 'date': '2026-03-08'},
        {'round': 2, 'name': 'China', 'date': '2026-03-15'},
        {'round': 3, 'name': 'Japan', 'date': '2026-03-29'},
        {'round': 4, 'name': 'Bahrain', 'date': '2026-04-12'},
        {'round': 5, 'name': 'Saudi Arabia', 'date': '2026-04-19'},
        {'round': 6, 'name': 'Miami', 'date': '2026-05-03'},
        {'round': 7, 'name': 'Canada', 'date': '2026-05-24'},
        {'round': 8, 'name': 'Monaco', 'date': '2026-06-07'},
        {'round': 9, 'name': 'Spain', 'date': '2026-06-14'},
        {'round': 10, 'name': 'Austria', 'date': '2026-06-28'},
        {'round': 11, 'name': 'Great Britain', 'date': '2026-07-05'},
        {'round': 12, 'name': 'Belgium', 'date': '2026-07-19'},
        {'round': 13, 'name': 'Netherlands', 'date': '2026-08-23'},
        {'round': 14, 'name': 'Italy', 'date': '2026-09-06'},
        {'round': 15, 'name': 'Madrid', 'date': '2026-09-13'},
        {'round': 16, 'name': 'Azerbaijan', 'date': '2026-09-20'},
        {'round': 17, 'name': 'Singapore', 'date': '2026-10-04'},
        {'round': 18, 'name': 'Austin', 'date': '2026-10-25'},
        {'round': 19, 'name': 'Mexico', 'date': '2026-11-01'},
        {'round': 20, 'name': 'São Paulo', 'date': '2026-11-08'},
        {'round': 21, 'name': 'Las Vegas', 'date': '2026-11-21'},
        {'round': 22, 'name': 'Qatar', 'date': '2026-11-29'},
        {'round': 23, 'name': 'Abu Dhabi', 'date': '2026-12-06'}
    ]
}

def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    for cat in CATEGORIES:
        os.makedirs(os.path.join(DATA_DIR, cat), exist_ok=True)

    # 1. Load latest data from data/standings_latest.json
    standings_file = os.path.join(DATA_DIR, "standings_latest.json")
    if not os.path.exists(standings_file):
        print(f"Error: {standings_file} not found")
        sys.exit(1)

    with open(standings_file, "r", encoding="utf-8") as f:
        record = json.load(f)

    # 2. Write category-specific JSON files
    for cat in CATEGORIES:
        cat_file = os.path.join(DATA_DIR, cat, "2026.json")
        cat_payload = {
            "season": 2026,
            "category": cat,
            "lastUpdated": record.get("_updated", ""),
            "calendar": CALENDARS_2026.get(cat, []),
            "riders": record.get(cat, []),
            "constructors": record.get(f"{cat}_constructors", []),
            "teams": record.get(f"{cat}_teams", [])
        }
        with open(cat_file, "w", encoding="utf-8") as out:
            json.dump(cat_payload, out, indent=2, ensure_ascii=False)
        print(f"Updated {cat_file}")

    # 3. Export CSV: season_standings.csv
    standings_csv_path = os.path.join(CSV_DIR, "season_standings.csv")
    with open(standings_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Season", "Category", "Rank", "Rider_Name", "Total_Points", "Gap_To_Leader", "Sprint_Points", "Main_Race_Points"])
        for cat in CATEGORIES:
            riders = record.get(cat, [])
            if riders:
                leader_pts = riders[0].get("pts", 0) if len(riders) > 0 else 0
                for rank, r in enumerate(riders, start=1):
                    pts = r.get("pts", 0)
                    gap = 0 if rank == 1 else (leader_pts - pts)
                    spr = r.get("sprint_pts", "")
                    long_pts = r.get("long_pts", "")
                    writer.writerow([2026, cat.upper(), rank, r.get("name", ""), pts, gap, spr, long_pts])
    print(f"Wrote {standings_csv_path}")

    # 4. Export CSV: calendar_events.csv
    cal_csv_path = os.path.join(CSV_DIR, "calendar_events.csv")
    with open(cal_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Season", "Category", "Round_Number", "Event_Name", "Date", "Weather"])
        for cat, events in CALENDARS_2026.items():
            for ev in events:
                writer.writerow([2026, cat.upper(), ev["round"], ev["name"], ev.get("date", ""), ev.get("weather", "TBD")])
    print(f"Wrote {cal_csv_path}")

    # 5. Export CSV: race_results_points.csv (Tidy Data for Tableau/Grafana)
    granular_csv_path = os.path.join(CSV_DIR, "race_results_points.csv")
    with open(granular_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Season", "Category", "Round_Number", "Event_Name", "Date", "Rider_Name",
            "Sprint_Points", "Main_Race_Points", "Points_Earned", "Cumulative_Points",
            "Gap_To_Leader", "Is_Zero_Points", "Weather"
        ])
        for cat in ["motogp", "moto2", "moto3"]:
            riders = record.get(cat, [])
            cal = CALENDARS_2026.get(cat, [])
            if riders and len(riders) > 0 and riders[0].get("history"):
                num_rounds = len(riders[0]["history"])
                for round_idx in range(num_rounds):
                    round_num = round_idx + 1
                    ev_name = cal[round_idx]["name"] if round_idx < len(cal) else f"Round {round_num}"
                    ev_date = cal[round_idx].get("date", "") if round_idx < len(cal) else ""
                    ev_weather = cal[round_idx].get("weather", "Dry") if round_idx < len(cal) else "Dry"

                    # Calculate leader cumulative points for this round
                    round_cum_scores = [sum(r.get("history", [])[:round_idx + 1]) for r in riders]
                    leader_cum = max(round_cum_scores) if round_cum_scores else 0

                    for r in riders:
                        history = r.get("history", [])
                        spr_history = r.get("sprint_history", [])
                        long_history = r.get("long_history", [])

                        pts_earned = history[round_idx] if round_idx < len(history) else 0
                        spr_pts = spr_history[round_idx] if round_idx < len(spr_history) else 0
                        long_pts = long_history[round_idx] if round_idx < len(long_history) else (pts_earned - spr_pts)

                        cum_pts = sum(history[:round_idx + 1])
                        gap = leader_cum - cum_pts

                        writer.writerow([
                            2026, cat.upper(), round_num, ev_name, ev_date, r.get("name", ""),
                            spr_pts, long_pts, pts_earned, cum_pts,
                            0 if gap == 0 else -gap,
                            1 if pts_earned == 0 else 0,
                            ev_weather
                        ])
    print(f"Wrote {granular_csv_path}")

    # 5b. Export CSV: motogp_fp1_stints.csv (FP1 Stints & Tyres Tidy Data for Grafana)
    fp1_json_path = os.path.join(DATA_DIR, "motogp_fp1_stints.json")
    fp1_csv_path = os.path.join(CSV_DIR, "motogp_fp1_stints.csv")
    if os.path.exists(fp1_json_path):
        with open(fp1_json_path, "r", encoding="utf-8") as f:
            fp1_data = json.load(f)

        cal_map = {
            'THA': {'round': 1, 'name': 'Thailand', 'date': '2026-03-01'},
            'BRA': {'round': 2, 'name': 'Brazil', 'date': '2026-03-22'},
            'USA': {'round': 3, 'name': 'USA', 'date': '2026-03-29'},
            'SPA': {'round': 4, 'name': 'Spain', 'date': '2026-04-26'},
            'FRA': {'round': 5, 'name': 'France', 'date': '2026-05-10'},
            'CAT': {'round': 6, 'name': 'Catalonia', 'date': '2026-05-17'},
            'ITA': {'round': 7, 'name': 'Italy', 'date': '2026-05-31'},
            'HUN': {'round': 8, 'name': 'Hungary', 'date': '2026-06-07'},
            'CZE': {'round': 9, 'name': 'Czechia', 'date': '2026-06-21'},
            'NED': {'round': 10, 'name': 'Netherlands', 'date': '2026-06-28'},
            'GER': {'round': 11, 'name': 'Germany', 'date': '2026-07-12'},
            'GBR': {'round': 12, 'name': 'Great Britain', 'date': '2026-08-09'},
            'ARA': {'round': 13, 'name': 'Aragon', 'date': '2026-08-30'},
            'RSM': {'round': 14, 'name': 'San Marino', 'date': '2026-09-13'},
            'AUT': {'round': 15, 'name': 'Austria', 'date': '2026-09-20'},
            'JPN': {'round': 16, 'name': 'Japan', 'date': '2026-10-04'},
            'INA': {'round': 17, 'name': 'Indonesia', 'date': '2026-10-11'},
            'AUS': {'round': 18, 'name': 'Australia', 'date': '2026-10-25'}
        }
        compound_names = {'S': 'Soft', 'M': 'Medium', 'H': 'Hard'}

        sorted_rounds = sorted(fp1_data.keys(), key=lambda r: cal_map.get(r, {}).get('round', 99))
        with open(fp1_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Season", "Category", "Round_Number", "Round_Short", "Event_Name", "Date",
                "Rider_Name", "Rider_Code", "Rider_Number", "Run_Number",
                "Front_Tyre", "Rear_Tyre", "Front_Compound", "Rear_Compound",
                "Laps_Count", "Start_Lap", "End_Lap",
                "Fastest_Lap_Time", "Fastest_Lap_Seconds", "Is_Session_Best_Stint", "Total_Session_Laps"
            ])
            for rnd_short in sorted_rounds:
                rnd_info = cal_map.get(rnd_short, {'round': 0, 'name': rnd_short, 'date': ''})
                riders_map = fp1_data[rnd_short]
                all_fastest = [
                    run.get('fastestSec', 0)
                    for r_info in riders_map.values()
                    for run in r_info.get('runs', [])
                    if run.get('fastestSec', 0) > 0
                ]
                session_best = min(all_fastest) if all_fastest else 0

                for r_name, r_info in sorted(riders_map.items()):
                    code = r_info.get('code', '')
                    num = r_info.get('number', '')
                    total_laps = r_info.get('totalLaps', 0)
                    runs = [r for r in r_info.get('runs', []) if r.get('lapsCount', 0) > 0]
                    for run_idx, run in enumerate(runs, start=1):
                        f_tyre = run.get('front', 'M')
                        r_tyre = run.get('rear', 'M')
                        laps = run.get('lapsCount', 0)
                        s_lap = run.get('startLap', 0)
                        e_lap = run.get('endLap', 0)
                        fastest_str = run.get('fastest', '-')
                        fastest_sec = run.get('fastestSec', 0)
                        is_best = 1 if (fastest_sec > 0 and fastest_sec == session_best) else 0

                        writer.writerow([
                            2026, "MOTOGP", rnd_info['round'], rnd_short, rnd_info['name'], rnd_info['date'],
                            r_name, code, num, run_idx,
                            f_tyre, r_tyre, compound_names.get(f_tyre, f_tyre), compound_names.get(r_tyre, r_tyre),
                            laps, s_lap, e_lap,
                            fastest_str, fastest_sec, is_best, total_laps
                        ])
        print(f"Wrote {fp1_csv_path}")

    # 6. Try generating Excel (.xlsx) if openpyxl is installed
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = openpyxl.Workbook()
        wb.remove(wb.active) # remove default sheet

        def add_csv_sheet(csv_path, sheet_title, header_fill_color):
            if not os.path.exists(csv_path):
                return
            ws = wb.create_sheet(title=sheet_title)
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row_idx, row in enumerate(reader, start=1):
                    for col_idx, val in enumerate(row, start=1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        if row_idx == 1:
                            cell.value = val
                            cell.font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
                            cell.fill = PatternFill(start_color=header_fill_color, end_color=header_fill_color, fill_type="solid")
                        else:
                            try:
                                if "." in val:
                                    cell.value = float(val)
                                else:
                                    cell.value = int(val)
                            except ValueError:
                                cell.value = val
                            cell.font = Font(name="Segoe UI", size=9.5)
                            if row_idx % 2 == 0:
                                cell.fill = PatternFill(start_color="F4F4F6", end_color="F4F4F6", fill_type="solid")

        add_csv_sheet(standings_csv_path, "Season_Standings", "C0392B")
        add_csv_sheet(granular_csv_path, "Race_Results_Granular", "2980B9")
        add_csv_sheet(cal_csv_path, "Calendars_2026", "27AE60")
        if os.path.exists(fp1_csv_path):
            add_csv_sheet(fp1_csv_path, "FP1_Stints_Analysis", "E67E22")

        xlsx_out = os.path.join(EXPORTS_DIR, "motorsport_database_2026.xlsx")
        wb.save(xlsx_out)
        print(f"Generated {xlsx_out} via openpyxl")
    except ImportError:
        print("openpyxl not installed in Python environment, skipped .xlsx generation (handled locally via PowerShell).")

if __name__ == "__main__":
    main()
