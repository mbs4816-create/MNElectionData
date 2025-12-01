#!/usr/bin/env python3
"""
create_hennepin_comprehensive_kml.py

Create a comprehensive KML for Hennepin County precincts showing:
- Minneapolis Mayor RCV Final Round 2025
- CD5 DFL Primary 2022  
- CD5 DFL Primary 2024
- Hennepin County Attorney 2022

Color-code by averaging performance: Blue for Frey/Samuels/Dimick, Red for their opponents
"""
import csv
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parents[1]
KML_IN = DATA_DIR / '2024_Results' / 'mn-cd5-precincts.kml'
VCR_CSV = DATA_DIR / '2025_Results' / '2025-Mayor-Cast-Vote-Record.csv'
PRIMARY_2022 = DATA_DIR / '2022_Results' / 'Federal_State_Results_2022_ByPrecinct_PRIMARY'
PRIMARY_2024 = DATA_DIR / '2024_Results' / 'Federal_State_County_ByPrecinct_2024_PRIMARY'
GENERAL_2022 = DATA_DIR / '2022_Results' / 'Federal_State_County_Precinct_2022'
KML_OUT = DATA_DIR / 'hennepin_comprehensive_2022_2025.kml'

# Target candidates - "blue" team
BLUE_CANDIDATES = {
    'frey', 'jacob frey',
    'samuels', 'don samuels', 'donald samuels',
    'dimick', 'martha holton dimick', 'martha dimick'
}

# Their main opponents - "red" team  
RED_CANDIDATES = {
    'fateh', 'omar fateh',
    'omar', 'ilhan omar',
    'moriarty', 'mary moriarty'
}


def normalize_precinct_name(name):
    """Normalize precinct name for matching"""
    if not name:
        return ''
    s = name.upper().strip()
    # Standardize formats
    s = re.sub(r'\bW-?\s*', 'W-', s)
    s = re.sub(r'\bP-?\s*', 'P-', s)
    # Pad single digit precinct/ward numbers
    s = re.sub(r'W-(\d)(?=\s|$|P)', r'W-0\1', s)
    s = re.sub(r'P-(\d)$', r'P-0\1', s)
    return s


def is_blue_candidate(name):
    """Check if candidate is on the 'blue' team"""
    if not name:
        return False
    n = name.strip().lower()
    return any(bc in n for bc in BLUE_CANDIDATES)


def is_red_candidate(name):
    """Check if candidate is on the 'red' team"""
    if not name:
        return False
    n = name.strip().lower()
    return any(rc in n for rc in RED_CANDIDATES)


