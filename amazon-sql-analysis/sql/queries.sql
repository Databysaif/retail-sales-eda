-- =====================================================================
-- SQL Analysis of Customer Orders  (SQLite)
-- Tables: products(…), customers(customer_id), orders(order_id, customer_id, product_id)
-- NOTE: an "order" here is a (reviewer, product) pair, and "revenue" is the selling
--       price of those ordered items, i.e. review-based proxies, not real sales.
-- Each query is separated by a  -- name: <id>  line so run_queries.py can execute it.
-- =====================================================================


-- name: q01_overview
-- Headline numbers (aggregate functions + JOIN)
SELECT
    COUNT(*)                                         AS orders,
    COUNT(DISTINCT o.customer_id)                    AS customers,
    COUNT(DISTINCT o.product_id)                     AS products_ordered,
    ROUND(SUM(p.discounted_price), 0)                AS revenue_inr,
    ROUND(AVG(p.discounted_price), 0)                AS avg_order_value_inr,
    ROUND(SUM(p.actual_price - p.discounted_price), 0) AS discount_given_inr
FROM orders o
JOIN products p ON p.product_id = o.product_id;


-- name: q02_revenue_by_category
-- Revenue and order share by main category (JOIN + GROUP BY + window function)
SELECT
    p.main_category,
    COUNT(*)                                                        AS orders,
    COUNT(DISTINCT o.customer_id)                                   AS customers,
    ROUND(SUM(p.discounted_price), 0)                               AS revenue_inr,
    ROUND(100.0 * SUM(p.discounted_price) / SUM(SUM(p.discounted_price)) OVER (), 1) AS revenue_share_pct,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)              AS order_share_pct,
    ROUND(AVG(p.discounted_price), 0)                               AS avg_order_value_inr
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY p.main_category
ORDER BY revenue_inr DESC;


-- name: q03_revenue_by_subcategory
-- Top 10 sub-categories by revenue (filtering + GROUP BY + HAVING)
SELECT
    p.main_category,
    p.sub_category,
    COUNT(*)                          AS orders,
    ROUND(SUM(p.discounted_price), 0) AS revenue_inr,
    ROUND(AVG(p.discounted_price), 0) AS avg_order_value_inr
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY p.main_category, p.sub_category
HAVING COUNT(*) >= 30
ORDER BY revenue_inr DESC
LIMIT 10;


-- name: q04_order_value_bands
-- Orders by price band (CASE + GROUP BY)
SELECT
    CASE
        WHEN p.discounted_price <  500  THEN '1. Under 500'
        WHEN p.discounted_price <  2000 THEN '2. 500 - 1,999'
        WHEN p.discounted_price <  10000 THEN '3. 2,000 - 9,999'
        ELSE                                 '4. 10,000 and above'
    END                                         AS price_band,
    COUNT(*)                                    AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS order_share_pct,
    ROUND(SUM(p.discounted_price), 0)           AS revenue_inr,
    ROUND(100.0 * SUM(p.discounted_price) / SUM(SUM(p.discounted_price)) OVER (), 1) AS revenue_share_pct
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY price_band
ORDER BY price_band;


-- name: q05_repeat_vs_one_time
-- Repeat customers = 2+ distinct products ordered (CTE + GROUP BY + CASE)
WITH customer_orders AS (
    SELECT o.customer_id,
           COUNT(*)                          AS orders,
           SUM(p.discounted_price)           AS spend
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    GROUP BY o.customer_id
)
SELECT
    CASE WHEN orders >= 2 THEN 'Repeat (2+ orders)' ELSE 'One-time (1 order)' END AS customer_type,
    COUNT(*)                                                         AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS customer_share_pct,
    SUM(orders)                                                      AS orders,
    ROUND(100.0 * SUM(orders) / SUM(SUM(orders)) OVER (), 1)         AS order_share_pct,
    ROUND(SUM(spend), 0)                                             AS revenue_inr,
    ROUND(100.0 * SUM(spend) / SUM(SUM(spend)) OVER (), 1)           AS revenue_share_pct,
    ROUND(AVG(spend), 0)                                             AS avg_spend_per_customer_inr
FROM customer_orders
GROUP BY customer_type
ORDER BY customer_type DESC;


-- name: q06_orders_per_customer
-- Distribution of orders per customer (subquery + GROUP BY)
SELECT orders_per_customer, COUNT(*) AS customers
FROM (SELECT customer_id, COUNT(*) AS orders_per_customer FROM orders GROUP BY customer_id)
GROUP BY orders_per_customer
ORDER BY orders_per_customer;


-- name: q07_top_customers
-- Top 10 customers by spend (hashed IDs) (JOIN + GROUP BY + ORDER BY)
SELECT
    o.customer_id,
    COUNT(*)                          AS orders,
    COUNT(DISTINCT p.main_category)   AS categories,
    ROUND(SUM(p.discounted_price), 0) AS spend_inr
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY o.customer_id
ORDER BY spend_inr DESC
LIMIT 10;


