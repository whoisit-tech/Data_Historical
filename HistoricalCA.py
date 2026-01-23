# ======================================================
# app.py — FULL Streamlit Dashboard Divisi CA Pro Final
# ======================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import plotly.express as px

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Dashboard Divisi CA Pro Final", layout="wide", initial_sidebar_state="expanded")

# ======================================================
# HOLIDAYS
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
# WORKDAY/SLA FUNCTIONS
# ======================================================
WORK_START = time(8,30)
WORK_END = time(15,30)

def is_workday(d):
    return d.weekday() < 5 and d not in HOLIDAYS

def adjust_start(dt):
    if not is_workday(dt.date()):
        nxt = dt
        while not is_workday(nxt.date()):
            nxt += timedelta(days=1)
        return nxt.replace(hour=8,minute=30,second=0)
    if dt.time() > WORK_END:
        nxt = dt
        while not is_workday(nxt.date()):
            nxt += timedelta(days=1)
        return nxt.replace(hour=8,minute=30,second=0)
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

# ======================================================
# SCORING & OVD FUNCTIONS
# ======================================================
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

def compute_ovd_flag(max_od):
    if max_od == 0:
        return 'No OVD'
    elif max_od <= 30:
        return 'OD 1–30'
    elif max_od <= 60:
        return 'OD 31–60'
    else:
        return 'OD >60'

# ======================================================
# LOAD DATA
# ======================================================
@st.cache_data
def load_data():
    df = pd.read_excel("HistoricalCA.xlsx")
    df['Initiation'] = pd.to_datetime(df['Initiation'], errors='coerce', dayfirst=True)
    df['action_on'] = pd.to_datetime(df['action_on'], errors='coerce', dayfirst=True)
    df = df.dropna(subset=['Initiation','action_on'])
    df['Action_Date'] = df['action_on'].dt.date
    df['YearMonth'] = df['action_on'].dt.to_period('M').astype(str)
    
    df['OSPH_Range'] = np.select(
        [df['Outstanding_PH'] <= 250_000_000,
         df['Outstanding_PH'] <= 500_000_000],
        ['0 - 250 Juta','250 - 500 Juta'],
        default='500 Juta+'
    )
    
    df['Scoring_Group'] = df['Hasil_Scoring_1'].fillna('-')
    df['Scoring_Tier'] = df['Scoring_Group'].apply(scoring_tier)
    
    df['LastOD'] = pd.to_numeric(df['LastOD'], errors='coerce').fillna(0)
    df['max_OD'] = pd.to_numeric(df['max_OD'], errors='coerce').fillna(0)
    df['OVD_Flag'] = df['max_OD'].apply(compute_ovd_flag)
    
    df['SLA_Start'] = df['Initiation'].apply(adjust_start)
    df['SLA_Hours'] = df.apply(lambda x: calculate_sla(x['SLA_Start'],x['action_on']),axis=1)
    
    return df

df = load_data()

# ======================================================
# SIDEBAR FILTER
# ======================================================
st.sidebar.title(" Filter Dashboard Pro")
branch = st.sidebar.multiselect("Branch", sorted(df['Branch'].dropna().unique()))
jenis_kendaraan = st.sidebar.multiselect("Jenis Kendaraan", sorted(df['Jenis_Kendaraan'].dropna().unique()))
produk = st.sidebar.multiselect("Produk", sorted(df['Produk'].dropna().unique()))
ca = st.sidebar.multiselect("Nama CA", sorted(df['user_name'].dropna().unique()))
scoring = st.sidebar.multiselect("Scoring Group", sorted(df['Scoring_Group'].unique()))
apps_status = st.sidebar.multiselect("Apps Status", sorted(df['apps_status'].unique()))
ovd = st.sidebar.multiselect("OVD Flag", sorted(df['OVD_Flag'].unique()))
date_range = st.sidebar.date_input("Periode Action", [df['Action_Date'].min(), df['Action_Date'].max()])

fdf = df.copy()
if branch: fdf = fdf[fdf['Branch'].isin(branch)]
if jenis_kendaraan: fdf = fdf[fdf['Jenis_Kendaraan'].isin(jenis_kendaraan)]
if produk: fdf = fdf[fdf['Produk'].isin(produk)]
if ca: fdf = fdf[fdf['user_name'].isin(ca)]
if scoring: fdf = fdf[fdf['Scoring_Group'].isin(scoring)]
if apps_status: fdf = fdf[fdf['apps_status'].isin(apps_status)]
if ovd: fdf = fdf[fdf['OVD_Flag'].isin(ovd)]
fdf = fdf[(fdf['Action_Date'] >= date_range[0]) & (fdf['Action_Date'] <= date_range[1])]

# ======================================================
# MULTI-PAGE NAVIGATION
# ======================================================
page = st.sidebar.radio("Pilih Halaman", ["Executive Summary","Risk Analysis","Performance","Pivot Table","Raw Data"])

