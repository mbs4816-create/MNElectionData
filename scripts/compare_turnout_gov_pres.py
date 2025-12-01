#!/usr/bin/env python3
"""
compare_turnout_gov_pres.py
Compare turnout totals for 2022 Governor & Lt Governor vs 2024 U.S. President & Vice President
for a specified set of districts.
"""
import csv
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parents[1]

INPUT_CSV = DATA_DIR / 'district_race_results.csv'
OUT_CSV = DATA_DIR / 'district_turnout_compare_gov2022_pres2024.csv'

TARGET_DISTRICTS = [
    'Hennepin County (all)',
    'Hennepin County Commission District 2',
    'Hennepin County Commission District 3',
    'Hennepin County Commission District 4',
    'Ramsey County Commission District 5',
    'Ramsey County Commission District 6',
    'State Senator District 46 (Hennepin)',
    'State House 43A (Hennepin)',
    'State House 43B (Hennepin)'
]

def main():
    # Parse per-candidate CSV to build totals per Year/Office/District
    totals = defaultdict(lambda: defaultdict(int))  # (year, office, district) -> total votes
    with INPUT_CSV.open('r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            year = int(row['Year'])
            office = row['Office']
            district = row['District']
            votes = int(row['Votes']) if row['Votes'] else 0
            key = (year, office, district)
            totals[key]['votes'] = totals[key].get('votes', 0) + votes

    # For each target district, find 2022 Governor totals and 2024 President totals
    comp_rows = []
    for d in TARGET_DISTRICTS:
        gov_key = (2022, 'Governor & Lt Governor', d)
        pres_key = (2024, 'U.S. President & Vice President', d)
        gov_total = totals.get(gov_key, {}).get('votes', 0)
        pres_total = totals.get(pres_key, {}).get('votes', 0)
        abs_change = pres_total - gov_total
        pct_change = None
        gov_missing = False
        if gov_total > 0:
            pct_change = round(abs_change / gov_total * 100, 2)
        else:
            # If gubernatorial total is 0 but presidential has votes, mark missing
            if pres_total > 0:
                gov_missing = True
            pct_change = None
        # write 'MISSING' for gov_total if flagged
        comp_rows.append([d, 'MISSING' if gov_missing else gov_total, pres_total, abs_change, pct_change])

    # Write out CSV
    with OUT_CSV.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['District','Gov2022_TotalVotes','Pres2024_TotalVotes','AbsoluteChange','PctChange'])
        for r in comp_rows:
            writer.writerow(r)

    print('Wrote', OUT_CSV)

if __name__ == '__main__':
    main()
