#!/usr/bin/env python3
"""
pivot_district_results.py

Read the top-2 summary CSV(s) and pivot into a district-by-race CSV where each cell contains
TopCandidate|Party Votes (Pct); RunnerUpCandidate|Party Votes (Pct)
"""
import csv
from pathlib import Path
from collections import defaultdict, OrderedDict

DATA_DIR = Path(__file__).resolve().parents[1]

SUMMARY_CSV = DATA_DIR / 'district_race_top2_summary.csv'
RCV_SUMMARY_CSV = DATA_DIR / 'district_race_top2_summary_rcv.csv'
OUT_CSV = DATA_DIR / 'district_race_pivot.csv'
OUT_MD = DATA_DIR / 'district_race_pivot.md'


def read_summary(path):
    rows = []
    with path.open('r', encoding='utf-8') as fh:
        r = csv.DictReader(fh)
        for rec in r:
            # fields: Year,Office,District,TopCandidate|Party,TopVotes,TopPct,RunnerUpCandidate|Party,RunnerUpVotes,RunnerUpPct,MarginVotes,MarginPct,TotalVotes
            rows.append(rec)
    return rows


def format_cell(rec):
    # if rec is None return empty cell
    if not rec:
        return ''
    top = rec.get('TopCandidate|Party','')
    topvotes = rec.get('TopVotes','0')
    toppct = rec.get('TopPct','0')
    runner = rec.get('RunnerUpCandidate|Party','')
    runvotes = rec.get('RunnerUpVotes','0')
    runpct = rec.get('RunnerUpPct','0')
    # format: Top (Name|Party) Votes (Pct%); RunnerUp ...
    return f"{top} {topvotes} ({toppct}%) ; {runner} {runvotes} ({runpct}%)"


if __name__ == '__main__':
    if not SUMMARY_CSV.exists():
        print('Summary CSV not found:', SUMMARY_CSV)
        raise SystemExit(1)
    rows = read_summary(SUMMARY_CSV)
    # optionally load RCV summary and allow it to override matching (Year, Office, District)
    rcv_rows = []
    if RCV_SUMMARY_CSV.exists():
        rcv_rows = read_summary(RCV_SUMMARY_CSV)
    # Build mapping (Year, Office, District) -> rec
    mapping = {}
    for rec in rows:
        key = (rec['Year'], rec['Office'], rec['District'])
        mapping[key] = rec
    for rec in rcv_rows:
        key = (rec['Year'], rec['Office'], rec['District'])
        # override existing mapping if present
        mapping[key] = rec

    # Get all unique offices sorted and districts sorted
    offices = sorted({k[1] for k in mapping.keys()})
    districts = sorted({k[2] for k in mapping.keys()})

    # Build pivot rows
    with OUT_CSV.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        header = ['District'] + offices
        w.writerow(header)
        for d in districts:
            row = [d]
            for office in offices:
                key_candidates = [k for k in mapping.keys() if k[1]==office and k[2]==d]
                if not key_candidates:
                    row.append('')
                else:
                    # In case of multiple years, pick Year 2025 over 2024/2022? We'll choose latest year by lexicographic value
                    # Pick mapping keyed by max year
                    rec_key = sorted(key_candidates, key=lambda k: int(k[0]), reverse=True)[0]
                    rec = mapping[rec_key]
                    row.append(format_cell(rec))
            w.writerow(row)

    # Also write markdown
    with OUT_MD.open('w', encoding='utf-8') as fh:
        fh.write('# District Pivot Results\n\n')
        # header
        fh.write('|' + '|'.join(header) + '|\n')
        fh.write('|' + '|'.join(['---']*len(header)) + '|\n')
        for d in districts:
            rowcells = [d]
            for office in offices:
                key_candidates = [k for k in mapping.keys() if k[1]==office and k[2]==d]
                if not key_candidates:
                    rowcells.append('')
                else:
                    rec_key = sorted(key_candidates, key=lambda k: int(k[0]), reverse=True)[0]
                    rec = mapping[rec_key]
                    rowcells.append(format_cell(rec))
            fh.write('|' + '|'.join(rowcells) + '|\n')

    print('Wrote pivot CSV to', OUT_CSV, 'and markdown to', OUT_MD)
