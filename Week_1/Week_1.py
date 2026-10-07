'''
Week 1 - Monthly Dataset Aggregation
Combines every monthly CRMLS file (Jan 2024 -> latest full month) into ONE listings dataset and 
ONE sold dataset, keeps only Residential properties, and saves both as new CSVs.
'''
import glob
import re
import pandas as pd
from pathlib import Path

# Folder this script is saved in (IDX Exchange), no matter where Python starts
BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "csv"
print("Looking for CSVs in:", CSV_DIR)   # confirm the path is right

def load_months(prefix, start="202401", end="202608"):
    """
    Read every monthly file that starts with `prefix` and falls between
    `start` and `end` (YYYYMM), then stack them into one big table.
    """
    frames = []

    # glob finds all matching files, e.g. csv/CRMLSSold202401_filled.csv, csv/CRMLSSold202402.csv and
    # sorted() puts them in date order so the combined data is chronological
    for f in sorted(glob.glob(str(CSV_DIR / f"{prefix}*.csv"))):
        # handles _filled names too
        ym = re.search(r"(\d{6})", f).group(1)          
        
        # Only keep files inside our date range.
        if start <= ym <= end:
            df = pd.read_csv(f, low_memory=False)
            # Add a column recording which month file each row came from.
            df["SourceMonth"] = ym                        
            print(f"{f}: {len(df):,} rows")
            # add this month's table to our list
            frames.append(df)

    # Stack all the monthly tables on top of each other into one table.
    # - Columns are matched by NAME, so column order doesn't matter.
    combined = pd.concat(frames, ignore_index=True)

    # Verification: the combined row count should EQUAL the sum of the
    # monthly counts. If they match, no rows were lost or duplicated.
    print(f"{prefix} combined: {len(combined):,} rows "
          f"(sum of parts = {sum(len(x) for x in frames):,})")
    return combined

# Build the two combined datasets
sold = load_months("CRMLSSold")
listings = load_months("CRMLSListing")

# Filter to Residential
# Loop over both datasets so we don't have to write this code twice.
for name, df in [("sold", sold), ("listings", listings)]:
    before = len(df)
    #Keep only rows where PropertyType is exactly "Residential"
    res = df[df["PropertyType"] == "Residential"]

    #Row counts BEFORE vs AFTER the filter
    print(f"{name}: {before:,} -> {len(res):,} after Residential filter")
    res.to_csv(BASE_DIR / f"{name}_residential_combined.csv", index=False)
