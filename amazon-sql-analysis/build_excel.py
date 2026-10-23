"""Build the Excel summary workbook from the SQL result CSVs in results/.

SQL-sourced numbers are written as values (blue font); shares, averages, totals and the
headline findings are Excel formulas (black font) so they recalculate.

Run:  python build_excel.py      ->  Amazon_Orders_SQL_Summary.xlsx
"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

R = lambda n: pd.read_csv(f"results/{n}.csv")
q01, q02, q03, q04 = R("q01_overview"), R("q02_revenue_by_category"), R("q03_revenue_by_subcategory"), R("q04_order_value_bands")
q05, q06, q08, q09 = R("q05_repeat_vs_one_time"), R("q06_orders_per_customer"), R("q08_cross_category_customers"), R("q09_repeat_customer_categories")
q10, q11, q12, q14 = R("q10_top_products_by_ratings"), R("q11_top_products_by_est_revenue"), R("q12_est_revenue_by_category"), R("q14_discount_vs_ratings")

FONT = "Arial"
NAVY, LIGHT, GREY = "1F3864", "DCE6F1", "F2F2F2"
f_base = Font(name=FONT, size=10)
f_in = Font(name=FONT, size=10, color="0000FF")          # values copied from SQL results
f_bold = Font(name=FONT, size=10, bold=True)
f_head = Font(name=FONT, size=10, bold=True, color="FFFFFF")
f_title = Font(name=FONT, size=16, bold=True, color=NAVY)
f_sec = Font(name=FONT, size=12, bold=True, color=NAVY)
f_note = Font(name=FONT, size=9, italic=True, color="595959")
fill_head = PatternFill("solid", fgColor=NAVY)
fill_tot = PatternFill("solid", fgColor=LIGHT)
fill_kpi = PatternFill("solid", fgColor=GREY)
thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)

INR, PCT, DEC1 = "#,##0", "0.0%", "0.0"

wb = Workbook()
ws_sum = wb.active; ws_sum.title = "Summary"
ws_rev, ws_cus, ws_pro, ws_not = (wb.create_sheet(n) for n in ["Revenue", "Customers", "Products", "Notes"])
for ws in wb.worksheets:
    ws.sheet_view.showGridLines = False


def title(ws, text, note=None):
    ws["A1"] = text; ws["A1"].font = f_title
    if note:
        ws["A2"] = note; ws["A2"].font = f_note


def section(ws, row, text):
    ws.cell(row, 1, text).font = f_sec


def header(ws, row, labels, col=1):
    for i, l in enumerate(labels):
        c = ws.cell(row, col + i, l)
        c.font, c.fill, c.border = f_head, fill_head, box
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 30


def put(ws, row, col, value, fmt=None, sql=False, bold=False, fill=None, wrap=False):
    c = ws.cell(row, col, value)
    c.font = Font(name=FONT, size=10, bold=bold, color="0000FF" if sql else "000000")
    c.border = box
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if wrap:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    return c


def short(n, k=46):
    n = n.strip()
    return n if len(n) <= k else n[:k].rstrip(" ,(-") + "…"


def widths(ws, ws_widths):
    for i, w in enumerate(ws_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def bar(ws, anchor, title_, cats, vals, ytitle, w=16, h=8, horizontal=False, fmt=None, labels=True):
    ch = BarChart(); ch.type = "bar" if horizontal else "col"
    ch.title = title_; ch.style = 10; ch.legend = None
    ch.add_data(vals, titles_from_data=True); ch.set_categories(cats)
    ch.y_axis.title = ytitle; ch.width, ch.height = w, h
    ch.y_axis.delete = False; ch.x_axis.delete = False
    if labels:
        ch.dataLabels = DataLabelList(); ch.dataLabels.showVal = True
        for a in ("showSerName", "showCatName", "showLegendKey", "showPercent"):
            setattr(ch.dataLabels, a, False)
    if fmt:
        ch.y_axis.number_format = fmt
    ch.series[0].graphicalProperties.solidFill = "2E75B6"
    if horizontal:
        ch.x_axis.scaling.orientation = "maxMin"
    ws.add_chart(ch, anchor)


# =====================================================================
# REVENUE sheet
# =====================================================================
ws = ws_rev
title(ws, "Revenue", "Orders = distinct customer reviews (a stand-in for purchases). Revenue = selling price of those items. Blue = values from SQL; black = formulas.")
section(ws, 4, "Overview (query q01)")
header(ws, 5, ["Orders", "Customers", "Products ordered", "Revenue (₹)", "Avg order value (₹)", "Discount given (₹)"])
o = q01.iloc[0]
for i, k in enumerate(["orders", "customers", "products_ordered", "revenue_inr"], 1):
    put(ws, 6, i, int(o[k]), INR, sql=True)
put(ws, 6, 5, "=D6/A6", INR)
put(ws, 6, 6, int(o["discount_given_inr"]), INR, sql=True)

section(ws, 8, "Revenue by main category (query q02)")
header(ws, 9, ["Main category", "Orders", "Customers", "Revenue (₹)", "Revenue share", "Order share", "Avg order value (₹)"])
c0 = 10
for i, r in q02.iterrows():
    row = c0 + i
    put(ws, row, 1, r["main_category"], sql=True)
    put(ws, row, 2, int(r["orders"]), INR, sql=True)
    put(ws, row, 3, int(r["customers"]), INR, sql=True)
    put(ws, row, 4, int(r["revenue_inr"]), INR, sql=True)
    put(ws, row, 5, f"=D{row}/D${c0 + len(q02)}", PCT)
    put(ws, row, 6, f"=B{row}/B${c0 + len(q02)}", PCT)
    put(ws, row, 7, f"=D{row}/B{row}", INR)
cat_last = c0 + len(q02) - 1
tot = cat_last + 1
put(ws, tot, 1, "Total", bold=True, fill=fill_tot)
put(ws, tot, 2, f"=SUM(B{c0}:B{cat_last})", INR, bold=True, fill=fill_tot)
put(ws, tot, 3, "n/a", bold=True, fill=fill_tot)
put(ws, tot, 4, f"=SUM(D{c0}:D{cat_last})", INR, bold=True, fill=fill_tot)
put(ws, tot, 5, f"=SUM(E{c0}:E{cat_last})", PCT, bold=True, fill=fill_tot)
put(ws, tot, 6, f"=SUM(F{c0}:F{cat_last})", PCT, bold=True, fill=fill_tot)
put(ws, tot, 7, f"=D{tot}/B{tot}", INR, bold=True, fill=fill_tot)
ws.cell(tot + 1, 1, "Customers are not additive across categories (one customer can buy in several), so the total is left blank.").font = f_note
REV_CAT = dict(first=c0, last=cat_last, tot=tot)

pb_title = tot + 4
section(ws, pb_title, "Orders by price band (query q04)")
header(ws, pb_title + 1, ["Price band (₹)", "Orders", "Revenue (₹)", "Order share", "Revenue share"])
p0 = pb_title + 2
for i, r in q04.iterrows():
    row = p0 + i
    put(ws, row, 1, r["price_band"][3:], sql=True)
    put(ws, row, 2, int(r["orders"]), INR, sql=True)
    put(ws, row, 3, int(r["revenue_inr"]), INR, sql=True)
    put(ws, row, 4, f"=B{row}/B${p0 + len(q04)}", PCT)
    put(ws, row, 5, f"=C{row}/C${p0 + len(q04)}", PCT)
pb_last = p0 + len(q04) - 1
pbt = pb_last + 1
put(ws, pbt, 1, "Total", bold=True, fill=fill_tot)
put(ws, pbt, 2, f"=SUM(B{p0}:B{pb_last})", INR, bold=True, fill=fill_tot)
put(ws, pbt, 3, f"=SUM(C{p0}:C{pb_last})", INR, bold=True, fill=fill_tot)
put(ws, pbt, 4, f"=SUM(D{p0}:D{pb_last})", PCT, bold=True, fill=fill_tot)
put(ws, pbt, 5, f"=SUM(E{p0}:E{pb_last})", PCT, bold=True, fill=fill_tot)
PB = dict(first=p0, last=pb_last)

sc_title = pbt + 3
section(ws, sc_title, "Top 10 sub-categories by revenue, 30+ orders (query q03)")
header(ws, sc_title + 1, ["Main category", "Sub-category", "Orders", "Revenue (₹)", "Avg order value (₹)"])
s0 = sc_title + 2
for i, r in q03.iterrows():
    row = s0 + i
    put(ws, row, 1, r["main_category"], sql=True)
    put(ws, row, 2, r["sub_category"], sql=True)
    put(ws, row, 3, int(r["orders"]), INR, sql=True)
    put(ws, row, 4, int(r["revenue_inr"]), INR, sql=True)
    put(ws, row, 5, f"=D{row}/C{row}", INR)
widths(ws, [26, 22, 14, 16, 18, 16, 20])
ws.freeze_panes = "A4"

bar(ws, "I4", "Revenue share by main category", Reference(ws, min_col=1, min_row=c0, max_row=c0 + 2),
    Reference(ws, min_col=5, min_row=9, max_row=c0 + 2), "Share of revenue", horizontal=True, fmt="0%")
ws._charts[-1].dataLabels.numFmt = "0.0%"
bar(ws, "I22", "Share of orders vs revenue by price band", Reference(ws, min_col=1, min_row=p0, max_row=pb_last),
    Reference(ws, min_col=5, min_row=pb_title + 1, max_row=pb_last), "Share of revenue", fmt="0%")
ws._charts[-1].dataLabels.numFmt = "0.0%"

# =====================================================================
# CUSTOMERS sheet
# =====================================================================
ws = ws_cus
title(ws, "Customers", "Customer = a reviewer (IDs are hashed). Repeat = 2+ distinct reviews. Customers come from a sample of up to 8 reviews per product, so repeat rates are a floor.")
section(ws, 4, "Repeat vs one-time customers (query q05)")
header(ws, 5, ["Customer type", "Customers", "Orders", "Revenue (₹)", "Customer share", "Order share", "Revenue share", "Avg spend per customer (₹)"])
for i, r in q05.iterrows():
    row = 6 + i
    put(ws, row, 1, r["customer_type"], sql=True)
    put(ws, row, 2, int(r["customers"]), INR, sql=True)
    put(ws, row, 3, int(r["orders"]), INR, sql=True)
    put(ws, row, 4, int(r["revenue_inr"]), INR, sql=True)
    put(ws, row, 5, f"=B{row}/B$8", PCT)
    put(ws, row, 6, f"=C{row}/C$8", PCT)
    put(ws, row, 7, f"=D{row}/D$8", PCT)
    put(ws, row, 8, f"=D{row}/B{row}", INR)
put(ws, 8, 1, "Total", bold=True, fill=fill_tot)
for col, f in ((2, INR), (3, INR), (4, INR)):
    L = get_column_letter(col)
    put(ws, 8, col, f"=SUM({L}6:{L}7)", f, bold=True, fill=fill_tot)
for col in (5, 6, 7):
    L = get_column_letter(col)
    put(ws, 8, col, f"=SUM({L}6:{L}7)", PCT, bold=True, fill=fill_tot)
put(ws, 8, 8, "=D8/B8", INR, bold=True, fill=fill_tot)

section(ws, 11, "Orders per customer (query q06)")
header(ws, 12, ["Orders per customer", "Customers", "Share of customers"])
for i, r in q06.iterrows():
    row = 13 + i
    put(ws, row, 1, int(r["orders_per_customer"]), sql=True)
    put(ws, row, 2, int(r["customers"]), INR, sql=True)
    put(ws, row, 3, f"=B{row}/B${13 + len(q06)}", PCT)
cl = 13 + len(q06) - 1
put(ws, cl + 1, 1, "Total", bold=True, fill=fill_tot)
put(ws, cl + 1, 2, f"=SUM(B13:B{cl})", INR, bold=True, fill=fill_tot)
put(ws, cl + 1, 3, f"=SUM(C13:C{cl})", PCT, bold=True, fill=fill_tot)
OPC = dict(first=13, last=cl)

x = cl + 4
section(ws, x, "Customers buying in 2+ main categories (query q08)")
header(ws, x + 1, ["Cross-category customers", "All customers", "Share"])
put(ws, x + 2, 1, int(q08.iloc[0]["cross_category_customers"]), INR, sql=True)
put(ws, x + 2, 2, "=B8", INR)
put(ws, x + 2, 3, f"=A{x + 2}/B{x + 2}", PCT)
XCAT = x + 2

y = x + 5
section(ws, y, "Where repeat customers buy (query q09)")
header(ws, y + 1, ["Main category", "Orders by repeat customers", "Revenue (₹)", "Revenue share"])
for i, r in q09.iterrows():
    row = y + 2 + i
    put(ws, row, 1, r["main_category"], sql=True)
    put(ws, row, 2, int(r["orders_by_repeat_customers"]), INR, sql=True)
    put(ws, row, 3, int(r["revenue_inr"]), INR, sql=True)
    put(ws, row, 4, f"=C{row}/C${y + 2 + len(q09)}", PCT)
ry = y + 2 + len(q09)
put(ws, ry, 1, "Total", bold=True, fill=fill_tot)
put(ws, ry, 2, f"=SUM(B{y + 2}:B{ry - 1})", INR, bold=True, fill=fill_tot)
put(ws, ry, 3, f"=SUM(C{y + 2}:C{ry - 1})", INR, bold=True, fill=fill_tot)
put(ws, ry, 4, f"=SUM(D{y + 2}:D{ry - 1})", PCT, bold=True, fill=fill_tot)
widths(ws, [30, 22, 16, 16, 16, 16, 16, 24])
ws.freeze_panes = "A4"
bar(ws, "J4", "Customers by number of orders", Reference(ws, min_col=1, min_row=13, max_row=cl),
    Reference(ws, min_col=2, min_row=12, max_row=cl), "Customers", fmt="#,##0")

# =====================================================================
# PRODUCTS sheet
# =====================================================================
ws = ws_pro
title(ws, "Products", "Variants of one product (colour/size) are collapsed to one listing (see Notes). Est. revenue = ratings received x selling price: a rough lower bound, not real sales.")
section(ws, 4, "Top 10 products by ratings received (query q10)")
header(ws, 5, ["#", "Product", "Main category", "Sub-category", "Price (₹)", "Discount %", "Rating", "Ratings received"])
for i, r in q10.iterrows():
    row = 6 + i
    put(ws, row, 1, i + 1)
    put(ws, row, 2, short(r["product_name"]), sql=True)
    put(ws, row, 3, r["main_category"], sql=True)
    put(ws, row, 4, r["sub_category"], sql=True)
    put(ws, row, 5, float(r["discounted_price"]), INR, sql=True)
    put(ws, row, 6, float(r["discount_pct"]) / 100, "0%", sql=True)
    put(ws, row, 7, float(r["rating"]), DEC1, sql=True)
    put(ws, row, 8, int(r["rating_count"]), INR, sql=True)
TOP10_LAST = 6 + len(q10) - 1

a = TOP10_LAST + 3
section(ws, a, "Top 10 products by estimated revenue (query q11)")
header(ws, a + 1, ["#", "Product", "Main category", "Price (₹)", "Rating", "Ratings received", "Est. revenue (₹ crore)"])
for i, r in q11.iterrows():
    row = a + 2 + i
    put(ws, row, 1, i + 1)
    put(ws, row, 2, short(r["product_name"]), sql=True)
    put(ws, row, 3, r["main_category"], sql=True)
    put(ws, row, 4, float(r["discounted_price"]), INR, sql=True)
    put(ws, row, 5, float(r["rating"]), DEC1, sql=True)
    put(ws, row, 6, int(r["rating_count"]), INR, sql=True)
    put(ws, row, 7, f"=D{row}*F{row}/10000000", "#,##0.0")
EST_FIRST = a + 2

b = a + 2 + len(q11) + 2
section(ws, b, "Estimated revenue by main category (query q12)")
header(ws, b + 1, ["Main category", "Product families", "Ratings received", "Est. revenue (₹)", "Est. revenue (₹ crore)", "Est. revenue share"])
for i, r in q12.iterrows():
    row = b + 2 + i
    put(ws, row, 1, r["main_category"], sql=True)
    put(ws, row, 2, int(r["product_families"]), INR, sql=True)
    put(ws, row, 3, int(r["total_ratings"]), INR, sql=True)
    put(ws, row, 4, int(round(r["est_revenue_inr"])), INR, sql=True)
    put(ws, row, 5, f"=D{row}/10000000", "#,##0.0")
    put(ws, row, 6, f"=D{row}/D${b + 2 + len(q12)}", PCT)
EC_FIRST, EC_LAST = b + 2, b + 2 + len(q12) - 1
et = EC_LAST + 1
put(ws, et, 1, "Total", bold=True, fill=fill_tot)
put(ws, et, 2, f"=SUM(B{EC_FIRST}:B{EC_LAST})", INR, bold=True, fill=fill_tot)
put(ws, et, 3, f"=SUM(C{EC_FIRST}:C{EC_LAST})", INR, bold=True, fill=fill_tot)
put(ws, et, 4, f"=SUM(D{EC_FIRST}:D{EC_LAST})", INR, bold=True, fill=fill_tot)
put(ws, et, 5, f"=D{et}/10000000", "#,##0.0", bold=True, fill=fill_tot)
put(ws, et, 6, f"=SUM(F{EC_FIRST}:F{EC_LAST})", PCT, bold=True, fill=fill_tot)

d = et + 3
section(ws, d, "Discount depth vs ratings received (query q14)")
header(ws, d + 1, ["Discount band", "Products", "Avg ratings per product", "Avg rating"])
for i, r in q14.iterrows():
    row = d + 2 + i
    put(ws, row, 1, r["discount_band"][3:], sql=True)
    put(ws, row, 2, int(r["products"]), INR, sql=True)
    put(ws, row, 3, int(r["avg_ratings_per_product"]), INR, sql=True)
    put(ws, row, 4, float(r["avg_rating"]), "0.00", sql=True)
ws.cell(d + 2 + len(q14), 1, "More discount does not clearly mean more ratings: the 30-59% band has the fewest.").font = f_note
widths(ws, [24, 50, 22, 20, 16, 16, 18, 18])
ws.freeze_panes = "A4"
bar(ws, "J4", "Top 10 products by ratings received", Reference(ws, min_col=2, min_row=6, max_row=TOP10_LAST),
    Reference(ws, min_col=8, min_row=5, max_row=TOP10_LAST), "Ratings", w=24, h=11, horizontal=True, fmt="#,##0", labels=False)
bar(ws, "J26", "Estimated revenue share by main category", Reference(ws, min_col=1, min_row=EC_FIRST, max_row=EC_FIRST + 2),
    Reference(ws, min_col=6, min_row=b + 1, max_row=EC_FIRST + 2), "Share", w=16, h=8, fmt="0%")
ws._charts[-1].dataLabels.numFmt = "0.0%"

# =====================================================================
# SUMMARY sheet
# =====================================================================
ws = ws_sum
title(ws, "SQL Analysis of Customer Orders: Amazon India", "Source: Kaggle Amazon Sales Dataset (CC BY-NC-SA 4.0). Orders and revenue are review-based proxies; see Notes before quoting any number.")
section(ws, 4, "Headline numbers")
kpis = [("Orders (reviews)", "=Revenue!A6", INR), ("Customers", "=Revenue!B6", INR), ("Products ordered", "=Revenue!C6", INR),
        ("Revenue (₹ lakh)", "=Revenue!D6/100000", "#,##0"), ("Avg order value (₹)", "=Revenue!E6", INR),
        ("Repeat customers", f"=Customers!E6", PCT)]
for i, (lab, f, fmt) in enumerate(kpis):
    col = 1 + i * 2
    ws.merge_cells(start_row=5, start_column=col, end_row=5, end_column=col + 1)
    ws.merge_cells(start_row=6, start_column=col, end_row=6, end_column=col + 1)
    c = ws.cell(5, col, lab); c.font = Font(name=FONT, size=9, bold=True, color="595959"); c.fill = fill_kpi
    c.alignment = Alignment(horizontal="center")
    c = ws.cell(6, col, f); c.font = Font(name=FONT, size=16, bold=True, color=NAVY); c.fill = fill_kpi
    c.number_format = fmt; c.alignment = Alignment(horizontal="center")
    ws.cell(5, col + 1).fill = fill_kpi; ws.cell(6, col + 1).fill = fill_kpi

section(ws, 8, "Key findings")
c0, cl_ = REV_CAT["first"], REV_CAT["last"]
findings = [
    f'="1. Electronics brings in "&TEXT(Revenue!E{c0},"0.0%")&" of review-based revenue from only "&TEXT(Revenue!F{c0},"0.0%")&" of orders (average order ₹"&TEXT(Revenue!G{c0},"#,##0")&"); Computers & Accessories is "&TEXT(Revenue!F{c0 + 2},"0.0%")&" of orders but only "&TEXT(Revenue!E{c0 + 2},"0.0%")&" of revenue."',
    f'="2. Orders of ₹10,000 or more are just "&TEXT(Revenue!D{PB["last"]},"0.0%")&" of orders but "&TEXT(Revenue!E{PB["last"]},"0.0%")&" of revenue; orders under ₹500 are "&TEXT(Revenue!D{PB["first"]},"0.0%")&" of orders and only "&TEXT(Revenue!E{PB["first"]},"0.0%")&" of revenue."',
    '="3. Repeat customers (2+ orders) are only "&TEXT(Customers!E6,"0.0%")&" of customers and "&TEXT(Customers!G6,"0.0%")&" of revenue, but each spends about "&TEXT(Customers!H6/Customers!H7,"0.0")&"x a one-time customer (₹"&TEXT(Customers!H6,"#,##0")&" vs ₹"&TEXT(Customers!H7,"#,##0")&")."',
    f'="4. Cross-selling is rare: only "&TEXT(Customers!C{XCAT},"0.0%")&" of customers bought from more than one main category."',
    f'="5. The most-rated product is "&LEFT(Products!B6,38)&"... with "&TEXT(Products!H6,"#,##0")&" ratings, and "&COUNTIF(Products!E6:E{TOP10_LAST},"<1300")&" of the top 10 by ratings cost under ₹1,300 (cables, earphones, memory, a kitchen chopper)."',
    f'="6. Weighting by ratings x price instead, Electronics is "&TEXT(Products!F{EC_FIRST},"0.0%")&" of estimated revenue, driven by smartphones and smart TVs."',
]
for i, f in enumerate(findings):
    ws.merge_cells(start_row=9 + i, start_column=1, end_row=9 + i, end_column=12)
    c = ws.cell(9 + i, 1, f); c.font = f_base
    c.alignment = Alignment(wrap_text=True, vertical="top"); ws.row_dimensions[9 + i].height = 30
widths(ws, [14] * 12)

bar(ws, "A17", "Revenue share by main category", Reference(ws_rev, min_col=1, min_row=c0, max_row=c0 + 2),
    Reference(ws_rev, min_col=5, min_row=9, max_row=c0 + 2), "Share of revenue", w=15.5, h=8, fmt="0%")
ws._charts[-1].dataLabels.numFmt = "0.0%"
bar(ws, "G17", "Share of orders vs revenue by price band", Reference(ws_rev, min_col=1, min_row=PB["first"], max_row=PB["last"]),
    Reference(ws_rev, min_col=5, min_row=PB["first"] - 1, max_row=PB["last"]), "Share of revenue", w=15.5, h=8, fmt="0%")
ws._charts[-1].dataLabels.numFmt = "0.0%"

# =====================================================================
# NOTES sheet
# =====================================================================
ws = ws_not
title(ws, "Notes: method and caveats")
notes = [
    ("Data", "Kaggle 'Amazon Sales Dataset' (karkavelrajaj), scraped from Amazon India; CC BY-NC-SA 4.0. 1,351 unique products, each with up to 8 sampled customer reviews."),
    ("What an 'order' is", "The data has no order table. One order = one distinct review (review_id). A review attached to several variants of the same product is counted once. Orders are therefore a sample, capped at ~8 per listing, not real purchases."),
    ("What 'revenue' is", "Selling price of the ordered item, summed over orders. It is a sample-based proxy; absolute amounts are NOT company revenue. Use the shares, not the rupee totals."),
    ("Customers", "A customer is a reviewer. IDs are hashed (SHA-256, truncated) and names and review text are not stored. Because only ~8 reviews per product are present, repeat-customer rates are a floor, not the true rate."),
    ("Estimated revenue", "Ratings received x selling price. Only some buyers leave a rating, so this is a lower bound, and it uses today's price for all past ratings."),
    ("Product families", "Many listings are variants (colour/size) with near-identical rating counts. Listings with 1,000+ ratings are merged when they share sub-category, star rating and rating_count/100. This is an approximation and may occasionally merge unrelated products or miss a variant."),
    ("Colour legend", "Blue = value copied from a SQL query result. Black = Excel formula (shares, averages, totals, headline findings)."),
    ("Rebuild", "python load_db.py -> python run_queries.py -> python build_excel.py. All SQL is in sql/queries.sql."),
]
header(ws, 3, ["Topic", "Note"])
for i, (k, v) in enumerate(notes):
    put(ws, 4 + i, 1, k, bold=True, wrap=True)
    put(ws, 4 + i, 2, v, wrap=True)
    ws.row_dimensions[4 + i].height = 48
widths(ws, [24, 110])

for sh in wb.worksheets:                       # print nicely: landscape, one page wide
    sh.page_setup.orientation = "landscape"
    sh.page_setup.fitToWidth = 1
    sh.page_setup.fitToHeight = 0
    sh.sheet_properties.pageSetUpPr.fitToPage = True

OUT = "Amazon_Orders_SQL_Summary.xlsx"
wb.save(OUT)
print("saved", OUT)
