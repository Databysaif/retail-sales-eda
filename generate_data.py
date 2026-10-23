"""Generate a synthetic, deliberately messy retail sales dataset.

Run:  python generate_data.py
Output: data/raw_sales.csv
"""
import os

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

PRODUCTS = {
    # product: (category, base_price, base_daily_units)
    "Laptop": ("Electronics", 55000, 3),
    "Smartphone": ("Electronics", 28000, 6),
    "Headphones": ("Electronics", 3000, 14),
    "T-Shirt": ("Apparel", 700, 40),
    "Jeans": ("Apparel", 1800, 22),
    "Jacket": ("Apparel", 4500, 8),
    "Rice (5kg)": ("Grocery", 420, 60),
    "Cooking Oil (1L)": ("Grocery", 160, 70),
    "Sofa": ("Home", 24000, 2),
    "Mixer Grinder": ("Home", 3800, 9),
}
REGIONS = {"North": 1.15, "South": 1.0, "East": 0.8, "West": 1.1}

# Seasonality multipliers by month (festive season Oct-Nov, winter jackets, etc.)
def season(product, month):
    m = 1.0
    if month in (10, 11):
        m *= 1.45          # festive season
    if month == 12:
        m *= 1.2
    if product == "Jacket":
        m *= {11: 2.2, 12: 2.8, 1: 2.4, 2: 1.5}.get(month, 0.3)
    if product in ("T-Shirt",) and month in (4, 5, 6):
        m *= 1.4
    return m


rows = []
dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
for d in dates:
    for region, rmult in REGIONS.items():
        for product, (cat, price, base) in PRODUCTS.items():
            lam = base * rmult * season(product, d.month) / 4  # per-store-day
            qty = rng.poisson(lam)
            if qty == 0:
                continue
            unit_price = price * rng.normal(1.0, 0.04)
            discount = rng.choice([0, 0.05, 0.10, 0.20], p=[0.6, 0.2, 0.15, 0.05])
            rows.append([d, region, product, cat, qty, round(unit_price, 2), discount])

df = pd.DataFrame(
    rows,
    columns=["order_date", "region", "product", "category", "quantity", "unit_price", "discount"],
)
df.insert(0, "order_id", [f"ORD{100000 + i}" for i in range(len(df))])

# ---- Inject realistic mess ----
n = len(df)
# missing values
df.loc[rng.choice(n, int(n * 0.015), replace=False), "region"] = np.nan
df.loc[rng.choice(n, int(n * 0.01), replace=False), "discount"] = np.nan
df.loc[rng.choice(n, int(n * 0.008), replace=False), "quantity"] = np.nan
# inconsistent text
idx = rng.choice(n, int(n * 0.02), replace=False)
df.loc[idx, "region"] = df.loc[idx, "region"].astype("string").str.lower()
idx = rng.choice(n, int(n * 0.02), replace=False)
df.loc[idx, "product"] = df.loc[idx, "product"].astype("string") + " "
# outliers (bulk orders / data-entry errors)
out_idx = rng.choice(n, 25, replace=False)
df.loc[out_idx, "quantity"] = df.loc[out_idx, "quantity"] * rng.integers(15, 40, 25)
# negative quantity (returns logged wrongly)
neg_idx = rng.choice(n, 10, replace=False)
df.loc[neg_idx, "quantity"] = -df.loc[neg_idx, "quantity"].abs()
# duplicates
dups = df.sample(int(n * 0.01), random_state=1)
df = pd.concat([df, dups], ignore_index=True).sample(frac=1, random_state=7).reset_index(drop=True)
# date stored as string
df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")

os.makedirs("data", exist_ok=True)
df.to_csv("data/raw_sales.csv", index=False)
print(f"Wrote data/raw_sales.csv with {len(df):,} rows")
