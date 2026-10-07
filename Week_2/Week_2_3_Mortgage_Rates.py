'''
Week 2-3 - Mortgage Rate Enrichment
Fetches the FRED MORTGAGE30US series (national 30-year fixed mortgage rate),
resamples it from weekly to monthly averages, and merges it onto both the
sold and listings datasets using a year_month key. Saves both enriched
datasets as new CSVs.

'''
import pandas as pd
from pathlib import Path

# Folder this script is saved in (IDX Exchange), no matter where Python starts
BASE_DIR = Path(__file__).resolve().parent

# Input datasets
# Sold: the filtered file from Week_2_3.py (Residential only, >90% null columns dropped)
# Listings: the Residential combined file from Week_1.py
sold = pd.read_csv(BASE_DIR / "sold_residential_filtered.csv", low_memory=False)
listings = pd.read_csv(BASE_DIR / "listings_residential_combined.csv", low_memory=False)
print(f"Sold rows: {len(sold):,}   Listings rows: {len(listings):,}")


# Step 1 – Fetch the mortgage rate data from FRED
url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
mortgage = pd.read_csv(url, parse_dates=['observation_date'])
mortgage.columns = ['date', 'rate_30yr_fixed']
print(f"FRED weekly observations: {len(mortgage):,} "
      f"({mortgage['date'].min().date()} to {mortgage['date'].max().date()})")

# Step 2 – Resample weekly rates to monthly averages
mortgage['year_month'] = mortgage['date'].dt.to_period('M')
mortgage_monthly = (
    mortgage.groupby('year_month')['rate_30yr_fixed']
    .mean()
    .reset_index()
)

# Step 3 – Create a matching year_month key on the MLS datasets

# Sold dataset — key off CloseDate
sold['year_month'] = pd.to_datetime(sold['CloseDate']).dt.to_period('M')

# Listings dataset — key off ListingContractDate
listings['year_month'] = pd.to_datetime(
    listings['ListingContractDate']
).dt.to_period('M')

# Step 4 – Merge
sold_with_rates = sold.merge(mortgage_monthly, on='year_month', how='left')
listings_with_rates = listings.merge(mortgage_monthly, on='year_month', how='left')

# Step 5 – Validate the merge

# Check for any unmatched rows (rate should not be null)
print(sold_with_rates['rate_30yr_fixed'].isnull().sum())
print(listings_with_rates['rate_30yr_fixed'].isnull().sum())

# Explain any nulls: rows with no date can't get a year_month key, so they can't match a rate
for name, df, date_col in [("Sold", sold_with_rates, "CloseDate"),
                           ("Listings", listings_with_rates, "ListingContractDate")]:
    nulls = df['rate_30yr_fixed'].isnull().sum()
    missing_dates = df[date_col].isnull().sum()
    if nulls == 0:
        print(f"{name}: validation passed, every row has a mortgage rate")
    else:
        print(f"{name}: {nulls:,} rows have no rate "
              f"({missing_dates:,} of them are missing {date_col})")

# Preview
print(
    sold_with_rates[
        ['CloseDate', 'year_month', 'ClosePrice', 'rate_30yr_fixed']
    ].head()
)


# Save both enriched datasets as new CSVs
sold_with_rates.to_csv(BASE_DIR / "sold_with_rates.csv", index=False)
listings_with_rates.to_csv(BASE_DIR / "listings_with_rates.csv", index=False)
print("Saved sold_with_rates.csv and listings_with_rates.csv")
