import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from prophet import Prophet


import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'superstore.db')

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Superstore Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Colour palette ─────────────────────────────────────────────
DARK_BG   = '#0a0e1a'
CARD_BG   = '#141824'
ACCENT    = '#4f8ef7'
ACCENT2   = '#f7914f'
TEXT      = '#e0e0e0'
GRID      = '#1e2436'
POSITIVE  = '#34d399'
NEGATIVE  = '#f87171'

# ── Database connection ────────────────────────────────────────
@st.cache_resource
def get_connection():
    return sqlite3.connect('data/superstore.db', check_same_thread=False)

def query(sql, params=None):
    conn = get_connection()
    if params:
        return pd.read_sql(sql, conn, params=params)
    return pd.read_sql(sql, conn)


# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Superstore")
    st.caption("Sales Analytics Dashboard")
    st.divider()

    st.subheader("Filters")

    years = query("SELECT DISTINCT STRFTIME('%Y', order_date) AS year FROM orders ORDER BY year")
    year_options = ['All Years'] + years['year'].tolist()
    selected_year = st.selectbox('Year', year_options)

    regions = query("SELECT DISTINCT region FROM orders ORDER BY region")
    region_options = ['All Regions'] + regions['region'].tolist()
    selected_region = st.selectbox('Region', region_options)

    segments = query("SELECT DISTINCT segment FROM orders ORDER BY segment")
    segment_options = ['All Segments'] + segments['segment'].tolist()
    selected_segment = st.selectbox('Segment', segment_options)

    st.divider()
    st.caption("Data: Superstore Dataset (2014–2017)\nModel: Prophet Time Series Forecast\nBuilt with Streamlit + Plotly")

# ── Build WHERE clause from filters ───────────────────────────
def build_where(year=None, region=None, segment=None):
    conditions = []
    if year and year != 'All Years':
        conditions.append(f"STRFTIME('%Y', order_date) = '{year}'")
    if region and region != 'All Regions':
        conditions.append(f"region = '{region}'")
    if segment and segment != 'All Segments':
        conditions.append(f"segment = '{segment}'")
    return "WHERE " + " AND ".join(conditions) if conditions else ""

where = build_where(selected_year, selected_region, selected_segment)


# ── Header ─────────────────────────────────────────────────────
st.title("Sales Analytics")
st.caption("Superstore Dataset · 2014–2017 · Interactive BI Dashboard")

# ── KPI Data ───────────────────────────────────────────────────
df_kpi = query(f"""
    SELECT
        ROUND(SUM(sales), 2)                        AS total_sales,
        ROUND(SUM(profit), 2)                       AS total_profit,
        ROUND(SUM(profit)/SUM(sales)*100, 2)        AS margin_pct,
        COUNT(DISTINCT order_id)                    AS total_orders
    FROM orders
    {where}
""")

df_kpi_prev = query(f"""
    SELECT
        ROUND(SUM(sales), 2)                        AS total_sales,
        ROUND(SUM(profit), 2)                       AS total_profit,
        ROUND(SUM(profit)/SUM(sales)*100, 2)        AS margin_pct,
        COUNT(DISTINCT order_id)                    AS total_orders
    FROM orders
    WHERE STRFTIME('%Y', order_date) =
        CAST(CAST(COALESCE(
            NULLIF('{selected_year}', 'All Years'), '2017'
        ) AS INTEGER) - 1 AS TEXT)
""")

total_sales   = df_kpi['total_sales'].iloc[0]
total_profit  = df_kpi['total_profit'].iloc[0]
margin_pct    = df_kpi['margin_pct'].iloc[0]
total_orders  = df_kpi['total_orders'].iloc[0]

prev_sales    = df_kpi_prev['total_sales'].iloc[0]
prev_profit   = df_kpi_prev['total_profit'].iloc[0]
prev_margin   = df_kpi_prev['margin_pct'].iloc[0]
prev_orders   = df_kpi_prev['total_orders'].iloc[0]

def delta(current, previous):
    if previous and previous != 0:
        return round((current - previous) / abs(previous) * 100, 1)
    return None

sales_delta   = delta(total_sales, prev_sales)
profit_delta  = delta(total_profit, prev_profit)
margin_delta  = round(margin_pct - prev_margin, 2) if prev_margin else None
orders_delta  = delta(total_orders, prev_orders)

