#!/usr/bin/env python3
"""
aggregate_minneapolis_mayor_by_ward_2025.py

Aggregate Minneapolis mayor election results from 2025 municipal precinct file by ward.
Outputs: `minneapolis_mayor_by_ward_2025.csv` and markdown.
"""
import argparse
import csv
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]
R_DIR = DATA_DIR / '2025_Results'

def read_precincts_map():
    pm = {}
    pfile = R_DIR / 'Precincts_2025'
    with pfile.open('r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cols = line.split(';')
            if len(cols) < 3:
                continue
            county = cols[0]
            precinct = cols[1]
            name = cols[2]
            pm[(county, precinct)] = name
    return pm

def read_municipalities_map():
    mfile = R_DIR / 'Municipalities_2025'
    mmap = {}
    with mfile.open('r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cols = line.split(';')
            if len(cols) < 4:
                continue
            county = cols[0]
            mun_id = cols[2]
            name = cols[3]
            mmap[mun_id] = name
    return mmap

def parse_municipal_results():
    files_to_try = [R_DIR / 'Municipal_Hospital_School_Precinct_2025',
                    R_DIR / 'All_MuniHospitalSchoolDistritct_2025']
    out = []
    total_lines = 0
    for path in files_to_try:
        if not path.exists():
            continue
        with path.open('r', encoding='utf-8') as fh:
            for line in fh:
                total_lines += 1
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                cols = line.split(';')
            if len(cols) < 13:
                cols += [''] * (13 - len(cols))
            state = cols[0]
            county = cols[1]
            precinct = cols[2]
            office_name = cols[4]
            municipality = cols[5].strip() if cols[5] else ''
            candidate_code = cols[6]
            candidate_name = cols[7]
            party = cols[10] if len(cols) > 10 else ''
            # normalize party string (e.g., "N P" to "NP")
            party = party.replace(' ', '') if party else ''
            votes = cols[13] if len(cols) > 13 else cols[-2] if len(cols) >=2 else '0'
            try:
                votes_i = int(votes)
            except ValueError:
                votes_i = 0
            out.append({
                'county': county,
                'precinct': precinct,
                'office_name': office_name,
                'candidate_name': candidate_name,
                'party': party,
                'votes': votes_i,
                'municipality': municipality,
            })
    print('Parsed total municipal lines from 2025 files:', total_lines)
    return out

def main():
    parser = argparse.ArgumentParser(description='Aggregate Minneapolis mayor results by ward (2025).')
    parser.add_argument('--choice', choices=['first', 'all'], default='first',
                        help='Which mayor choice to aggregate. "first" aggregates only the "Mayor First Choice" entries; "all" aggregates all mayor entries (first/second choice, etc.).')
    args = parser.parse_args()
    precincts = read_precincts_map()
    rows = parse_municipal_results()
    # Debug: show sample parsed rows
    print('DEBUG: sample parsed rows (first 5):')
    for r in rows[:5]:
        print(r.get('office_name'), r.get('municipality'))

    # Build ward mapping: for Minneapolis (county 27), precinct name contains 'MINNEAPOLIS W-<num>' or 'MINNEAPOLIS W <num>' or 'MINNEAPOLIS W-<num> P-..'
    ward_map = {}
    for (county, precinct), name in precincts.items():
        if county == '27' and 'MINNEAPOLIS' in name.upper():
            m = re.search(r'W-?\s*([0-9]{1,2})', name.upper())
            if m:
                ward = m.group(1).lstrip('0')
                if ward == '':
                    ward = '0'
                ward_map[(county, precinct)] = ward

    # Aggregate by ward
    agg = {}
    ward_totals = {}
    missing_precincts = set()

    # identify Minneapolis municipality id from Municipalities_2025 map
    municipalities_map = read_municipalities_map()
    mpls_ids = [mid for mid, n in municipalities_map.items() if n and n.strip().upper() == 'MINNEAPOLIS']
    mpls_set = set(mpls_ids)
    # Quick check counts
    from collections import Counter
    names = [r.get('office_name','').strip() for r in rows if r.get('office_name')]
    c = Counter(names)
    print('DEBUG: top 10 office names and counts:')
    for name, cnt in c.most_common(10):
        print(cnt, name)
    global_mayor_count = sum(1 for r in rows if r.get('office_name') and 'MAYOR' in r['office_name'].upper())
    global_mpls_mayor_count = sum(1 for r in rows if r.get('office_name') and 'MAYOR' in r['office_name'].upper() and r.get('municipality') in mpls_set)
    print('DEBUG: global mayor rows: ', global_mayor_count)
    print('DEBUG: global Minneapolis mayor rows: ', global_mpls_mayor_count)

    mayor_row_count = 0
    mayor_mpls_count = 0
    ward_added_count = 0
    for r in rows:
        if not r.get('office_name'):
            continue
        oname = r['office_name'].upper()
        if 'MAYOR' not in oname:
            continue
        mayor_row_count += 1
        if r.get('municipality') not in mpls_set:
            continue
        mayor_mpls_count += 1
        # if user only wants "first" choices, skip 2nd/3rd etc lines
        if args.choice == 'first' and 'FIRST CHOICE' not in oname:
            continue
        keyp = (r['county'], r['precinct'])
        ward = ward_map.get(keyp)
        if not ward:
            missing_precincts.add(keyp)
            continue
        ward_dict = agg.setdefault(ward, {})
        cand_key = f"{r['candidate_name']}|{r['party']}"
        ward_dict[cand_key] = ward_dict.get(cand_key, 0) + r['votes']
        ward_totals[ward] = ward_totals.get(ward, 0) + r['votes']
        ward_added_count += 1

    # Output CSV and markdown
    out_csv = DATA_DIR / 'minneapolis_mayor_by_ward_2025.csv'
    with out_csv.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['Ward','Candidate|Party','Votes','Pct','WardTotal'])
        for ward in sorted(agg.keys(), key=lambda x: int(x)):
            total = ward_totals.get(ward, 0)
            for cand, v in sorted(agg[ward].items(), key=lambda kv: kv[1], reverse=True):
                pct = round((v/total*100),2) if total>0 else 0
                w.writerow([ward, cand, v, pct, total])

    out_md = DATA_DIR / 'minneapolis_mayor_by_ward_2025.md'
    with out_md.open('w', encoding='utf-8') as fh:
        fh.write('# Minneapolis Mayoral Results by Ward (2025)\n\n')
        fh.write('|Ward|Candidate|Party|Votes|Pct|WardTotal|\n')
        fh.write('|---:|---|---|---:|---:|---:|\n')
        for ward in sorted(agg.keys(), key=lambda x: int(x)):
            total = ward_totals.get(ward, 0)
            for cand, v in sorted(agg[ward].items(), key=lambda kv: kv[1], reverse=True):
                name, party = cand.split('|') if '|' in cand else (cand, '')
                pct = round((v/total*100),2) if total>0 else 0
                fh.write(f'|{ward}|{name}|{party}|{v}|{pct}|{total}|\n')

    # Summary & warnings
    print(f'Mayor rows in municipal file: {mayor_row_count}')
    print(f'Mayor rows for Minneapolis (municipality id match): {mayor_mpls_count}')
    print(f'Ward-level mayor rows included in aggregation: {ward_added_count}')
    if missing_precincts:
        print('WARNING: Some Minneapolis precincts could not be mapped to a ward (missing from Precincts_2025).')
        print('Count:', len(missing_precincts))
        # save or list a sample of missing precincts for debugging
        sample = list(missing_precincts)[:10]
        print('Sample missing precincts (county,precinct):', sample)
    print('Wrote', out_csv, 'and', out_md)

if __name__ == '__main__':
    main()
