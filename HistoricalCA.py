import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="Dashboard Divisi Credit Analyst",
    layout="wide"
)

# ======================================================
# HOLIDAY CALENDAR
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

HOLIDAYS = set(HOLIDAYS.date)

# ======================================================
# LOAD DATA
# ======================================================
@st.cache_data
def load_data():
    return pd.read_excel("HistoricalCA.xlsx")

df = load_data()

# ======================================================
# SAFE DATE PARSING
# ======================================================
df['Initiation'] = pd.to_datetime(df['Initiation'], errors='coerce', dayfirst=True)
df['action_on'] = pd.to_datetime(df['action_on'], errors='coerce', dayfirst=True)
df = df.dropna(subset=['Initiation','action_on'])

df['Action_Date'] = df['action_on'].dt.date
df['YearMonth'] = df['action_on'].dt.to_period('M').astype(str)

# ======================================================
# OSPH RANGE
# ======================================================
df['OSPH_Range'] = np.select(
    [
        df['Outstanding_PH'] <= 250_000_000,
        df['Outstanding_PH'] <= 500_000_000
    ],
    ['0 - 250 Juta','250 - 500 Juta'],
    default='500 Juta+'
)

# ======================================================
# SCORING (FULL – NO SIMPLIFICATION)
# ======================================================
df['Scoring_Group'] = df['Hasil_Scoring_1'].fillna('-')

def scoring_tier(x):
    if x in ['APPROVE','Approve 1']:
        return 'Low Risk'
    if x in ['Approve 2','Reguler']:
        return 'Medium Risk'
    if x in ['Reguler 1','Reguler 2']:
        return 'High Risk'
    if x in ['Reject','Reject 1','Reject 2']:
        return 'Very High Risk'
    if x == 'Scoring in Progress':
        return 'In Progress'
    return 'Unknown'

df['Scoring_Tier'] = df['Scoring_Group'].apply(scoring_tier)

# ======================================================
# OVD FEATURE
# ======================================================
df['LastOD'] = pd.to_numeric(df['LastOD'], errors='coerce').fillna(0)
df['max_OD'] = pd.to_numeric(df['max_OD'], errors='coerce').fillna(0)

df['OVD_Flag'] = np.select(
    [
        df['max_OD'] == 0,
        df['max_OD'] <= 30,
        df['max_OD'] <= 60,
        df['max_OD'] > 60
    ],
    ['No OVD','OD 1–30','OD 31–60','OD >60'],
    default='Unknown'
)

# ======================================================
# SLA LOGIC
# ======================================================
WORK_START = time(8,30)
WORK_END = time(15,30)

def is_workday(d):
    return d.weekday() < 5 and d not in HOLIDAYS

def next_workday(dt):
    nxt = dt + timedelta(days=1)
    while not is_workday(nxt.date()):
        nxt += timedelta(days=1)
    return nxt.replace(hour=8,minute=30,second=0)

def adjust_start(dt):
    if not is_workday(dt.date()):
        return next_workday(dt)
    if dt.time() > WORK_END:
        return next_workday(dt)
    if dt.time() < WORK_START:
        return dt.replace(hour=8,minute=30,second=0)
    return dt

def calculate_sla(start,end):
    if end <= start:
        return 0
    total = 0
    cur = start
    while cur < end:
        if is_workday(cur.date()):
            ws = cur.replace(hour=8,minute=30)
            we = cur.replace(hour=15,minute=30)
            s = max(cur,ws)
            e = min(end,we)
            if s < e:
                total += (e-s).total_seconds()/3600
        cur = (cur + timedelta(days=1)).replace(hour=0,minute=0)
    return round(total,2)

df['SLA_Start'] = df['Initiation'].apply(adjust_start)
df['SLA_Hours'] = df.apply(lambda x: calculate_sla(x['SLA_Start'],x['action_on']),axis=1)