def fmt_delta(d, is_pp=False):
    if d is None or selected_year == 'All Years':
        return None
    suffix = 'pp' if is_pp else '%'
    return f"{d:+.1f}{suffix} vs prev year"

# ── KPI Cards ─────────────────────────────────────────────────
st.header("Overview", divider="blue")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Sales",
        value=f"${total_sales:,.0f}",
        delta=fmt_delta(sales_delta),
        border=True
    )

with col2:
    st.metric(
        label="Total Profit",
        value=f"${total_profit:,.0f}",
        delta=fmt_delta(profit_delta),
        border=True
    )

with col3:
    st.metric(
        label="Profit Margin",
        value=f"{margin_pct}%",
        delta=fmt_delta(margin_delta, is_pp=True),
        border=True
    )

with col4:
    st.metric(
        label="Total Orders",
        value=f"{total_orders:,}",
        delta=fmt_delta(orders_delta),
        border=True
    )

# ── Section 2: Sales Trends ────────────────────────────────────
st.header("Sales Trends", divider="blue")

col_left, col_right = st.columns(2)

with col_left:
    df_year = query(f"""
        WITH yearly AS (
            SELECT
                STRFTIME('%Y', order_date)               AS year,
                ROUND(SUM(sales), 2)                     AS total_sales,
                ROUND(SUM(profit)/SUM(sales)*100, 2)     AS margin_pct
            FROM orders
            {where}
            GROUP BY year
        )
        SELECT * FROM yearly ORDER BY year
    """)

    fig_year = go.Figure()
    fig_year.add_trace(go.Bar(
        x=df_year['year'],
        y=df_year['total_sales'],
        name='Total Sales',
        marker_color=ACCENT,
        opacity=0.85
    ))
    fig_year.add_trace(go.Scatter(
        x=df_year['year'],
        y=df_year['margin_pct'],
        name='Margin %',
        mode='lines+markers',
        line=dict(color=ACCENT2, width=2.5),
        marker=dict(size=8),
        yaxis='y2'
    ))
    fig_year.update_layout(
        title='Annual Sales & Margin',
        plot_bgcolor=DARK_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT),
        legend=dict(bgcolor=CARD_BG, orientation='h', y=-0.2, x=0.5,
                    xanchor='center', yanchor='bottom'),
        yaxis=dict(gridcolor=GRID, tickformat='$,.0f'),
        yaxis2=dict(overlaying='y', side='right', gridcolor=GRID,
                    ticksuffix='%'),
        xaxis=dict(gridcolor=GRID,type='category'),
        margin=dict(t=40, b=40, l=40, r=40),
        height=350
    )
    st.plotly_chart(fig_year, use_container_width=True)

with col_right:
    df_month = query(f"""
        SELECT
            STRFTIME('%Y-%m', order_date)             AS year_month,
            ROUND(SUM(sales), 2)                      AS total_sales,
            ROUND(SUM(profit)/SUM(sales)*100, 2)      AS margin_pct
        FROM orders
        {where}
        GROUP BY year_month
        ORDER BY year_month
    """)

    fig_month = go.Figure()
    fig_month.add_trace(go.Scatter(
        x=df_month['year_month'],
        y=df_month['total_sales'],
        name='Monthly Sales',
        mode='lines',
        line=dict(color=ACCENT, width=2),
        fill='tozeroy',
        fillcolor='rgba(79, 142, 247, 0.1)'
    ))
    fig_month.update_layout(
        title='Monthly Sales Trend',
        plot_bgcolor=DARK_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT),
        showlegend=False,
        yaxis=dict(gridcolor=GRID, tickformat='$,.0f'),
        xaxis=dict(gridcolor=GRID, tickangle=45,
                   tickmode='array',
                   tickvals=df_month['year_month'][::6]),
        margin=dict(t=40, b=60, l=40, r=40),
        height=350
    )
    st.plotly_chart(fig_month, use_container_width=True)

# ── Section 3: Regional & Category Performance ─────────────────
st.header("Regional & Category Performance", divider="blue")

col_left2, col_right2 = st.columns(2)

