"""Exploratory Data Analysis of Retail Sales.

Run:  python eda.py
Reads data/raw_sales.csv, writes data/clean_sales.csv, figures/*.png and
prints key numbers used in the README.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

os.makedirs("figures", exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})

# ------------------------------------------------------------------
# 1. LOAD
# ------------------------------------------------------------------
raw = pd.read_csv("data/raw_sales.csv")
print("RAW SHAPE:", raw.shape)
print("\nMissing values:\n", raw.isna().sum())
print("Duplicate rows:", raw.duplicated().sum())

# ------------------------------------------------------------------
# 2. CLEAN
# ------------------------------------------------------------------
df = raw.drop_duplicates().copy()
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
df["product"] = df["product"].str.strip()
df["region"] = df["region"].str.strip().str.title()

# product -> category lookup lets us trust category; region missing -> "Unknown"
df["region"] = df["region"].fillna("Unknown")
df["discount"] = df["discount"].fillna(0)

# negative / missing quantity: drop (returns mis-logged, cannot be trusted)
bad_qty = df["quantity"].isna() | (df["quantity"] <= 0)
print("Dropping rows with missing/non-positive quantity:", bad_qty.sum())
df = df[~bad_qty].copy()

# revenue
df["revenue"] = df["quantity"] * df["unit_price"] * (1 - df["discount"])
df["month"] = df["order_date"].dt.month
df["month_name"] = df["order_date"].dt.strftime("%b")
df["weekday"] = df["order_date"].dt.day_name()

# ------------------------------------------------------------------
# 3. OUTLIERS (IQR on quantity, computed per product)
# ------------------------------------------------------------------
def flag_outliers(g):
    q1, q3 = g["quantity"].quantile([0.25, 0.75])
    iqr = q3 - q1
    return g["quantity"] > q3 + 3 * iqr

df["is_outlier"] = df.groupby("product", group_keys=False).apply(flag_outliers)
print("\nOutlier orders flagged:", int(df["is_outlier"].sum()))
outliers = df[df["is_outlier"]]
clean = df[~df["is_outlier"]].copy()
print("Revenue share held by outlier rows: %.2f%%" % (100 * outliers["revenue"].sum() / df["revenue"].sum()))

clean.to_csv("data/clean_sales.csv", index=False)
print("CLEAN SHAPE:", clean.shape)

month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# ------------------------------------------------------------------
# 4. ANALYSIS
# ------------------------------------------------------------------
total_rev = clean["revenue"].sum()
print("\nTOTAL REVENUE: %.2f Cr" % (total_rev / 1e7))

by_product = clean.groupby("product").agg(revenue=("revenue", "sum"), units=("quantity", "sum")).sort_values("revenue", ascending=False)
by_product["rev_share_%"] = 100 * by_product["revenue"] / total_rev
by_product["avg_price"] = by_product["revenue"] / by_product["units"]
print("\nBY PRODUCT:\n", by_product.round(1))

by_cat = clean.groupby("category")["revenue"].sum().sort_values(ascending=False)
print("\nBY CATEGORY (share %):\n", (100 * by_cat / total_rev).round(1))

by_region = clean.groupby("region")["revenue"].sum().sort_values(ascending=False)
print("\nBY REGION (share %):\n", (100 * by_region / total_rev).round(1))

by_month = clean.groupby("month_name")["revenue"].sum().reindex(month_order)
print("\nBY MONTH (Cr):\n", (by_month / 1e7).round(2))
peak, low = by_month.idxmax(), by_month.idxmin()
print(f"Peak month: {peak} | Lowest month: {low} | Peak/Low ratio: {by_month.max()/by_month.min():.2f}x")
fest = by_month[["Oct", "Nov"]].sum() / total_rev * 100
print("Oct+Nov share of annual revenue: %.1f%%" % fest)

pivot = clean.pivot_table(index="product", columns="month_name", values="revenue", aggfunc="sum")[month_order]
jacket = pivot.loc["Jacket"]
print("\nJacket Nov-Jan share of its revenue: %.1f%%" % (100 * jacket[["Nov", "Dec", "Jan"]].sum() / jacket.sum()))

# discount effect
disc = clean.groupby("discount").agg(orders=("order_id", "count"), avg_qty=("quantity", "mean"), revenue=("revenue", "sum"))
disc["rev_share_%"] = 100 * disc["revenue"] / total_rev
print("\nDISCOUNT BANDS:\n", disc.round(2))
disc_given = (clean["quantity"] * clean["unit_price"] * clean["discount"]).sum()
print("Total discount given (Cr): %.2f  (%.1f%% of gross)" % (disc_given / 1e7, 100 * disc_given / (total_rev + disc_given)))

weekday = clean.groupby("weekday")["revenue"].sum().reindex(
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
print("\nBY WEEKDAY (share %):\n", (100 * weekday / total_rev).round(1))

# region x category
rc = clean.pivot_table(index="region", columns="category", values="revenue", aggfunc="sum")
print("\nREGION x CATEGORY (Cr):\n", (rc / 1e7).round(2))

# MoM growth
mom = by_month.pct_change() * 100
print("\nMoM growth %:\n", mom.round(1))

# ------------------------------------------------------------------
# 5. VISUALS
# ------------------------------------------------------------------
# (a) monthly revenue trend
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(month_order, by_month.values / 1e7, marker="o", linewidth=2.2, color="#1f77b4")
ax.fill_between(month_order, by_month.values / 1e7, alpha=0.12, color="#1f77b4")
ax.set_title("Monthly Revenue (2025)", fontweight="bold")
ax.set_ylabel("Revenue (₹ Crore)")
ax.annotate(f"Peak: {peak}", (peak, by_month.max() / 1e7), textcoords="offset points", xytext=(0, 10), ha="center")
fig.tight_layout(); fig.savefig("figures/01_monthly_revenue.png"); plt.close(fig)

# (b) revenue by product
fig, ax = plt.subplots(figsize=(9, 5))
bp = by_product.sort_values("revenue")
ax.barh(bp.index, bp["revenue"] / 1e7, color="#2a9d8f")
ax.set_title("Revenue by Product", fontweight="bold")
ax.set_xlabel("Revenue (₹ Crore)")
fig.tight_layout(); fig.savefig("figures/02_revenue_by_product.png"); plt.close(fig)

# (c) region share
fig, ax = plt.subplots(figsize=(7, 4.5))
br = by_region.sort_values()
ax.bar(br.index, br.values / 1e7, color=["#e76f51" if r == "Unknown" else "#264653" for r in br.index])
ax.set_title("Revenue by Region", fontweight="bold")
ax.set_ylabel("Revenue (₹ Crore)")
fig.tight_layout(); fig.savefig("figures/03_revenue_by_region.png"); plt.close(fig)

# (d) heatmap product x month
fig, ax = plt.subplots(figsize=(10, 5.5))
norm = pivot.div(pivot.max(axis=1), axis=0)   # normalise per product to see seasonality shape
im = ax.imshow(norm.values, cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(12)); ax.set_xticklabels(month_order)
ax.set_yticks(range(len(norm))); ax.set_yticklabels(norm.index)
ax.set_title("Seasonality Heatmap (each product scaled to its own peak)", fontweight="bold")
fig.colorbar(im, ax=ax, label="Relative sales")
fig.tight_layout(); fig.savefig("figures/04_seasonality_heatmap.png"); plt.close(fig)

# (e) outliers boxplot
fig, ax = plt.subplots(figsize=(10, 5))
order = df.groupby("product")["quantity"].median().sort_values().index
ax.boxplot([df.loc[df["product"] == p, "quantity"] for p in order], tick_labels=list(order), orientation="vertical", flierprops={"markersize": 3})
ax.set_title("Order Quantity Distribution & Outliers (before outlier removal)", fontweight="bold")
ax.set_ylabel("Quantity per order")
plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
fig.tight_layout(); fig.savefig("figures/05_quantity_outliers.png"); plt.close(fig)

# (f) category by region stacked
fig, ax = plt.subplots(figsize=(8, 5))
(rc / 1e7).plot(kind="bar", stacked=True, ax=ax, colormap="tab20c")
ax.set_title("Revenue by Region and Category", fontweight="bold")
ax.set_ylabel("Revenue (₹ Crore)"); ax.set_xlabel("")
plt.xticks(rotation=0)
fig.tight_layout(); fig.savefig("figures/06_region_category.png"); plt.close(fig)

# (g) weekday
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar([d[:3] for d in weekday.index], weekday.values / 1e7, color="#8d99ae")
ax.set_title("Revenue by Day of Week", fontweight="bold"); ax.set_ylabel("Revenue (₹ Crore)")
fig.tight_layout(); fig.savefig("figures/07_weekday.png"); plt.close(fig)

print("\nSaved 7 figures to figures/")
