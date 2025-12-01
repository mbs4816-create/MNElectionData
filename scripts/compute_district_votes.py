#!/usr/bin/env python3
"""
compute_district_votes.py

Aggregate election results for specified races and districts using OSS 2022 & 2024 flat files
Output: district_race_results.csv and district_race_results.md

Usage: python scripts/compute_district_votes.py
"""
import csv
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]

def read_precincts(year):
    # The repo stores Precincts_2022/Precincts_2024/Precincts_2025 under their respective folders
    if year == 2022:
        pfile = DATA_DIR / '2022_Results' / 'Precincts_2022'
    elif year == 2024:
        pfile = DATA_DIR / '2024_Results' / 'Precincts_2024'
    elif year == 2025:
        pfile = DATA_DIR / '2025_Results' / 'Precincts_2025'
    else:
        pfile = DATA_DIR / f"{year}_Results" / f"Precincts_{year}"

    mapping = {}
    with pfile.open('r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cols = line.split(';')
            # Expected fields: County ID, Precinct ID, Precinct Name, Congressional District, Legislative District, County Commissioner District, Judicial District, Soil & Water District, MCD FIPS, School District number
            if len(cols) < 6:
                continue
            county = cols[0]
            precinct = cols[1]
            leg = cols[4] if len(cols) > 4 else ''
            ccd = cols[5] if len(cols) > 5 else ''
            mapping[(county, precinct)] = {
                'leg': leg.strip(),
                'ccd': ccd.strip(),
            }
    return mapping

def parse_results_file(path):
    """Parse OSS flat file into rows
    Returns list of dicts with keys: state, county, precinct, office_name, district, candidate_code, candidate_name, party, votes, pct, total
    """
    out = []
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cols = line.split(';')
            # Some file rows may be shorter if fields missing
            if len(cols) < 15:
                # Pad to avoid index errors
                cols += [''] * (15 - len(cols))
            state = cols[0]
            county = cols[1]
            precinct = cols[2]
            office_name = cols[4]
            district = cols[5]
            candidate_code = cols[6]
            candidate_name = cols[7]
            party = cols[10]
            votes = cols[13] if len(cols) > 13 else '0'
            pct = cols[14] if len(cols) > 14 else '0'
            total = cols[15] if len(cols) > 15 else ''
            try:
                votes_i = int(votes)
            except ValueError:
                votes_i = 0
            try:
                pct_f = float(pct)
            except ValueError:
                pct_f = 0.0
            out.append({
                'state': state,
                'county': county,
                'precinct': precinct,
                'office_name': office_name,
                'district': district,
                'candidate_code': candidate_code,
                'candidate_name': candidate_name,
                'party': party,
                'votes': votes_i,
                'pct': pct_f,
            })
    return out

def precincts_for_county_commissioner_district(precinct_map, county_id, ccd):
    # returns set of (county, precinct) keys matching county id and ccd
    keys = set()
    for (county, precinct), v in precinct_map.items():
        if county == county_id and v.get('ccd','') == ccd:
            keys.add((county, precinct))
    return keys

def precincts_for_legislative_district(precinct_map, county_id, leg_suffix):
    keys = set()
    # leg_suffix like '46' or '43A'. The precinct leg may be '46A' or '46B' for a senate district split.
    # Support matches where leg == leg_suffix OR (leg starts with leg_suffix and has a single-letter suffix).
    for (county, precinct), v in precinct_map.items():
        if county == county_id:
            leg = v.get('leg','').strip()
            if not leg:
                continue
            if leg == leg_suffix:
                keys.add((county, precinct))
                continue
            # If the search key is purely numeric (e.g., '46'), match '46A', '46B'
            if leg_suffix.isdigit():
                # match '46', '46A', '46B', but avoid matching '461'
                if re.match(rf'^{leg_suffix}(?:[A-Za-z])?$', leg):
                    keys.add((county, precinct))
            else:
                # leg_suffix may already include letter (e.g., '43A') - match startswith exact
                if leg.startswith(leg_suffix):
                    keys.add((county, precinct))
    return keys

def aggregate_by_district(results, precinct_keys):
    # results: list of parsed lines for a given file
    totals = defaultdict(lambda: defaultdict(int))
    office_total_votes = defaultdict(int)
    for row in results:
        key = (row['county'], row['precinct'])
        if key in precinct_keys:
            office = row['office_name']
            candidate = f"{row['candidate_name']}|{row['party']}"
            totals[office][candidate] += row['votes']
            office_total_votes[office] += row['votes']
    return totals, office_total_votes

def summarize(office_totals, office_total_votes, remove_writein=True):
    rows = []
    for office, cand_map in office_totals.items():
        total_votes = office_total_votes.get(office, 0)
        # convert to sorted list
        pairs = sorted(cand_map.items(), key=lambda kv: kv[1], reverse=True)
        if remove_writein:
            pairs = [(c, v) for (c, v) in pairs if not c.startswith('WRITE-IN') and c.strip()]
        if not pairs:
            continue
        top = pairs[0]
        second = pairs[1] if len(pairs) > 1 else (None, 0)
        rows.append({
            'office': office,
            'total_votes': total_votes,
            'top_candidate': top[0],
            'top_votes': top[1],
            'top_pct': (top[1]/ total_votes *100) if total_votes>0 else 0,
            'second_candidate': second[0] if second[0] else '',
            'second_votes': second[1] if second[1] else 0,
            'second_pct': (second[1]/ total_votes *100) if total_votes>0 else 0,
            'margin_votes': top[1]-second[1] if second[0] else top[1],
            'margin_pct': ((top[1]-second[1])/ total_votes *100) if total_votes>0 and second[0] else (top[1]/total_votes *100 if total_votes>0 else 0)
        })
        # Also include all candidate rows for the office
        for c,v in pairs:
            rows.append({
                'office': office,
                'total_votes': total_votes,
                'candidate': c,
                'votes': v,
                'pct': (v/total_votes*100) if total_votes>0 else 0,
            })
    return rows

def main():
    # Prepare precinct maps for 2024 & 2022
    p2022 = read_precincts(2022)
    p2024 = read_precincts(2024)
    p2025 = read_precincts(2025)

    # Races
    races_2024 = ["U.S. President & Vice President"]
    # Add county commissioner offices for the target counties if present (0392 - Dist 2, 0393 - D3, 0394 - D4, Ramsey 0395 & 0396 for 5/6)
    races_2022 = ["Governor & Lt Governor", "Attorney General", "County Attorney", "County Commissioner District 2", "County Commissioner District 3", "County Commissioner District 4", "County Commissioner District 5", "County Commissioner District 6", "State Senator District 46", "State Representative District 43A", "State Representative District 43B"]

    # Districts: a list of dicts for config
    districts = [
        {'name': 'Hennepin County (all)', 'county': '27', 'type': 'county'},
        {'name': 'Hennepin County Commission District 2', 'county': '27', 'ccd': '02', 'type': 'ccd'},
        {'name': 'Hennepin County Commission District 3', 'county': '27', 'ccd': '03', 'type': 'ccd'},
        {'name': 'Hennepin County Commission District 4', 'county': '27', 'ccd': '04', 'type': 'ccd'},
        {'name': 'Ramsey County Commission District 5', 'county': '62', 'ccd': '05', 'type': 'ccd'},
        {'name': 'Ramsey County Commission District 6', 'county': '62', 'ccd': '06', 'type': 'ccd'},
        {'name': 'State Senator District 46 (Hennepin)', 'county': '27', 'leg': '46', 'type': 'leg'},
        {'name': 'State House 43A (Hennepin)', 'county': '27', 'leg': '43A', 'type': 'leg'},
        {'name': 'State House 43B (Hennepin)', 'county': '27', 'leg': '43B', 'type': 'leg'},
    ]

    # Parse results
    res2022 = parse_results_file(DATA_DIR / "2022_Results" / "Federal_State_County_Precinct_2022")
    # Optional supplemental 2022 file (for missing counties like Ramsey) can be provided as CLI argument:
    #   python scripts/compute_district_votes.py --supplemental-2022 /path/to/file
    if '--supplemental-2022' in sys.argv:
        idx = sys.argv.index('--supplemental-2022')
        if idx + 1 < len(sys.argv):
            supp_path = Path(sys.argv[idx+1])
            if supp_path.exists():
                print('Merging supplemental 2022 file:', supp_path)
                supp_rows = parse_results_file(supp_path)
                # avoid duplicates by building a set of existing keys
                existing_keys = set((r['state'], r['county'], r['precinct'], r['office_name'], r['district'], r['candidate_code'], r['candidate_name']) for r in res2022)
                before = len(res2022)
                for r in supp_rows:
                    key = (r['state'], r['county'], r['precinct'], r['office_name'], r['district'], r['candidate_code'], r['candidate_name'])
                    if key not in existing_keys:
                        res2022.append(r)
                after = len(res2022)
                print(f'Appended {after - before} supplemental 2022 rows')
            else:
                print('Supplemental 2022 path not found:', supp_path)
    res2024 = parse_results_file(DATA_DIR / "2024_Results" / "Federal_State_County_ByPrecinct_2024")
    # read municipal 2025 OSS results if present
    res2025 = []
    mfile1 = DATA_DIR / '2025_Results' / 'Municipal_Hospital_School_Precinct_2025'
    mfile2 = DATA_DIR / '2025_Results' / 'All_MuniHospitalSchoolDistritct_2025'
    if mfile1.exists():
        res2025.extend(parse_results_file(mfile1))
    if mfile2.exists():
        res2025.extend(parse_results_file(mfile2))

    # detect missing counties in 2022 Federal/State results (e.g. Ramsey 62 may be absent)
    present_counties_2022 = set(r['county'] for r in res2022)
    requested_counties = set(d['county'] for d in districts)
    missing_counties = requested_counties - present_counties_2022
    if missing_counties:
        print('WARNING: The following requested counties are missing from 2022 Federal/State data:', ','.join(sorted(missing_counties)))

    all_rows = []

    # Helper to compute district's precinct keys for a year
    def precinct_keys_for(district, year):
        pm = p2022 if year==2022 else p2024 if year==2024 else p2025 if year==2025 else {}
        county = district['county']
        if district['type'] == 'county':
            return set(k for k in pm.keys() if k[0] == county)
        if district['type'] == 'ccd':
            return precincts_for_county_commissioner_district(pm, county, district['ccd'])
        if district['type'] == 'leg':
            return precincts_for_legislative_district(pm, county, district['leg'])
        return set()

    # For each district, compute 2024 president (filter res2024 by precincts)
    for d in districts:
        # 2024 President
        keys24 = precinct_keys_for(d, 2024)
        totals24, t24 = aggregate_by_district(res2024, keys24)
        # pick the race of interest
        office = 'U.S. President & Vice President'
        if office in totals24:
            # summarize top candidates
            # compute candidate rows
            total_votes = t24.get(office, 0)
            cand_map = totals24[office]
            for candidate, votes in sorted(cand_map.items(), key=lambda kv: kv[1], reverse=True):
                pct = (votes/total_votes*100) if total_votes>0 else 0
                all_rows.append([2024, office, d['name'], candidate, votes, round(pct,2)])

    # For 2022 races
    for d in districts:
        keys22 = precinct_keys_for(d, 2022)
        totals22, t22 = aggregate_by_district(res2022, keys22)
        for office in races_2022:
            if office in totals22:
                total_votes = t22.get(office, 0)
                for candidate, votes in sorted(totals22[office].items(), key=lambda kv: kv[1], reverse=True):
                    pct = (votes/total_votes*100) if total_votes>0 else 0
                    all_rows.append([2022, office, d['name'], candidate, votes, round(pct,2)])

    # For 2025 municipal races (Minneapolis Mayor), if present
    if res2025:
        for d in districts:
            keys25 = precinct_keys_for(d, 2025)
            if not keys25:
                continue
            # restrict to Minneapolis municipal rows if parsing municipal OSS files
            mpls_rows = [r for r in res2025 if r.get('district') == '43000']
            totals25, t25 = aggregate_by_district(mpls_rows, keys25)
            # select mayor offices (any office with 'MAYOR')
            for office, cand_map in totals25.items():
                if 'MAYOR' in office.upper():
                    total_votes = t25.get(office, 0)
                    for candidate, votes in sorted(cand_map.items(), key=lambda kv: kv[1], reverse=True):
                        pct = (votes/total_votes*100) if total_votes>0 else 0
                        all_rows.append([2025, office, d['name'], candidate, votes, round(pct,2)])

    # Save CSV
    out_csv = DATA_DIR / 'district_race_results.csv'
    with out_csv.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['Year','Office','District','Candidate|Party','Votes','Pct'])
        for r in all_rows:
            w.writerow(r)

    # Save markdown
    out_md = DATA_DIR / 'district_race_results.md'
    with out_md.open('w', encoding='utf-8') as fh:
        fh.write('# District Race Results (Extracted)\n\n')
        fh.write('|Year|Office|District|Candidate|Party|Votes|Pct|\n')
        fh.write('|---|---|---|---|---:|---:|---:|\n')
        for r in all_rows:
            year, office, district, candparty, votes, pct = r
            cand, party = candparty.split('|') if '|' in candparty else (candparty, '')
            fh.write(f'|{year}|{office}|{district}|{cand}|{party}|{votes}|{pct}|\n')

    # Create a summary top-2 and margin CSV per Year/Office/District
    summary_rows = []
    # convert all_rows to mapping
    rows_map = defaultdict(list)
    for r in all_rows:
        year, office, district, candparty, votes, pct = r
        rows_map[(year, office, district)].append((candparty, votes))
    for (year, office, district), candlist in rows_map.items():
        total_votes = sum(v for _, v in candlist)
        sorted_cand = sorted(candlist, key=lambda kv: kv[1], reverse=True)
        top = sorted_cand[0] if sorted_cand else (None, 0)
        second = sorted_cand[1] if len(sorted_cand)>1 else (None, 0)
        topname, topvotes = top
        secondname, secondvotes = second
        top_pct = round((topvotes/total_votes*100) if total_votes>0 else 0, 2)
        second_pct = round((secondvotes/total_votes*100) if total_votes>0 else 0, 2)
        margin_votes = topvotes - secondvotes
        margin_pct = round((margin_votes/total_votes*100) if total_votes>0 else 0, 2)
        summary_rows.append([year, office, district, topname, topvotes, top_pct, secondname, secondvotes, second_pct, margin_votes, margin_pct, total_votes])

    summary_csv = DATA_DIR / 'district_race_top2_summary.csv'
    with summary_csv.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['Year','Office','District','TopCandidate|Party','TopVotes','TopPct','RunnerUpCandidate|Party','RunnerUpVotes','RunnerUpPct','MarginVotes','MarginPct','TotalVotes'])
        for r in sorted(summary_rows):
            w.writerow(r)
    print('Wrote', out_csv, 'and', out_md, 'and', summary_csv)

    print('Wrote', out_csv, 'and', out_md)

if __name__ == '__main__':
    main()