# ======================================================
# SIDEBAR FILTER
# ======================================================
st.sidebar.title(" Filter")
produk = st.sidebar.multiselect("Produk", sorted(df['Produk'].dropna().unique()))
ca = st.sidebar.multiselect("Nama CA", sorted(df['user_name'].dropna().unique()))
scoring = st.sidebar.multiselect("Scoring Group", sorted(df['Scoring_Group'].unique()))
ovd = st.sidebar.multiselect("OVD Flag", sorted(df['OVD_Flag'].unique()))

date_range = st.sidebar.date_input(
    "Periode Action",
    [df['Action_Date'].min(),df['Action_Date'].max()]
)

fdf = df.copy()
if produk: fdf = fdf[fdf['Produk'].isin(produk)]
if ca: fdf = fdf[fdf['user_name'].isin(ca)]
if scoring: fdf = fdf[fdf['Scoring_Group'].isin(scoring)]
if ovd: fdf = fdf[fdf['OVD_Flag'].isin(ovd)]

fdf = fdf[
    (fdf['Action_Date'] >= date_range[0]) &
    (fdf['Action_Date'] <= date_range[1])
]

# ======================================================
# HEADER
# ======================================================
st.title(" Dashboard ANALYTICAL Divisi Credit Analyst")
st.caption("Risk • Policy • Performance • Early Warning")

# ======================================================
# KPI
# ======================================================
k1,k2,k3,k4 = st.columns(4)
k1.metric("Distinct AppID", fdf['apps_id'].nunique())
k2.metric("Approval Rate (%)",
    f"{(fdf['apps_status'].str.contains('RECOMMENDED',case=False)).mean()*100:.1f}")
k3.metric("Avg SLA (Hours)", f"{fdf['SLA_Hours'].mean():.2f}")
k4.metric("High OVD (%)",
    f"{(fdf['OVD_Flag'].isin(['OD 31–60','OD >60'])).mean()*100:.1f}")

st.divider()

# ======================================================
# MONTHLY TREND
# ======================================================
st.subheader(" Monthly Trend – Volume, Quality & Risk")

monthly = (
    fdf
    .groupby('YearMonth')
    .agg(
        AppID=('apps_id','nunique'),
        ApproveRate=('apps_status',
            lambda x:(x.str.contains('RECOMMENDED',case=False)).mean()*100),
        RejectRate=('apps_status',
            lambda x:(x=='NOT RECOMMENDED CA').mean()*100),
        AvgSLA=('SLA_Hours','mean'),
        AvgOSPH=('Outstanding_PH','mean')
    )
    .reset_index()
)

st.line_chart(monthly.set_index('YearMonth')[['AppID','ApproveRate','RejectRate']])

# ======================================================
# SCORING DETAIL TREND
# ======================================================
st.subheader(" Scoring Distribution Trend (Detail)")

score_trend = (
    fdf.groupby(['YearMonth','Scoring_Group'])['apps_id']
    .nunique().reset_index()
)

st.area_chart(
    score_trend.pivot(
        index='YearMonth',
        columns='Scoring_Group',
        values='apps_id'
    ).fillna(0)
)

# ======================================================
# OVD vs SCORING
# ======================================================
st.subheader(" OVD vs Scoring (Risk Signal)")

ovd_score = (
    fdf.groupby(['OVD_Flag','Scoring_Group'])['apps_id']
    .nunique().reset_index()
)

st.dataframe(ovd_score, use_container_width=True)

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
# AUTO INSIGHT
# ======================================================
st.subheader("🚨 Auto Risk Insights")

high_risk_override = fdf[
    (fdf['OVD_Flag'].isin(['OD 31–60','OD >60'])) &
    (fdf['Scoring_Tier'].isin(['Low Risk','Medium Risk']))
]['apps_id'].nunique()

if high_risk_override > 0:
    st.error(
        f"{high_risk_override} aplikasi dengan OVD >30 hari "
        f"masuk scoring APPROVE / REGULER"
    )

# ======================================================
# FOOTER
# ======================================================
st.caption("Analytical Dashboard Divisi CA | Production Ready")
