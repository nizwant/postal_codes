#!/usr/bin/env python3
"""
Column-Aware Polish Postal Codes Parser
Handles the specific column layout where data is split across different X positions
"""

import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Optional, Tuple


def clean_text(text: str) -> str:
    """Clean extracted text"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def is_postal_code(text: str) -> bool:
    """Check if text matches Polish postal code format (XX-XXX)"""
    if not text:
        return False
    return bool(re.match(r"^\d{2}-\d{3}$", text.strip()))


def extract_row_data(
    page, y_position: float, tolerance: float = 2.0
) -> Optional[Dict[str, str]]:
    """Extract text from a specific Y position across all columns"""

    # Get all characters near this Y position
    row_chars = []
    for char in page.chars:
        if abs(char["y0"] - y_position) <= tolerance:
            row_chars.append(char)

    if not row_chars:
        return None

    # Sort by X position
    row_chars.sort(key=lambda x: x["x0"])

    # Group characters by X position ranges (columns)
    # Based on the analysis, we have two main sections:
    # Left section: X ~28-200 (PNA + Miejscowość)
    # Right section: X ~300+ (Gmina + Powiat + Województwo)

    left_chars = [c for c in row_chars if c["x0"] < 250]
    right_chars = [c for c in row_chars if c["x0"] >= 300]

    # Add spaces between words by detecting gaps in X positions
    def add_word_spacing(chars):
        if not chars:
            return ""

        text_parts = []
        current_word = ""
        last_x = chars[0]["x0"]

        for char in chars:
            # If there's a significant gap (>3 pixels), start a new word
            if char["x0"] - last_x > 3:
                if current_word:
                    text_parts.append(current_word)
                    current_word = ""

            current_word += char["text"]
            last_x = char["x0"] + char.get("width", 5)  # Estimate character width

        if current_word:
            text_parts.append(current_word)

        return " ".join(text_parts).strip()

    left_text = add_word_spacing(left_chars)
    right_text = add_word_spacing(right_chars)

    return {"left": left_text, "right": right_text, "y_pos": y_position}


def parse_combined_data(left_text: str, right_text: str) -> Optional[Dict[str, str]]:
    """Parse the left and right text sections into structured data"""

    if not left_text or not right_text:
        return None

    # Parse left side (PNA + Miejscowość)
    left_parts = left_text.split()
    if len(left_parts) < 2:
        return None

    # First part should be postal code
    if not is_postal_code(left_parts[0]):
        return None

    postal_code = left_parts[0]
    locality_parts = left_parts[1:]

    # Handle special cases in locality names
    locality = " ".join(locality_parts)

    # Parse right side (Gmina + Powiat + Województwo)
    right_parts = right_text.split()
    if len(right_parts) < 3:
        return None

    # Known voivodeships
    voivodeships = [
        "mazowieckie",
        "śląskie",
        "wielkopolskie",
        "małopolskie",
        "lubelskie",
        "podkarpackie",
        "dolnośląskie",
        "kujawsko-pomorskie",
        "pomorskie",
        "łódzkie",
        "zachodniopomorskie",
        "lubuskie",
        "podlaskie",
        "świętokrzyskie",
        "opolskie",
        "warmińsko-mazurskie",
    ]

    # Find voivodeship from the end
    voivodeship = ""
    voiv_idx = -1

    for i in range(len(right_parts) - 1, -1, -1):
        if right_parts[i] in voivodeships:
            voivodeship = right_parts[i]
            voiv_idx = i
            break
        # Check compound voivodeships
        if i > 0:
            compound = right_parts[i - 1] + "-" + right_parts[i]
            if compound in voivodeships:
                voivodeship = compound
                voiv_idx = i - 1
                break

    if not voivodeship or voiv_idx < 2:
        return None

    # Powiat is just before voivodeship
    powiat_idx = voiv_idx - 1
    if powiat_idx < 1:
        return None

    powiat = right_parts[powiat_idx]

    # Everything before powiat is gmina
    gmina_parts = right_parts[:powiat_idx]
    gmina = " ".join(gmina_parts)

    return {
        "PNA": postal_code,
        "Miejscowość": locality,
        "Ulica": "",  # Not present in this format
        "Numery": "",  # Not present in this format
        "Gmina": gmina,
        "Powiat": powiat,
        "Województwo": voivodeship,
    }


def analyze_page_rows(pdf_path: str, page_num: int = 3):
    """Analyze all rows on a page and extract data"""

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]

        print(f"=== ANALYZING PAGE {page_num} ===")

        # Get all unique Y positions
        y_positions = set()
        for char in page.chars:
            y_positions.add(round(char["y0"], 1))

        # Sort Y positions (top to bottom)
        sorted_y = sorted(y_positions, reverse=True)

        print(f"Found {len(sorted_y)} unique Y positions")

        results = []

        for y_pos in sorted_y:
            row_data = extract_row_data(page, y_pos)

            if row_data and row_data["left"] and row_data["right"]:
                # Skip headers
                if any(
                    keyword in row_data["left"] + row_data["right"]
                    for keyword in ["Poczta Polska", "PNA", "Strona", "Copyright"]
                ):
                    continue

                parsed = parse_combined_data(row_data["left"], row_data["right"])

                if parsed:
                    results.append(parsed)
                    print(
                        f"✓ {parsed['PNA']} | {parsed['Miejscowość']:20} | {parsed['Gmina']:15} | {parsed['Powiat']:12} | {parsed['Województwo']}"
                    )
                else:
                    print(
                        f"✗ Could not parse: '{row_data['left']}' | '{row_data['right']}'"
                    )

        return results


def parse_full_pdf(
    pdf_path: str,
    output_csv: str = "postal_codes_column_aware.csv",
    start_page: int = 1,
    end_page: int = None,
):
    """Parse full PDF using column-aware extraction"""

    print(f"Processing PDF with column-aware parsing: {pdf_path}")

    all_results = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        if end_page is None:
            end_page = total_pages

        print(f"Processing pages {start_page} to {end_page} of {total_pages}")

        for page_num in range(start_page - 1, min(end_page, total_pages)):
            page = pdf.pages[page_num]
            current_page = page_num + 1

            if current_page % 10 == 0:
                print(f"Page {current_page}... ({len(all_results)} records so far)")

            try:
                # Get all unique Y positions
                y_positions = set()
                for char in page.chars:
                    y_positions.add(round(char["y0"], 1))

                # Sort Y positions (top to bottom)
                sorted_y = sorted(y_positions, reverse=True)

                for y_pos in sorted_y:
                    row_data = extract_row_data(page, y_pos)

                    if row_data and row_data["left"] and row_data["right"]:
                        # Skip headers
                        if any(
                            keyword in row_data["left"] + row_data["right"]
                            for keyword in [
                                "Poczta Polska",
                                "PNA",
                                "Strona",
                                "Copyright",
                            ]
                        ):
                            continue

                        parsed = parse_combined_data(
                            row_data["left"], row_data["right"]
                        )

                        if parsed:
                            all_results.append(parsed)

            except Exception as e:
                print(f"Error on page {current_page}: {e}")
                continue

    print(f"\nCompleted processing!")
    print(f"Successfully parsed: {len(all_results)} records")

    # Save to CSV
    if all_results:
        df = pd.DataFrame(all_results)

        # Ensure column order
        columns = [
            "PNA",
            "Miejscowość",
            "Ulica",
            "Numery",
            "Gmina",
            "Powiat",
            "Województwo",
        ]
        df = df[columns]

        df.to_csv(output_csv, index=False, encoding="utf-8")

        print(f"\n✓ Saved {len(all_results)} records to {output_csv}")

        # Show statistics
        print(f"\nStatistics:")
        print(f"  Unique postal codes: {df['PNA'].nunique()}")
        print(f"  Unique voivodeships: {df['Województwo'].nunique()}")

        print(f"\nFirst 10 records:")
        for i, row in df.head(10).iterrows():
            print(
                f"  {row['PNA']} | {row['Miejscowość']:25} | {row['Gmina']:15} | {row['Powiat']:12} | {row['Województwo']}"
            )

        return df
    else:
        print("No records parsed!")
        return None


def main():
    pdf_file = "/Users/mat/Downloads/oficjalny_spis_pna_2025.pdf"  # Change this to your full PDF path when ready

    print("=== COLUMN-AWARE PDF PARSER ===")
    print("This parser understands the specific column layout of the PDF")

    # Test on a single page first
    results = analyze_page_rows(pdf_file, 3)

    if results:
        print(f"\n✓ Successfully parsed {len(results)} records from page 3")

        # Automatically process first 5 pages
        print(f"\nProcessing first 5 pages...")
        df = parse_full_pdf(pdf_file, "postal_codes_column_aware.csv", 1, 5)

        if df is not None:
            print(f"\n✓ Success! Check 'postal_codes_column_aware.csv' for results")
    else:
        print("No records parsed from test page.")


if __name__ == "__main__":
    main()
