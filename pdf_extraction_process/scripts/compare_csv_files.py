#!/usr/bin/env python3
"""
Compare two CSV files and show differences between them.
"""

import pandas as pd
import sys

def compare_csv_files(file1, file2):
    """
    Compare two CSV files and show differences.
    
    Args:
        file1: Path to first CSV file
        file2: Path to second CSV file
    """
    try:
        # Load both CSV files
        print(f"📊 Loading {file1}...")
        df1 = pd.read_csv(file1)
        print(f"📊 Loading {file2}...")
        df2 = pd.read_csv(file2)
        
        print(f"\n📈 File 1 ({file1}): {len(df1)} records")
        print(f"📈 File 2 ({file2}): {len(df2)} records")
        print(f"📊 Difference in record count: {len(df2) - len(df1)}")
        
        # Check if column names are the same
        cols1 = set(df1.columns)
        cols2 = set(df2.columns)
        
        if cols1 != cols2:
            print(f"\n⚠️  Column differences:")
            print(f"  Only in {file1}: {cols1 - cols2}")
            print(f"  Only in {file2}: {cols2 - cols1}")
        else:
            print(f"✅ Both files have same columns: {list(df1.columns)}")
        
        # Find common columns for comparison
        common_cols = list(cols1.intersection(cols2))
        if not common_cols:
            print("❌ No common columns found!")
            return
            
        # Compare records that exist in both files
        min_len = min(len(df1), len(df2))
        different_rows = []
        
        print(f"\n🔍 Comparing first {min_len} rows...")
        
        for idx in range(min_len):
            row1 = df1.iloc[idx][common_cols]
            row2 = df2.iloc[idx][common_cols]
            
            # Check if rows are different
            if not row1.equals(row2):
                different_rows.append({
                    'index': idx,
                    'row1': row1,
                    'row2': row2
                })
        
        print(f"🔍 Found {len(different_rows)} different rows in common range")
        
        # Show different rows
        if different_rows:
            print(f"\n📋 Different rows (showing first 10):")
            print("=" * 100)
            
            for i, diff in enumerate(different_rows[:10]):
                idx = diff['index']
                print(f"\nRow {idx + 2} (CSV line {idx + 2}):")  # +2 for header and 0-based index
                print(f"File 1 ({file1}):")
                for col in common_cols:
                    val1 = diff['row1'][col]
                    val2 = diff['row2'][col]
                    marker = " ← DIFF" if str(val1) != str(val2) else ""
                    print(f"  {col}: '{val1}'{marker}")
                
                print(f"File 2 ({file2}):")
                for col in common_cols:
                    val1 = diff['row1'][col]
                    val2 = diff['row2'][col]
                    marker = " ← DIFF" if str(val1) != str(val2) else ""
                    print(f"  {col}: '{val2}'{marker}")
                print("-" * 80)
        
        # Show records that exist only in one file
        if len(df1) > len(df2):
            print(f"\n📋 Records only in {file1} (rows {len(df2)+2} to {len(df1)+1}):")
            extra_rows = df1.iloc[len(df2):]
            for idx, row in extra_rows.head(5).iterrows():
                print(f"  Row {idx+2}: PNA={row.get('PNA', 'N/A')}, Miejscowość='{row.get('Miejscowość', 'N/A')}'")
            if len(extra_rows) > 5:
                print(f"  ... and {len(extra_rows) - 5} more rows")
                
        elif len(df2) > len(df1):
            print(f"\n📋 Records only in {file2} (rows {len(df1)+2} to {len(df2)+1}):")
            extra_rows = df2.iloc[len(df1):]
            for idx, row in extra_rows.head(5).iterrows():
                print(f"  Row {idx+2}: PNA={row.get('PNA', 'N/A')}, Miejscowość='{row.get('Miejscowość', 'N/A')}'")
            if len(extra_rows) > 5:
                print(f"  ... and {len(extra_rows) - 5} more rows")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"  • Total different rows in common range: {len(different_rows)}")
        print(f"  • Records only in {file1}: {max(0, len(df1) - len(df2))}")
        print(f"  • Records only in {file2}: {max(0, len(df2) - len(df1))}")
        
        # Detailed column-by-column differences
        if different_rows:
            print(f"\n🔍 COLUMN-BY-COLUMN DIFFERENCES:")
            col_diffs = {}
            for diff in different_rows:
                for col in common_cols:
                    val1 = str(diff['row1'][col])
                    val2 = str(diff['row2'][col])
                    if val1 != val2:
                        if col not in col_diffs:
                            col_diffs[col] = 0
                        col_diffs[col] += 1
            
            for col, count in sorted(col_diffs.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {col}: {count} differences")
                
    except FileNotFoundError as e:
        print(f"❌ Error: File not found - {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_csv_files.py <file1.csv> <file2.csv>")
        print("Example: python compare_csv_files.py test.csv postal_codes_poland.csv")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    compare_csv_files(file1, file2)