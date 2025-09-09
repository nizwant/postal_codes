#!/usr/bin/env python3
"""
Fix merged Gmina data by looking up known gmina values in Numery column.

Usage:
    python fix_gmina_lookup.py [input.csv] [output.csv] [--show-summary]
    
Options:
    --show-summary    Show detailed summary of fixed gminas at the end
    
Examples:
    python fix_gmina_lookup.py                                    # Default files
    python fix_gmina_lookup.py postal_codes.csv                   # Custom input
    python fix_gmina_lookup.py input.csv output.csv               # Custom input/output  
    python fix_gmina_lookup.py input.csv output.csv --show-summary # With summary
"""

import pandas as pd


def extract_known_gmina_from_numery(df):
    """
    Extract gmina names from Numery column by looking up known gmina values.
    This approach is more reliable than regex patterns.
    """
    print("🔍 Building list of known gmina values...")

    # Get all known gmina values from rows where gmina is not null
    known_gminas = set()
    for gmina in df["Gmina"].dropna():
        gmina_str = str(gmina).strip()
        if gmina_str and gmina_str not in ["", "nan"]:
            known_gminas.add(gmina_str)

    # Also get gmina values from Powiat column (many are the same)
    for powiat in df["Powiat"].dropna():
        powiat_str = str(powiat).strip()
        if powiat_str and powiat_str not in ["", "nan"]:
            known_gminas.add(powiat_str)

    # Sort by length (longest first) to match compound names before single words
    known_gminas = sorted(known_gminas, key=len, reverse=True)

    print(f"📊 Found {len(known_gminas)} known gmina values")
    print(f"🔍 Examples: {list(known_gminas)[:10]}")

    fixed_count = 0

    print(f"\n🔄 Checking rows with missing gmina...")

    for idx, row in df.iterrows():
        # Only process rows where Gmina is missing/null
        if pd.isna(row["Gmina"]) or str(row["Gmina"]).strip() in ["", "nan"]:
            numery_str = str(row["Numery"])

            # Skip if Numery is also null/empty
            if pd.isna(row["Numery"]) or numery_str.strip() in ["", "nan"]:
                continue

            # Look for any known gmina in the Numery string
            found_gmina = None

            for gmina in known_gminas:
                # Check if this gmina appears at the end of the Numery string
                # This handles cases like "1-33(n), 2a-22(p) Białystok"
                if numery_str.endswith(" " + gmina):
                    # Extract the numbers part and the gmina part
                    numbers_part = numery_str[: -len(" " + gmina)].strip()
                    found_gmina = gmina
                    break
                # Also check for cases without space before gmina (edge case)
                elif numery_str.endswith(gmina) and len(numery_str) > len(gmina):
                    # Make sure there's some separation (not just part of a word)
                    char_before = numery_str[-(len(gmina) + 1)]
                    if char_before in [" ", ")", "-"]:
                        numbers_part = numery_str[: -len(gmina)].strip()
                        found_gmina = gmina
                        break

            if found_gmina:
                # Update the row
                df.loc[idx, "Numery"] = numbers_part
                df.loc[idx, "Gmina"] = found_gmina
                fixed_count += 1

                print(f"Row {idx + 2}: '{found_gmina}' -> Gmina | {numery_str} → {numbers_part}")

    return df, fixed_count


def main():
    import sys

    # Parse command line arguments
    show_summary = "--show-summary" in sys.argv
    if show_summary:
        sys.argv.remove("--show-summary")
    
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "postal_codes_poland.csv"
    output_file = (
        sys.argv[2]
        if len(sys.argv) > 2
        else csv_file.replace(".csv", "_gmina_fixed.csv")
    )

    try:
        print(f"📊 Loading {csv_file}...")
        df = pd.read_csv(csv_file)

        print(f"📈 Total records: {len(df)}")
        missing_gmina_before = len(
            df[df["Gmina"].isna() | (df["Gmina"] == "") | (df["Gmina"] == "nan")]
        )
        print(f"⚠️  Records with missing Gmina: {missing_gmina_before}")

        if missing_gmina_before > 0:
            print(f"\n🔄 Using lookup-based approach to fix merged Gmina data...")
            df_fixed, fixed_count = extract_known_gmina_from_numery(df)

            missing_gmina_after = len(
                df_fixed[
                    df_fixed["Gmina"].isna()
                    | (df_fixed["Gmina"] == "")
                    | (df_fixed["Gmina"] == "nan")
                ]
            )

            print(f"📊 RESULTS:")
            print(f"✅ Fixed {fixed_count} records")
            print(f"📉 Missing Gmina: {missing_gmina_before} → {missing_gmina_after}")
            print(f"📈 Success rate: {(fixed_count / missing_gmina_before * 100):.1f}%")

            # Save the fixed data
            df_fixed.to_csv(output_file, index=False)
            print(f"\n💾 Saved fixed data to: {output_file}")

            # Show summary of what gminas were found (optional)
            if fixed_count > 0 and show_summary:
                print(f"\n📋 Summary of fixed gminas:")
                gmina_counts = {}
                for idx, row in df_fixed.iterrows():
                    if not (
                        pd.isna(df.loc[idx, "Gmina"])
                        or str(df.loc[idx, "Gmina"]).strip() in ["", "nan"]
                    ):
                        if not (
                            pd.isna(row["Gmina"])
                            or str(row["Gmina"]).strip() in ["", "nan"]
                        ):
                            # This was a fixed row
                            gmina = row["Gmina"]
                            gmina_counts[gmina] = gmina_counts.get(gmina, 0) + 1

                for gmina, count in sorted(
                    gmina_counts.items(), key=lambda x: x[1], reverse=True
                ):
                    print(f"  • {gmina}: {count} records")
        else:
            print("✅ No missing Gmina records found!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
