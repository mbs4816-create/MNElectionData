#!/usr/bin/env python3
"""
create_mayor_kml.py

Create a KML file showing Minneapolis mayoral RCV final round results by precinct.
Blue shading for Frey, Red shading for Fateh, based on vote share.
"""
import csv
import re
import xml.etree.ElementTree as ET
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]
KML_IN = DATA_DIR / '2024_Results' / 'mn-cd5-precincts.kml'
VCR_CSV = DATA_DIR / '2025_Results' / '2025-Mayor-Cast-Vote-Record.csv'
KML_OUT = DATA_DIR / 'minneapolis_mayor_2025_rcv_map.kml'


def normalize_precinct_name(name):
    """Normalize precinct name for matching"""
    if not name:
        return ''
    # Convert "Minneapolis W-1 P-1" to "MINNEAPOLIS W-1 P-01" format
    s = name.upper().strip()
    # Handle P-# to P-0# padding
    s = re.sub(r'P-(\d)$', r'P-0\1', s)
    s = re.sub(r'P-(\d)\s', r'P-0\1 ', s)
    return s


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


def parse_vcr():
    """Parse vote cast record and aggregate RCV results by precinct"""
    precinct_results = {}
    
    with VCR_CSV.open('r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        # Strip BOM if present
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
            except ValueError:
                try:
                    count = int(float(count_str))
                except:
                    count = 1
            
            # RCV reallocation: assign to Frey or Fateh or exhausted
            assigned = None
            if is_frey(first):
                assigned = 'Frey'
            elif is_fateh(first):
                assigned = 'Fateh'
            else:
                if is_frey(second):
                    assigned = 'Frey'
                elif is_fateh(second):
                    assigned = 'Fateh'
                else:
                    if is_frey(third):
                        assigned = 'Frey'
                    elif is_fateh(third):
                        assigned = 'Fateh'
            
            # Normalize precinct name for lookup
            pkey = normalize_precinct_name(precinct)
            if pkey not in precinct_results:
                precinct_results[pkey] = {'Frey': 0, 'Fateh': 0, 'Exhausted': 0, 'Total': 0}
            
            if assigned:
                precinct_results[pkey][assigned] += count
            else:
                precinct_results[pkey]['Exhausted'] += count
            precinct_results[pkey]['Total'] += count
    
    return precinct_results


def color_for_precinct(frey_votes, fateh_votes, total_votes):
    """Generate KML color code based on vote share.
    Blue for Frey (higher = darker blue)
    Red for Fateh (higher = darker red)
    Format: aabbggrr (alpha, blue, green, red in hex)
    """
    if total_votes == 0:
        return 'ff888888'  # Gray for no data
    
    frey_pct = frey_votes / total_votes
    fateh_pct = fateh_votes / total_votes
    
    if frey_pct > fateh_pct:
        # Frey won - use blue
        # Intensity based on margin: 50-100% -> lighter to darker blue
        intensity = min(1.0, (frey_pct - 0.5) * 2)  # 0 to 1 scale
        # Blue in KML is aabbggrr, so blue is high bb value
        alpha = 'cc'  # Semi-transparent
        blue = hex(int(100 + 155 * intensity))[2:].zfill(2)
        green = '40'
        red = '40'
        return f'{alpha}{blue}{green}{red}'
    else:
        # Fateh won - use red
        intensity = min(1.0, (fateh_pct - 0.5) * 2)
        alpha = 'cc'
        blue = '40'
        green = '40'
        red = hex(int(100 + 155 * intensity))[2:].zfill(2)
        return f'{alpha}{blue}{green}{red}'


def create_kml(precinct_results):
    """Parse input KML and create new KML with mayoral results"""
    # Parse the input KML
    tree = ET.parse(KML_IN)
    root = tree.getroot()
    
    # Create new KML structure
    new_kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    doc = ET.SubElement(new_kml, 'Document')
    doc_name = ET.SubElement(doc, 'name')
    doc_name.text = 'Minneapolis Mayor 2025 - RCV Final Round Results'
    
    # Add styles for each precinct (we'll create dynamic styles)
    # But for simplicity, we'll add styles inline to each placemark
    
    # Find all Placemarks in original KML (no namespace in this file)
    matched_count = 0
    unmatched_count = 0
    
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
        
        # Check if this is a Minneapolis precinct
        if 'minneapolis' not in precinct_name.lower():
            continue
        
        # Normalize for lookup
        pkey = normalize_precinct_name(precinct_name)
        
        if pkey not in precinct_results:
            unmatched_count += 1
            continue
        
        matched_count += 1
        results = precinct_results[pkey]
        frey = results['Frey']
        fateh = results['Fateh']
        exhausted = results['Exhausted']
        total = results['Total']
        
        # Calculate percentages
        frey_pct = round(frey / total * 100, 1) if total > 0 else 0
        fateh_pct = round(fateh / total * 100, 1) if total > 0 else 0
        exhausted_pct = round(exhausted / total * 100, 1) if total > 0 else 0
        
        # Create new placemark
        new_pm = ET.SubElement(doc, 'Placemark')
        new_name = ET.SubElement(new_pm, 'name')
        new_name.text = precinct_name
        
        # Add description with results
        desc = ET.SubElement(new_pm, 'description')
        winner = 'Frey' if frey > fateh else 'Fateh'
        desc.text = f'''<![CDATA[
<h3>{precinct_name}</h3>
<b>RCV Final Round Results:</b><br/>
<b style="color:blue;">Jacob Frey:</b> {frey:,} ({frey_pct}%)<br/>
<b style="color:red;">Omar Fateh:</b> {fateh:,} ({fateh_pct}%)<br/>
<b>Exhausted:</b> {exhausted:,} ({exhausted_pct}%)<br/>
<b>Total Ballots:</b> {total:,}<br/>
<br/>
<b>Winner: {winner}</b>
]]>'''
        
        # Copy geometry from original placemark
        polygon = None
        for child in placemark:
            if 'Polygon' in child.tag:
                polygon = child
                break
        
        if polygon is not None:
            new_pm.append(polygon)
        
        # Add style with color
        color = color_for_precinct(frey, fateh, total)
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
        line_color.text = 'ff000000'  # Black outline
        line_width = ET.SubElement(line_style, 'width')
        line_width.text = '1'
    
    print(f'Matched {matched_count} Minneapolis precincts')
    print(f'Unmatched {unmatched_count} Minneapolis precincts')
    
    # Write KML
    tree_out = ET.ElementTree(new_kml)
    ET.indent(tree_out, space='  ')
    tree_out.write(KML_OUT, encoding='utf-8', xml_declaration=True)
    print(f'Wrote KML to {KML_OUT}')


if __name__ == '__main__':
    print('Parsing vote cast record...')
    precinct_results = parse_vcr()
    print(f'Loaded results for {len(precinct_results)} precincts')
    
    print('Creating KML...')
    create_kml(precinct_results)
    print('Done!')
