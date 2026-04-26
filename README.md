# Superstore Sales Dashboard

An interactive BI dashboard built on the Kaggle Superstore dataset. 
The goal was to go beyond basic EDA — store the data in SQLite, write 
real SQL queries, build interactive Plotly charts, and deploy a 
professional-looking dashboard on Streamlit.

**Live Demo:** [add your Streamlit URL here]


## What I built

A dark-themed interactive dashboard with filters for year, region, and 
segment — covering sales trends, regional and category performance, 
discount analysis, customer profitability, and a Prophet time series forecast.

Dashboard sections: KPI cards (total sales, profit, margin, orders with 
year-over-year delta), annual bar/line combo chart, monthly seasonality 
line chart, regional and category horizontal bar charts with margin labels, 
a profitability matrix scatter plot with data-driven quadrant lines, 
top 5 and bottom 5 customer leaderboards, and a 12-month Prophet forecast 
with confidence intervals.


## What I found

The margin problem is a discounting problem, not a product problem. The 
business makes 29.5% margin on undiscounted sales. The overall 12.47% 
margin is almost entirely explained by aggressive discounting on specific 
sub-categories. Tables, Bookcases, and Machines all have healthy margins 
at 0% discount — they're just being over-discounted.

The break-even discount threshold is approximately 25%. Below 20% discount 
the business is profitable. Above 30% it's consistently loss-making. The 
business discounts in fixed tiers — 20% is the most common level, used 
across 3,657 transactions. This looks less like a market pricing response 
and more like a default sales rep behaviour.

Central region is the weakest at 7.92% margin vs 14.94% in the West — 
roughly half. Worth investigating whether this is a discounting policy 
issue or a structural cost problem.

Furniture's margin problem is concentrated in two sub-categories. Tables 
(-8.56%) and Bookcases (-3.02%) are loss-making. Furnishings (14.24%) is 
actually healthy. The category average is being dragged down by two 
over-discounted products, not the whole category.

The worst customers aren't bad customers — they're badly managed accounts. 
Cindy Stewart lost the business $6,626 entirely because of a 35% discount 
on Machines and a 70% discount on Binders. The same products sold to Tamara 
Chand (our best customer) at normal discounts generated $8,981 profit. 
This is a sales governance problem, not a customer problem. Someone 
approved a 70% discount on Binders and nobody flagged it.

Clear seasonality in the data — September and November/December spike every 
year without exception. January always drops sharply. The Prophet model 
captures this pattern well and forecasts continued growth into 2018 with 
the same seasonal shape.


## Discount Analysis

This was the most interesting part of the project. The first pass used 
AVG(profit/sales) to calculate margin by sub-category, which showed Binders 
at -20% margin. But this turned out to be misleading — a few heavily 
discounted individual orders were dragging the row-level average into 
negative territory even though the overall product was profitable. 
Switching to SUM(profit)/SUM(sales) gave a completely different picture.

The correct margin calculation showed Binders at +14.86% overall — a 
profitable product being unnecessarily over-discounted at 37.2% average. 
Tables and Bookcases are genuinely loss-making even with the correct 
calculation (-8.56% and -3.02%), but the cause is the same: discounting 
above the break-even threshold.

To find that threshold, I grouped all orders by discount level and 
calculated margin at each level. The margin is positive at 20% discount 
(+11.82%) and negative at 30% (-10.05%), putting the break-even point 
at approximately 25%.

A basket analysis confirmed that Binders is not a loss leader — only 20.9% 
of Binders orders also contained Paper. The overlap is too weak to justify 
selling at a heavy loss.

The volume analysis was the most revealing finding: average quantity per 
order stays almost completely flat regardless of discount level (3.74 units 
at 20% discount vs 3.96 units at 80%). The business is giving away margin 
without getting any meaningful volume increase in return. The discounting 
is not working as intended.


## Why SQLite

Every BI job asks for SQL. Instead of doing everything in pandas, I stored 
the cleaned data in a SQLite database and wrote real queries — CTEs, window 
functions, aggregations, subqueries, and basket analysis. The goal was to 
build SQL muscle, not just get the numbers out.


## Data Cleaning

A few things needed fixing before analysis. Column names had spaces and 
hyphens so everything was renamed to lowercase with underscores for clean 
SQL. order_date and ship_date were loaded as strings and converted to 
datetime. postal_code was read as integer, silently stripping leading zeros 
from 449 New England zip codes — converted to string and restored with 
zfill(5). Nulls were verified three ways: real nulls, empty strings, and 
disguised nulls like 'none' or 'missing'.


## Forecasting

Used Facebook's Prophet for time series forecasting with 
seasonality_mode='multiplicative' — chosen because as overall sales grow, 
the seasonal spikes also grow proportionally, which matches the pattern in 
the data. The model was trained on 2014–2017 monthly sales and forecasts 
12 months ahead.

One honest caveat: Prophet extrapolates patterns it has seen. It can't 
account for external shocks like a new competitor, economic downturn, or 
supply chain issues.


## Tech Stack

Python, pandas, SQLite, SQLAlchemy, Plotly, Prophet, Streamlit.


## Project Structure

\`\`\`
├── data/
│   ├── superstore.csv
│   └── superstore.db
├── Notebook/
│   ├── 01_sales_eda.ipynb
│   └── dashboard.py
└── requirements.txt
\`\`\`


## What's next

RFM customer segmentation — the data shows 6.3 average orders per customer, 
making this viable. Profit margin forecasting alongside sales. Basket 
analysis for more sub-categories beyond Binders and Paper. Investigate 
the root cause of heavy Machines discounting — inventory clearance vs 
sales policy vs competitive pressure.
