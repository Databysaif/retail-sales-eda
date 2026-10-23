# SQL Analysis of Customer Orders: Amazon India

**Stack:** SQL (SQLite) · Python (load + export) · Excel

Used filtering, joins, `GROUP BY`, aggregate and window functions to answer questions about revenue, repeat customers and top-selling products, and presented the findings in an Excel summary with charts.

📊 **Deliverable:** [`Amazon_Orders_SQL_Summary.xlsx`](Amazon_Orders_SQL_Summary.xlsx), with a Summary sheet (headline numbers, findings, charts), detail sheets for Revenue, Customers and Products, and a Notes sheet.

## Important: what the data can and cannot say

The Kaggle [Amazon Sales Dataset](https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset) (CC BY-NC-SA 4.0) has **no orders table**. It lists ~1,350 products, each with up to 8 sampled customer reviews. So this project builds a *review-based stand-in* for an orders database:

| Concept | How it is defined here |
|---|---|
| **Order** | One distinct review (a review attached to several colour/size variants of one product is counted once) |
| **Customer** | A reviewer; IDs are hashed, names and review text are not stored |
| **Revenue** | Selling price of the ordered items |

Because only ~8 reviews per product are present, **these are sample-based proxies, not real sales**. Use the shares and comparisons, not the rupee totals, and treat repeat-customer rates as a floor. Ratings received (`rating_count`) is used as the real popularity signal for "top-selling" products.

## Database

```
products  (product_id PK, product_name, main_category, sub_category, actual_price,
           discounted_price, discount_pct, rating, rating_count)
customers (customer_id PK)                       -- hashed reviewer id
orders    (order_id PK, customer_id FK, product_id FK)
```

9,269 orders · 9,050 customers · 1,351 products.

## SQL techniques used (all in [`sql/queries.sql`](sql/queries.sql))

| Technique | Where |
|---|---|
| Filtering (`WHERE`, `HAVING`) | q03, q08, q09, q10 |
| Joins (inner, multi-table) | q01–q05, q07–q09 |
| `GROUP BY` + aggregates (`SUM`, `COUNT`, `AVG`, `COUNT DISTINCT`) | nearly all |
| `CASE` bands | q04, q05, q14 |
| CTEs and subqueries | q05, q06, q08–q13 |
| Window functions (`SUM() OVER`, `RANK`, `ROW_NUMBER`) | q02, q04, q05, q10–q13 |

Example: share of revenue from repeat customers.

```sql
WITH customer_orders AS (
    SELECT o.customer_id, COUNT(*) AS orders, SUM(p.discounted_price) AS spend
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    GROUP BY o.customer_id
)
SELECT CASE WHEN orders >= 2 THEN 'Repeat (2+ orders)' ELSE 'One-time (1 order)' END AS customer_type,
       COUNT(*)                                                AS customers,
       ROUND(100.0 * SUM(spend) / SUM(SUM(spend)) OVER (), 1)  AS revenue_share_pct
FROM customer_orders
GROUP BY customer_type;
```

## Key findings

**Revenue**
1. **Electronics earns more per order than its share of orders suggests.** It is 53.7% of review-based revenue from 31.5% of orders (average order ₹4,288). Computers & Accessories is the reverse: 27.4% of orders but only 10.9% of revenue (average order ₹1,004). Home & Kitchen sits in between at 34.9% of revenue.
2. **A few big-ticket items carry the revenue.** Orders of ₹10,000 or more are 5.2% of orders but 44.7% of revenue, while orders under ₹500 are 37.7% of orders and just 4.3% of revenue. Smart TVs alone (287 orders, ₹21.5k average) bring in the most revenue of any sub-category, ahead of smartphones.

**Repeat customers**
3. **Repeat customers are rare in this sample.** 202 customers (2.2%) placed two or more orders, 187 of them exactly two. They account for 4.5% of orders and 4.2% of revenue, but spend about 1.9× a one-time customer (₹4,872 vs ₹2,523).
4. **Cross-selling is almost absent.** Only 107 customers (1.2%) bought from more than one main category, which points to an opportunity to recommend across categories. Among repeat customers, Computers & Accessories has the most orders (159), but Electronics brings the most revenue.

**Top-selling products**
5. **The most-rated products are cheap staples.** Amazon Basics HDMI cable (about 427k ratings), boAt Bassheads earphones (about 364k) and the Redmi 9 Activ phone (about 314k) lead. Nine of the top 10 by ratings cost under ₹1,300.
6. **Revenue and popularity point to different products.** Ranking by ratings × price, the top 10 are all smartphones and smart TVs, and Electronics is 70.4% of estimated revenue. High-volume accessories drive attention, while phones and TVs drive money.
7. **Heavier discounts do not clearly bring more ratings.** Average ratings per product is 18,490 for products under 30% off, 15,608 for 30–59% off and 19,906 for 60%+ off, so there is no consistent pattern. Average star rating drifts down slightly with discount depth (4.16 → 4.09 → 4.04).

## Data handling choices

- **Variants collapsed.** Many listings are colour/size variants with near-identical rating counts. For product rankings, listings with 1,000+ ratings are merged when they share sub-category, star rating and `rating_count/100`; 1,349 rated listings become 1,184 product families. This is an approximation and can occasionally merge unrelated products or miss a variant.
- **Duplicated reviews counted once.** The same review is often attached to several variants; counting each distinct `review_id` once avoids fake repeat purchases (a first pass without this showed 10% repeat customers, the corrected figure is 2.2%).
- **Privacy.** Reviewer IDs are hashed (SHA-256, truncated). Reviewer names, review text and links are not stored or published.
- **Estimated revenue** (ratings × price) is a lower bound: only some buyers rate, and today's price is applied to past ratings.

## How to reproduce

```bash
pip install -r requirements.txt
# download amazon.csv from Kaggle into data/
python load_db.py          # builds amazon_orders.db
python run_queries.py      # runs sql/queries.sql, writes results/*.csv
python build_excel.py      # builds Amazon_Orders_SQL_Summary.xlsx
```

## Project structure

```
├── sql/queries.sql                    # 14 documented queries
├── load_db.py                         # CSV -> SQLite (customers, products, orders)
├── run_queries.py                     # executes the queries, saves results/
├── build_excel.py                     # Excel summary with formulas and charts
├── amazon_orders.db                   # the SQLite database
├── results/                           # one CSV per query + query_output.txt
└── Amazon_Orders_SQL_Summary.xlsx     # the summary / dashboard
```

The raw `amazon.csv` is not committed. Data © the dataset authors, licensed CC BY-NC-SA 4.0; this derived work carries the same licence.
