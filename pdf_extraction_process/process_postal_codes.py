#!/usr/bin/env python3
"""
Polish Postal Codes PDF Processor

This script extracts postal code data from the official Polish postal codes PDF
published by Poczta Polska and processes it into clean CSV format. The processing
pipeline consists of 4 sequential steps:

1. PDF Table Extraction - Uses Camelot with optimized parameters for Polish postal PDF format
2. Row Merging - Handles data split across multiple table rows iteratively  
3. Data Validation - Comprehensive validation of Polish administrative divisions
4. Output Generation - Saves both raw extracted and final processed CSV files

The script handles complex multi-page table structures where data often spans 
multiple rows, text can be split mid-word with hyphens across rows, and uses
validation specifically designed for Polish administrative divisions.

Usage:
    python process_postal_codes.py [options]

Options:
    --pdf-path PATH                 Path to the PDF file (default: data/oficjalny_spis_pna_2025.pdf)
    --pages PAGES                   Pages to process (default: 3-1672)
    --output OUTPUT                 Output CSV filename (default: postal_codes_poland.csv)
    --raw-output RAW                Raw extracted CSV filename (default: data/postal_codes_raw.csv)
    --verbose, -v                   Enable verbose output
    --skip-validation-flags         Skip adding validation flag columns to output CSV
    --skip-merged-column-fix        Skip fixing columns merged during PDF extraction (e.g., Gmina in Numery)

Examples:
    # Basic processing with default settings
    python process_postal_codes.py
    
    # Custom PDF path with verbose output
    python process_postal_codes.py --pdf-path data/my_postal_codes.pdf --verbose
    
    # Skip validation flags in output
    python process_postal_codes.py --skip-validation-flags

"""

import argparse
import os
import sys
from pathlib import Path

import camelot
import numpy as np
import pandas as pd

try:
    from .post_process_merged_columns import extract_known_gmina_from_numery
except ImportError:
    from post_process_merged_columns import extract_known_gmina_from_numery


def extract_tables_from_pdf(
    pdf_path: str,
    pages: str = "3-1672",
    flavor: str = "stream",
    output_file: str = "postal_codes_raw.csv",
    verbose: bool = False,
) -> tuple[pd.DataFrame, list]:
    """
    Extract tables from PDF and merge into a single DataFrame.

    Args:
        pdf_path: Path to the PDF file
        pages: Pages to parse (e.g., '3-1672', 'all', '1,2,3')
        flavor: Camelot flavor ('stream' for tables without lines, 'lattice' for tables with lines)
        output_file: Name of the output CSV file for raw data
        verbose: Enable verbose output

    Returns:
        Tuple of (merged_dataframe, list_of_tables)
    """
    if verbose:
        print(f"📖 Reading tables from {pdf_path}...")
        print(f"📄 Processing pages: {pages}")

    # Read PDF tables with specific parameters optimized for Polish postal codes PDF
    tables = camelot.read_pdf(
        pdf_path,
        pages=pages,
        flavor=flavor,
        table_areas=["28,813,567,27"],
        columns=["60,144,267,332,422,497"],
        row_tol=9,
    )

    if len(tables) == 0:
        raise ValueError("No tables found in the PDF")

    if verbose:
        print(f"✅ Found {len(tables)} table(s) across pages")

    # Initialize merged dataframe
    merged_df = None

    for i, table in enumerate(tables):
        df = table.df

        # Clean up text formatting
        df = df.apply(
            lambda col: (
                col.astype(str)
                .str.replace("\n", "", regex=False)
                .str.replace("\r", "", regex=False)
                .str.strip()
                if col.dtype == "object"
                else col
            )
        )

        if verbose and i < 5:  # Show progress for first few tables
            print(f"  📊 Page table {i+1}: Shape {df.shape}")

        if i == 0:
            # First table - skip first 2 rows (headers)
            merged_df = df.iloc[2:]
        else:
            # Skip header row for subsequent tables
            df = df.iloc[1:]
            merged_df = pd.concat([merged_df, df], ignore_index=True)

    # Set column names from first data row
    first_row = merged_df.iloc[0].astype(str)
    merged_df.columns = first_row
    merged_df = merged_df[1:].reset_index(drop=True)

    # Remove completely empty rows
    merged_df = merged_df.dropna(how="all").reset_index(drop=True)

    # Save raw extracted data
    merged_df.to_csv(output_file, index=False)

    if verbose:
        print(f"💾 Raw data saved to: {output_file}")
        print(f"📊 Raw table shape: {merged_df.shape}")

    return merged_df, tables


