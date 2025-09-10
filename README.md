# Polish Postal Codes Extractor

Extracts Polish postal code data from the official Poczta Polska PDF into clean CSV format. Processes ~1,670 pages to extract **117,680 postal code entries** with complete location data.

## 🎯 What It Does

Converts the official Polish postal codes PDF (normally costs 500 PLN for raw data) into structured CSV with:

- Postal codes (PNA) in XX-XXX format
- Locations, streets, address ranges
- Administrative divisions (gmina, powiat, województwo)
- Data validation for Polish administrative structure

## 🛠 Installation using Conda and Poetry

```bash
conda create -n postal-codes python=3.11
conda activate postal-codes
pip install poetry
poetry install
```

## 🚀 Usage

```bash
# Basic processing
python3 pdf_extraction_process/process_postal_codes.py

# With verbose output
python3 pdf_extraction_process/process_postal_codes.py --verbose

# Custom options
python3 pdf_extraction_process/process_postal_codes.py \
  --pdf-path data/oficjalny_spis_pna_2025.pdf \
  --output my_postal_codes.csv \
  --skip-validation-flags
```

### Key Options

- `--pdf-path` - Input PDF path (default: `data/oficjalny_spis_pna_2025.pdf`)
- `--output` - Output CSV filename (default: `postal_codes_poland.csv`)
- `--pages` - Page range to process (default: `3-1672`)
- `--verbose` - Show detailed progress
- `--skip-validation-flags` - Exclude validation columns from output

## 📁 Project Structure

```txt
postal_codes/
├── postal_codes_poland.csv              # Final output (117K records)
├── data/
│   ├── oficjalny_spis_pna_2025.pdf     # Source PDF
│   └── postal_codes_raw.csv            # Raw extracted data
└── pdf_extraction_process/
    ├── process_postal_codes.py         # Main script
    └── scripts/                        # Development utilities
```

## 🔍 Processing Pipeline

1. **PDF Table Extraction** - Camelot with optimized parameters
2. **Row Merging** - Handles data split across multiple rows
3. **Data Validation** - Polish administrative divisions validation
4. **Output Generation** - Clean CSV with quality checks

## 📊 Technical Features

- Processes complex multi-page PDF tables
- Handles text continuation across rows
- Validates against 16 Polish voivodeships
- Detects OCR errors and data inconsistencies
- Produces 117,680 validated postal code entries

## 🧪 Development

```bash
# Interactive PDF exploration
python3 pdf_extraction_process/scripts/helper_pdf_table_explorer.py

# Jupyter notebook
jupyter notebook pdf_extraction_process/process_pdf_postal_codes.ipynb
```

## 📋 Requirements

- Python 3.9+ (3.11+ recommended)
- camelot-py[base], pandas, matplotlib, jupyter