# ======================================================
# EXECUTIVE SUMMARY
# ======================================================
if page == "Executive Summary":
    st.title(" Executive Summary Pro Final")
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Distinct AppID", fdf['apps_id'].nunique())
    k2.metric("Approval Rate (%)", f"{(fdf['apps_status'].str.contains('RECOMMENDED',case=False)).mean()*100:.1f}")
    k3.metric("Avg SLA (Hours)", f"{fdf['SLA_Hours'].mean():.2f}")
    k4.metric("High OVD (%)", f"{(fdf['OVD_Flag'].isin(['OD 31–60','OD >60'])).mean()*100:.1f}")
    
    st.divider()
    
    st.subheader(" Monthly Trend (Interaktif)")
    monthly = fdf.groupby(['YearMonth','Branch','Jenis_Kendaraan']).agg(
        AppID=('apps_id','nunique'),
        ApproveRate=('apps_status', lambda x:(x.str.contains('RECOMMENDED',case=False)).mean()*100),
        RejectRate=('apps_status', lambda x:(x=='NOT RECOMMENDED CA').mean()*100),
        AvgSLA=('SLA_Hours','mean'),
        AvgOSPH=('Outstanding_PH','mean')
    ).reset_index()
    
    fig = px.line(monthly, x='YearMonth', y='AppID', color='Branch', line_dash='Jenis_Kendaraan', title="Trend Bulanan AppID per Branch & Jenis Kendaraan")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader(" Scoring Group Trend")
    score_trend = fdf.groupby(['YearMonth','Branch','Jenis_Kendaraan','Scoring_Group'])['apps_id'].nunique().reset_index()
    pivot_score = score_trend.pivot_table(index='YearMonth',columns='Scoring_Group',values='apps_id',aggfunc='sum').fillna(0)
    fig2 = px.area(pivot_score, x=pivot_score.index, y=pivot_score.columns, title="Trend Scoring per Bulan")
    st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader(" Auto Risk Alerts")
    high_risk_override = fdf[(fdf['OVD_Flag'].isin(['OD 31–60','OD >60'])) &
                             (fdf['Scoring_Tier'].isin(['Low Risk','Medium Risk']))]['apps_id'].nunique()
    if high_risk_override > 0:
        st.warning(f"{high_risk_override} aplikasi dengan OVD >30 hari masuk scoring APPROVE / REGULER")

# ======================================================
# RISK ANALYSIS (Heatmap & Pivot)
# ======================================================
elif page == "Risk Analysis":
    st.title(" Risk Analysis Pro Final")
    st.subheader("OVD vs Scoring Group Heatmap")
    ovd_score = pd.pivot_table(fdf,index='OVD_Flag',columns='Scoring_Group',values='apps_id',aggfunc='nunique',fill_value=0)
    fig3 = px.imshow(ovd_score, text_auto=True, color_continuous_scale='RdYlGn_r', title="OVD vs Scoring Heatmap")
    st.plotly_chart(fig3,use_container_width=True)
    
    st.subheader("CA vs Apps Status Pivot")
    matrix = pd.pivot_table(fdf,index=['Branch','Jenis_Kendaraan','user_name'],columns='apps_status',values='apps_id',aggfunc='nunique',fill_value=0)
    st.dataframe(matrix,use_container_width=True)

# ======================================================
# PERFORMANCE
# ======================================================
elif page == "Performance":
    st.title(" Performance Metrics Pro Final")
    st.subheader("CA SLA vs Reject Rate Quadrant")
    ca_perf = fdf.groupby(['Branch','Jenis_Kendaraan','user_name']).agg(
        AvgSLA=('SLA_Hours','mean'),
        RejectRate=('apps_status', lambda x:(x=='NOT RECOMMENDED CA').mean()*100),
        AppCount=('apps_id','nunique')
    ).reset_index()
    fig4 = px.scatter(ca_perf, x='AvgSLA', y='RejectRate', size='AppCount', color='RejectRate',
                      hover_data=['user_name','Branch','Jenis_Kendaraan'], title="SLA vs Reject Rate Quadrant")
    st.plotly_chart(fig4,use_container_width=True)

# ======================================================
# PIVOT TABLE
# ======================================================
elif page == "Pivot Table":
    st.title(" Pivot Table Pro Final")
    pivot_index = st.multiselect("Row Index", options=['Branch','Jenis_Kendaraan','Produk','Pekerjaan'], default=['Branch','Jenis_Kendaraan'])
    pivot_columns = st.multiselect("Columns", options=['Scoring_Group','apps_status','OVD_Flag'], default=['Scoring_Group','apps_status'])
    pivot_values = st.multiselect("Values", options=['apps_id','SLA_Hours','Outstanding_PH','LastOD','max_OD'], default=['apps_id'])
    
    if pivot_index and pivot_columns and pivot_values:
        pivot_df = pd.pivot_table(
            fdf,
            index=pivot_index,
            columns=pivot_columns,
            values=pivot_values,
            aggfunc={'apps_id':'nunique','SLA_Hours':'mean','Outstanding_PH':'mean','LastOD':'max','max_OD':'max'},
            fill_value=0
        )
        st.dataframe(pivot_df,use_container_width=True)

# ======================================================
# RAW DATA
# ======================================================
elif page == "Raw Data":
    st.title(" Raw Data Pro Final")
    st.dataframe(fdf,use_container_width=True)
    st.download_button("Export Excel", fdf.to_excel(index=False), file_name="RawData_Pro_Final.xlsx")
