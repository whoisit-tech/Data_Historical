import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="Dashboard Divisi CA",
    layout="wide"
)

# ======================================================
# HOLIDAY CALENDAR (FIXED)
# ======================================================
HOLIDAYS = pd.to_datetime([
    "01-01-2025","27-01-2025","28-01-2025","29-01-2025",
    "28-03-2025","31-03-2025","01-04-2025","02-04-2025","03-04-2025",
    "04-04-2025","07-04-2025","18-04-2025","01-05-2025","12-05-2025",
    "29-05-2025","06-06-2025","09-06-2025","27-06-2025",
    "18-08-2025","05-09-2025","25-12-2025","26-12-2025","31-12-2025",
    "01-01-2026","02-01-2026","16-01-2026","16-02-2026","17-02-2026",
    "18-03-2026","19-03-2026","20-03-2026","23-03-2026","24-03-2026",
    "03-04-2026","01-05-2026","14-05-2026","27-05-2026","28-05-2026",
    "01-06-2026","16-06-2026","17-08-2026","25-08-2026",
    "25-12-2026","31-12-2026"
], dayfirst=True)

# ======================================================
# LOAD DATA
# ======================================================
@st.cache_data
def load_data():
    df = pd.read_excel("HistoricalCA.xlsx")
    return df

df = load_data()

# ======================================================
# DATA PREPARATION
# ======================================================
df['Initiation'] = pd.to_datetime(df['Initiation'])
df['action_on'] = pd.to_datetime(df['action_on'])
df['Action_Date'] = df['action_on'].dt.date

# ---- OSPH RANGE
df['OSPH_Range'] = np.select(
    [
        df['Outstanding_PH'] <= 250_000_000,
        df['Outstanding_PH'] <= 500_000_000
    ],
    ['0 - 250 Juta', '250 - 500 Juta'],
    default='500 Juta+'
)

# ---- NORMALIZE SCORING
def normalize_scoring(x):
    if pd.isna(x) or x == "-":
        return "-"
    x = x.lower()
    if "approve" in x:
        return "APPROVE"
    if "reguler" in x:
        return "REGULER"
    if "reject" in x:
        return "REJECT"
    if "progress" in x:
        return "SCORING IN PROGRESS"
    return "OTHER"

df['Scoring_Group'] = df['Hasil_Scoring_1'].apply(normalize_scoring)

# ======================================================
# SLA FUNCTIONS
# ======================================================
WORK_START = time(8, 30)
WORK_END = time(15, 30)

def is_workday(d):
    return (
        d.weekday() < 5 and
        pd.to_datetime(d) not in HOLIDAYS
    )

def next_workday(dt):
    nxt = dt + timedelta(days=1)
    while not is_workday(nxt.date()):
        nxt += timedelta(days=1)
    return nxt.replace(hour=8, minute=30)

def adjust_start(dt):
    if not is_workday(dt.date()):
        return next_workday(dt)
    if dt.time() > WORK_END:
        return next_workday(dt)
    if dt.time() < WORK_START:
        return dt.replace(hour=8, minute=30)
    return dt

def calculate_sla(start, end):
    if end <= start:
        return 0

    total_minutes = 0
    current = start

    while current < end:
        if is_workday(current.date()):
            work_start = current.replace(hour=8, minute=30)
            work_end = current.replace(hour=15, minute=30)

            period_start = max(current, work_start)
            period_end = min(end, work_end)

            if period_start < period_end:
                total_minutes += (period_end - period_start).seconds / 60

        current = (current + timedelta(days=1)).replace(hour=0, minute=0)

    return total_minutes / 60

df['SLA_Start'] = df['Initiation'].apply(adjust_start)
df['SLA_Hours'] = df.apply(
    lambda x: calculate_sla(x['SLA_Start'], x['action_on']),
    axis=1
)

# ======================================================
# SIDEBAR FILTER
# ======================================================
st.sidebar.title(" Filter")

produk = st.sidebar.multiselect("Produk", sorted(df['Produk'].dropna().unique()))
ca = st.sidebar.multiselect("Nama CA", sorted(df['user_name'].dropna().unique()))
osph = st.sidebar.multiselect("Range OSPH", sorted(df['OSPH_Range'].unique()))
scoring = st.sidebar.multiselect("Scoring Group", sorted(df['Scoring_Group'].unique()))
status = st.sidebar.multiselect("Status CA", sorted(df['apps_status'].unique()))

date_range = st.sidebar.date_input(
    "Periode Action",
    [df['Action_Date'].min(), df['Action_Date'].max()]
)

fdf = df.copy()
if produk:
    fdf = fdf[fdf['Produk'].isin(produk)]
if ca:
    fdf = fdf[fdf['user_name'].isin(ca)]
if osph:
    fdf = fdf[fdf['OSPH_Range'].isin(osph)]
if scoring:
    fdf = fdf[fdf['Scoring_Group'].isin(scoring)]
if status:
    fdf = fdf[fdf['apps_status'].isin(status)]

fdf = fdf[
    (fdf['Action_Date'] >= date_range[0]) &
    (fdf['Action_Date'] <= date_range[1])
]

# ======================================================
# HEADER
# ======================================================
st.title(" Dashboard Historical Divisi Credit Analyst")
st.caption("SLA exclude weekend & tanggal merah | Jam kerja 08.30–15.30")

# ======================================================
# KPI
# ======================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Distinct AppID", fdf['apps_id'].nunique())
c2.metric("Total Records", len(fdf))
c3.metric("Total CA", fdf['user_name'].nunique())
c4.metric("Avg SLA (Hours)", f"{fdf['SLA_Hours'].mean():.2f}")

st.divider()

# ======================================================
# CA vs SCORING
# ======================================================
st.subheader(" CA vs Scoring")

matrix = pd.pivot_table(
    fdf,
    index='Scoring_Group',
    columns='apps_status',
    values='apps_id',
    aggfunc=pd.Series.nunique,
    fill_value=0
)

st.dataframe(matrix, use_container_width=True)

# ======================================================
# RISK PATTERN
# ======================================================
st.subheader(" Risk Pattern")

risk = (
    fdf
    .groupby(['Produk','OSPH_Range','JenisKendaraan','Pekerjaan'])
    ['apps_id'].nunique()
    .reset_index(name='Distinct AppID')
    .sort_values('Distinct AppID', ascending=False)
)

st.dataframe(risk, use_container_width=True)

# ======================================================
# SLA BY CA
# ======================================================
st.subheader("⏱ SLA per CA")

sla_ca = (
    fdf
    .groupby('user_name')['SLA_Hours']
    .mean()
    .reset_index(name='Avg SLA (Hours)')
    .sort_values('Avg SLA (Hours)')
)

st.dataframe(sla_ca, use_container_width=True)

# ======================================================
# ANOMALY
# ======================================================
st.subheader(" Scoring Approve/Reguler tapi NOT Recommended")

anom = fdf[
    (fdf['Scoring_Group'].isin(['APPROVE','REGULER'])) &
    (fdf['apps_status'] == 'NOT RECOMMENDED CA')
]

st.dataframe(
    anom[['apps_id','Produk','OSPH_Range','Hasil_Scoring_1','apps_status','user_name']],
    use_container_width=True
)

# ======================================================
# FOOTER
# ======================================================
st.caption("Dashboard Divisi CA | HistoricalCA.xlsx | Streamlit")
