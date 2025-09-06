#!/usr/bin/env python3
"""
Polish Postal Codes PDF Parser
Converts PDF to CSV with proper handling of compound locality names
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

def parse_postal_record(line: str) -> Optional[Dict[str, str]]:
    """Parse a single line into postal record components"""
    line = clean_text(line)
    
    if not line:
        return None
    
    # Skip header/footer lines
    skip_patterns = [
        'Poczta Polska', 'Oficjalny Spis', 'Strona', 'Copyright', 
        'PNA Miejscowość', 'Część 1', 'miejscowości i ulic'
    ]
    
    if any(pattern in line for pattern in skip_patterns):
        return None
    
    parts = line.split()
    
    if len(parts) < 4:
        return None
    
    # First part must be postal code
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
    
    # Find voivodeship from the end
    voivodeship = ""
    voiv_idx = -1
    
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] in voivodeships:
            voivodeship = parts[i]
            voiv_idx = i
            break
        # Check compound voivodeships
        if i > 0:
            compound = parts[i-1] + '-' + parts[i]
            if compound in voivodeships:
                voivodeship = compound
                voiv_idx = i - 1
                break
    
    if not voivodeship or voiv_idx < 3:
        return None
    
    # Powiat is just before voivodeship
    powiat_idx = voiv_idx - 1
    if powiat_idx < 2:
        return None
        
    powiat = parts[powiat_idx]
    
    # Everything between postal code and powiat
    remaining_parts = parts[1:powiat_idx]
    
    if len(remaining_parts) < 1:
        return None
    
    # Common compound municipality names
    compound_gminas = [
        'Nowe Miasto', 'Stare Miasto', 'Biała Rawska', 'Góra Kalwaria',
        'Nowa Dęba', 'Stary Sącz', 'Nowy Dwór', 'Biała Podlaska',
        'Pruszcz Gdański', 'Nowy Tomyśl', 'Stary Dzierzgoń', 'Bielsk Podlaski'
    ]
    
    # Identify gmina (working backwards)
    gmina = ""
    gmina_word_count = 1
    
    # Check if last 2 words form a compound gmina
    if len(remaining_parts) >= 2:
        potential_compound = remaining_parts[-2] + ' ' + remaining_parts[-1]
        if potential_compound in compound_gminas:
            gmina = potential_compound
            gmina_word_count = 2
        else:
            gmina = remaining_parts[-1]
            gmina_word_count = 1
    else:
        gmina = remaining_parts[-1]
        gmina_word_count = 1
    
    # Everything before gmina is address/locality info
    address_parts = remaining_parts[:-gmina_word_count]
    
    if len(address_parts) < 1:
        return None
    
    # Strategy: Keep locality names together, only separate clear streets and numbers
    locality_parts = []
    street = ""
    numbers = ""
    
    # Look for explicit street indicators
    street_found = False
    number_start_idx = -1
    
    # Check for clear house number patterns (digits, ranges, parentheses)
    for i, part in enumerate(address_parts):
        if re.search(r'^\d+[-,]|\d+$|\(\w+\)|^DK$', part) or part in [',', '-', 'n', 'p']:
            number_start_idx = i
            break
    
    # If we found numbers, split there
    if number_start_idx >= 0:
        locality_parts = address_parts[:number_start_idx]
        number_parts = address_parts[number_start_idx:]
        numbers = ' '.join(number_parts)
    else:
        # No clear numbers found - check for street indicators
        street_indicators = ['ul.', 'Ulica', 'Al.', 'Aleja', 'Pl.', 'Plac', 'os.', 'Osiedle']
        
        for i, part in enumerate(address_parts):
            if part in street_indicators or part.lower().startswith('ul.') or part.lower().startswith('al.'):
                locality_parts = address_parts[:i]
                street_parts = address_parts[i:]
                street = ' '.join(street_parts)
                street_found = True
                break
        
        # If no street indicators found, treat everything as locality
        if not street_found:
            locality_parts = address_parts
    
    locality = ' '.join(locality_parts)
    
    # Handle empty locality (shouldn't happen but just in case)
    if not locality and address_parts:
        locality = address_parts[0]
        if len(address_parts) > 1:
            remaining = ' '.join(address_parts[1:])
            if re.search(r'\d', remaining):
                numbers = remaining
            else:
                street = remaining
    
    return {
        'PNA': postal_code,
        'Miejscowość': locality,
        'Ulica': street,
        'Numery': numbers,
        'Gmina': gmina,
        'Powiat': powiat,
        'Województwo': voivodeship
    }

def parse_pdf_to_csv(pdf_path: str, output_csv: str = "postal_codes.csv", start_page: int = 1, end_page: int = None):
    """Parse PDF and save directly to CSV"""
    
    print(f"Processing PDF: {pdf_path}")
    
    results = []
    unparsed_count = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        if end_page is None:
            end_page = total_pages
        
        print(f"Processing pages {start_page} to {end_page} of {total_pages}")
        
        for page_num in range(start_page - 1, min(end_page, total_pages)):
            page = pdf.pages[page_num]
            current_page = page_num + 1
            
            if current_page % 10 == 0:
                print(f"Page {current_page}... ({len(results)} records so far)")
            
            try:
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                
                for line in lines:
                    parsed = parse_postal_record(line)
                    
                    if parsed:
                        results.append(parsed)
                    else:
                        # Count unparsed lines that look like postal records
                        line_clean = clean_text(line)
                        if line_clean and len(line_clean.split()) >= 4:
                            first_part = line_clean.split()[0]
                            if is_postal_code(first_part):
                                unparsed_count += 1
                
            except Exception as e:
                print(f"Error on page {current_page}: {e}")
                continue
    
    print(f"\nCompleted processing!")
    print(f"Successfully parsed: {len(results)} records")
    print(f"Could not parse: {unparsed_count} lines")
    
    # Save to CSV
    if results:
        df = pd.DataFrame(results)
        
        # Ensure column order
        columns = ['PNA', 'Miejscowość', 'Ulica', 'Numery', 'Gmina', 'Powiat', 'Województwo']
        df = df[columns]
        
        df.to_csv(output_csv, index=False, encoding='utf-8')
        
        print(f"\n✓ Saved {len(results)} records to {output_csv}")
        
        # Show statistics
        print(f"\nStatistics:")
        print(f"  Unique postal codes: {df['PNA'].nunique()}")
        print(f"  Unique voivodeships: {df['Województwo'].nunique()}")
        
        print(f"\nRecords per voivodeship:")
        for voiv, count in df['Województwo'].value_counts().items():
            print(f"  {voiv}: {count}")
        
        print(f"\nFirst 10 records:")
        for i, row in df.head(10).iterrows():
            print(f"  {row['PNA']} | {row['Miejscowość']:20} | {row['Ulica']:15} | {row['Numery']:15} | {row['Gmina']:15} | {row['Powiat']:12} | {row['Województwo']}")
        
        return df
    else:
        print("No records parsed!")
        return None

def test_parser():
    """Test the parser with sample lines"""
    test_lines = [
        "20-388 Abramowice Kościelne Głusk lubelski lubelskie",
        "20-388 Abramowice Prywatne Głusk lubelski lubelskie",
        "87-815 Adaminowo (Łączki) Włocławek włocławski kujawsko-pomorskie",
        "05-192 Aleksandria 4-6, 7-9(n), 12-15 Nowe Miasto płoński mazowieckie",
        "09-120 Aleksandria 8-10(p), 11, 31 Nowe Miasto płoński mazowieckie"
    ]
    
    print("Testing parser:")
    print()
    
    for i, line in enumerate(test_lines):
        print(f"{i+1}. {line}")
        result = parse_postal_record(line)
        if result:
            print(f"   → {result['PNA']} | {result['Miejscowość']:20} | {result['Ulica']:15} | {result['Numery']:20} | {result['Gmina']:15} | {result['Powiat']:12} | {result['Województwo']}")
        else:
            print("   → Failed to parse")
        print()

if __name__ == "__main__":
    # Test first
    test_parser()
    
    # Parse the sample PDF
    print("="*80)
    pdf_file = "pages_3_to_22.pdf"
    df = parse_pdf_to_csv(pdf_file, "postal_codes_sample.csv", start_page=1, end_page=5)
    
    # Uncomment below to process the full PDF
    # print("="*80)
    # print("To process the full PDF, uncomment the line below and run again:")
    # print("parse_pdf_to_csv('oficjalny_spis_pna_2025.pdf', 'complete_postal_codes.csv')")