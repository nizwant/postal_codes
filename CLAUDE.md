# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository processes official Polish postal codes from PDF documents published by Poczta Polska into clean CSV format. The project extracts tabular data from multi-page PDFs, handles text merging across rows, and validates Polish administrative divisions.

## Commands

### Environment Setup
```bash
# Install dependencies (Poetry preferred but pip works)
poetry install
# OR
pip install camelot-py[base] pandas matplotlib ipykernel
```

### Data Processing
```bash
# Main processing pipeline - extract and validate postal codes
python3 pdf_extraction_process/process_postal_codes.py

# With verbose output and custom options
python3 pdf_extraction_process/process_postal_codes.py \
  --pdf-path data/oficjalny_spis_pna_2025.pdf \
  --output my_postal_codes.csv \
  --verbose

# Skip validation flag columns in output
python3 pdf_extraction_process/process_postal_codes.py --skip-validation-flags

# Interactive PDF table exploration for development
python3 pdf_extraction_process/helper_pdf_table_explorer.py
```

### Jupyter Development
```bash
# Launch notebook for iterative development
jupyter notebook pdf_extraction_process/process_pdf_postal_codes.ipynb
```

## Architecture

### Processing Pipeline
The main processing consists of 4 sequential steps:
1. **PDF Table Extraction** (`extract_tables_from_pdf()`) - Uses Camelot with optimized parameters for Polish postal PDF format
2. **Row Merging** (`process_merged_rows()`) - Handles data split across multiple table rows iteratively
3. **Data Validation** (`validate_data()`) - Comprehensive validation of Polish administrative divisions
4. **Output Generation** - Saves both raw extracted and final processed CSV files

### Key Components

**`pdf_extraction_process/process_postal_codes.py`**
- Main production script with CLI interface
- Contains the complete processing pipeline
- Handles PDF extraction with specific table areas: `["28,813,567,27"]` and columns: `["60,144,267,332,422,497"]`
- Uses `flavor="stream"` and `row_tol=9` optimized for the Polish postal PDF format

**`pdf_extraction_process/helper_pdf_table_explorer.py`** 
- Interactive development tool for visualizing PDF table extraction
- Uses matplotlib for grid visualization of detected tables
- Useful for adjusting extraction parameters when PDF format changes

**Data Validation System**
- Validates all 16 Polish województwa (voivodeships) 
- Flags numbers in place names (Miejscowość) as potential OCR errors
- Allows Roman numerals and Polish ordinals in gmina/powiat names
- Detects suspiciously long fields and missing essential data
- Identifies postal code duplicates across different administrative regions

### Data Structure
```
data/
├── oficjalny_spis_pna_2025.pdf          # Source PDF from Poczta Polska
├── postal_codes_raw.csv                 # Raw extracted data 
└── postal_codes_with_street_numbers.csv # Intermediate processing file

postal_codes_poland.csv                  # Final output at project root
```

### PDF Processing Specifics
The Polish postal codes PDF has a complex multi-page table structure where:
- Data often spans multiple rows (continuation rows lack postal codes)
- Text can be split mid-word with hyphens across rows  
- Pages 3-1672 contain the actual postal code data
- Fixed table boundaries and column positions are used for consistent extraction

### Validation Logic
The validation system is designed specifically for Polish administrative divisions:
- **Województwa**: Must match one of 16 official Polish voivodeships
- **Place Names**: Numbers indicate potential OCR errors (except for legitimate cases)
- **Administrative Consistency**: Flags postal codes assigned to multiple województwa as suspicious
- **Data Completeness**: Essential fields (PNA, Miejscowość, Gmina, Powiat, Województwo) must be present

## Development Notes

- The project uses Poetry for dependency management but falls back to pip
- Python 3.13+ required due to type hint syntax (`tuple[pd.DataFrame, list]`)
- Camelot-py handles PDF table extraction but requires specific parameter tuning for this PDF format
- The iterative row merging process continues until no more changes occur (convergence)
- Validation flags can be optionally added as columns to help identify data quality issues