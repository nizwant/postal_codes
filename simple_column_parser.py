#!/usr/bin/env python3
"""
Simple Column-based Parser for Polish Postal Codes
Uses pdfplumber's table extraction capabilities
"""

import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Optional

def clean_text(text: str) -> str:
    """Clean extracted text"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.strip())

def is_postal_code(text: str) -> bool:
    """Check if text matches Polish postal code format (XX-XXX)"""
    if not text:
        return False
    return bool(re.match(r'^\d{2}-\d{3}$', text.strip()))

def show_page_tables(pdf_path: str, page_num: int = 3):
    """Show table structure on a page"""
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]
        
        print(f"\n=== PAGE {page_num} TABLE ANALYSIS ===")
        
        # Try to find tables automatically
        tables = page.find_tables()
        print(f"Found {len(tables)} automatic tables")
        
        if tables:
            for i, table in enumerate(tables):
                print(f"\nTable {i+1}: {len(table.rows)} rows, {len(table.rows[0]) if table.rows else 0} columns")
                if table.rows:
                    print(f"Sample rows:")
                    for j, row in enumerate(table.rows[:3]):
                        print(f"  Row {j+1}: {[cell[:20] if cell else '' for cell in row]}")
        
        # Try manual table detection with different settings
        print(f"\n=== TRYING DIFFERENT TABLE DETECTION SETTINGS ===")
        
        # Method 1: Find tables with explicit settings
        table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "explicit_vertical_lines": [],
            "explicit_horizontal_lines": [],
            "snap_tolerance": 3,
        }
        
        tables_v2 = page.find_tables(table_settings)
        print(f"Method 1 (lines): Found {len(tables_v2)} tables")
        
        # Method 2: Use text positioning
        table_settings_v2 = {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
        }
        
        tables_v3 = page.find_tables(table_settings_v2)
        print(f"Method 2 (text): Found {len(tables_v3)} tables")
        
        # Show raw text for analysis
        print(f"\n=== RAW PAGE TEXT (first 1000 chars) ===")
        text = page.extract_text()
        print(text[:1000])
        
        return tables, tables_v2, tables_v3

def extract_with_bbox(pdf_path: str, page_num: int = 3):
    """Extract text using bounding boxes"""
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]
        
        print(f"\n=== BOUNDING BOX EXTRACTION ===")
        
        # Define approximate column boundaries based on typical PDF layout
        page_width = page.width
        page_height = page.height
        
        print(f"Page dimensions: {page_width} x {page_height}")
        
        # Typical column positions for Polish postal codes (estimated)
        columns = {
            'PNA': (30, 80),           # Postal code
            'Miejscowość': (80, 180),  # Locality  
            'Ulica': (180, 280),       # Street
            'Numery': (280, 350),      # Numbers
            'Gmina': (350, 420),       # Municipality
            'Powiat': (420, 480),      # County
            'Województwo': (480, 560)  # Voivodeship
        }
        
        # Extract text from different regions
        print(f"\nExtracting from different column regions:")
        
        # Focus on main content area (skip header/footer)
        content_bbox = (0, 100, page_width, page_height - 100)
        content = page.within_bbox(content_bbox)
        
        text_lines = content.extract_text().split('\\n')
        
        print(f"Found {len(text_lines)} lines in content area")
        
        # Show first 10 lines
        data_lines = []
        for i, line in enumerate(text_lines[:20]):
            line_clean = clean_text(line)
            if line_clean and len(line_clean) > 10:
                print(f"{i+1:2d}: {line_clean[:80]}")
                
                # Check if starts with postal code
                parts = line_clean.split()
                if parts and is_postal_code(parts[0]):
                    data_lines.append(line_clean)
        
        print(f"\\nFound {len(data_lines)} potential data lines")
        return data_lines

def manual_column_definition():
    """Let user manually define column positions"""
    
    print(f"\\n=== MANUAL COLUMN DEFINITION ===")
    print(f"We'll define column boundaries by looking at the data patterns")
    
    # Show sample line for reference
    sample_line = "16-503 Aleksandrowo Krasnopol sejneński podlaskie"
    print(f"\\nSample line: '{sample_line}'")
    print(f"Characters:   {''.join([f'{i%10}' for i in range(len(sample_line))])}")
    print(f"Positions:    {''.join([f'{(i//10)%10}' if i%10==0 else ' ' for i in range(len(sample_line))])}")
    
    # Standard Polish postal data pattern
    columns_info = {
        'PNA': "Postal code (XX-XXX format)",
        'Miejscowość': "Locality name (can be compound)", 
        'Ulica': "Street name (often empty)",
        'Numery': "House numbers/ranges (often empty)",
        'Gmina': "Municipality", 
        'Powiat': "County",
        'Województwo': "Voivodeship"
    }
    
    print(f"\\nColumns to extract:")
    for col, desc in columns_info.items():
        print(f"  {col:12}: {desc}")
    
    return True

def parse_line_by_pattern(line: str) -> Optional[Dict[str, str]]:
    """Parse line using improved pattern recognition"""
    
    line = clean_text(line)
    if not line:
        return None
    
    # Skip headers
    if any(keyword in line for keyword in ['Poczta Polska', 'PNA Miejscowość', 'Strona', 'Copyright']):
        return None
    
    parts = line.split()
    if len(parts) < 4:
        return None
    
    # Must start with postal code
    if not is_postal_code(parts[0]):
        return None
    
    postal_code = parts[0]
    
    # Known voivodeships
    voivodeships = [
        'mazowieckie', 'śląskie', 'wielkopolskie', 'małopolskie', 'lubelskie',
        'podkarpackie', 'dolnośląskie', 'kujawsko-pomorskie', 'pomorskie',
        'łódzkie', 'zachodniopomorskie', 'lubuskie', 'podlaskie', 'świętokrzyskie',
        'opolskie', 'warmińsko-mazurskie'
    ]
    
    # Find voivodeship
    voivodeship = ""
    voiv_idx = -1
    
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] in voivodeships:
            voivodeship = parts[i]
            voiv_idx = i
            break
        if i > 0:
            compound = parts[i-1] + '-' + parts[i]
            if compound in voivodeships:
                voivodeship = compound
                voiv_idx = i - 1
                break
    
    if not voivodeship:
        return None
    
    # Powiat is before voivodeship
    powiat_idx = voiv_idx - 1 if voiv_idx > 0 else -1
    powiat = parts[powiat_idx] if powiat_idx >= 1 else ""
    
    # Gmina is before powiat
    gmina_idx = powiat_idx - 1 if powiat_idx > 0 else -1
    
    # Handle compound gmina names
    compound_gminas = ['Nowe Miasto', 'Stare Miasto', 'Biała Rawska', 'Góra Kalwaria']
    gmina = ""
    
    if gmina_idx >= 2:  # Need at least 2 parts for compound
        potential_compound = parts[gmina_idx-1] + ' ' + parts[gmina_idx]
        if potential_compound in compound_gminas:
            gmina = potential_compound
            gmina_idx -= 1  # Adjust for compound name
        else:
            gmina = parts[gmina_idx]
    elif gmina_idx >= 1:
        gmina = parts[gmina_idx]
    
    # Everything between postal code and gmina is locality/street/numbers
    if gmina_idx > 1:
        middle_parts = parts[1:gmina_idx]
    else:
        middle_parts = parts[1:-3]  # Fallback: assume last 3 are gmina/powiat/voiv
    
    if not middle_parts:
        return None
    
    # First part is locality
    locality = middle_parts[0]
    
    # Handle compound localities
    locality_parts = [locality]
    street_parts = []
    number_parts = []
    
    if len(middle_parts) > 1:
        remaining = middle_parts[1:]
        
        # Look for obvious street indicators
        street_indicators = ['ul.', 'Al.', 'Pl.', 'os.']
        street_found = False
        
        for i, part in enumerate(remaining):
            if part in street_indicators:
                # Everything from here is street
                street_parts = remaining[i:]
                street_found = True
                break
            elif re.search(r'^\\d+[,-]|\\d+$|\\(', part):
                # This looks like house numbers
                number_parts = remaining[i:]
                break
            else:
                # Could be part of locality name
                locality_parts.append(part)
    
    # Final assembly
    locality_final = ' '.join(locality_parts)
    street_final = ' '.join(street_parts) if street_parts else ""
    numbers_final = ' '.join(number_parts) if number_parts else ""
    
    return {
        'PNA': postal_code,
        'Miejscowość': locality_final,
        'Ulica': street_final,
        'Numery': numbers_final,  
        'Gmina': gmina,
        'Powiat': powiat,
        'Województwo': voivodeship
    }

def test_and_parse(pdf_path: str):
    """Test different extraction methods and parse"""
    
    print("=== TESTING DIFFERENT EXTRACTION METHODS ===")
    
    # Method 1: Show table structure
    tables_info = show_page_tables(pdf_path, 3)
    
    # Method 2: Bounding box extraction  
    data_lines = extract_with_bbox(pdf_path, 3)
    
    # Method 3: Manual column definition
    manual_column_definition()
    
    # Parse the extracted lines
    print(f"\\n=== PARSING EXTRACTED LINES ===")
    
    results = []
    for line in data_lines:
        parsed = parse_line_by_pattern(line)
        if parsed:
            results.append(parsed)
    
    print(f"\\nParsed {len(results)} records from data lines:")
    
    for i, record in enumerate(results[:10]):
        print(f"{i+1:2d}. {record['PNA']} | {record['Miejscowość'][:20]:20} | {record['Ulica'][:15]:15} | {record['Numery'][:15]:15} | {record['Gmina'][:15]:15}")
    
    return results

def main():
    pdf_file = "pages_3_to_22.pdf"
    
    print("=== SIMPLE COLUMN-BASED PARSER ===")
    
    results = test_and_parse(pdf_file)
    
    if results:
        # Save results
        df = pd.DataFrame(results)
        columns = ['PNA', 'Miejscowość', 'Ulica', 'Numery', 'Gmina', 'Powiat', 'Województwo']
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        df = df[columns]
        
        df.to_csv("postal_codes_column_test.csv", index=False, encoding='utf-8')
        print(f"\\nSaved {len(results)} records to postal_codes_column_test.csv")

if __name__ == "__main__":
    main()