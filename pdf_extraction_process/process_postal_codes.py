#!/usr/bin/env python3
"""
Polish Postal Codes PDF Processor

This script extracts postal code data from the official Polish postal codes PDF
and processes it into a clean CSV format.

Usage:
    python process_postal_codes.py [options]

Options:
    --pdf-path PATH         Path to the PDF file (default: oficjalny_spis_pna_2025.pdf)
    --pages PAGES           Pages to process (default: 3-1672)
    --output OUTPUT         Output CSV filename (default: postal_codes_poland.csv)
    --raw-output RAW        Raw extracted CSV filename (default: postal_codes_raw.csv)
    --verbose               Enable verbose output

"""

import argparse
import os
import sys
from pathlib import Path

import camelot
import numpy as np
import pandas as pd


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


def validate_postal_codes(df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    """
    Validate and clean postal codes in the DataFrame.

    Args:
        df: DataFrame with postal codes
        verbose: Enable verbose output

    Returns:
        DataFrame with validated postal codes
    """
    if verbose:
        print("🔍 Validating postal codes...")

    postal_code_pattern = r"^\d{2}-\d{3}$"

    # Count missing PNA values
    missing_pna = df[df["PNA"].isna() | (df["PNA"] == "")]
    if verbose and len(missing_pna) > 0:
        print(f"⚠️  Found {len(missing_pna)} rows with missing PNA")

    # Count invalid PNA format
    invalid_pna = df[
        (df["PNA"].notna())
        & (~df["PNA"].astype(str).str.strip().str.match(postal_code_pattern))
    ]

    if len(invalid_pna) > 0:
        if verbose:
            print(f"⚠️  Found {len(invalid_pna)} rows with invalid PNA format")
            print("🔧 Invalid PNA examples:")
            print(invalid_pna[["PNA", "Miejscowość"]].head())
    else:
        if verbose:
            print("✅ All PNA values have valid format")

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

        # Step 3: Validate postal codes
        df_validated = validate_postal_codes(df_processed, verbose=args.verbose)

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
