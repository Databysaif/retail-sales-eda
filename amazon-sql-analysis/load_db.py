"""Build a SQLite database of customers, products and orders from the Kaggle Amazon Sales Dataset.

The dataset has NO real order table. It lists ~1,350 products, each with a sample of up to 8
customer reviews. So in this project:

    one ORDER  = one (reviewer, product) pair      -> a review-based stand-in for a purchase
    CUSTOMER   = a reviewer (ID is hashed; names and review text are NOT stored)

Run:  python load_db.py      (needs data/amazon.csv from Kaggle)
Output: amazon_orders.db
"""
import hashlib
import os
import sqlite3

import pandas as pd

SRC, DB = "data/amazon.csv", "amazon_orders.db"

raw = pd.read_csv(SRC)

# ---------------- products ----------------
p = raw.drop_duplicates("product_id").copy()
for c in ["discounted_price", "actual_price"]:
    p[c] = pd.to_numeric(p[c].str.replace("₹", "", regex=False).str.replace(",", "", regex=False), errors="coerce")
p["discount_pct"] = pd.to_numeric(p["discount_percentage"].str.replace("%", "", regex=False), errors="coerce")
p["rating"] = pd.to_numeric(p["rating"], errors="coerce")                      # one bad value ('|') -> NULL
p["rating_count"] = pd.to_numeric(p["rating_count"].str.replace(",", "", regex=False), errors="coerce")
parts = p["category"].str.split("|")
fix = {"OfficeProducts": "Office Products", "MusicalInstruments": "Musical Instruments",
       "HomeImprovement": "Home Improvement", "Health&PersonalCare": "Health & Personal Care"}
p["main_category"] = parts.str[0].replace(fix).str.replace("&", " & ", regex=False).str.replace("  ", " ")
p["sub_category"] = parts.str[-1]
products = p[["product_id", "product_name", "main_category", "sub_category",
              "actual_price", "discounted_price", "discount_pct", "rating", "rating_count"]]

# ---------------- orders (review-based) ----------------
r = raw[["product_id", "user_id", "review_id"]].copy()
r["user_id"] = r["user_id"].str.split(",")
r["review_id"] = r["review_id"].str.split(",")
r = r.explode(["user_id", "review_id"])
r["user_id"] = r["user_id"].str.strip()
r["review_id"] = r["review_id"].str.strip()
# The same review is often attached to several variants of one product (colour/size listings).
# Count each distinct review once so variants don't create fake repeat purchases.
r = r.drop_duplicates("review_id")
r["customer_id"] = r["user_id"].map(lambda u: "C" + hashlib.sha256(u.encode()).hexdigest()[:10])
orders = r[["customer_id", "product_id"]].reset_index(drop=True)
orders.insert(0, "order_id", range(1, len(orders) + 1))
customers = orders[["customer_id"]].drop_duplicates()

# ---------------- write ----------------
if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
con.executescript("""
CREATE TABLE products (
    product_id       TEXT PRIMARY KEY,
    product_name     TEXT,
    main_category    TEXT,
    sub_category     TEXT,
    actual_price     REAL,      -- list price, INR
    discounted_price REAL,      -- selling price, INR
    discount_pct     REAL,
    rating           REAL,
    rating_count     INTEGER
);
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY          -- hashed reviewer id
);
CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    product_id  TEXT NOT NULL REFERENCES products(product_id)
);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_product  ON orders(product_id);
""")
products.to_sql("products", con, if_exists="append", index=False)
customers.to_sql("customers", con, if_exists="append", index=False)
orders.to_sql("orders", con, if_exists="append", index=False)
con.commit()
for t in ["products", "customers", "orders"]:
    print(t, con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
con.close()
