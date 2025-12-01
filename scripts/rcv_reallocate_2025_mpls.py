#!/usr/bin/env python3
"""
rcv_reallocate_2025_mpls.py

Perform an RCV reallocation for the Minneapolis 2025 mayor race, eliminating all candidates
except Jacob Frey and Omar Fateh and reallocating ballots by 2nd/3rd choices.

Output:
 - district_rcv_frey_fateh_2025.csv (per district Frey/Fateh/exhausted totals)
 - district_race_top2_summary_rcv.csv (top2 summary with margins and totals)
 - Optionally: append RCV final rows into existing district_race_results.csv
"""
import csv
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parents[1]
R_DIR = DATA_DIR / '2025_Results'


def read_precincts_map_for_names():
    """Read Precincts_2025 and build a map from normalized precinct name -> (county, precinct id)
    Normalization: uppercase, collapse whitespace, remove punctuation except dash and spaces.
    """
    pfile = R_DIR / 'Precincts_2025'
    name_to_key = {}
    with pfile.open('r', encoding='utf-8') as fh:
        for line in fh:
            line=line.strip()
            if not line:
                continue
            cols = line.split(';')
            if len(cols) < 3:
                continue
            county, precinct, pname = cols[0], cols[1], cols[2]
            norm = normalize_precinct_name(pname)
            name_to_key[norm] = (county, precinct)
    return name_to_key