with col_left2:
    df_region = query(f"""
        SELECT
            region,
            ROUND(SUM(sales), 2)                     AS total_sales,
            ROUND(SUM(profit)/SUM(sales)*100, 2)     AS margin_pct
        FROM orders
        {where}
        GROUP BY region
        ORDER BY total_sales DESC
    """)

    fig_region = go.Figure()
    fig_region.add_trace(go.Bar(
        x=df_region['total_sales'],
        y=df_region['region'],
        orientation='h',
        marker_color=ACCENT,
        opacity=0.85,
        text=df_region['margin_pct'].apply(lambda x: f'Margin: {x}%'),
        textposition='inside',
        textfont=dict(color='white', size=11)
    ))
    fig_region.update_layout(
        title='Sales by Region',
        plot_bgcolor=DARK_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT),
        showlegend=False,
        xaxis=dict(gridcolor=GRID, tickformat='$,.0f'),
        yaxis=dict(gridcolor=GRID, ticksuffix='  '),
        margin=dict(t=40, b=40, l=40, r=40),
        height=300
    )
    st.plotly_chart(fig_region, use_container_width=True)

with col_right2:
    df_category = query(f"""
        SELECT
            category,
            ROUND(SUM(sales), 2)                     AS total_sales,
            ROUND(SUM(profit)/SUM(sales)*100, 2)     AS margin_pct
        FROM orders
        {where}
        GROUP BY category
        ORDER BY total_sales DESC
    """)

    fig_cat = go.Figure()
    fig_cat.add_trace(go.Bar(
        x=df_category['total_sales'],
        y=df_category['category'],
        orientation='h',
        marker_color=ACCENT,
        opacity=0.85,
        text=df_category['margin_pct'].apply(lambda x: f'Margin: {x}%'),
        textposition='inside',
        textfont=dict(color='white', size=11)
    ))
    fig_cat.update_layout(
        title='Sales by Category',
        plot_bgcolor=DARK_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT),
        showlegend=False,
        xaxis=dict(gridcolor=GRID, tickformat='$,.0f'),
        yaxis=dict(gridcolor=GRID, ticksuffix='  '),
        margin=dict(t=40, b=40, l=40, r=40),
        height=300
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# ── Section 4: Profitability Matrix ───────────────────────────
st.header("Profitability Matrix", divider="blue")

df_discount = query(f"""
    SELECT
        sub_category,
        ROUND(AVG(discount)*100, 1)              AS avg_discount_pct,
        ROUND(SUM(profit)/SUM(sales)*100, 2)     AS margin_pct
    FROM orders
    {where + ' AND sales > 0' if where else 'WHERE sales > 0'}
    GROUP BY sub_category
""")

fig_matrix = go.Figure()
fig_matrix.add_trace(go.Scatter(
    x=df_discount['avg_discount_pct'],
    y=df_discount['margin_pct'],
    mode='markers',
    marker=dict(color=ACCENT, size=10),
    text=df_discount['sub_category'],
    hovertemplate='<b>%{text}</b><br>Discount: %{x}%<br>Margin: %{y}%<extra></extra>'
))

fig_matrix.add_hline(y=0, line=dict(color='white', width=1, dash='dash'))
fig_matrix.add_hline(y=12.47, line=dict(color=ACCENT2, width=1, dash='dot'),
                     annotation_text='Avg Margin',
                     annotation_position='right',
                     annotation_font=dict(color=ACCENT2, size=10))
fig_matrix.add_vline(x=25,
                     line=dict(color='white', width=1, dash='dash'))
fig_matrix.update_layout(
    title='Profitability Matrix — Discount vs Margin by Sub-Category',
    plot_bgcolor=DARK_BG,
    paper_bgcolor=CARD_BG,
    font=dict(color=TEXT),
    xaxis=dict(title='Average Discount %', gridcolor=GRID, ticksuffix='%'),
    yaxis=dict(title='Profit Margin %', gridcolor=GRID, ticksuffix='%'),
    margin=dict(t=40, b=40, l=40, r=40),
    height=450
)
st.plotly_chart(fig_matrix, use_container_width=True)

# ── Section 5: Customer Leaderboard ───────────────────────────
st.header("Customer Leaderboard", divider="blue")

col_top, col_bot = st.columns(2)

