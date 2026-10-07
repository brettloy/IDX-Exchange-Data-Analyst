'''
Week 2-3 - Data Understanding & Cleaning Report (Sold Dataset)
1. Documents the unique PropertyType values found in the raw monthly sold files
2. Applies (and documents) the Residential filter
3. Builds a null-count summary table for every column
4. Flags and drops columns that are more than 90% null
5. Summarizes the distributions of ClosePrice, LivingArea, and DaysOnMarket
6. Saves the filtered dataset as a new CSV
'''
import glob
import re
import pandas as pd
from pathlib import Path

# Folder this script is saved in (IDX Exchange), no matter where Python starts
BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "csv"
OUTPUT_CSV = BASE_DIR / "sold_residential_filtered.csv"

NULL_THRESHOLD = 0.90                                   # flag columns above 90% null
NUMERIC_COLS = ["ClosePrice", "LivingArea", "DaysOnMarket"]


def section(title):
    """Print a clear header so each part of the report is easy to find."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ---------------------------------------------------------------------
# Load every monthly sold file (same logic as Week 1)
# ---------------------------------------------------------------------
frames = []
for f in sorted(glob.glob(str(CSV_DIR / "CRMLSSold*.csv"))):
    df = pd.read_csv(f, low_memory=False)
    # record which month file each row came from
    df["SourceMonth"] = re.search(r"(\d{6})", f).group(1)
    frames.append(df)

sold_raw = pd.concat(frames, ignore_index=True)
section("RAW SOLD DATA")
print(f"Monthly files combined: {len(frames)}")
print(f"Rows: {len(sold_raw):,}   Columns: {sold_raw.shape[1]}")


# ---------------------------------------------------------------------
# 1. Unique property types
# ---------------------------------------------------------------------
section("1. UNIQUE PROPERTY TYPES (before filtering)")
type_counts = sold_raw["PropertyType"].value_counts(dropna=False)
type_table = pd.DataFrame({
    "Count": type_counts,
    "Percent": (type_counts / len(sold_raw) * 100).round(2),
})
print(f"Unique PropertyType values: {sold_raw['PropertyType'].nunique()}\n")
print(type_table.to_string())


# ---------------------------------------------------------------------
# 2. Filtering logic
# ---------------------------------------------------------------------
section("2. FILTERING LOGIC")
print('Rule: keep only rows where PropertyType == "Residential".')
print("Why: the analysis focuses on residential home sales. Leases, land,")
print("commercial, income properties, and manufactured homes in parks behave")
print("like different markets and would distort price and DOM statistics.\n")

before = len(sold_raw)
sold = sold_raw[sold_raw["PropertyType"] == "Residential"].copy()
after = len(sold)

print(f"Rows before filter: {before:,}")
print(f"Rows after filter:  {after:,}")
print(f"Rows removed:       {before - after:,} ({(before - after) / before:.1%})")


# ---------------------------------------------------------------------
# 3. Null-count summary table
# ---------------------------------------------------------------------
section("3. NULL-COUNT SUMMARY (Residential only)")
null_summary = pd.DataFrame({
    "NullCount": sold.isnull().sum(),
    "NullPercent": (sold.isnull().mean() * 100).round(2),
    "DataType": sold.dtypes.astype(str),
}).sort_values("NullPercent", ascending=False)

pd.set_option("display.max_rows", None)
print(null_summary.to_string())


# ---------------------------------------------------------------------
# 4. Missing value report: columns above 90% null
# ---------------------------------------------------------------------
section(f"4. MISSING VALUE REPORT (columns > {NULL_THRESHOLD:.0%} null)")
high_missing_cols = null_summary[null_summary["NullPercent"] > NULL_THRESHOLD * 100].index.tolist()

if high_missing_cols:
    print(f"{len(high_missing_cols)} column(s) flagged and dropped:\n")
    for col in high_missing_cols:
        print(f"  - {col}: {null_summary.loc[col, 'NullPercent']}% null")
    sold = sold.drop(columns=high_missing_cols)
else:
    print("No columns are above the threshold.")

print(f"\nColumns remaining: {sold.shape[1]}")


# ---------------------------------------------------------------------
# 5. Numeric distribution summary
# ---------------------------------------------------------------------
section("5. NUMERIC DISTRIBUTION SUMMARY")
percentiles = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]

dist_summary = sold[NUMERIC_COLS].describe(percentiles=percentiles).T
dist_summary.insert(dist_summary.columns.get_loc("mean") + 1, "median", sold[NUMERIC_COLS].median())
dist_summary = dist_summary.rename(columns={"50%": "p50"})

pd.set_option("display.float_format", "{:,.2f}".format)
print(dist_summary.to_string())


# ---------------------------------------------------------------------
# 6. Save the filtered dataset
# ---------------------------------------------------------------------
section("6. SAVE FILTERED DATASET")
sold.to_csv(OUTPUT_CSV, index=False)
print(f"Saved {len(sold):,} rows x {sold.shape[1]} columns to:")
print(OUTPUT_CSV)
