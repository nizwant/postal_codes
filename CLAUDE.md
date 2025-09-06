# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Polish postal codes extraction project that converts PDF data to CSV format using Python. The workflow follows an iterative development approach:
1. Create and experiment with Jupyter notebooks for solution validation
2. Iteratively improve the solution based on results
3. Once satisfied, create automated scripts for production use

## Project Structure

- `extract.py` - PDF page extraction utility (extracts pages 3-22 from postal code PDFs)
- `parse_pdf.ipynb` - Jupyter notebook for iterative PDF parsing development
- `README.md` - Project description and goals

## Development Workflow

**Primary development tool**: Jupyter notebooks for interactive development and validation
**Target format**: Convert PDF postal code data to CSV with high fidelity replication
**PDF source**: Polish postal codes from `oficjalny_spis_pns_2025.pdf` (deleted file)

## Key Dependencies

- `PyPDF2` - PDF manipulation and page extraction
- Standard Python libraries: `sys`, `os`

## Common Tasks

**Extract PDF pages for testing**:
```bash
python extract.py
```
This extracts pages 3-22 from the source PDF where postal code data begins.

**Interactive development**:
Use `parse_pdf.ipynb` for iterative solution development and validation.

## Architecture Notes

The current codebase follows a two-phase approach:
1. **Extraction phase** (`extract.py`): Isolates relevant pages from large PDF documents
2. **Parsing phase** (`parse_pdf.ipynb`): Iterative development of PDF-to-CSV conversion logic

The extraction utility is designed to work with the specific structure of Polish postal code PDFs, starting from page 3 where actual data begins.