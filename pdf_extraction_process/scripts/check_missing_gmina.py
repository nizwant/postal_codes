#!/usr/bin/env python3
"""
Check for records with missing Gmina in the postal codes dataset.
"""

import pandas as pd

def check_missing_gmina(csv_path="postal_codes_poland.csv"):
    """
    Load CSV and print records with missing Gmina values.
    
    Args:
        csv_path: Path to the CSV file to check
    """
    try:
        # Load the dataset
        df = pd.read_csv(csv_path)
        print(f"📊 Total records: {len(df)}")
        
        # Find records with missing Gmina
        missing_gmina = df[df["Gmina"].isna() | (df["Gmina"] == "")]
        
        print(f"⚠️  Records with missing Gmina: {len(missing_gmina)}")
        
        if len(missing_gmina) > 0:
            print("\n📋 Records with missing Gmina:")
            print("=" * 80)
            
            # Display all records with missing Gmina
            for idx, row in missing_gmina.iterrows():
                print(f"Row {idx + 2}:")  # +2 because CSV has header and 0-based index
                print(f"  PNA: {row['PNA']}")
                print(f"  Miejscowość: {row['Miejscowość']}")
                print(f"  Ulica: {row['Ulica']}")
                print(f"  Numery: {row['Numery']}")
                print(f"  Gmina: '{row['Gmina']}'")
                print(f"  Powiat: {row['Powiat']}")
                print(f"  Województwo: {row['Województwo']}")
                print("-" * 40)
        else:
            print("✅ No records with missing Gmina found!")
            
    except FileNotFoundError:
        print(f"❌ Error: File '{csv_path}' not found")
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    import sys
    
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "postal_codes_poland.csv"
    check_missing_gmina(csv_file)