"""Exploratory Data Analysis of the Amazon Sales Dataset (India).

Data: Kaggle "Amazon Sales Dataset" by karkavelrajaj (CC BY-NC-SA 4.0)
      https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset
Put amazon.csv in data/ then run:  python eda.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

os.makedirs("figures", exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})
BLUE, TEAL, ORANGE, GREY = "#1f77b4", "#2a9d8f", "#e76f51", "#8d99ae"

# ------------------------------------------------------------------
# 1. LOAD & PROFILE
# ------------------------------------------------------------------
raw = pd.read_csv("data/amazon.csv")
print("RAW SHAPE:", raw.shape)
print("Unique products:", raw["product_id"].nunique(), "| duplicate product_id rows:", raw["product_id"].duplicated().sum())
print("Missing values:\n", raw.isna().sum()[lambda s: s > 0])

# ------------------------------------------------------------------
# 2. CLEAN
# ------------------------------------------------------------------
df = raw.copy()
for col in ["discounted_price", "actual_price"]:
    df[col] = pd.to_numeric(df[col].str.replace("₹", "", regex=False).str.replace(",", "", regex=False), errors="coerce")
df["discount_pct"] = pd.to_numeric(df["discount_percentage"].str.replace("%", "", regex=False), errors="coerce")
bad_rating = pd.to_numeric(df["rating"], errors="coerce").isna()
print("Non-numeric ratings (e.g. '|'):", int(bad_rating.sum()), df.loc[bad_rating, "rating"].unique())
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
df["rating_count"] = pd.to_numeric(df["rating_count"].str.replace(",", "", regex=False), errors="coerce")

# category hierarchy
parts = df["category"].str.split("|")
df["main_category"] = (parts.str[0].str.replace("&", " & ", regex=False)
                       .str.replace("OfficeProducts", "Office Products").str.replace("MusicalInstruments", "Musical Instruments")
                       .str.replace("HomeImprovement", "Home Improvement").str.replace("PersonalCare", "Personal Care"))
df["sub_category"] = parts.str[-1]

# Several rows are separate reviews of the same product -> keep one row per product
before = len(df)
df = df.drop_duplicates(subset="product_id", keep="first").copy()
print(f"Collapsed to one row per product: {before} -> {len(df)}")

# sanity check: stated discount vs recomputed discount
calc = (1 - df["discounted_price"] / df["actual_price"]) * 100
mismatch = (calc - df["discount_pct"]).abs() > 1
print("Rows where stated discount differs from price-based discount by >1pt:", int(mismatch.sum()))

# a rough demand proxy (no sales volume in this dataset): ratings received x price
df["demand_proxy"] = df["rating_count"] * df["discounted_price"]
df["saving"] = df["actual_price"] - df["discounted_price"]

keep = ["product_id", "product_name", "main_category", "sub_category", "discounted_price", "actual_price",
        "discount_pct", "rating", "rating_count", "demand_proxy"]
df[keep].to_csv("data/clean_products.csv", index=False)
print("CLEAN SHAPE:", df[keep].shape)
print(df[["discounted_price", "actual_price", "discount_pct", "rating", "rating_count"]].describe().round(2))

# ------------------------------------------------------------------
# 3. ANALYSIS
# ------------------------------------------------------------------
n = len(df)
print("\n=== CATEGORIES ===")
cat = df.groupby("main_category").agg(
    products=("product_id", "count"), median_price=("discounted_price", "median"),
    median_discount=("discount_pct", "median"), avg_rating=("rating", "mean"),
    total_ratings=("rating_count", "sum"), demand=("demand_proxy", "sum")).sort_values("products", ascending=False)
cat["product_share_%"] = 100 * cat["products"] / n
cat["demand_share_%"] = 100 * cat["demand"] / cat["demand"].sum()
print(cat.round(2).to_string())

print("\n=== TOP 10 SUB-CATEGORIES BY PRODUCTS ===")
sub = df.groupby("sub_category").agg(products=("product_id", "count"), avg_rating=("rating", "mean"),
                                     median_discount=("discount_pct", "median"), ratings=("rating_count", "sum"))
print(sub.sort_values("products", ascending=False).head(10).round(2).to_string())

print("\n=== RATINGS ===")
print("Mean rating: %.2f | median: %.1f | share >=4.0: %.1f%% | share <3.5: %.1f%%" % (
    df["rating"].mean(), df["rating"].median(), 100 * (df["rating"] >= 4).mean(), 100 * (df["rating"] < 3.5).mean()))
print("Rating std: %.2f" % df["rating"].std())
print("Lowest-rated main categories:\n", cat["avg_rating"].sort_values().head(3).round(2).to_string())

print("\n=== DISCOUNTS ===")
print("Mean discount: %.1f%% | median: %.0f%%" % (df["discount_pct"].mean(), df["discount_pct"].median()))
print("Share of products discounted >=50%%: %.1f%%" % (100 * (df["discount_pct"] >= 50).mean()))
print("Share discounted >=70%%: %.1f%%" % (100 * (df["discount_pct"] >= 70).mean()))
bands = pd.cut(df["discount_pct"], [-1, 20, 40, 60, 80, 100], labels=["0-20", "21-40", "41-60", "61-80", "81-100"])
bd = df.groupby(bands, observed=True).agg(products=("product_id", "count"), avg_rating=("rating", "mean"),
                                          median_ratings=("rating_count", "median"))
print(bd.round(2).to_string())
print("Correlation discount vs rating: %.3f | discount vs rating_count: %.3f | price vs discount: %.3f" % (
    df["discount_pct"].corr(df["rating"]), df["discount_pct"].corr(df["rating_count"]),
    df["actual_price"].corr(df["discount_pct"])))
print("Spearman discount vs rating_count: %.3f | rating vs rating_count: %.3f" % (
    df["discount_pct"].corr(df["rating_count"], method="spearman"), df["rating"].corr(df["rating_count"], method="spearman")))

print("\n=== PRICE ===")
print("Median discounted price: Rs %.0f | median actual: Rs %.0f" % (df["discounted_price"].median(), df["actual_price"].median()))
print("Share of products with discounted price under Rs 500: %.1f%%; under Rs 1000: %.1f%%" % (
    100 * (df["discounted_price"] < 500).mean(), 100 * (df["discounted_price"] < 1000).mean()))
df["price_band"] = pd.cut(df["discounted_price"], [0, 200, 500, 1000, 5000, 1e6], labels=["<200", "200-500", "500-1k", "1k-5k", ">5k"])
pb = df.groupby("price_band", observed=True).agg(products=("product_id", "count"), avg_rating=("rating", "mean"),
                                                median_discount=("discount_pct", "median"), median_ratings=("rating_count", "median"))
print(pb.round(2).to_string())

print("\n=== CONCENTRATION OF ATTENTION (rating_count) ===")
rc = df["rating_count"].dropna().sort_values(ascending=False)
top10 = rc.head(int(len(rc) * 0.10)).sum() / rc.sum() * 100
print("Top 10%% of products hold %.1f%% of all ratings" % top10)
top = df.nlargest(5, "rating_count")[["product_name", "rating_count", "rating", "discounted_price"]]
top["product_name"] = top["product_name"].str[:50]
print(top.to_string(index=False))

print("\n=== OUTLIERS (IQR x 3) ===")
for col in ["actual_price", "rating_count"]:
    q1, q3 = df[col].quantile([0.25, 0.75]); hi = q3 + 3 * (q3 - q1)
    print(col, "outliers:", int((df[col] > hi).sum()), "| threshold: %.0f" % hi)
print("Highest-priced products:")
print(df.nlargest(3, "actual_price")[["product_name", "actual_price", "discounted_price", "discount_pct"]].assign(
    product_name=lambda d: d["product_name"].str[:50]).to_string(index=False))

# value-for-money: high rating + many ratings + discount
good = df[(df["rating"] >= 4.3) & (df["rating_count"] >= df["rating_count"].median())]
print("\nProducts with rating>=4.3 and above-median rating_count:", len(good), "(%.1f%%)" % (100 * len(good) / n))
print("Their median discount: %.0f%%" % good["discount_pct"].median())

# ------------------------------------------------------------------
# 4. VISUALS
# ------------------------------------------------------------------
# (1) products per main category
fig, ax = plt.subplots(figsize=(9, 4.8))
c = cat["products"].sort_values()
ax.barh(c.index, c.values, color=TEAL)
for i, v in enumerate(c.values):
    ax.text(v + 6, i, str(v), va="center", fontsize=9)
ax.set_title("Products per Main Category", fontweight="bold"); ax.set_xlabel("Number of products")
fig.tight_layout(); fig.savefig("figures/01_products_per_category.png"); plt.close(fig)

# (2) rating distribution
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(df["rating"].dropna(), bins=np.arange(2, 5.2, 0.1), color=BLUE, edgecolor="white")
ax.axvline(df["rating"].mean(), color=ORANGE, linestyle="--", label="mean %.2f" % df["rating"].mean())
ax.set_title("Distribution of Product Ratings", fontweight="bold"); ax.set_xlabel("Rating"); ax.set_ylabel("Products"); ax.legend()
fig.tight_layout(); fig.savefig("figures/02_rating_distribution.png"); plt.close(fig)

# (3) discount distribution
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(df["discount_pct"].dropna(), bins=20, color=TEAL, edgecolor="white")
ax.axvline(df["discount_pct"].median(), color=ORANGE, linestyle="--", label="median %.0f%%" % df["discount_pct"].median())
ax.set_title("Distribution of Discount %", fontweight="bold"); ax.set_xlabel("Discount (%)"); ax.set_ylabel("Products"); ax.legend()
fig.tight_layout(); fig.savefig("figures/03_discount_distribution.png"); plt.close(fig)

# (4) price distribution (log scale)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(np.log10(df["discounted_price"].dropna()), bins=30, color=BLUE, edgecolor="white")
ticks = [2, 3, 4, 5]
ax.set_xticks(ticks); ax.set_xticklabels(["₹100", "₹1,000", "₹10,000", "₹1,00,000"])
ax.set_title("Discounted Price Distribution (log scale)", fontweight="bold"); ax.set_ylabel("Products")
fig.tight_layout(); fig.savefig("figures/04_price_distribution.png"); plt.close(fig)

# (5) discount vs rating_count scatter
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(df["discount_pct"], df["rating_count"], s=14, alpha=0.4, color=BLUE)
ax.set_yscale("log"); ax.set_xlabel("Discount (%)"); ax.set_ylabel("Number of ratings (log scale)")
ax.set_title("Do Bigger Discounts Mean More Ratings?", fontweight="bold")
fig.tight_layout(); fig.savefig("figures/05_discount_vs_ratings.png"); plt.close(fig)

# (6) median discount by main category
fig, ax = plt.subplots(figsize=(9, 4.8))
big = cat[cat["products"] >= 30]          # categories with 1-2 products would be misleading
md = big["median_discount"].sort_values()
ax.barh(md.index, md.values, color=ORANGE)
ax.set_title("Median Discount % by Main Category (categories with 30+ products)", fontweight="bold"); ax.set_xlabel("Median discount (%)")
fig.tight_layout(); fig.savefig("figures/06_discount_by_category.png"); plt.close(fig)

# (7) rating by price band boxplot
fig, ax = plt.subplots(figsize=(8, 4.5))
groups = [df.loc[df["price_band"] == b, "rating"].dropna() for b in pb.index]
ax.boxplot(groups, tick_labels=[f"₹{b}" for b in pb.index], orientation="vertical", flierprops={"markersize": 3})
ax.set_title("Rating by Price Band", fontweight="bold"); ax.set_ylabel("Rating")
fig.tight_layout(); fig.savefig("figures/07_rating_by_price_band.png"); plt.close(fig)

# (8) avg rating by main category (zoomed axis)
fig, ax = plt.subplots(figsize=(9, 4.8))
ar = big["avg_rating"].sort_values()
ax.barh(ar.index, ar.values, color=TEAL)
ax.set_xlim(3.5, 4.6); ax.set_title("Average Rating by Main Category (30+ products; axis starts at 3.5)", fontweight="bold"); ax.set_xlabel("Average rating")
fig.tight_layout(); fig.savefig("figures/08_rating_by_category.png"); plt.close(fig)

print("\nSaved 8 figures to figures/")
