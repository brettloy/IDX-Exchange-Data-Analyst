'''
Week 6 - Feature Engineering and Market Metrics (Sold Dataset)

Input:  sold_cleaned.csv   (cleaned, analysis-ready sold data from Weeks 4-5)

Builds the market indicators that power the Tableau dashboards.
'''
# %%
import pandas as pd
import geopandas as gpd
from pathlib import Path

# %%
# Folder this script is saved in (IDX Exchange), no matter where Python starts
BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "sold_cleaned.csv"


def section(title):
    """Print a clear header so each part of the report is easy to find."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

# %%
# ---------------------------------------------------------------------
# Load the data
# ---------------------------------------------------------------------
section("LOAD DATA")
sold = pd.read_csv(INPUT_CSV, low_memory=False)
print(f"Loaded {INPUT_CSV.name}: {len(sold):,} rows x {sold.shape[1]} columns")

# CSV files don't remember data types, so the dates come back as text.
# Convert them to datetime again so later metrics can do date math.
DATE_COLS = ["CloseDate", "PurchaseContractDate", "ListingContractDate", "ContractStatusChangeDate"]
for col in DATE_COLS:
    sold[col] = pd.to_datetime(sold[col], errors="coerce")
print("Date columns converted back to datetime:", ", ".join(DATE_COLS))

# %%
# ---------------------------------------------------------------------
# 1. Price Ratio = ClosePrice / OriginalListPrice
# ---------------------------------------------------------------------
# Measures negotiation strength: how the final sale price compares to the
# price the home was FIRST listed at.
#   - 1.00  = sold for exactly the original asking price
#   - above 1 = sold over asking (strong seller's market / bidding war)
#   - below 1 = sold under asking (buyer negotiated down or price was cut)
# Only divide where OriginalListPrice is above 0. Dividing by 0 would give
# infinity, so those rows (and rows with no OriginalListPrice) stay NaN.
section("1. PRICE RATIO (ClosePrice / OriginalListPrice)")

# .where() keeps prices above 0 and turns everything else into NaN, so we
# never actually divide by 0 (no "divide by zero" warning)
usable_original_price = sold["OriginalListPrice"].where(sold["OriginalListPrice"] > 0)
sold["price_ratio"] = sold["ClosePrice"] / usable_original_price

print(f"Rows with a price ratio:       {sold['price_ratio'].notnull().sum():,}")
print(f"Left blank (no usable price):  {sold['price_ratio'].isnull().sum():,}")

# Summary of the new column
# Note: the max is huge because a few listings have a typo'd OriginalListPrice
# (e.g. $1). 
print("\nPrice ratio summary:")
print(sold["price_ratio"].describe(percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
      .to_string(float_format="{:,.4f}".format))

# Share of homes sold over, at, and under their original asking price
pr_ratio = sold["price_ratio"].dropna()
print(f"\nSold over original asking:  {(pr_ratio > 1).mean():.1%}")
print(f"Sold at original asking:    {(pr_ratio == 1).mean():.1%}")
print(f"Sold under original asking: {(pr_ratio < 1).mean():.1%}")

# Sample output: confirm the new column is filled in correctly
print("\nSample rows:")
print(sold[["ListingKey", "OriginalListPrice", "ClosePrice", "price_ratio"]].head().to_string(index=False))

# %%
# ---------------------------------------------------------------------
# 2. Price Per Sq Ft = ClosePrice / LivingArea
# ---------------------------------------------------------------------

# Normalizes price across sizes
# Shows how expensive the space itself is

section("2. Price Per Sq Ft = ClosePrice / LivingArea")

# .where() keeps prices above 0 and turns everything else into NaN, so we
# never actually divide by 0 (no "divide by zero" warning)
usable_living_area = sold["LivingArea"].where(sold["LivingArea"] > 0)
sold["price_p_sq_ft"] = sold["ClosePrice"] / usable_living_area

# Summary of the new column
# Note: the max is huge because a few listings have a typo'd Living Area
# (e.g. .0005).
print("\nPrice Per Square Foot summary:")
print(sold["price_p_sq_ft"].describe(percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
      .to_string(float_format="{:,.4f}".format))

# Sample output: confirm the new column is filled in correctly
print("\nSample rows:")
print(sold[["ListingKey", "OriginalListPrice", "LivingArea", "price_p_sq_ft"]].head().to_string(index=False))

# %%
# ---------------------------------------------------------------------
# 3. Days On Market = DaysOnMarket(raw field)
# ---------------------------------------------------------------------
#don't change anything for this variable
section("3. Days On Market = DaysOnMarket(raw field)")

sold['DaysOnMarket'].head()

# %%
# ---------------------------------------------------------------------
# 4. Year / Month / YrMo  = Derived from CloseDate 
# ---------------------------------------------------------------------

# Enables time series analysis: splitting CloseDate into its parts lets us
# group sales by year, by month, or by each year-month combination
# (e.g. compare March 2024 vs March 2025, or plot a monthly trend line).
section("4. YEAR / MONTH / YRMO (from CloseDate)")

# .dt gives access to the parts of a datetime column
sold["close_year"] = sold["CloseDate"].dt.year      # e.g. 2024
sold["close_month"] = sold["CloseDate"].dt.month    # 1-12 (1 = January)

# YrMo as text like "2024-03". Year comes first, so sorting the text
# also sorts the months in the right order (and Tableau reads it cleanly).
sold["close_yrmo"] = sold["CloseDate"].dt.strftime("%Y-%m")

print(f"Rows missing a CloseDate (so no year/month): {sold['CloseDate'].isnull().sum():,}")
print(f"Date range: {sold['CloseDate'].min().date()} to {sold['CloseDate'].max().date()}")

# Sales per year, and sales per month for the first few months
print("\nSales per year:")
print(sold["close_year"].value_counts().sort_index().to_string())

print("\nSales per YrMo (first 6 months):")
print(sold["close_yrmo"].value_counts().sort_index().head(6).to_string())

# Sample output: confirm the new columns are filled in correctly
print("\nSample rows:")
print(sold[["ListingKey", "CloseDate", "close_year", "close_month", "close_yrmo"]].head().to_string(index=False))

# %%
# ---------------------------------------------------------------------
# 5. Close to Original List Ratio = ClosePrice / OriginalListPrice
# ---------------------------------------------------------------------
# Captures the full price reduction history: comparing the sale price to
# the FIRST asking price shows the total discount, including any price
# cuts made while the home sat on the market.
# Note: the handbook gives this the same formula as Price Ratio (section 1),
# so the two columns hold the same values. It's kept as its own column so
# it matches the handbook's metric list and Tableau field names.
section("5. CLOSE TO ORIGINAL LIST RATIO (ClosePrice / OriginalListPrice)")

# Same safe division as section 1: prices of 0 or below become NaN first
sold["close_to_original_list_ratio"] = sold["ClosePrice"] / usable_original_price

print("Close to original list ratio summary:")
print(sold["close_to_original_list_ratio"].describe(percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
      .to_string(float_format="{:,.4f}".format))

# Typical discount from the first asking price (e.g. a median of 0.97 would mean 3% below)
median_ratio = sold["close_to_original_list_ratio"].median()
print(f"\nMedian sale was {1 - median_ratio:.1%} below the original list price")

# Sample output: confirm the new column is filled in correctly
print("\nSample rows:")
print(sold[["ListingKey", "OriginalListPrice", "ClosePrice", "close_to_original_list_ratio"]].head().to_string(index=False))

# %%
# ---------------------------------------------------------------------
# 6. Listing to Contract Days = PurchaseContractDate - ListingContractDate
# ---------------------------------------------------------------------
# Measures time from listing to an accepted offer: how long it took
# to find a buyer. Lower = hotter market.
# Subtracting two dates gives a time span; .dt.days turns it into a whole
# number of days. If either date is missing, the result is NaN.
# A negative value means the offer came before the listing date. Those rows
# were already flagged in Weeks 4-5 (negative_timeline_flag) and are left
# as-is here; extreme values are handled in Week 7 (outliers).
section("6. LISTING TO CONTRACT DAYS (PurchaseContractDate - ListingContractDate)")

sold["listing_to_contract_days"] = (sold["PurchaseContractDate"] - sold["ListingContractDate"]).dt.days

print(f"Rows missing a date (left blank): {sold['listing_to_contract_days'].isnull().sum():,}")
print(f"Negative values (already flagged): {(sold['listing_to_contract_days'] < 0).sum():,}")

print("\nListing to contract days summary:")
print(sold["listing_to_contract_days"].describe(percentiles=[0.01, 0.25, 0.50, 0.75, 0.99])
      .to_string(float_format="{:,.1f}".format))

# Sample output: confirm the new column is filled in correctly
print("\nSample rows:")
print(sold[["ListingKey", "ListingContractDate", "PurchaseContractDate", "listing_to_contract_days"]].head().to_string(index=False))

# %%
# ---------------------------------------------------------------------
# 7. Contract to Close Days = CloseDate - PurchaseContractDate
# ---------------------------------------------------------------------
# Measures the escrow and closing period: time from the accepted offer
# to the sale closing (inspections, loan approval, paperwork).
# Same date subtraction as section 6. Negative values (closed before the
# offer was accepted) were flagged in Weeks 4-5 (purchase_after_close_flag).
section("7. CONTRACT TO CLOSE DAYS (CloseDate - PurchaseContractDate)")

sold["contract_to_close_days"] = (sold["CloseDate"] - sold["PurchaseContractDate"]).dt.days

print(f"Rows missing a date (left blank): {sold['contract_to_close_days'].isnull().sum():,}")
print(f"Negative values (already flagged): {(sold['contract_to_close_days'] < 0).sum():,}")

print("\nContract to close days summary:")
print(sold["contract_to_close_days"].describe(percentiles=[0.01, 0.25, 0.50, 0.75, 0.99])
      .to_string(float_format="{:,.1f}".format))

# Sample output: confirm the new column is filled in correctly
print("\nSample rows:")
print(sold[["ListingKey", "PurchaseContractDate", "CloseDate", "contract_to_close_days"]].head().to_string(index=False))

# %%
# ---------------------------------------------------------------------
# 8. School Districts (from Latitude / Longitude)
# ---------------------------------------------------------------------
# School district is a big driver of home prices, so we tag each home with
# its district. The CA Dept. of Education shapefile (DistrictAreas2425)
# holds each district's boundary as a shape on the map. A "spatial join"
# checks which boundary each home's coordinates fall inside.
#
# California has 3 district types:
#   - Unified:    covers all grades (K-12)
#   - Elementary: covers K-8, and overlaps with a High district
#   - High:       covers 9-12, and overlaps with Elementary districts
# So a home sits in EITHER one Unified district, OR one Elementary + one
# High district. To keep one row per home, we make two columns:
#   - elementary_district: the Unified district, or the Elementary one
#   - high_school_district: the Unified district, or the High one
section("8. SCHOOL DISTRICTS (from Latitude / Longitude)")

SHAPEFILE = BASE_DIR / "DistrictAreas2425" / "DistrictAreas2425.shp"
districts = gpd.read_file(SHAPEFILE)

# Shapefiles cut column names to 10 characters, so rename the two we need
districts = districts.rename(columns={"DistrictNa": "district_name", "DistrictTy": "district_type"})
districts = districts[["district_name", "district_type", "geometry"]]
print(f"Loaded {len(districts):,} school districts:")
print(districts["district_type"].value_counts().to_string())

# The shapefile uses map coordinates (EPSG:3857, in meters). Convert it to
# regular latitude/longitude (EPSG:4326) so it lines up with our data.
districts = districts.to_crs("EPSG:4326")

# Only look up homes with good coordinates (invalid ones were flagged in
# Weeks 4-5). Those other homes get a blank district.
good_coords = sold[~sold["invalid_coords_flag"]]
print(f"\nHomes with usable coordinates: {len(good_coords):,} "
      f"(skipped {len(sold) - len(good_coords):,} flagged in Weeks 4-5)")

# Turn each home's Longitude/Latitude into a point on the map
# (points_from_xy takes x = Longitude first, then y = Latitude)
homes = gpd.GeoDataFrame(
    good_coords[["ListingKey"]],
    geometry=gpd.points_from_xy(good_coords["Longitude"], good_coords["Latitude"]),
    crs="EPSG:4326",
)

# Spatial join: for each home point, find every district it falls "within".
# A home in an Elementary + High area gets 2 rows here (one per district).
matches = gpd.sjoin(homes, districts, how="inner", predicate="within")


def district_lookup(types):
    """ListingKey -> district name, using only the given district types."""
    found = matches[matches["district_type"].isin(types)]
    # A home right on a border can match 2 districts; keep the first one
    found = found.drop_duplicates(subset="ListingKey")
    return found.set_index("ListingKey")["district_name"]


# .map() looks up each ListingKey and fills in its district (blank if none)
sold["elementary_district"] = sold["ListingKey"].map(district_lookup(["Unified", "Elementary"]))
sold["high_school_district"] = sold["ListingKey"].map(district_lookup(["Unified", "High"]))

print(f"\nHomes matched to an elementary district: {sold['elementary_district'].notnull().sum():,}")
print(f"Homes matched to a high school district: {sold['high_school_district'].notnull().sum():,}")
print(f"Homes with no district (blank):          {sold['high_school_district'].isnull().sum():,}")

# Districts with the most sales
print("\nTop 10 high school districts by number of sales:")
print(sold["high_school_district"].value_counts().head(10).to_string())

# Sample output: confirm the new columns are filled in correctly
print("\nSample rows:")
print(sold[["ListingKey", "City", "elementary_district", "high_school_district"]].head().to_string(index=False))


# %%
# ---------------------------------------------------------------------
# 9. Segment Analysis
# ---------------------------------------------------------------------
# Splits the sales into groups (segments) and calculates the same summary
# statistics for each group, so the groups can be compared side by side.
# Medians are used instead of averages because a few extreme values
# (typo'd prices / sizes) would distort averages until Week 7 removes them.
section("9. SEGMENT ANALYSIS")


def segment_summary(group_col):
    """One row per group in group_col, with key market metrics for each."""
    table = sold.groupby(group_col).agg(
        sales=("ListingKey", "count"),
        median_close_price=("ClosePrice", "median"),
        median_price_p_sq_ft=("price_p_sq_ft", "median"),
        median_price_ratio=("price_ratio", "median"),
        median_days_on_market=("DaysOnMarket", "median"),
        median_listing_to_contract_days=("listing_to_contract_days", "median"),
        median_contract_to_close_days=("contract_to_close_days", "median"),
        total_sales_volume=("ClosePrice", "sum"),   # total $ of all sales in the group
    )
    # Biggest groups first
    return table.sort_values("sales", ascending=False)


def print_table(table):
    """Print a summary table with readable number formatting."""
    print(table.to_string(formatters={
        "sales": "{:,}".format,
        "median_close_price": "${:,.0f}".format,
        "median_price_p_sq_ft": "${:,.0f}".format,
        "median_price_ratio": "{:.3f}".format,
        "median_days_on_market": "{:.0f}".format,
        "median_listing_to_contract_days": "{:.0f}".format,
        "median_contract_to_close_days": "{:.0f}".format,
        "total_sales_volume": "${:,.0f}".format,
    }))


# %%
# --- 9a. By County (CountyOrParish) -----------------------------------
# Where homes are most expensive, fastest to sell, and most competitive
county_summary = segment_summary("CountyOrParish")
print(f"\n9a. Sales by County ({len(county_summary)} counties)")
print_table(county_summary)

# %%
# --- 9b. By Listing Office (ListOfficeName) ---------------------------
# Competitive intelligence: which brokerages list the most homes that sell,
# at what price points, and how quickly their listings sell.
# There are thousands of offices, so only the top 15 by sales are shown.
list_office_summary = segment_summary("ListOfficeName")
print(f"\n9b. Top 15 Listing Offices (of {len(list_office_summary):,} offices)")
print_table(list_office_summary.head(15))

# %%
# --- 9c. By Buyer's Office (BuyerOfficeName) ---------------------------
# Same idea, for the brokerages that represented the BUYERS.
# Rows with no BuyerOfficeName are left out of this table by groupby.
buyer_office_summary = segment_summary("BuyerOfficeName")
print(f"\n9c. Top 15 Buyer Offices (of {len(buyer_office_summary):,} offices)")
print_table(buyer_office_summary.head(15))
