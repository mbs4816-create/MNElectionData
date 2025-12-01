#!/usr/bin/env python3
"""
calculate_undervotes.py

Calculate undervote rates for specified races compared to baseline turnout
(Governor 2022 for 2022 races, President 2024 for 2024 races).

Undervote % = 1 - (Total votes for this office / Total votes for baseline)
"""
import csv
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parents[1]
SUMMARY_CSV = DATA_DIR / 'district_race_top2_summary.csv'
OUT_CSV = DATA_DIR / 'undervote_analysis.csv'

# Race mappings: (Year, Office pattern, District pattern) -> baseline office for that year
RACES_TO_ANALYZE = [
    # Hennepin County Attorney (2022, compare to 2022 Governor in Hennepin County (all))
    (2022, 'County Attorney', 'Hennepin County (all)', 2022, 'Governor & Lt Governor', 'Hennepin County (all)'),
    
    # Hennepin County Board District 2 - Irene Fernando (2022)
    (2022, 'County Commissioner District 2', 'Hennepin County Commission District 2', 2022, 'Governor & Lt Governor', 'Hennepin County Commission District 2'),
    
    # Hennepin County Board District 3 (2022)
    (2022, 'County Commissioner District 3', 'Hennepin County Commission District 3', 2022, 'Governor & Lt Governor', 'Hennepin County Commission District 3'),
    
    # Hennepin County Board District 4 (2022)
    (2022, 'County Commissioner District 4', 'Hennepin County Commission District 4', 2022, 'Governor & Lt Governor', 'Hennepin County Commission District 4'),
    
    # Ramsey County Board District 5 (2022)
    (2022, 'County Commissioner District 5', 'Ramsey County Commission District 5', 2022, 'Governor & Lt Governor', 'Ramsey County Commission District 5'),
    
    # Ramsey County Board District 6 (2022)
    (2022, 'County Commissioner District 6', 'Ramsey County Commission District 6', 2022, 'Governor & Lt Governor', 'Ramsey County Commission District 6'),
    
    # State Senator District 46 (2022) - compare State Senate race to Governor
    (2022, 'State Senator District 46', 'State Senator District 46 (Hennepin)', 2022, 'Governor & Lt Governor', 'State Senator District 46 (Hennepin)'),
    
    # State House 43B (2022) - compare State Rep race to Governor
    (2022, 'State Representative District 43B', 'State House 43B (Hennepin)', 2022, 'Governor & Lt Governor', 'State House 43B (Hennepin)'),
    
    # State House 43A (2022) - compare State Rep race to Governor
    (2022, 'State Representative District 43A', 'State House 43A (Hennepin)', 2022, 'Governor & Lt Governor', 'State House 43A (Hennepin)'),
]

def read_summary():
    """Read the summary CSV and build a lookup dict"""
    data = {}
    with SUMMARY_CSV.open('r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (int(row['Year']), row['Office'], row['District'])
            data[key] = {
                'TotalVotes': int(row['TotalVotes']),
                'TopCandidate': row['TopCandidate|Party'],
                'TopVotes': int(row['TopVotes']),
                'TopPct': float(row['TopPct']),
            }
    return data

if __name__ == '__main__':
    data = read_summary()
    
    results = []
    
    for race_year, race_office, race_district, base_year, base_office, base_district in RACES_TO_ANALYZE:
        race_key = (race_year, race_office, race_district)
        base_key = (base_year, base_office, base_district)
        
        if race_key not in data:
            print(f'WARNING: Race not found: {race_key}')
            continue
        
        if base_key not in data:
            print(f'WARNING: Baseline not found: {base_key}')
            continue
        
        race_votes = data[race_key]['TotalVotes']
        base_votes = data[base_key]['TotalVotes']
        
        undervote_pct = round((1 - race_votes / base_votes) * 100, 2) if base_votes > 0 else 0
        undervote_count = base_votes - race_votes
        
        results.append({
            'Year': race_year,
            'Office': race_office,
            'District': race_district,
            'RaceVotes': race_votes,
            'BaselineOffice': base_office,
            'BaselineVotes': base_votes,
            'UndervoteCount': undervote_count,
            'UndervoterPct': undervote_pct,
        })
    
    # Write results
    with OUT_CSV.open('w', newline='', encoding='utf-8') as fh:
        fieldnames = ['Year', 'Office', 'District', 'RaceVotes', 'BaselineOffice', 'BaselineVotes', 'UndervoteCount', 'UndervoterPct']
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    
    print(f'Wrote undervote analysis to {OUT_CSV}')
    
    # Print summary table
    print('\nUndervote Analysis:')
    print(f"{'Office':<40} {'District':<45} {'Undervote %':>12}")
    print('-' * 100)
    for r in results:
        print(f"{r['Office']:<40} {r['District']:<45} {r['UndervoterPct']:>11.2f}%")
