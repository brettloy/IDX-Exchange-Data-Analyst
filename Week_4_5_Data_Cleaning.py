'''
Weeks 4-5 - Data Cleaning and Preparation (Sold Dataset)

Input:  sold_with_rates.csv   (Residential sold data + mortgage rates, from Weeks 2-3)
Output: sold_cleaned.csv      (cleaned, analysis-ready dataset)

Steps (each one prints a short report so every change is documented):
1. Convert date fields to datetime
2. Remove unnecessary or redundant columns, plus any column over 75% missing
3. Remove duplicate listings
4. Handle missing values
5. Make sure numeric fields are properly typed
6. Remove invalid numeric values
7. Date consistency checks (flag columns)
8. Geographic data checks (flag columns)
9. Final summary and save
'''
import pandas as pd
from pathlib import Path

# Folder this script is saved in (IDX Exchange), no matter where Python starts
BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "sold_with_rates.csv"
OUTPUT_CSV = BASE_DIR / "sold_cleaned.csv"


def section(title):
    """Print a clear header so each part of the report is easy to find."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def report_rows(step, before, after):
    """Print the row count before and after a step."""
    print(f"{step}: {before:,} -> {after:,} rows ({before - after:,} removed)")


# ---------------------------------------------------------------------
# Load the data
# ---------------------------------------------------------------------
section("LOAD DATA")
sold = pd.read_csv(INPUT_CSV, low_memory=False)
start_rows = len(sold)
print(f"Loaded {INPUT_CSV.name}: {start_rows:,} rows x {sold.shape[1]} columns")


# ---------------------------------------------------------------------
# 1. Convert date fields to datetime
# ---------------------------------------------------------------------
# Dates are read in as text. Converting them lets us compare dates and
# subtract them (needed for the date checks below and for Week 6 metrics).
# errors="coerce" turns any unreadable date into NaT (missing) instead of crashing.
section("1. CONVERT DATE FIELDS TO DATETIME")
DATE_COLS = ["CloseDate", "PurchaseContractDate", "ListingContractDate", "ContractStatusChangeDate"]

for col in DATE_COLS:
    missing_before = sold[col].isnull().sum()
    sold[col] = pd.to_datetime(sold[col], errors="coerce")
    unreadable = sold[col].isnull().sum() - missing_before
    print(f"{col:<26} -> {sold[col].dtype}   (already missing: {missing_before:,}, unreadable: {unreadable:,})")


# ---------------------------------------------------------------------
# 2. Remove unnecessary or redundant columns
# ---------------------------------------------------------------------
section("2. REMOVE UNNECESSARY OR REDUNDANT COLUMNS")

# Each column we drop, and the reason why
DROP_COLS = {
    "ListingKeyNumeric": "exact copy of ListingKey",
    "ListingId": "another ID for the same listing; ListingKey is the one we join on",
    "MlsStatus": "only one value ('Closed'), so it tells us nothing",
    "OriginatingSystemName": "about 89% missing and only one value",
    "OriginatingSystemSubName": "about 89% missing, MLS system bookkeeping",
    "ListAgentFirstName": "already captured in ListAgentFullName",
    "ListAgentLastName": "already captured in ListAgentFullName",
    "ListAgentEmail": "personal contact info, not needed for market analysis",
    "LotSizeArea": "lot size is already in LotSizeAcres and LotSizeSquareFeet",
    "SourceMonth": "file bookkeeping from Week 1; year_month replaces it",
}

for col, reason in DROP_COLS.items():
    print(f"  - {col}: {reason}")

cols_before = sold.shape[1]
# errors="ignore" means the script still runs if a column is already gone
sold = sold.drop(columns=list(DROP_COLS), errors="ignore")
print(f"\nColumns: {cols_before} -> {sold.shape[1]}")

# Also drop any column where more than 75% of the values are missing.
# With that little data, the column can't be relied on for analysis.
MISSING_THRESHOLD = 0.4
missing_pct = sold.isnull().mean()   # share of missing values in each column
# latfilled / lonfilled are never dropped: a blank there means "coordinate
# was not filled in", not missing data (they are converted in step 4)
KEEP_COLS = ["latfilled", "lonfilled"]
high_missing_cols = [col for col in missing_pct.index
                     if missing_pct[col] > MISSING_THRESHOLD and col not in KEEP_COLS]

print(f"\nColumns more than {MISSING_THRESHOLD:.0%} missing (dropped):")
for col in high_missing_cols:
    print(f"  - {col}: {missing_pct[col]:.1%} missing")

cols_before = sold.shape[1]
sold = sold.drop(columns=high_missing_cols)
print(f"\nColumns: {cols_before} -> {sold.shape[1]}")


# ---------------------------------------------------------------------
# 3. Remove duplicate listings
# ---------------------------------------------------------------------
# Some listings show up in more than one monthly file (e.g. a record that
# was updated later). Each ListingKey should appear only once, so we keep
# the most recent record (the latest CloseDate).
section("3. REMOVE DUPLICATE LISTINGS")
before = len(sold)
print(f"Rows sharing a ListingKey with another row: {sold['ListingKey'].duplicated(keep=False).sum():,}")

sold = sold.sort_values("CloseDate")
sold = sold.drop_duplicates(subset="ListingKey", keep="last")
report_rows("Duplicate removal", before, len(sold))


# ---------------------------------------------------------------------
# 4. Handle missing values
# ---------------------------------------------------------------------
# Rule: a sale with no close price or no close date can't be analyzed,
# so those rows are removed. Other missing values are left as missing
# (NaN) on purpose: filling them with guesses (like 0 or the average)
# would make prices, sizes, and timelines look wrong.
section("4. HANDLE MISSING VALUES")
REQUIRED_COLS = ["ClosePrice", "CloseDate"]

before = len(sold)
for col in REQUIRED_COLS:
    print(f"Missing {col}: {sold[col].isnull().sum():,}")
sold = sold.dropna(subset=REQUIRED_COLS)
report_rows("Drop rows missing a required field", before, len(sold))

# latfilled / lonfilled are True/False markers, but are blank for rows
# where no coordinate fill was done. Blank here simply means "not filled".
# Comparing to "True" gives True for filled rows and False for everything else
sold["latfilled"] = sold["latfilled"].astype(str) == "True"
sold["lonfilled"] = sold["lonfilled"].astype(str) == "True"
print("latfilled / lonfilled: blanks set to False (coordinate was not filled in)")

# Show what is still missing in the key analysis columns (kept on purpose)
KEY_COLS = ["ListPrice", "OriginalListPrice", "LivingArea", "BedroomsTotal",
            "BathroomsTotalInteger", "DaysOnMarket", "PurchaseContractDate",
            "ListingContractDate", "Latitude", "Longitude"]
print("\nRemaining missing values in key columns (left as NaN on purpose):")
print(sold[KEY_COLS].isnull().sum().to_string())


# ---------------------------------------------------------------------
# 5. Make sure numeric fields are properly typed
# ---------------------------------------------------------------------
# pd.to_numeric makes sure each column is a number. Anything that isn't a
# valid number (like stray text) becomes NaN instead of breaking math later.
section("5. ENSURE NUMERIC FIELDS ARE PROPERLY TYPED")
NUMERIC_COLS = ["ClosePrice", "ListPrice", "OriginalListPrice", "LivingArea",
                "LotSizeAcres", "LotSizeSquareFeet", "BedroomsTotal",
                "BathroomsTotalInteger", "DaysOnMarket", "YearBuilt",
                "Latitude", "Longitude", "AssociationFee", "rate_30yr_fixed"]

for col in NUMERIC_COLS:
    sold[col] = pd.to_numeric(sold[col], errors="coerce")

# PostalCode stays text: zip codes are labels, not amounts
# (and as numbers we could lose leading zeros)
# ("string" type keeps blanks as missing instead of turning them into the text "nan")
sold["PostalCode"] = sold["PostalCode"].astype("string").str.strip()

print(sold[NUMERIC_COLS + ["PostalCode"]].dtypes.to_string())


# ---------------------------------------------------------------------
# 6. Remove invalid numeric values
# ---------------------------------------------------------------------
# These values are impossible for a real sale, so the rows are removed:
#   - ClosePrice <= 0      (a home can't sell for $0 or less)
#   - LivingArea <= 0      (a home must have some square footage;
#                           this would also break price per sq ft in Week 6)
#   - DaysOnMarket < 0     (time on market can't be negative)
#   - Bedrooms/Bathrooms < 0
# Missing values are NOT removed here (NaN fails these comparisons).
section("6. REMOVE INVALID NUMERIC VALUES")
invalid_rules = {
    "ClosePrice <= 0": sold["ClosePrice"] <= 0,
    "LivingArea <= 0": sold["LivingArea"] <= 0,
    "DaysOnMarket < 0": sold["DaysOnMarket"] < 0,
    "BedroomsTotal < 0": sold["BedroomsTotal"] < 0,
    "BathroomsTotalInteger < 0": sold["BathroomsTotalInteger"] < 0,
}

# Start with "no row is invalid", then mark rows that break any rule
invalid_any = pd.Series(False, index=sold.index)
for rule, mask in invalid_rules.items():
    print(f"{rule:<28} {mask.sum():>6,} rows")
    invalid_any = invalid_any | mask

before = len(sold)
sold = sold[~invalid_any]
report_rows("\nRemove invalid values", before, len(sold))


# ---------------------------------------------------------------------
# 7. Date consistency checks
# ---------------------------------------------------------------------
# The normal order is: ListingContractDate -> PurchaseContractDate -> CloseDate
# Rows that break this order are FLAGGED (not removed) so they can be
# reviewed or filtered out later. A comparison with a missing date is False,
# so missing dates are never flagged by mistake.
section("7. DATE CONSISTENCY CHECKS")

# Listed after it closed
sold["listing_after_close_flag"] = sold["ListingContractDate"] > sold["CloseDate"]

# Offer accepted after it closed
sold["purchase_after_close_flag"] = sold["PurchaseContractDate"] > sold["CloseDate"]

# Offer accepted before it was listed (listing-to-contract time would be negative)
sold["negative_timeline_flag"] = sold["ListingContractDate"] > sold["PurchaseContractDate"]

DATE_FLAGS = ["listing_after_close_flag", "purchase_after_close_flag", "negative_timeline_flag"]
date_summary = pd.DataFrame({
    "FlaggedRows": sold[DATE_FLAGS].sum(),
    "Percent": (sold[DATE_FLAGS].mean() * 100).round(2),
})
print(date_summary.to_string())
print(f"\nRows with at least one date flag: {sold[DATE_FLAGS].any(axis=1).sum():,}")


# ---------------------------------------------------------------------
# 8. Geographic data checks
# ---------------------------------------------------------------------
# All rows are California sales, so coordinates should fall inside
# California's rough bounding box. Rows are FLAGGED, not removed.
section("8. GEOGRAPHIC DATA CHECKS")

# Rough California boundaries
CA_LAT_MIN, CA_LAT_MAX = 32.5, 42.1
CA_LON_MIN, CA_LON_MAX = -124.5, -114.1

lat = sold["Latitude"]
lon = sold["Longitude"]

# Latitude or Longitude is blank
sold["missing_coords_flag"] = lat.isnull() | lon.isnull()

# 0 is used as a placeholder for "no value" (0, 0 is in the ocean off Africa)
sold["zero_coords_flag"] = (lat == 0) | (lon == 0)

# California longitudes are always negative (west of Greenwich)
sold["positive_longitude_flag"] = lon > 0

# Has coordinates, but they land outside California
# (also catches rows where latitude and longitude were swapped)
has_coords = ~sold["missing_coords_flag"]
inside_ca = lat.between(CA_LAT_MIN, CA_LAT_MAX) & lon.between(CA_LON_MIN, CA_LON_MAX)
sold["out_of_state_coords_flag"] = has_coords & ~inside_ca

GEO_FLAGS = ["missing_coords_flag", "zero_coords_flag",
             "positive_longitude_flag", "out_of_state_coords_flag"]

# One summary flag: True if ANY geographic problem was found
sold["invalid_coords_flag"] = sold[GEO_FLAGS].any(axis=1)

geo_summary = pd.DataFrame({
    "FlaggedRows": sold[GEO_FLAGS + ["invalid_coords_flag"]].sum(),
    "Percent": (sold[GEO_FLAGS + ["invalid_coords_flag"]].mean() * 100).round(2),
})
print(geo_summary.to_string())

# Note: StateOrProvince is not changed, but non-CA values are worth knowing about
print("\nStateOrProvince values other than CA:")
print(sold.loc[sold["StateOrProvince"] != "CA", "StateOrProvince"].value_counts().to_string())


# ---------------------------------------------------------------------
# 9. Final summary and save
# ---------------------------------------------------------------------
section("9. FINAL SUMMARY")
print(f"Rows:    {start_rows:,} -> {len(sold):,} ({start_rows - len(sold):,} removed in total)")
print(f"Columns: {sold.shape[1]} (after dropping redundant ones and adding flag columns)")

print("\nData type confirmation for key fields:")
print(sold[DATE_COLS + ["ClosePrice", "LivingArea", "DaysOnMarket",
                        "BedroomsTotal", "BathroomsTotalInteger",
                        "Latitude", "Longitude"]
           + DATE_FLAGS + ["invalid_coords_flag"]].dtypes.to_string())

sold.to_csv(OUTPUT_CSV, index=False)
print(f"\nSaved cleaned dataset to: {OUTPUT_CSV}")
