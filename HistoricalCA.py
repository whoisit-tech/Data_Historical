import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(page_title="CA Analytics", layout="wide", page_icon="📊")

FILE_NAME = "HistoricalCA.xlsx"

st.markdown("""
<style>
    .insight-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; margin: 10px 0; }
    .warning-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 15px; color: white; margin: 10px 0; }
    .success-card { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 20px; border-radius: 15px; color: white; margin: 10px 0; }
    .info-card { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 20px; border-radius: 15px; color: white; margin: 10px 0; }
    h1 { color: #667eea; text-align: center; }
    h2 { color: #764ba2; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
    .metric-card { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

TANGGAL_MERAH = ["01-01-2025", "27-01-2025", "28-01-2025", "29-01-2025", "28-03-2025", "31-03-2025",
    "01-04-2025", "02-04-2025", "03-04-2025", "04-04-2025", "07-04-2025", "18-04-2025",
    "01-05-2025", "12-05-2025", "29-05-2025", "06-06-2025", "09-06-2025", "27-06-2025",
    "18-08-2025", "05-09-2025", "25-12-2025", "26-12-2025", "31-12-2025"]
TANGGAL_MERAH_DT = [datetime.strptime(d, "%d-%m-%Y").date() for d in TANGGAL_MERAH]

def parse_date(date_str):
    if pd.isna(date_str) or date_str == '-':
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        for fmt in ["%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                return datetime.strptime(str(date_str).split('.')[0], fmt)
            except:
                continue
        return pd.to_datetime(date_str, errors='coerce').to_pydatetime()
    except:
        return None

def is_working_day(date):
    if pd.isna(date):
        return False
    if not isinstance(date, datetime):
        date = pd.to_datetime(date)
    return date.weekday() < 5 and date.date() not in TANGGAL_MERAH_DT

def calculate_sla_days(start_dt, end_dt):
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        
        start_adjusted = start_dt
        if start_dt.time() >= datetime.strptime("15:30", "%H:%M").time():
            start_adjusted = start_dt + timedelta(days=1)
            start_adjusted = start_adjusted.replace(hour=8, minute=30, second=0)
            while not is_working_day(start_adjusted):
                start_adjusted += timedelta(days=1)
        
        working_days = 0
        current = start_adjusted.date()
        end_date = end_dt.date()
        while current <= end_date:
            if is_working_day(datetime.combine(current, datetime.min.time())):
                working_days += 1
            current += timedelta(days=1)
        return working_days
    except:
        return None

def get_osph_category(osph_value):
    try:
        if pd.isna(osph_value):
            return "Unknown"
        osph_value = float(osph_value)
        if osph_value <= 250000000:
            return "0 - 250 Juta"
        elif osph_value <= 500000000:
            return "250 - 500 Juta"
        return "500 Juta+"
    except:
        return "Unknown"

def standardize_case(value_str):
    """Standardize case: convert to proper format, keep original variations"""
    if pd.isna(value_str):
        return "Unknown"
    value_str = str(value_str).strip()
    return value_str

def calculate_risk_score(row):
    score = 0
    if pd.notna(row.get('OSPH_clean')):
        if row['OSPH_clean'] > 500000000:
            score += 30
        elif row['OSPH_clean'] > 250000000:
            score += 20
        else:
            score += 10
    if pd.notna(row.get('LastOD_clean')):
        if row['LastOD_clean'] > 30:
            score += 40
        elif row['LastOD_clean'] > 10:
            score += 25
        elif row['LastOD_clean'] > 0:
            score += 15
    if pd.notna(row.get('SLA_Days')):
        if row['SLA_Days'] > 5:
            score += 20
        elif row['SLA_Days'] > 3:
            score += 10
    return min(score, 100)

def preprocess_data(df):
    df = df.copy()
    
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    if all(c in df.columns for c in ['action_on_parsed', 'RealisasiDate_parsed']):
        df['SLA_Days'] = df.apply(lambda r: calculate_sla_days(r['action_on_parsed'], r['RealisasiDate_parsed']), axis=1)
    
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(df['Outstanding_PH'].astype(str).str.replace(',', ''), errors='coerce')
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    for col in ['LastOD', 'max_OD']:
        if col in df.columns:
            df[f'{col}_clean'] = pd.to_numeric(df[col], errors='coerce')
    
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
    if 'Hasil_Scoring_1' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring_1'].fillna('-').astype(str).str.strip()
    
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Quarter'] = df['action_on_parsed'].dt.quarter
    
    for field in ['desc_status_apps', 'Produk', 'Pekerjaan', 'Jabatan',
                  'Pekerjaan_Pasangan', 'JenisKendaraan', 'branch_name', 'Tujuan_Kredit',
                  'user_name', 'position_name']:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
    df['Risk_Score'] = df.apply(calculate_risk_score, axis=1)
    df['Risk_Category'] = pd.cut(df['Risk_Score'], bins=[0, 30, 60, 100], labels=['Low Risk', 'Medium Risk', 'High Risk'])
    
    return df

@st.cache_data
def load_data():
    try:
        if not Path(FILE_NAME).exists():
            st.error(f"File tidak ditemukan: {FILE_NAME}")
            return None
        df = pd.read_excel(FILE_NAME)
        
        required_cols = ['apps_id', 'position_name', 'user_name', 'apps_status', 'desc_status_apps', 
                        'Produk', 'action_on', 'Initiation', 'RealisasiDate', 'Outstanding_PH', 
                        'Pekerjaan', 'Jabatan', 'Pekerjaan_Pasangan', 'Hasil_Scoring_1', 
                        'JenisKendaraan', 'branch_name', 'Tujuan_Kredit', 'LastOD', 'max_OD']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"Kolom tidak ditemukan: {', '.join(missing)}")
            return None
        
        return preprocess_data(df)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def generate_analytical_insights(df):
    insights = []
    warnings = []
    
    # 1. ANALYTICAL: OSPH vs Approval Rate
    if 'OSPH_Category' in df.columns and 'Scoring_Detail' in df.columns:
        for osph in ['0 - 250 Juta', '250 - 500 Juta', '500 Juta+']:
            df_osph = df[df['OSPH_Category'] == osph]
            if len(df_osph) > 0:
                approve = df_osph['Scoring_Detail'].str.lower().str.contains('approve', na=False).sum()
                total = len(df_osph[df_osph['Scoring_Detail'] != '-'])
                if total > 0:
                    rate = approve / total * 100
                    if rate < 30:
                        warnings.append(f"Low approval rate {rate:.1f}% in {osph} segment")
                    elif rate > 60:
                        insights.append(f"Strong approval rate {rate:.1f}% in {osph} segment")
    
    # 2. ANALYTICAL: LastOD Impact
    if 'LastOD_clean' in df.columns and 'Scoring_Detail' in df.columns:
        high_od = df[df['LastOD_clean'] > 30]
        if len(high_od) > 0:
            reject_rate = high_od['Scoring_Detail'].str.lower().str.contains('reject', na=False).sum() / len(high_od) * 100
            warnings.append(f"High LastOD (>30): {reject_rate:.1f}% rejection rate")
    
    # 3. ANALYTICAL: SLA Monitoring
    if 'SLA_Days' in df.columns and 'apps_status_clean' in df.columns:
        for status in df['apps_status_clean'].unique()[:5]:
            if status == 'Unknown':
                continue
            df_status = df[df['apps_status_clean'] == status]
            sla_avg = df_status['SLA_Days'].mean()
            if pd.notna(sla_avg) and sla_avg > 5:
                warnings.append(f"{status}: Average SLA {sla_avg:.1f} days (above target)")
    
    return insights, warnings

def main():
    st.title("CA Analytics Dashboard")
    st.markdown("Advanced Business Intelligence - Performance Analysis & Monitoring")
    st.markdown("---")
    
    df = load_data()
    if df is None or df.empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    st.success(f"{len(df):,} records | {df['apps_id'].nunique():,} unique applications | {len(df.columns)} fields")
    
    # SIDEBAR
    st.sidebar.title("Analytics Control Panel")
    
    if 'apps_status_clean' in df.columns:
        all_status = sorted([x for x in df['apps_status_clean'].unique() if x != 'Unknown'])
        selected_status = st.sidebar.multiselect("Application Status", all_status, default=all_status)
    else:
        selected_status = []
    
    if 'Scoring_Detail' in df.columns:
        all_scoring = sorted([x for x in df['Scoring_Detail'].unique() if x not in ['', 'nan', '-']])
        selected_scoring = st.sidebar.multiselect("Scoring Result", all_scoring, default=all_scoring)
    else:
        selected_scoring = []
    
    selected_product = st.sidebar.selectbox("Product", ['All'] + sorted(df['Produk_clean'].unique().tolist()) if 'Produk_clean' in df.columns else ['All'])
    selected_branch = st.sidebar.selectbox("Branch", ['All'] + sorted(df['branch_name_clean'].unique().tolist()) if 'branch_name_clean' in df.columns else ['All'])
    selected_ca = st.sidebar.selectbox("CA Name", ['All'] + sorted(df['user_name_clean'].unique().tolist()) if 'user_name_clean' in df.columns else ['All'])
    selected_osph = st.sidebar.selectbox("Outstanding PH", ['All'] + sorted([x for x in df['OSPH_Category'].unique() if x != 'Unknown']) if 'OSPH_Category' in df.columns else ['All'])
    
    df_filtered = df.copy()
    if selected_status:
        df_filtered = df_filtered[df_filtered['apps_status_clean'].isin(selected_status)]
    if selected_scoring:
        df_filtered = df_filtered[df_filtered['Scoring_Detail'].isin(selected_scoring)]
    if selected_product != 'All':
        df_filtered = df_filtered[df_filtered['Produk_clean'] == selected_product]
    if selected_branch != 'All':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    if selected_ca != 'All':
        df_filtered = df_filtered[df_filtered['user_name_clean'] == selected_ca]
    if selected_osph != 'All':
        df_filtered = df_filtered[df_filtered['OSPH_Category'] == selected_osph]
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"{len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f"{df_filtered['apps_id'].nunique():,} unique applications")
    
    # ANALYTICAL INSIGHTS
    st.header("Key Insights & Alerts")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="success-card"><h3>Strategic Insights</h3>', unsafe_allow_html=True)
        if insights:
            for i in insights:
                st.markdown(f"**{i}**")
        else:
            st.markdown("No significant patterns detected")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="warning-card"><h3>Risk Alerts</h3>', unsafe_allow_html=True)
        if warnings:
            for w in warnings:
                st.markdown(f"**{w}**")
        else:
            st.markdown("All metrics within acceptable range")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # KPIs
    st.header("Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        total_apps = df_filtered['apps_id'].nunique()
        st.metric("Total Applications", f"{total_apps:,}")
    
    with kpi2:
        avg_sla = df_filtered['SLA_Days'].mean()
        st.metric("Average SLA (days)", f"{avg_sla:.1f}" if not pd.isna(avg_sla) else "N/A")
    
    with kpi3:
        if 'Scoring_Detail' in df_filtered.columns:
            approve = df_filtered['Scoring_Detail'].str.contains('Approve', case=False, na=False).sum()
            total = len(df_filtered[df_filtered['Scoring_Detail'] != '-'])
            rate = approve / total * 100 if total > 0 else 0
            st.metric("Approval Rate", f"{rate:.1f}%")
    
    with kpi4:
        avg_osph = df_filtered['OSPH_clean'].mean()
        st.metric("Average Outstanding PH", f"Rp {avg_osph/1e6:.0f}M" if not pd.isna(avg_osph) else "N/A")
    
    with kpi5:
        if 'LastOD_clean' in df_filtered.columns:
            avg_last_od = df_filtered['LastOD_clean'].mean()
            st.metric("Average LastOD", f"{avg_last_od:.1f}" if not pd.isna(avg_last_od) else "N/A")
    
    with kpi6:
        if 'max_OD_clean' in df_filtered.columns:
            avg_max_od = df_filtered['max_OD_clean'].mean()
            st.metric("Average max_OD", f"{avg_max_od:.1f}" if not pd.isna(avg_max_od) else "N/A")
    
    st.markdown("---")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Outstanding PH Analysis",
        "OD Impact Analysis",
        "Status & Scoring Matrix",
        "CA Performance",
        "Predictive Patterns",
        "Trends & Forecasting",
        "Duplicate Applications",
        "Raw Data"
    ])
    
    with tab1:
        st.header("Outstanding PH Analysis - 3 Dimensions")
        st.info("Analysis of Outstanding PH from multiple perspectives to identify patterns")
        
        # Dimension 1: OSPH vs Hasil_Scoring
        st.subheader("Dimension 1: Outstanding PH vs Scoring Result")
        st.markdown("**Purpose**: Understand scoring decision patterns across Outstanding PH ranges")
        
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            dim1_data = []
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_o = df_filtered[df_filtered['OSPH_Category'] == osph]
                harga_min = df_o['OSPH_clean'].min() if 'OSPH_clean' in df_o.columns else 0
                harga_max = df_o['OSPH_clean'].max() if 'OSPH_clean' in df_o.columns else 0
                
                row = {
                    'Range': osph,
                    'Min Value': f"Rp {harga_min:,.0f}",
                    'Max Value': f"Rp {harga_max:,.0f}",
                    'Total Apps': df_o['apps_id'].nunique(),
                    '% of Total': f"{df_o['apps_id'].nunique()/df_filtered['apps_id'].nunique()*100:.1f}%",
                    'Total Records': len(df_o)
                }
                
                for scoring in ['-', 'APPROVE', 'REGULER', 'REJECT', 'Scoring in Progress', 'data historical']:
                    count = len(df_o[df_o['Scoring_Detail'] == scoring])
                    if count > 0:
                        row[scoring] = count
                
                dim1_data.append(row)
            
            dim1_df = pd.DataFrame(dim1_data)
            st.dataframe(dim1_df, use_container_width=True, hide_index=True)
            
            # Heatmap
            scoring_cols = [c for c in dim1_df.columns if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', '% of Total', 'Total Records']]
            if scoring_cols:
                heatmap_data = dim1_df[['Range'] + scoring_cols].set_index('Range')
                fig = px.imshow(heatmap_data.T, text_auto=True,
                              title="Outstanding PH vs Scoring Result Distribution",
                              labels=dict(x="Outstanding PH Range", y="Scoring Result", color="Count"),
                              aspect="auto")
                st.plotly_chart(fig, use_container_width=True)
        
        # Dimension 2: OSPH vs Status
        st.markdown("---")
        st.subheader("Dimension 2: Outstanding PH vs Application Status")
        st.markdown("**Purpose**: Distribution of application status across Outstanding PH ranges")
        
        if 'OSPH_Category' in df_filtered.columns and 'apps_status_clean' in df_filtered.columns:
            status_data = []
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_o = df_filtered[df_filtered['OSPH_Category'] == osph]
                row = {'Range': osph, 'Total Apps': df_o['apps_id'].nunique()}
                
                for status in df_filtered['apps_status_clean'].unique():
                    if status != 'Unknown':
                        count = len(df_o[df_o['apps_status_clean'] == status])
                        if count > 0:
                            row[status] = count
                
                status_data.append(row)
            
            status_df = pd.DataFrame(status_data)
            st.dataframe(status_df, use_container_width=True, hide_index=True)
            
            status_cols = [c for c in status_df.columns if c not in ['Range', 'Total Apps']]
            if status_cols:
                heatmap_status = status_df[['Range'] + status_cols].set_index('Range')
                fig = px.imshow(heatmap_status.T, text_auto=True,
                              title="Outstanding PH vs Application Status",
                              labels=dict(x="Outstanding PH Range", y="Application Status", color="Count"),
                              aspect="auto")
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Dimension 3: OSPH vs Job Type
        st.subheader("Dimension 3: Outstanding PH vs Job Type")
        st.markdown("**Purpose**: Occupation profile and approval patterns by Outstanding PH range")
        
        if 'OSPH_Category' in df_filtered.columns and 'Pekerjaan_clean' in df_filtered.columns:
            dim3_data = []
            all_pekerjaan = sorted(df_filtered['Pekerjaan_clean'].unique())
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_o = df_filtered[df_filtered['OSPH_Category'] == osph]
                harga_min = df_o['OSPH_clean'].min() if 'OSPH_clean' in df_o.columns else 0
                harga_max = df_o['OSPH_clean'].max() if 'OSPH_clean' in df_o.columns else 0
                
                row = {
                    'Range': osph,
                    'Min Value': f"Rp {harga_min:,.0f}",
                    'Max Value': f"Rp {harga_max:,.0f}",
                    'Total Apps': df_o['apps_id'].nunique(),
                    'Total Records': len(df_o)
                }
                
                for pekerjaan in all_pekerjaan:
                    if pekerjaan != 'Unknown':
                        count = len(df_o[df_o['Pekerjaan_clean'] == pekerjaan])
                        if count > 0:
                            row[pekerjaan] = count
                
                dim3_data.append(row)
            
            dim3_df = pd.DataFrame(dim3_data)
            st.dataframe(dim3_df, use_container_width=True, hide_index=True)
            
            pekerjaan_cols = [c for c in dim3_df.columns if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', 'Total Records']]
            if pekerjaan_cols:
                fig = px.bar(dim3_df, x='Range', y=pekerjaan_cols[:10],
                           title="Top 10 Job Types by Outstanding PH Range",
                           barmode='stack')
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("OD Impact Analysis - LastOD & max_OD")
        st.info("Analysis of how Overdue Days (OD) impact scoring decisions and risk profiles")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("LastOD Analysis")
            if 'LastOD_clean' in df_filtered.columns:
                df_filtered['LastOD_Category'] = pd.cut(df_filtered['LastOD_clean'],
                                                        bins=[-np.inf, 0, 10, 30, np.inf],
                                                        labels=['0 (No OD)', '1-10 days', '11-30 days', '>30 days'])
                
                lastod_analysis = []
                for cat in ['0 (No OD)', '1-10 days', '11-30 days', '>30 days']:
                    df_od = df_filtered[df_filtered['LastOD_Category'] == cat]
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].str.contains('Approve', case=False, na=False).sum()
                        reject = df_od['Scoring_Detail'].str.contains('Reject', case=False, na=False).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '-'])
                        
                        lastod_analysis.append({
                            'LastOD Range': cat,
                            'Total Apps': df_od['apps_id'].nunique(),
                            'Approve': approve,
                            'Reject': reject,
                            'Approval %': f"{approve/total*100:.1f}%" if total > 0 else "-",
                            'Avg Risk': f"{df_od['Risk_Score'].mean():.1f}"
                        })
                
                lastod_df = pd.DataFrame(lastod_analysis)
                st.dataframe(lastod_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("max_OD Analysis")
            if 'max_OD_clean' in df_filtered.columns:
                df_filtered['maxOD_Category'] = pd.cut(df_filtered['max_OD_clean'],
                                                       bins=[-np.inf, 0, 15, 45, np.inf],
                                                       labels=['0', '1-15 days', '16-45 days', '>45 days'])
                
                maxod_analysis = []
                for cat in ['0', '1-15 days', '16-45 days', '>45 days']:
                    df_od = df_filtered[df_filtered['maxOD_Category'] == cat]
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].str.contains('Approve', case=False, na=False).sum()
                        reject = df_od['Scoring_Detail'].str.contains('Reject', case=False, na=False).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '-'])
                        
                        maxod_analysis.append({
                            'max_OD Range': cat,
                            'Total Apps': df_od['apps_id'].nunique(),
                            'Approve': approve,
                            'Reject': reject,
                            'Approval %': f"{approve/total*100:.1f}%" if total > 0 else "-",
                            'Avg Risk': f"{df_od['Risk_Score'].mean():.1f}"
                        })
                
                maxod_df = pd.DataFrame(maxod_analysis)
                st.dataframe(maxod_df, use_container_width=True, hide_index=True)
        
        # OD Trend Analysis
        st.subheader("OD Trend Analysis: LastOD vs max_OD")
        if 'LastOD_clean' in df_filtered.columns and 'max_OD_clean' in df_filtered.columns:
            df_filtered['OD_Trend'] = df_filtered['LastOD_clean'] - df_filtered['max_OD_clean']
            df_filtered['OD_Trend_Category'] = pd.cut(df_filtered['OD_Trend'],
                                                      bins=[-np.inf, -10, -1, 0, 10, np.inf],
                                                      labels=['Significant Improvement', 'Slight Improvement', 'Stable', 'Slight Worsening', 'Significant Worsening'])
            
            trend_analysis = df_filtered.groupby('OD_Trend_Category').agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (x.str.contains('Approve', case=False, na=False).sum() / len(x[x != '-']) * 100) if len(x[x != '-']) > 0 else 0,
                'Risk_Score': 'mean'
            }).reset_index()
            trend_analysis.columns = ['OD Trend', 'Total Apps', 'Approval %', 'Avg Risk']
            
            st.dataframe(trend_analysis, use_container_width=True, hide_index=True)
            
            fig = px.bar(trend_analysis, x='OD Trend', y='Approval %',
                        color='Avg Risk', title="OD Trend Impact on Approval Rate")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.header("Status & Scoring Matrix")
        st.info("Complete cross-tabulation of application status and scoring results")
        
        st.subheader("Complete Cross-Tabulation Matrix")
        if 'apps_status_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            cross_tab = pd.crosstab(df_filtered['apps_status_clean'],
                                   df_filtered['Scoring_Detail'],
                                   margins=True, margins_name='TOTAL')
            st.dataframe(cross_tab, use_container_width=True)
            
            cross_tab_no_total = cross_tab.drop('TOTAL').drop('TOTAL', axis=1)
            fig = px.imshow(cross_tab_no_total, text_auto=True,
                          title="Application Status vs Scoring Result",
                          labels=dict(x="Scoring Result", y="Application Status", color="Count"),
                          aspect="auto")
            st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Application Status Summary")
            if 'apps_status_clean' in df_filtered.columns:
                status_detail = df_filtered.groupby('apps_status_clean').agg({
                    'apps_id': 'nunique',
                    'SLA_Days': 'mean',
                    'Risk_Score': 'mean'
                }).reset_index()
                status_detail.columns = ['Status', 'Total Apps', 'Avg SLA', 'Avg Risk']
                status_detail = status_detail.sort_values('Total Apps', ascending=False)
                st.dataframe(status_detail, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Scoring Result Summary")
            if 'Scoring_Detail' in df_filtered.columns:
                scoring_detail = df_filtered['Scoring_Detail'].value_counts().reset_index()
                scoring_detail.columns = ['Scoring Result', 'Count']
                scoring_detail['Percentage'] = (scoring_detail['Count'] / len(df_filtered) * 100).round(1)
                st.dataframe(scoring_detail, use_container_width=True, hide_index=True)
    
    with tab4:
        st.header("CA Performance Analytics")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = []
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                approve = df_ca['Scoring_Detail'].str.lower().str.contains('approve', na=False).sum()
                reject = df_ca['Scoring_Detail'].str.lower().str.contains('reject', na=False).sum()
                total_scored = len(df_ca[df_ca['Scoring_Detail'] != '-'])
                
                ca_perf.append({
                    'CA Name': ca,
                    'Total Apps': df_ca['apps_id'].nunique(),
                    'Avg SLA (days)': f"{df_ca['SLA_Days'].mean():.1f}" if df_ca['SLA_Days'].notna().any() else "-",
                    'Approve': approve,
                    'Reject': reject,
                    'Other': total_scored - approve - reject,
                    'Approval %': f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "-",
                    'Avg Risk Score': f"{df_ca['Risk_Score'].mean():.0f}" if df_ca['Risk_Score'].notna().any() else "-"
                })
            
            ca_df = pd.DataFrame(ca_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(ca_df.head(10), x='CA Name', y='Total Apps',
                           title="Top 10 CA by Volume")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                ca_df_plot = ca_df.copy()
                ca_df_plot['Approval_num'] = ca_df_plot['Approval %'].str.replace('%', '').replace('-', '0').astype(float)
                fig = px.scatter(ca_df_plot, x='Total Apps', y='Approval_num',
                               size='Total Apps', hover_data=['CA Name'],
                               title="Volume vs Approval Rate",
                               labels={'Approval_num': 'Approval %'})
                st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.header("Predictive Pattern Recognition")
        st.info("Identification of patterns that predict approval or rejection outcomes")
        
        st.subheader("High-Impact Combinations")
        if all(c in df_filtered.columns for c in ['OSPH_Category', 'LastOD_clean', 'Pekerjaan_clean', 'Scoring_Detail']):
            df_filtered['LastOD_Segment'] = pd.cut(df_filtered['LastOD_clean'],
                                                   bins=[-np.inf, 0, 30, np.inf],
                                                   labels=['No OD', 'OD 1-30', 'OD >30'])
            
            pattern_analysis = df_filtered.groupby(['OSPH_Category', 'LastOD_Segment', 'Pekerjaan_clean']).agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (x.str.lower().str.contains('approve', na=False).sum() / len(x[x != '-']) * 100) if len(x[x != '-']) > 0 else 0,
                'SLA_Days': 'mean'
            }).reset_index()
            pattern_analysis.columns = ['Outstanding PH', 'OD Segment', 'Job Type', 'Total Apps', 'Approval %', 'Avg SLA']
            pattern_analysis = pattern_analysis.sort_values('Total Apps', ascending=False).head(15)
            
            st.dataframe(pattern_analysis, use_container_width=True, hide_index=True)
            
            if len(pattern_analysis) > 0:
                best = pattern_analysis.loc[pattern_analysis['Approval %'].idxmax()]
                worst = pattern_analysis.loc[pattern_analysis['Approval %'].idxmin()]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'<div class="success-card">Best Combination<br>{best["Outstanding PH"]} + {best["OD Segment"]} + {best["Job Type"]}<br>Approval Rate: {best["Approval %"]:.1f}%</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="warning-card">Lowest Performing Combination<br>{worst["Outstanding PH"]} + {worst["OD Segment"]} + {worst["Job Type"]}<br>Approval Rate: {worst["Approval %"]:.1f}%</div>', unsafe_allow_html=True)
    
    with tab6:
        st.header("Trends & Time-Series Analysis")
        
        if 'YearMonth' in df_filtered.columns:
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean',
                'Scoring_Detail': lambda x: (x.str.lower().str.contains('approve', na=False).sum() / len(x[x != '-']) * 100) if len(x[x != '-']) > 0 else 0
            }).reset_index()
            monthly.columns = ['Month', 'Volume', 'Avg SLA', 'Approval %']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=monthly['Month'], y=monthly['Volume'], name="Volume"), secondary_y=False)
            fig.add_trace(go.Scatter(x=monthly['Month'], y=monthly['Approval %'], name="Approval %", mode='lines+markers'), secondary_y=True)
            fig.update_layout(title="Monthly Trend: Volume & Approval Rate", height=500)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab7:
        st.header("Duplicate Applications Analysis")
        st.markdown("**Historical Data Context**: This dataset may contain multiple records for the same application ID due to historical tracking, status updates, or data consolidation processes. This analysis identifies applications appearing more than once.")
        
        if 'apps_id' in df.columns:
            # Count duplicates in original data
            app_counts = df['apps_id'].value_counts()
            duplicates = app_counts[app_counts > 1]
            
            if len(duplicates) > 0:
                st.info(f"Found {len(duplicates)} duplicate application IDs with {duplicates.sum()} total duplicate records")
                
                # Create detailed duplicate table
                duplicate_ids = duplicates.index.tolist()
                dup_records = df[df['apps_id'].isin(duplicate_ids)].sort_values('apps_id')
                
                display_cols = ['apps_id', 'user_name', 'apps_status', 'Scoring_Detail', 'action_on', 'RealisasiDate', 'Outstanding_PH', 'SLA_Days']
                available_cols = [c for c in display_cols if c in dup_records.columns]
                
                st.subheader("Duplicate Application Records")
                st.dataframe(dup_records[available_cols].sort_values('apps_id'), use_container_width=True, height=600)
                
                # Summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Duplicate IDs", len(duplicates))
                with col2:
                    st.metric("Max Records per ID", duplicates.max())
                with col3:
                    st.metric("Total Duplicate Records", duplicates.sum())
                
                # Distribution chart
                st.subheader("Distribution of Duplicate Counts")
                dup_dist = duplicates.value_counts().sort_index()
                fig = px.bar(x=dup_dist.index, y=dup_dist.values,
                           labels={'x': 'Number of Records', 'y': 'Count of Application IDs'},
                           title="How many applications appear N times")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("No duplicate application IDs found in the dataset")
    
    with tab8:
        st.header("Complete Raw Data Export")
        
        display_cols = ['apps_id', 'position_name', 'user_name', 'apps_status', 'desc_status_apps',
                       'Produk', 'action_on', 'Initiation', 'RealisasiDate',
                       'Outstanding_PH', 'Pekerjaan', 'Jabatan', 'Pekerjaan_Pasangan', 
                       'Hasil_Scoring_1', 'JenisKendaraan', 'branch_name', 'Tujuan_Kredit', 
                       'LastOD', 'max_OD', 'OSPH_clean', 'OSPH_Category', 'Scoring_Detail', 
                       'SLA_Days', 'Risk_Score', 'Risk_Category']
        
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        st.dataframe(df_filtered[available_cols], use_container_width=True, height=500)
        
        csv = df_filtered[available_cols].to_csv(index=False).encode('utf-8')
        st.download_button("Download Dataset (CSV)",
                          data=csv,
                          file_name=f"CA_Analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                          mime="text/csv")
    
    st.markdown("---")
    st.markdown(f"<div style='text-align:center;color:#666'>CA Analytics Dashboard | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