def parse_vcr_mayor():
    """Parse 2025 mayor RCV results by precinct"""
    results = {}
    
    with VCR_CSV.open('r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames:
            reader.fieldnames = [fn.lstrip('\ufeff') for fn in reader.fieldnames]
        
        for row in reader:
            precinct = row.get('Precinct', '').strip()
            first = row.get('1st Choice Mayor', '').strip()
            second = row.get('2nd Choice Mayor', '').strip()
            third = row.get('3rd Choice Mayor', '').strip()
            count_str = row.get('Count', '1')
            try:
                count = int(count_str)
            except:
                count = 1
            
            # RCV reallocation
            blue_vote = 0
            red_vote = 0
            
            if is_blue_candidate(first):
                blue_vote = count
            elif is_red_candidate(first):
                red_vote = count
            else:
                if is_blue_candidate(second):
                    blue_vote = count
                elif is_red_candidate(second):
                    red_vote = count
                else:
                    if is_blue_candidate(third):
                        blue_vote = count
                    elif is_red_candidate(third):
                        red_vote = count
            
            pkey = normalize_precinct_name(precinct)
            if pkey not in results:
                results[pkey] = {'blue': 0, 'red': 0, 'total': 0}
            
            results[pkey]['blue'] += blue_vote
            results[pkey]['red'] += red_vote
            results[pkey]['total'] += count
    
    return results


def parse_primary_cd5(filepath, year):
    """Parse CD5 DFL primary results from primary file"""
    results = {}
    
    with open(filepath, 'r', encoding='utf-8') as fh:
        for line in fh:
            cols = line.strip().split(';')
            if len(cols) < 14:
                continue
            
            county = cols[1]
            precinct = cols[2]
            office = cols[4]
            candidate = cols[7]
            party = cols[10]
            votes_str = cols[13]
            
            # Only CD5, DFL primary, Hennepin County (27)
            if county != '27':
                continue
            if 'representative' not in office.lower() or '5' not in office:
                continue
            if party != 'DFL':
                continue
            
            try:
                votes = int(votes_str)
            except:
                votes = 0
            
            # Build precinct key from county/precinct
            # Map precinct ID to precinct name using Precincts file
            pkey = (county, precinct)
            
            if pkey not in results:
                results[pkey] = {'blue': 0, 'red': 0, 'total': 0}
            
            if is_blue_candidate(candidate):
                results[pkey]['blue'] += votes
            elif is_red_candidate(candidate):
                results[pkey]['red'] += votes
            
            results[pkey]['total'] += votes
    
    return results


def parse_county_attorney_2022():
    """Parse Hennepin County Attorney 2022 results"""
    results = {}
    
    with open(GENERAL_2022, 'r', encoding='utf-8') as fh:
        for line in fh:
            cols = line.strip().split(';')
            if len(cols) < 14:
                continue
            
            county = cols[1]
            precinct = cols[2]
            office = cols[4]
            candidate = cols[7]
            votes_str = cols[13]
            
            if county != '27':
                continue
            if 'county attorney' not in office.lower():
                continue
            
            try:
                votes = int(votes_str)
            except:
                votes = 0
            
            pkey = (county, precinct)
            
            if pkey not in results:
                results[pkey] = {'blue': 0, 'red': 0, 'total': 0}
            
            if is_blue_candidate(candidate):
                results[pkey]['blue'] += votes
            elif is_red_candidate(candidate):
                results[pkey]['red'] += votes
            
            results[pkey]['total'] += votes
    
    return results


def load_precinct_id_to_name():
    """Load mapping from (county, precinct_id) to precinct name"""
    mapping = {}
    precinct_file = DATA_DIR / '2024_Results' / 'Precincts_2024'
    
    if not precinct_file.exists():
        precinct_file = DATA_DIR / '2022_Results' / 'Precincts_2022'
    
    with open(precinct_file, 'r', encoding='utf-8') as fh:
        for line in fh:
            cols = line.strip().split(';')
            if len(cols) < 3:
                continue
            county = cols[0]
            precinct_id = cols[1]
            name = cols[2]
            mapping[(county, precinct_id)] = normalize_precinct_name(name)
    
    return mapping


def calculate_avg_blue_share(mayor, cd5_2022, cd5_2024, county_atty):
    """Calculate average blue share across all available races"""
    shares = []
    race_details = []
    
    if mayor and mayor['total'] > 0:
        blue_pct = round(mayor['blue'] / mayor['total'] * 100, 1)
        red_pct = round(mayor['red'] / mayor['total'] * 100, 1)
        other_pct = round((mayor['total'] - mayor['blue'] - mayor['red']) / mayor['total'] * 100, 1)
        shares.append(mayor['blue'] / mayor['total'])
        race_details.append({
            'name': 'Minneapolis Mayor RCV 2025',
            'candidates': [
                ('Jacob Frey', mayor['blue'], blue_pct),
                ('Omar Fateh', mayor['red'], red_pct),
                ('Exhausted', mayor['total'] - mayor['blue'] - mayor['red'], other_pct)
            ],
            'total': mayor['total']
        })
    
    if cd5_2022 and cd5_2022['total'] > 0:
        blue_pct = round(cd5_2022['blue'] / cd5_2022['total'] * 100, 1)
        red_pct = round(cd5_2022['red'] / cd5_2022['total'] * 100, 1)
        other_pct = round((cd5_2022['total'] - cd5_2022['blue'] - cd5_2022['red']) / cd5_2022['total'] * 100, 1)
        shares.append(cd5_2022['blue'] / cd5_2022['total'])
        race_details.append({
            'name': 'CD5 DFL Primary 2022',
            'candidates': [
                ('Don Samuels', cd5_2022['blue'], blue_pct),
                ('Ilhan Omar', cd5_2022['red'], red_pct),
                ('Other', cd5_2022['total'] - cd5_2022['blue'] - cd5_2022['red'], other_pct)
            ],
            'total': cd5_2022['total']
        })
    
    if cd5_2024 and cd5_2024['total'] > 0:
        blue_pct = round(cd5_2024['blue'] / cd5_2024['total'] * 100, 1)
        red_pct = round(cd5_2024['red'] / cd5_2024['total'] * 100, 1)
        other_pct = round((cd5_2024['total'] - cd5_2024['blue'] - cd5_2024['red']) / cd5_2024['total'] * 100, 1)
        shares.append(cd5_2024['blue'] / cd5_2024['total'])
        race_details.append({
            'name': 'CD5 DFL Primary 2024',
            'candidates': [
                ('Don Samuels', cd5_2024['blue'], blue_pct),
                ('Ilhan Omar', cd5_2024['red'], red_pct),
                ('Other', cd5_2024['total'] - cd5_2024['blue'] - cd5_2024['red'], other_pct)
            ],
            'total': cd5_2024['total']
        })
    
    if county_atty and county_atty['total'] > 0:
        blue_pct = round(county_atty['blue'] / county_atty['total'] * 100, 1)
        red_pct = round(county_atty['red'] / county_atty['total'] * 100, 1)
        other_pct = round((county_atty['total'] - county_atty['blue'] - county_atty['red']) / county_atty['total'] * 100, 1)
        shares.append(county_atty['blue'] / county_atty['total'])
        race_details.append({
            'name': 'Hennepin County Attorney 2022',
            'candidates': [
                ('Martha Holton Dimick', county_atty['blue'], blue_pct),
                ('Mary Moriarty', county_atty['red'], red_pct),
                ('Other', county_atty['total'] - county_atty['blue'] - county_atty['red'], other_pct)
            ],
            'total': county_atty['total']
        })
    
    if not shares:
        return 0.5, race_details
    
    return sum(shares) / len(shares), race_details


def color_for_avg_share(avg_blue_share):
    """Generate color based on average blue share (0-1)"""
    if avg_blue_share > 0.5:
        # Blue wins
        intensity = min(1.0, (avg_blue_share - 0.5) * 2)
        alpha = 'cc'
        blue = hex(int(100 + 155 * intensity))[2:].zfill(2)
        green = '40'
        red = '40'
        return f'{alpha}{blue}{green}{red}'
    else:
        # Red wins
        intensity = min(1.0, (0.5 - avg_blue_share) * 2)
        alpha = 'cc'
        blue = '40'
        green = '40'
        red = hex(int(100 + 155 * intensity))[2:].zfill(2)
        return f'{alpha}{blue}{green}{red}'


def format_description(precinct_name, race_details):
    """Generate HTML description for precinct popup"""
    html = f'<![CDATA[\n<h3>{precinct_name}</h3>\n'
    
    for race in race_details:
        html += f'<h4>{race["name"]}</h4>\n'
        html += '<table border="1" cellpadding="5" style="border-collapse:collapse;">\n'
        html += '<tr><th>Candidate</th><th>Votes</th><th>Percent</th></tr>\n'
        
        for candidate_name, votes, pct in race['candidates']:
            if votes > 0 or candidate_name in ['Jacob Frey', 'Don Samuels', 'Martha Holton Dimick', 'Omar Fateh', 'Ilhan Omar', 'Mary Moriarty']:
                html += f'<tr><td>{candidate_name}</td><td>{votes:,}</td><td>{pct}%</td></tr>\n'
        
        html += f'<tr style="font-weight:bold;"><td>Total</td><td>{race["total"]:,}</td><td>100.0%</td></tr>\n'
        html += '</table>\n<br/>\n'
    
    html += ']]>'
    return html


def create_kml(mayor_data, cd5_2022_data, cd5_2024_data, county_atty_data, id_to_name):
    """Create comprehensive KML"""
    tree = ET.parse(KML_IN)
    root = tree.getroot()
    
    new_kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    doc = ET.SubElement(new_kml, 'Document')
    doc_name = ET.SubElement(doc, 'name')
    doc_name.text = 'Hennepin County Comprehensive Results 2022-2025'
    
    matched = 0
    skipped = 0
    
    for placemark in root.iter():
        if 'Placemark' not in placemark.tag:
            continue
        
        name_elem = None
        for child in placemark:
            if 'name' in child.tag:
                name_elem = child
                break
        
        if name_elem is None or not name_elem.text:
            continue
        
        precinct_name = name_elem.text.strip()
        pkey_normalized = normalize_precinct_name(precinct_name)
        
        # Look up data for this precinct
        mayor = mayor_data.get(pkey_normalized)
        
        # For primary data, we need to reverse-lookup the (county, precinct_id) from name
        # Find matching ID
        pkey_id = None
        for (county, pid), name in id_to_name.items():
            if name == pkey_normalized:
                pkey_id = (county, pid)
                break
        
        # Skip if not Hennepin County
        if not pkey_id or pkey_id[0] != '27':
            skipped += 1
            continue
        
        cd5_2022 = cd5_2022_data.get(pkey_id) if pkey_id else None
        cd5_2024 = cd5_2024_data.get(pkey_id) if pkey_id else None
        county_atty = county_atty_data.get(pkey_id) if pkey_id else None
        
        # Include all Hennepin County precincts even if only one race has data
        if not any([mayor, cd5_2022, cd5_2024, county_atty]):
            skipped += 1
            continue
        
        matched += 1
        
        # Calculate average blue share and get race details
        avg_blue, race_details = calculate_avg_blue_share(mayor, cd5_2022, cd5_2024, county_atty)
        
        # Create placemark
        new_pm = ET.SubElement(doc, 'Placemark')
        new_name = ET.SubElement(new_pm, 'name')
        new_name.text = precinct_name
        
        desc = ET.SubElement(new_pm, 'description')
        desc.text = format_description(precinct_name, race_details)
        
        # Copy geometry
        polygon = None
        for child in placemark:
            if 'Polygon' in child.tag:
                polygon = child
                break
        
        if polygon is not None:
            new_pm.append(polygon)
        
        # Add style
        color = color_for_avg_share(avg_blue)
        style = ET.SubElement(new_pm, 'Style')
        poly_style = ET.SubElement(style, 'PolyStyle')
        color_elem = ET.SubElement(poly_style, 'color')
        color_elem.text = color
        fill = ET.SubElement(poly_style, 'fill')
        fill.text = '1'
        outline = ET.SubElement(poly_style, 'outline')
        outline.text = '1'
        
        line_style = ET.SubElement(style, 'LineStyle')
        line_color = ET.SubElement(line_style, 'color')
        line_color.text = 'ff000000'
        line_width = ET.SubElement(line_style, 'width')
        line_width.text = '1'
    
    print(f'Matched {matched} precincts with data')
    print(f'Skipped {skipped} precincts (no data)')
    
    tree_out = ET.ElementTree(new_kml)
    ET.indent(tree_out, space='  ')
    tree_out.write(KML_OUT, encoding='utf-8', xml_declaration=True)
    print(f'Wrote KML to {KML_OUT}')


if __name__ == '__main__':
    print('Loading precinct ID mappings...')
    id_to_name = load_precinct_id_to_name()
    
    print('Parsing 2025 Mayor RCV results...')
    mayor_data = parse_vcr_mayor()
    print(f'  Loaded {len(mayor_data)} precincts')
    
    print('Parsing 2022 CD5 DFL Primary...')
    cd5_2022_data = parse_primary_cd5(PRIMARY_2022, 2022)
    print(f'  Loaded {len(cd5_2022_data)} precincts')
    
    print('Parsing 2024 CD5 DFL Primary...')
    cd5_2024_data = parse_primary_cd5(PRIMARY_2024, 2024)
    print(f'  Loaded {len(cd5_2024_data)} precincts')
    
    print('Parsing 2022 County Attorney...')
    county_atty_data = parse_county_attorney_2022()
    print(f'  Loaded {len(county_atty_data)} precincts')
    
    print('\nCreating comprehensive KML...')
    create_kml(mayor_data, cd5_2022_data, cd5_2024_data, county_atty_data, id_to_name)
    print('Done!')
