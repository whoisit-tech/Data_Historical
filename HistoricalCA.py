import streamlit as st
import pandas as pd
import numpy as np
from datetime import time, timedelta

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="Dashboard Divisi CA",
    layout="wide"
)

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
df['action_on'] = pd.to_datetime(df['action_on'])
df['Initiation'] = pd.to_datetime(df['Initiation'])

# ---- OSPH RANGE
df['OSPH_Range'] = np.select(
    [
        df['Outstanding_PH'] <= 250_000_000,
        df['Outstanding_PH'] <= 500_000_000
    ],
    [
        '0 - 250 Juta',
        '250 - 500 Juta'
    ],
    default='500 Juta+'
)

# ---- DATE
df['Action_Date'] = df['action_on'].dt.date

# ======================================================
# SIDEBAR FILTER
# ======================================================
st.sidebar.title("🔎 Filter Dashboard")

produk = st.sidebar.multiselect(
    "Produk",
    sorted(df['Produk'].dropna().unique())
)

ca_name = st.sidebar.multiselect(
    "Nama CA",
    sorted(df['user_name'].dropna().unique())
)

posisi = st.sidebar.multiselect(
    "Posisi",
    sorted(df['position_name'].dropna().unique())
)

osph_range = st.sidebar.multiselect(
    "Range OSPH",
    sorted(df['OSPH_Range'].unique())
)

scoring = st.sidebar.multiselect(
    "Hasil Scoring",
    sorted(df['Hasil_Scoring_1'].dropna().unique())
)

date_range = st.sidebar.date_input(
    "Periode Action",
    [df['Action_Date'].min(), df['Action_Date'].max()]
)

# ---- APPLY FILTER
fdf = df.copy()

if produk:
    fdf = fdf[fdf['Produk'].isin(produk)]
if ca_name:
    fdf = fdf[fdf['user_name'].isin(ca_name)]
if posisi:
    fdf = fdf[fdf['position_name'].isin(posisi)]
if osph_range:
    fdf = fdf[fdf['OSPH_Range'].isin(osph_range)]
if scoring:
    fdf = fdf[fdf['Hasil_Scoring_1'].isin(scoring)]

fdf = fdf[
    (fdf['Action_Date'] >= date_range[0]) &
    (fdf['Action_Date'] <= date_range[1])
]

# ======================================================
# HEADER
# ======================================================
st.title(" Dashboard Historical Divisi Credit Analyst")
st.caption("Analisis CA vs Scoring | Risk Pattern | SLA")

# ======================================================
# KPI SECTION
# ======================================================
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Distinct AppID", fdf['apps_id'].nunique())
c2.metric("Total Records", len(fdf))
c3.metric("Total CA", fdf['user_name'].nunique())

approve_rate = (
    fdf['apps_status']
    .str.contains("APPROVE", case=False, na=False)
    .mean() * 100
)

c4.metric("% Approve", f"{approve_rate:.1f}%")

c5.metric(
    "Avg OSPH (Rp)",
    f"Rp {int(fdf['Outstanding_PH'].mean()):,}".replace(",", ".")
)

st.divider()

# ======================================================
# CA vs SCORING MATRIX
# ======================================================
st.subheader(" CA vs Scoring (History)")

ca_scoring = pd.pivot_table(
    fdf,
    index='Hasil_Scoring_1',
    columns='apps_status',
    values='apps_id',
    aggfunc=pd.Series.nunique,
    fill_value=0
)

st.dataframe(ca_scoring, use_container_width=True)

# ======================================================
# RISK PATTERN ANALYSIS
# ======================================================
st.subheader(" Risk Pattern (Produk → OSPH → Kendaraan → Pekerjaan)")

risk = (
    fdf
    .groupby([
        'Produk',
        'OSPH_Range',
        'JenisKendaraan',
        'Pekerjaan'
    ])['apps_id']
    .nunique()
    .reset_index(name='Distinct AppID')
    .sort_values('Distinct AppID', ascending=False)
)

st.dataframe(risk, use_container_width=True)

# ======================================================
# DISTRIBUSI STATUS
# ======================================================
st.subheader(" Distribusi Keputusan CA")

status_dist = (
    fdf
    .groupby('apps_status')['apps_id']
    .nunique()
    .reset_index(name='Total AppID')
)

st.bar_chart(status_dist.set_index('apps_status'))

# ======================================================
# SLA CALCULATION (DIVISI RULE)
# ======================================================
st.subheader("⏱ SLA CA (Jam Kerja)")

WORK_START = time(8, 30)
WORK_END = time(15, 30)

def adjust_start(dt):
    if dt.time() > WORK_END:
        return (dt + timedelta(days=1)).replace(hour=8, minute=30)
    return dt

fdf['SLA_Start'] = fdf['Initiation'].apply(adjust_start)

fdf['SLA_Hours'] = (
    (fdf['action_on'] - fdf['SLA_Start'])
    .dt.total_seconds() / 3600
)

sla_ca = (
    fdf
    .groupby('user_name')['SLA_Hours']
    .mean()
    .reset_index(name='Avg SLA (Hours)')
    .sort_values('Avg SLA (Hours)')
)

st.dataframe(sla_ca, use_container_width=True)

# ======================================================
# INSIGHT QUICK FLAG
# ======================================================
st.subheader(" Scoring Bagus tapi Ditolak")

anomaly = fdf[
    (fdf['Hasil_Scoring_1'].str.contains("APPROVE|REGULER", case=False, na=False)) &
    (fdf['apps_status'].str.contains("REJECT", case=False, na=False))
]

st.dataframe(
    anomaly[[
        'apps_id','Produk','OSPH_Range',
        'JenisKendaraan','Pekerjaan',
        'Hasil_Scoring_1','apps_status','user_name'
    ]],
    use_container_width=True
)

# ======================================================
# FOOTER
# ======================================================
st.caption("Dashboard Divisi CA | HistoricalCA.xlsx | Streamlit")
