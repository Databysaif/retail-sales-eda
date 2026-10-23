"""Run every query in sql/queries.sql against amazon_orders.db and save results/*.csv

Run:  python run_queries.py
"""
import re
import sqlite3

import pandas as pd

con = sqlite3.connect("amazon_orders.db")
text = open("sql/queries.sql", encoding="utf-8").read()
blocks = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)[1:]      # [name, sql, name, sql, ...]

for name, sql in zip(blocks[::2], blocks[1::2]):
    df = pd.read_sql_query(sql, con)
    df.to_csv(f"results/{name}.csv", index=False)
    print(f"\n=== {name}  ({len(df)} rows) ===")
    print(df.to_string(index=False, max_colwidth=45))
