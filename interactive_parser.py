#!/usr/bin/env python3
"""
Interactive Polish Postal Codes Parser
Allows visual identification of table columns and boundaries
"""

import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Optional, Tuple
import json

def save_column_config(config: dict, filename: str = "column_config.json"):
    """Save column configuration to file"""
    with open(filename, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Configuration saved to {filename}")

def load_column_config(filename: str = "column_config.json") -> dict:
    """Load column configuration from file"""
    try:
        with open(filename, 'r') as f:
            config = json.load(f)
        print(f"Configuration loaded from {filename}")
        return config
    except FileNotFoundError:
        print(f"No configuration file found at {filename}")
        return None

def analyze_page_structure(pdf_path: str, page_num: int = 1):
    """Analyze a single page structure and show character positions"""
    
    with pdfplumber.open(pdf_path) as pdf:
        if page_num > len(pdf.pages):
            print(f"Page {page_num} not found. PDF has {len(pdf.pages)} pages.")
            return
        
        page = pdf.pages[page_num - 1]
        
        print(f"\n=== PAGE {page_num} ANALYSIS ===")
        print(f"Page dimensions: {page.width} x {page.height}")
        
        # Get all characters with their positions
        chars = page.chars
        
        if not chars:
            print("No characters found on this page")
            return
        
        # Group characters by approximate y-position (rows)
        rows = {}
        for char in chars:
            y = round(char['y0'], 1)
            if y not in rows:
                rows[y] = []
            rows[y].append(char)
        
        # Sort rows by y-position (top to bottom)
        sorted_rows = sorted(rows.items(), key=lambda x: -x[0])
        
        print(f"\nFound {len(sorted_rows)} text rows")
        
        # Show first 20 rows with their content and positions
        print(f"\nFirst 20 rows (Y-position : Content):")
        print("-" * 100)
        
        data_rows = []
        
        for i, (y_pos, row_chars) in enumerate(sorted_rows[:20]):
            # Sort characters in this row by x-position
            row_chars.sort(key=lambda x: x['x0'])
            
            # Reconstruct text from characters
            text = ''.join([char['text'] for char in row_chars])
            text_clean = re.sub(r'\s+', ' ', text.strip())
            
            # Get x-positions of characters
            x_positions = [char['x0'] for char in row_chars]
            min_x = min(x_positions) if x_positions else 0
            max_x = max(x_positions) if x_positions else 0
            
            print(f"{i+1:2d}. Y={y_pos:6.1f} X={min_x:4.0f}-{max_x:4.0f} | {text_clean[:80]}")
            
            # Check if this looks like a data row (starts with postal code)
            parts = text_clean.split()
            if parts and re.match(r'^\d{2}-\d{3}$', parts[0]):
                data_rows.append({
                    'row_num': i + 1,
                    'y_pos': y_pos,
                    'x_start': min_x,
                    'x_end': max_x,
                    'content': text_clean,
                    'chars': row_chars
                })
        
        return data_rows

def analyze_column_positions(data_rows: List[dict]):
    """Analyze column positions from data rows"""
    
    if not data_rows:
        print("No data rows to analyze")
        return None
    
    print(f"\n=== COLUMN ANALYSIS ===")
    print(f"Analyzing {len(data_rows)} data rows...")
    
    # Analyze character positions across all data rows
    all_x_positions = []
    
    for row in data_rows:
        chars = row['chars']
        chars.sort(key=lambda x: x['x0'])
        
        # Group characters by approximate x-position (columns)
        x_groups = {}
        for char in chars:
            x = round(char['x0'], 0)  # Round to nearest pixel
            if x not in x_groups:
                x_groups[x] = []
            x_groups[x].append(char['text'])
        
        all_x_positions.extend(x_groups.keys())
    
    # Find common x-positions (column boundaries)
    from collections import Counter
    x_counter = Counter(all_x_positions)
    
    # Get most common x-positions (likely column starts)
    common_x = [x for x, count in x_counter.most_common() if count >= len(data_rows) * 0.3]
    common_x.sort()
    
    print(f"\nMost common X-positions (potential column boundaries):")
    for x in common_x[:10]:  # Show top 10
        count = x_counter[x]
        print(f"  X={x:4.0f} (appears in {count}/{len(data_rows)} rows)")
    
    return common_x

def interactive_column_setup(pdf_path: str, sample_page: int = 3):
    """Interactive setup of column boundaries"""
    
    print("=== INTERACTIVE COLUMN SETUP ===")
    
    # First, analyze the page structure
    data_rows = analyze_page_structure(pdf_path, sample_page)
    
    if not data_rows:
        print("No data rows found for analysis")
        return None
    
    # Show some sample rows
    print(f"\nSample data rows:")
    for i, row in enumerate(data_rows[:5]):
        print(f"{i+1}. {row['content']}")
    
    print(f"\nNow let's define the column boundaries...")
    
    # Analyze column positions
    common_x = analyze_column_positions(data_rows)
    
    if not common_x:
        print("Could not automatically detect column positions")
        return None
    
    # Interactive column definition
    print(f"\nColumn Definition:")
    print(f"Based on analysis, suggested column X-positions: {common_x[:7]}")
    
    columns = ['PNA', 'Miejscowość', 'Ulica', 'Numery', 'Gmina', 'Powiat', 'Województwo']
    
    column_config = {
        'page_width': 600,  # Default, will be updated
        'columns': {}
    }
    
    # Get user input for column boundaries
    print(f"\nDefine column boundaries (X-positions):")
    print(f"Suggested positions: {common_x[:7]}")
    
    # Auto-suggest boundaries based on common positions
    if len(common_x) >= 6:
        suggested_boundaries = common_x[:6] + [999]  # Add end boundary
    else:
        # Fallback manual input
        print("Not enough automatic boundaries detected. Please define manually.")
        suggested_boundaries = []
        for i, col in enumerate(columns):
            if i == 0:
                start_x = 0
            else:
                start_x = int(input(f"Enter starting X-position for '{col}' column: ") or "0")
            suggested_boundaries.append(start_x)
        suggested_boundaries.append(999)  # End boundary
    
    # Define column ranges
    for i, col in enumerate(columns):
        start_x = suggested_boundaries[i] if i < len(suggested_boundaries) else 0
        end_x = suggested_boundaries[i+1] if i+1 < len(suggested_boundaries) else 999
        
        column_config['columns'][col] = {
            'start_x': start_x,
            'end_x': end_x,
            'index': i
        }
        
        print(f"{col:12}: X {start_x:3.0f} - {end_x:3.0f}")
    
    # Test the configuration
    print(f"\n=== TESTING COLUMN CONFIGURATION ===")
    
    test_results = []
    for row in data_rows[:3]:
        parsed = parse_row_with_columns(row, column_config)
        if parsed:
            test_results.append(parsed)
            print(f"✓ {parsed['PNA']} | {parsed['Miejscowość'][:15]:15} | {parsed['Ulica'][:10]:10} | {parsed['Numery'][:12]:12} | {parsed['Gmina'][:12]:12}")
    
    if test_results:
        # Ask user if configuration looks good
        response = input(f"\nDoes this look correct? (y/n): ").strip().lower()
        if response == 'y':
            save_column_config(column_config)
            return column_config
        else:
            print("Column configuration rejected. Please try manual setup.")
            return None
    
    return column_config

def parse_row_with_columns(row_data: dict, column_config: dict) -> Optional[Dict[str, str]]:
    """Parse a row using defined column positions"""
    
    chars = row_data['chars']
    if not chars:
        return None
    
    # Sort characters by x-position
    chars.sort(key=lambda x: x['x0'])
    
    result = {}
    
    # Extract text for each column
    for col_name, col_info in column_config['columns'].items():
        start_x = col_info['start_x']
        end_x = col_info['end_x']
        
        # Get characters within this column's x-range
        col_chars = [c for c in chars if start_x <= c['x0'] < end_x]
        col_text = ''.join([c['text'] for c in col_chars]).strip()
        
        # Clean up text
        col_text = re.sub(r'\s+', ' ', col_text)
        
        result[col_name] = col_text
    
    return result

def parse_pdf_with_columns(pdf_path: str, column_config: dict, output_csv: str = "postal_codes_columns.csv", 
                          start_page: int = 1, end_page: int = None):
    """Parse PDF using column configuration"""
    
    print(f"Processing PDF with column-based parsing...")
    
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
                chars = page.chars
                
                if not chars:
                    continue
                
                # Group characters by rows
                rows = {}
                for char in chars:
                    y = round(char['y0'], 1)
                    if y not in rows:
                        rows[y] = []
                    rows[y].append(char)
                
                # Process each row
                for y_pos, row_chars in rows.items():
                    # Check if this looks like a data row
                    text = ''.join([c['text'] for c in row_chars]).strip()
                    if not text or len(text.split()) < 3:
                        continue
                    
                    # Skip headers
                    if any(keyword in text for keyword in ['Poczta Polska', 'PNA Miejscowość', 'Strona']):
                        continue
                    
                    # Check if starts with postal code
                    first_word = text.split()[0]
                    if re.match(r'^\d{2}-\d{3}$', first_word):
                        row_data = {
                            'y_pos': y_pos,
                            'chars': row_chars,
                            'content': text
                        }
                        
                        parsed = parse_row_with_columns(row_data, column_config)
                        
                        if parsed and parsed.get('PNA'):
                            results.append(parsed)
                        else:
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
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        df = df[columns]
        
        df.to_csv(output_csv, index=False, encoding='utf-8')
        
        print(f"\n✓ Saved {len(results)} records to {output_csv}")
        
        # Show statistics
        print(f"\nFirst 10 records:")
        for i, row in df.head(10).iterrows():
            print(f"  {row['PNA']} | {row['Miejscowość'][:20]:20} | {row['Ulica'][:15]:15} | {row['Numery'][:15]:15} | {row['Gmina'][:15]:15}")
        
        return df
    else:
        print("No records parsed!")
        return None

def main():
    pdf_file = "pages_3_to_22.pdf"
    
    print("=== INTERACTIVE PDF PARSER ===")
    print("This tool helps you define column boundaries for accurate parsing")
    
    # Check if we have existing configuration
    existing_config = load_column_config()
    
    if existing_config:
        print(f"\nFound existing configuration:")
        for col, info in existing_config['columns'].items():
            print(f"  {col}: X {info['start_x']} - {info['end_x']}")
        
        use_existing = input(f"\nUse existing configuration? (y/n): ").strip().lower()
        if use_existing == 'y':
            config = existing_config
        else:
            config = interactive_column_setup(pdf_file)
    else:
        config = interactive_column_setup(pdf_file)
    
    if not config:
        print("No valid configuration. Exiting.")
        return
    
    # Parse with the configuration
    print(f"\n" + "="*50)
    df = parse_pdf_with_columns(pdf_file, config, "postal_codes_interactive.csv", 1, 5)
    
    if df is not None:
        print(f"\nSuccess! Check 'postal_codes_interactive.csv' for results")

if __name__ == "__main__":
    main()