-- name: q08_cross_category_customers
-- Customers buying from 2+ main categories (HAVING + CTE)
WITH multi AS (
    SELECT o.customer_id
    FROM orders o
    JOIN products p ON p.product_id = o.product_id
    GROUP BY o.customer_id
    HAVING COUNT(DISTINCT p.main_category) >= 2
)
SELECT
    (SELECT COUNT(*) FROM multi)                              AS cross_category_customers,
    (SELECT COUNT(*) FROM customers)                          AS all_customers,
    ROUND(100.0 * (SELECT COUNT(*) FROM multi) / (SELECT COUNT(*) FROM customers), 1) AS share_pct;


-- name: q09_repeat_customer_categories
-- Where do repeat customers spend? (self-join via CTE; filtering on repeat set)
WITH repeat_customers AS (
    SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) >= 2
)
SELECT
    p.main_category,
    COUNT(*)                          AS orders_by_repeat_customers,
    ROUND(SUM(p.discounted_price), 0) AS revenue_inr
FROM orders o
JOIN repeat_customers rc ON rc.customer_id = o.customer_id
JOIN products p          ON p.product_id   = o.product_id
GROUP BY p.main_category
ORDER BY revenue_inr DESC;


-- Listings that are variants of one product (colour/size) carry the same rating_count, so the
-- queries below keep ONE listing per product family. Listings with 1,000+ ratings are treated as
-- the same family when they share sub-category, star rating and rating_count/100 (rounded down),
-- since variants differ by only a few ratings. Smaller listings are never merged. This is an
-- approximation: it can occasionally merge two unrelated products or miss a variant.

-- name: q10_top_products_by_ratings
-- Top-selling products, measured by ratings received (rating_count)  (CTE + window function)
WITH fam AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY CASE WHEN rating_count >= 1000 THEN sub_category || '|' || CAST(rating AS TEXT) || '|' || CAST(CAST(rating_count / 100 AS INTEGER) AS TEXT) ELSE product_id END
               ORDER BY rating_count DESC, discounted_price DESC) AS rn
    FROM products
    WHERE rating_count IS NOT NULL
)
SELECT product_name, main_category, sub_category, discounted_price, discount_pct, rating, rating_count
FROM fam
WHERE rn = 1
ORDER BY rating_count DESC
LIMIT 10;


-- name: q11_top_products_by_est_revenue
-- Estimated revenue = ratings received x selling price (a lower-bound proxy: not every buyer rates)
WITH fam AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY CASE WHEN rating_count >= 1000 THEN sub_category || '|' || CAST(rating AS TEXT) || '|' || CAST(CAST(rating_count / 100 AS INTEGER) AS TEXT) ELSE product_id END
               ORDER BY rating_count DESC, discounted_price DESC) AS rn
    FROM products
    WHERE rating_count IS NOT NULL
)
SELECT product_name, main_category, discounted_price, rating, rating_count,
       ROUND(rating_count * discounted_price, 0) AS est_revenue_inr
FROM fam
WHERE rn = 1
ORDER BY est_revenue_inr DESC
LIMIT 10;


-- name: q12_est_revenue_by_category
-- Estimated revenue by category using ratings x price (GROUP BY + window function)
WITH fam AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY CASE WHEN rating_count >= 1000 THEN sub_category || '|' || CAST(rating AS TEXT) || '|' || CAST(CAST(rating_count / 100 AS INTEGER) AS TEXT) ELSE product_id END
               ORDER BY rating_count DESC, discounted_price DESC) AS rn
    FROM products
    WHERE rating_count IS NOT NULL
)
SELECT main_category,
       COUNT(*)                                        AS product_families,
       SUM(rating_count)                               AS total_ratings,
       ROUND(SUM(rating_count * discounted_price), 0)  AS est_revenue_inr,
       ROUND(100.0 * SUM(rating_count * discounted_price) / SUM(SUM(rating_count * discounted_price)) OVER (), 1) AS est_revenue_share_pct
FROM fam
WHERE rn = 1
GROUP BY main_category
ORDER BY est_revenue_inr DESC;


-- name: q13_best_in_each_category
-- Most-rated product family in each main category (window function RANK)
WITH fam AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY CASE WHEN rating_count >= 1000 THEN sub_category || '|' || CAST(rating AS TEXT) || '|' || CAST(CAST(rating_count / 100 AS INTEGER) AS TEXT) ELSE product_id END
               ORDER BY rating_count DESC, discounted_price DESC) AS rn
    FROM products
    WHERE rating_count IS NOT NULL
),
ranked AS (
    SELECT *, RANK() OVER (PARTITION BY main_category ORDER BY rating_count DESC) AS rnk
    FROM fam WHERE rn = 1
)
SELECT main_category, product_name, rating_count, rating, discounted_price
FROM ranked
WHERE rnk = 1
ORDER BY rating_count DESC;


-- name: q14_discount_vs_ratings
-- Do heavily discounted products collect more ratings? (CASE + GROUP BY; median is not available in SQLite, so avg + max)
SELECT
    CASE WHEN discount_pct >= 60 THEN '3. 60%+ off'
         WHEN discount_pct >= 30 THEN '2. 30-59% off'
         ELSE                         '1. Under 30% off' END AS discount_band,
    COUNT(*)                          AS products,
    ROUND(AVG(rating_count), 0)       AS avg_ratings_per_product,
    ROUND(AVG(rating), 2)             AS avg_rating
FROM products
WHERE rating_count IS NOT NULL
GROUP BY discount_band
ORDER BY discount_band;