def process_merged_rows(df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    """
    Process rows where data spans multiple lines by merging incomplete rows
    with their parent rows.

    Args:
        df: DataFrame with raw extracted data
        verbose: Enable verbose output

    Returns:
        Processed DataFrame with merged rows
    """
    if verbose:
        print("🔄 Processing merged rows...")

    df = df.copy()
    columns_to_merge = [
        "Miejscowość",
        "Ulica",
        "Numery",
        "Gmina",
        "Powiat",
        "Województwo",
    ]

    # Iterative processing until no more changes occur
    iteration = 0
    while True:
        iteration += 1
        initial_length = len(df)

        if verbose and iteration <= 3:
            print(f"  🔄 Iteration {iteration}: Processing {initial_length} rows")

        # Process each row
        for i in range(1, len(df)):
            # Check if current row has missing PNA (indicates it's a continuation)
            if pd.isna(df.loc[i, "PNA"]) or str(df.loc[i, "PNA"]).strip() == "":
                # Copy PNA from previous row
                df.loc[i, "PNA"] = df.loc[i - 1, "PNA"]

                # Merge data from continuation row into previous row
                for col in columns_to_merge:
                    above = (
                        str(df.loc[i - 1, col])
                        if not pd.isna(df.loc[i - 1, col])
                        else ""
                    )
                    current = str(df.loc[i, col]) if not pd.isna(df.loc[i, col]) else ""

                    if current.strip():  # Only merge if current row has data
                        if above.endswith("-"):
                            # Handle hyphenated words split across rows
                            df.loc[i - 1, col] = above + current.strip()
                        else:
                            # Add space between merged parts
                            df.loc[i - 1, col] = (above + " " + current.strip()).strip()

                # Mark current row for deletion
                df.loc[i, :] = np.nan

        # Remove rows marked for deletion
        df = df.dropna(how="all").reset_index(drop=True)

        # Check if we've reached convergence
        if len(df) == initial_length:
            break

    if verbose:
        print(f"✅ Processing complete after {iteration} iterations")
        print(f"📊 Final shape: {df.shape}")

    return df


def validate_data(
    df: pd.DataFrame, verbose: bool = False, add_flags: bool = True
) -> pd.DataFrame:
    """
    Validate and clean all data in the DataFrame with comprehensive Polish administrative checks.

    Args:
        df: DataFrame with postal codes and administrative data
        verbose: Enable verbose output
        add_flags: Add validation flag columns to DataFrame

    Returns:
        DataFrame with validation results
    """
    if verbose:
        print("🔍 Performing comprehensive data validation...")

    # Define Polish województwa (voivodeships)
    POLISH_WOJEWODZTWA = {
        "dolnośląskie",
        "kujawsko-pomorskie",
        "lubelskie",
        "lubuskie",
        "łódzkie",
        "małopolskie",
        "mazowieckie",
        "opolskie",
        "podkarpackie",
        "podlaskie",
        "pomorskie",
        "śląskie",
        "świętokrzyskie",
        "warmińsko-mazurskie",
        "wielkopolskie",
        "zachodniopomorskie",
    }

    validation_issues = []

    # 1. Validate PNA (postal code) format
    postal_code_pattern = r"^\d{2}-\d{3}$"
    missing_pna = df[df["PNA"].isna() | (df["PNA"] == "")]
    invalid_pna = df[
        (df["PNA"].notna())
        & (~df["PNA"].astype(str).str.strip().str.match(postal_code_pattern))
    ]

    if len(missing_pna) > 0:
        validation_issues.append(f"Missing PNA: {len(missing_pna)} rows")
        if verbose:
            print(f"⚠️  Found {len(missing_pna)} rows with missing PNA")

    if len(invalid_pna) > 0:
        validation_issues.append(f"Invalid PNA format: {len(invalid_pna)} rows")
        if verbose:
            print(f"⚠️  Found {len(invalid_pna)} rows with invalid PNA format")
            print("🔧 Invalid PNA examples:")
            print(invalid_pna[["PNA", "Miejscowość"]].head())
    else:
        if verbose:
            print("✅ All PNA values have valid format")

    # 2. Validate Województwo (voivodeship)
    df_clean_wojewodztwo = df[df["Województwo"].notna() & (df["Województwo"] != "")]
    invalid_wojewodztwa = df_clean_wojewodztwo[
        ~df_clean_wojewodztwo["Województwo"]
        .str.lower()
        .str.strip()
        .isin(POLISH_WOJEWODZTWA)
    ]

    if len(invalid_wojewodztwa) > 0:
        validation_issues.append(
            f"Invalid województwo: {len(invalid_wojewodztwa)} rows"
        )
        if verbose:
            print(f"⚠️  Found {len(invalid_wojewodztwa)} rows with invalid województwo")
            unique_invalid = invalid_wojewodztwa["Województwo"].unique()[:5]
            print(f"🔧 Examples: {list(unique_invalid)}")
    else:
        if verbose:
            print("✅ All województwa are valid")

    # 3. Check for numbers in place names (Miejscowość)
    has_numbers_pattern = r"\d"
    miejscowosc_with_numbers = df[
        (df["Miejscowość"].notna())
        & (df["Miejscowość"] != "")
        & (df["Miejscowość"].astype(str).str.contains(has_numbers_pattern, regex=True))
    ]

    if len(miejscowosc_with_numbers) > 0:
        validation_issues.append(
            f"Miejscowość with numbers: {len(miejscowosc_with_numbers)} rows"
        )
        if verbose:
            print(f"⚠️  Found {len(miejscowosc_with_numbers)} miejscowości with numbers")
            examples = miejscowosc_with_numbers["Miejscowość"].unique()[:5]
            print(f"🔧 Examples: {list(examples)}")
    else:
        if verbose:
            print("✅ No numbers found in miejscowość names")

    # 4. Check for numbers in gmina names (excluding Roman numerals and common patterns)
    # Allow Roman numerals (I, II, III, IV, V) and ordinal numbers in Polish
    roman_numeral_pattern = r"\b(?:I{1,3}|IV|V|VI{1,3}|IX|X)\b"
    ordinal_pattern = r"\d+[-.](?:go|ej|ma|sze)"  # Polish ordinal patterns

    gmina_with_suspicious_numbers = df[
        (df["Gmina"].notna())
        & (df["Gmina"] != "")
        & (df["Gmina"].astype(str).str.contains(has_numbers_pattern, regex=True))
        & (~df["Gmina"].astype(str).str.contains(roman_numeral_pattern, regex=True))
        & (~df["Gmina"].astype(str).str.contains(ordinal_pattern, regex=True))
    ]

    if len(gmina_with_suspicious_numbers) > 0:
        validation_issues.append(
            f"Gmina with suspicious numbers: {len(gmina_with_suspicious_numbers)} rows"
        )
        if verbose:
            print(
                f"⚠️  Found {len(gmina_with_suspicious_numbers)} gminy with suspicious numbers"
            )
            examples = gmina_with_suspicious_numbers["Gmina"].unique()[:5]
            print(f"🔧 Examples: {list(examples)}")
    else:
        if verbose:
            print("✅ No suspicious numbers found in gmina names")

    # 5. Check for numbers in powiat names
    powiat_with_suspicious_numbers = df[
        (df["Powiat"].notna())
        & (df["Powiat"] != "")
        & (df["Powiat"].astype(str).str.contains(has_numbers_pattern, regex=True))
        & (~df["Powiat"].astype(str).str.contains(roman_numeral_pattern, regex=True))
        & (~df["Powiat"].astype(str).str.contains(ordinal_pattern, regex=True))
    ]

    if len(powiat_with_suspicious_numbers) > 0:
        validation_issues.append(
            f"Powiat with suspicious numbers: {len(powiat_with_suspicious_numbers)} rows"
        )
        if verbose:
            print(
                f"⚠️  Found {len(powiat_with_suspicious_numbers)} powiaty with suspicious numbers"
            )
            examples = powiat_with_suspicious_numbers["Powiat"].unique()[:5]
            print(f"🔧 Examples: {list(examples)}")
    else:
        if verbose:
            print("✅ No suspicious numbers found in powiat names")

    # 6. Check for missing essential data
    essential_columns = ["PNA", "Miejscowość", "Gmina", "Powiat", "Województwo"]
    for col in essential_columns:
        missing = df[df[col].isna() | (df[col] == "")]
        if len(missing) > 0:
            validation_issues.append(f"Missing {col}: {len(missing)} rows")
            if verbose:
                print(f"⚠️  Found {len(missing)} rows with missing {col}")

    # 7. Check for suspiciously long values (potential parsing errors)
    max_lengths = {
        "Miejscowość": 100,
        "Ulica": 150,
        "Numery": 200,
        "Gmina": 100,
        "Powiat": 100,
    }

    for col, max_len in max_lengths.items():
        if col in df.columns:
            too_long = df[(df[col].notna()) & (df[col].astype(str).str.len() > max_len)]
            if len(too_long) > 0:
                validation_issues.append(f"{col} too long: {len(too_long)} rows")
                if verbose:
                    print(
                        f"⚠️  Found {len(too_long)} rows with {col} longer than {max_len} characters"
                    )
                    example = (
                        too_long[col].iloc[0][:100] + "..."
                        if len(too_long[col].iloc[0]) > 100
                        else too_long[col].iloc[0]
                    )
                    print(f"🔧 Example: {example}")

    # 8. Check for duplicate postal codes with different locations (potential errors)
    duplicate_pna_diff_locations = df.groupby("PNA").agg(
        {
            "Miejscowość": "nunique",
            "Gmina": "nunique",
            "Powiat": "nunique",
            "Województwo": "nunique",
        }
    )

    suspicious_duplicates = duplicate_pna_diff_locations[
        (duplicate_pna_diff_locations["Województwo"] > 1)
        | (
            duplicate_pna_diff_locations["Powiat"] > 3
        )  # Allow some variation but flag excessive
    ]

    if len(suspicious_duplicates) > 0:
        validation_issues.append(
            f"Suspicious PNA duplicates: {len(suspicious_duplicates)} postal codes"
        )
        if verbose:
            print(
                f"⚠️  Found {len(suspicious_duplicates)} postal codes with suspicious location variations"
            )
            print("🔧 Examples:")
            print(suspicious_duplicates.head())

    # Summary
    if verbose:
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY:")
        if validation_issues:
            print(f"⚠️  Found {len(validation_issues)} types of validation issues:")
            for issue in validation_issues:
                print(f"   • {issue}")
        else:
            print("✅ All validation checks passed!")
        print("=" * 50)

    # Add validation flags to DataFrame (optional)
    if add_flags:
        if verbose:
            print("\n🏷️  Adding validation flags to DataFrame...")

        # Add flag columns for major issues
        df = df.copy()
        df["validation_invalid_pna"] = (
            df["PNA"].isin(invalid_pna["PNA"]) if len(invalid_pna) > 0 else False
        )
        df["validation_invalid_wojewodztwo"] = (
            df["Województwo"].isin(invalid_wojewodztwa["Województwo"])
            if len(invalid_wojewodztwa) > 0
            else False
        )
        df["validation_numbers_in_places"] = (
            df["Miejscowość"].isin(miejscowosc_with_numbers["Miejscowość"])
            if len(miejscowosc_with_numbers) > 0
            else False
        )

    return df


def main():
    """Main function to process Polish postal codes PDF."""
    parser = argparse.ArgumentParser(
        description="Extract and process Polish postal codes from PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--pdf-path",
        default="data/oficjalny_spis_pna_2025.pdf",
        help="Path to the PDF file (default: data/oficjalny_spis_pna_2025.pdf)",
    )
    parser.add_argument(
        "--pages", default="3-1672", help="Pages to process (default: 3-1672)"
    )
    parser.add_argument(
        "--output",
        default="postal_codes_poland.csv",
        help="Output CSV filename (default: postal_codes_poland.csv)",
    )
    parser.add_argument(
        "--raw-output",
        default="data/postal_codes_raw.csv",
        help="Raw extracted CSV filename (default: data/postal_codes_raw.csv)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--skip-validation-flags",
        action="store_true",
        help="Skip adding validation flag columns to output CSV",
    )
    parser.add_argument(
        "--skip-merged-column-fix",
        action="store_true",
        help="Skip fixing columns merged during PDF extraction (e.g., Gmina in Numery)",
    )

    args = parser.parse_args()

    # Check if PDF exists
    if not os.path.exists(args.pdf_path):
        print(f"❌ Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)

    try:
        if args.verbose:
            print("🚀 Starting Polish postal codes processing...")
            print(f"📁 PDF file: {args.pdf_path}")
            print(f"📄 Pages: {args.pages}")
            print(f"💾 Raw output: {args.raw_output}")
            print(f"✨ Final output: {args.output}")
            print("-" * 50)

        # Step 1: Extract tables from PDF
        df, tables = extract_tables_from_pdf(
            args.pdf_path, args.pages, output_file=args.raw_output, verbose=args.verbose
        )

        # Step 2: Process merged rows
        df_processed = process_merged_rows(df, verbose=args.verbose)

        # Step 2.5: Fix merged columns (runs by default)
        if not args.skip_merged_column_fix:
            df_processed, fixed_count = extract_known_gmina_from_numery(df_processed)
            if fixed_count > 0:
                print(f"🔧 Fixed {fixed_count} merged column issues")
            elif args.verbose:
                print("✅ No merged column issues found")

        # Step 3: Comprehensive data validation
        df_validated = validate_data(
            df_processed, verbose=args.verbose, add_flags=not args.skip_validation_flags
        )

        # Step 4: Save final result
        df_validated.to_csv(args.output, index=False)

        if args.verbose:
            print(f"🎉 Processing complete!")
            print(f"✨ Final dataset saved to: {args.output}")
            print(f"📊 Final shape: {df_validated.shape}")
            print(f"🏙️  Unique postal codes: {df_validated['PNA'].nunique()}")
        else:
            print(f"✅ Processed {df_validated.shape[0]} records → {args.output}")

    except Exception as e:
        print(f"❌ Error during processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