with col_top:
    df_top5 = query(f"""
        SELECT customer_name,
               ROUND(SUM(profit), 2) AS total_profit,
               ROUND(SUM(profit)/SUM(sales)*100, 2) AS margin_pct
        FROM orders
        {where}
        GROUP BY customer_name
        ORDER BY total_profit DESC
        LIMIT 5
    """)
    df_top5 = df_top5.sort_values('total_profit', ascending=True)

    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(
        x=df_top5['total_profit'],
        y=df_top5['customer_name'],
        orientation='h',
        marker_color=ACCENT,
        opacity=0.85,
        text=df_top5['margin_pct'].apply(lambda x: f'Margin: {x}%'),
        textposition='inside',
        textfont=dict(color='white', size=10)
    ))
    fig_top.update_layout(
        title='Top 5 Customers by Profit',
        plot_bgcolor=DARK_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT),
        showlegend=False,
        xaxis=dict(gridcolor=GRID, tickformat='$,.0f'),
        yaxis=dict(gridcolor=GRID, ticksuffix='  '),
        margin=dict(t=40, b=40, l=150, r=40),
        height=300
    )
    st.plotly_chart(fig_top, use_container_width=True)

with col_bot:
    df_bot5 = query(f"""
        SELECT customer_name,
               ROUND(SUM(profit), 2) AS total_profit,
               ROUND(SUM(profit)/SUM(sales)*100, 2) AS margin_pct
        FROM orders
        {where}
        GROUP BY customer_name
        ORDER BY total_profit ASC
        LIMIT 5
    """)
    df_bot5 = df_bot5.sort_values('total_profit', ascending=False)

    fig_bot = go.Figure()
    fig_bot.add_trace(go.Bar(
        x=df_bot5['total_profit'],
        y=df_bot5['customer_name'],
        orientation='h',
        marker_color=NEGATIVE,
        opacity=0.85,
        text=df_bot5['margin_pct'].apply(lambda x: f'Margin: {x}%'),
        textposition='inside',
        textfont=dict(color='white', size=10)
    ))
    fig_bot.update_layout(
        title='Bottom 5 Customers by Profit',
        plot_bgcolor=DARK_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT),
        showlegend=False,
        xaxis=dict(gridcolor=GRID, tickformat='$,.0f'),
        yaxis=dict(gridcolor=GRID, ticksuffix='  '),
        margin=dict(t=40, b=40, l=150, r=40),
        height=300
    )
    st.plotly_chart(fig_bot, use_container_width=True)

# ── Section 6: Prophet Forecast ───────────────────────────────
st.header("Sales Forecast — Prophet Model", divider="blue")

@st.cache_data
def run_forecast():
    df_prophet = query("""
        SELECT
            DATE(order_date, 'start of month') AS ds,
            ROUND(SUM(sales), 2)               AS y
        FROM orders
        GROUP BY ds
        ORDER BY ds
    """)
    df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode='multiplicative'
    )
    model.fit(df_prophet)
    future = model.make_future_dataframe(periods=12, freq='MS')
    forecast = model.predict(future)
    return df_prophet, forecast

df_prophet, forecast = run_forecast()

fig_forecast = go.Figure()
fig_forecast.add_trace(go.Scatter(
    x=pd.concat([forecast['ds'], forecast['ds'][::-1]]),
    y=pd.concat([forecast['yhat_upper'], forecast['yhat_lower'][::-1]]),
    fill='toself',
    fillcolor='rgba(79, 142, 247, 0.15)',
    line=dict(color='rgba(255,255,255,0)'),
    name='Confidence Interval'
))
fig_forecast.add_trace(go.Scatter(
    x=df_prophet['ds'],
    y=df_prophet['y'],
    mode='lines+markers',
    name='Actual Sales',
    line=dict(color=ACCENT2, width=2),
    marker=dict(size=4)
))
fig_forecast.add_trace(go.Scatter(
    x=forecast['ds'],
    y=forecast['yhat'],
    mode='lines',
    name='Forecast',
    line=dict(color=ACCENT, width=2, dash='dash')
))
fig_forecast.add_vline(
    x=pd.Timestamp('2018-01-01').timestamp() * 1000,
    line=dict(color='white', width=1, dash='dot'),
    annotation_text='Forecast Start',
    annotation_position='top right',
    annotation_font=dict(color='white', size=10)
)
fig_forecast.update_layout(
    plot_bgcolor=DARK_BG,
    paper_bgcolor=CARD_BG,
    font=dict(color=TEXT),
    legend=dict(bgcolor=CARD_BG, orientation='h', y=-0.15,
                x=0.5, xanchor='center', yanchor='bottom'),
    xaxis=dict(title='Date', gridcolor=GRID),
    yaxis=dict(title='Sales ($)', gridcolor=GRID, tickformat='$,.0f'),
    margin=dict(t=20, b=60, l=40, r=40),
    height=450
)
st.plotly_chart(fig_forecast, use_container_width=True)