def normalize_precinct_name(name: str) -> str:
    if not name:
        return ''
    s = name.upper().strip()
    s = re.sub(r"[^A-Z0-9\- ]+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


# Reuse read_precincts from compute_district_votes slightly altered: returns mapping (county,precinct) -> metadata

def read_precincts_for_rcv():
    pfile = R_DIR / 'Precincts_2025'
    mapping = {}
    with pfile.open('r', encoding='utf-8') as fh:
        for line in fh:
            line=line.strip()
            if not line:
                continue
            cols = line.split(';')
            if len(cols) < 6:
                continue
            county = cols[0]
            precinct = cols[1]
            leg = cols[4] if len(cols) > 4 else ''
            ccd = cols[5] if len(cols) > 5 else ''
            name = cols[2]
            mapping[(county, precinct)] = {
                'leg': leg.strip(),
                'ccd': ccd.strip(),
                'name': name,
            }
    return mapping


def precincts_for_county_commissioner_district(precinct_map, county_id, ccd):
    keys = set()
    for (county, precinct), v in precinct_map.items():
        if county == county_id and v.get('ccd','') == ccd:
            keys.add((county, precinct))
    return keys


def precincts_for_legislative_district(precinct_map, county_id, leg_suffix):
    keys = set()
    import re
    for (county, precinct), v in precinct_map.items():
        if county != county_id:
            continue
        leg = v.get('leg','') or ''
        if not leg:
            continue
        if leg == leg_suffix:
            keys.add((county, precinct))
            continue
        if leg_suffix.isdigit():
            if re.match(rf'^{leg_suffix}(?:[A-Za-z])?$', leg):
                keys.add((county, precinct))
        else:
            if leg.startswith(leg_suffix):
                keys.add((county, precinct))
    return keys


def parse_vote_cast_record(vcr_path):
    out = []
    with open(vcr_path, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        # Strip BOM from the first fieldname if present (some CSVs include a BOM)
        if reader.fieldnames:
            reader.fieldnames = [fn.lstrip('\ufeff') for fn in reader.fieldnames]
        for r in reader:
            precinct = r.get('Precinct','').strip()
            first = r.get('1st Choice Mayor','').strip()
            second = r.get('2nd Choice Mayor','').strip()
            third = r.get('3rd Choice Mayor','').strip()
            count = r.get('Count','1')
            try:
                cnt = int(count)
            except ValueError:
                try:
                    cnt = int(float(count))
                except Exception:
                    cnt = 1
            out.append({
                'precinct_name': precinct,
                'first': first,
                'second': second,
                'third': third,
                'count': cnt,
            })
    return out


def is_frey(name):
    if not name:
        return False
    n = name.strip().lower()
    return 'frey' in n or 'jacob frey' in n


def is_fateh(name):
    if not name:
        return False
    n = name.strip().lower()
    return 'fateh' in n or 'omar fateh' in n


def rcv_reallocate_for_districts(vcr_rows, precinct_name_map, precincts_map, districts):
    # Build mapping from precinct name to (county,precinct) using normalized key
    # We will accumulate per district totals for Frey/Fateh/exhausted
    results = defaultdict(lambda: defaultdict(int))
    # For fast lookup: mapping of precinct_name_norm -> key
    # Note: some precinct names in VCR may have exact mapping in precinct_name_map; else try partial matching by removing p-suffix

    # Build normalized map
    normalized_name_to_key = {}
    for name, key in precinct_name_map.items():
        normalized_name_to_key[name] = key

    # For faster precinct membership checks per district: compute keys sets
    district_keys = {}
    for d in districts:
        dname = d['name']
        if d['type'] == 'county':
            keys = set(k for k in precincts_map.keys() if k[0] == d['county'])
        elif d['type'] == 'ccd':
            keys = precincts_for_county_commissioner_district(precincts_map, d['county'], d['ccd'])
        elif d['type'] == 'leg':
            keys = precincts_for_legislative_district(precincts_map, d['county'], d['leg'])
        else:
            keys = set()
        district_keys[dname] = keys

    # For each ballot row
    for r in vcr_rows:
        pname = r['precinct_name']
        pn_norm = normalize_precinct_name(pname)
        # find matching key
        if pn_norm in normalized_name_to_key:
            key = normalized_name_to_key[pn_norm]
        else:
            # try removing P-xx suffix, or P xx
            k2 = re.sub(r'\bP-?\d+\b','', pn_norm).strip()
            if k2 in normalized_name_to_key:
                key = normalized_name_to_key[k2]
            else:
                # try matching only 'MINNEAPOLIS W-<num>' prefix
                m = re.search(r'(MINNEAPOLIS W-?\d+)', pn_norm)
                key = None
                if m:
                    pref = m.group(1).strip()
                    # Find any mapping that contains pref
                    for nm, kk in normalized_name_to_key.items():
                        if pref in nm:
                            key = kk
                            break
                if not key:
                    continue
        # Now for each district, if the ballot's precinct key is within that district, allocate
        for d in districts:
            if key not in district_keys.get(d['name'], set()):
                continue
            # perform RCV elimination of everyone except Frey & Fateh
            assigned = None
            if is_frey(r['first']):
                assigned = 'Jacob Frey|N P'
            elif is_fateh(r['first']):
                assigned = 'Omar Fateh|D'
            else:
                # try second
                if is_frey(r['second']):
                    assigned = 'Jacob Frey|N P'
                elif is_fateh(r['second']):
                    assigned = 'Omar Fateh|D'
                else:
                    if is_frey(r['third']):
                        assigned = 'Jacob Frey|N P'
                    elif is_fateh(r['third']):
                        assigned = 'Omar Fateh|D'
            if assigned:
                results[(2025, 'Mayor Final Round (Frey vs Fateh, RCV Reallocated)', d['name'])][assigned] += r['count']
            else:
                results[(2025, 'Mayor Final Round (Frey vs Fateh, RCV Reallocated)', d['name'])]['EXHAUSTED'] += r['count']
            # also count total ballots
            results[(2025, 'Mayor Final Round (Frey vs Fateh, RCV Reallocated)', d['name'])]['_TOTAL_BALLOTS'] += r['count']
    return results


def write_results_csv(results, out_csv_path):
    # results: dict keyed by (year, office, district) -> candidate -> votes; includes EXHAUSTED and _TOTAL_BALLOTS
    rows = []
    for (year, office, district), candmap in results.items():
        total = candmap.get('_TOTAL_BALLOTS', 0)
        for cand, votes in candmap.items():
            if cand == '_TOTAL_BALLOTS':
                continue
            pct = round((votes/total*100), 2) if total>0 else 0
            rows.append([year, office, district, cand, votes, pct, total])
    # write CSV
    with open(out_csv_path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['Year','Office','District','Candidate|Party','Votes','Pct','TotalBallots'])
        for r in sorted(rows):
            w.writerow(r)


if __name__ == '__main__':
    # District list (should match compute_district_votes's districts)
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

    vcr_path = R_DIR / '2025-Mayor-Cast-Vote-Record.csv'
    if not vcr_path.exists():
        print('Vote-cast record file not found:', vcr_path)
        raise SystemExit(1)
    vcr_rows = parse_vote_cast_record(vcr_path)

    precincts_map = read_precincts_for_rcv()
    precinct_name_map = read_precincts_map_for_names()

    results = rcv_reallocate_for_districts(vcr_rows, precinct_name_map, precincts_map, districts)

    # write results
    out_csv = DATA_DIR / 'district_rcv_frey_fateh_2025.csv'
    write_results_csv(results, out_csv)

    # Build top2 summary for RCV results
    summary_rows = []
    for (year, office, district), cand_map in results.items():
        total = cand_map.get('_TOTAL_BALLOTS', 0)
        # exclude _TOTAL_BALLOTS and EXHAUSTED for candidate sorting
        pairs = [(c, v) for c, v in cand_map.items() if c not in ('_TOTAL_BALLOTS','EXHAUSTED')]
        pairs = sorted(pairs, key=lambda kv: kv[1], reverse=True)
        top = pairs[0] if pairs else (None, 0)
        second = pairs[1] if len(pairs)>1 else (None, 0)
        exhausted = cand_map.get('EXHAUSTED', 0)
        topname, topvotes = top
        secondname, secondvotes = second
        top_pct = round((topvotes/total*100) if total>0 else 0, 2)
        second_pct = round((secondvotes/total*100) if total>0 else 0, 2)
        margin_votes = topvotes - secondvotes
        margin_pct = round((margin_votes/total*100) if total>0 else 0, 2)
        summary_rows.append([year, office, district, topname, topvotes, top_pct, secondname, secondvotes, second_pct, margin_votes, margin_pct, total, exhausted])

    out_summary = DATA_DIR / 'district_race_top2_summary_rcv.csv'
    with out_summary.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['Year','Office','District','TopCandidate|Party','TopVotes','TopPct','RunnerUpCandidate|Party','RunnerUpVotes','RunnerUpPct','MarginVotes','MarginPct','TotalBallots','Exhausted'])
        for r in sorted(summary_rows):
            w.writerow(r)

    print('Wrote RCV results to', out_csv, 'and summary', out_summary)
