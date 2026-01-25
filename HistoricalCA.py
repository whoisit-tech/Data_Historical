import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

# ========== KONFIGURASI ==========
st.set_page_config(page_title="CA Analytics Dashboard", layout="wide", page_icon="📊")

FILE_NAME = "HistoricalCA.xlsx"

# Custom CSS
st.markdown("""
<style>
    .big-font { font-size: 20px !important; font-weight: bold; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px; border-radius: 10px; color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .insight-box {
        background-color: #f0f2f6; padding: 15px; border-radius: 8px;
        border-left: 4px solid #667eea; margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda; padding: 15px; border-radius: 8px;
        border-left: 4px solid #28a745; margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd; padding: 15px; border-radius: 8px;
        border-left: 4px solid #ffc107; margin: 10px 0;
    }
    h1 { color: #667eea; }
    h2 { color: #764ba2; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# Tanggal merah
TANGGAL_MERAH = [
    "01-01-2025", "27-01-2025", "28-01-2025", "29-01-2025", "28-03-2025", "31-03-2025",
    "01-04-2025", "02-04-2025", "03-04-2025", "04-04-2025", "07-04-2025", "18-04-2025",
    "01-05-2025", "12-05-2025", "29-05-2025", "06-06-2025", "09-06-2025", "27-06-2025",
    "18-08-2025", "05-09-2025", "25-12-2025", "26-12-2025", "31-12-2025", "01-01-2026",
    "02-01-2026", "16-01-2026", "16-02-2026", "17-02-2026", "18-03-2026", "19-03-2026",
    "20-03-2026", "23-03-2026", "24-03-2026", "03-04-2026", "01-05-2026", "14-05-2026",
    "27-05-2026", "28-05-2026", "01-06-2026", "16-06-2026", "17-08-2026", "25-08-2026",
    "25-12-2026", "31-12-2026"
]
TANGGAL_MERAH_DT = [datetime.strptime(d, "%d-%m-%Y").date() for d in TANGGAL_MERAH]

# ========== FUNGSI HELPER ==========

def parse_date(date_str):
    if pd.isna(date_str) or date_str == '-' or date_str == '':
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        formats = ["%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).split('.')[0], fmt)
            except:
                continue
        result = pd.to_datetime(date_str, errors='coerce')
        if pd.isna(result):
            return None
        return result.to_pydatetime()
    except:
        return None

def is_working_day(date):
    try:
        if pd.isna(date):
            return False
        if not isinstance(date, datetime):
            date = pd.to_datetime(date)
        if date.weekday() >= 5 or date.date() in TANGGAL_MERAH_DT:
            return False
        return True
    except:
        return False

def calculate_sla_days(start_dt, end_dt):
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        if pd.isna(start_dt) or pd.isna(end_dt):
            return None
        
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
        if pd.isna(osph_value) or osph_value is None:
            return "Unknown"
        osph_value = float(osph_value)
        if osph_value <= 250000000:
            return "0 - 250 Juta"
        elif osph_value <= 500000000:
            return "250 - 500 Juta"
        else:
            return "500 Juta+"
    except:
        return "Unknown"

def preprocess_data(df):
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Calculate SLA
    if 'action_on_parsed' in df.columns and 'RealisasiDate_parsed' in df.columns:
        df['SLA_Days'] = df.apply(
            lambda row: calculate_sla_days(row['action_on_parsed'], row['RealisasiDate_parsed']), axis=1
        )
    
    # Process OSPH
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(df['Outstanding_PH'].astype(str).str.replace(',', ''), errors='coerce')
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    # Process LastOD dan max_OD
    if 'LastOD' in df.columns:
        df['LastOD_clean'] = pd.to_numeric(df['LastOD'], errors='coerce')
    if 'max_OD' in df.columns:
        df['max_OD_clean'] = pd.to_numeric(df['max_OD'], errors='coerce')
    
    # Process Scoring - TIDAK DI-GROUP, semua detail
    if 'Hasil_Scoring_1' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring_1'].fillna('BELUM SCORING').astype(str).str.strip()
        df['Scoring_Detail'] = df['Scoring_Detail'].replace(['-', '', 'data historical'], 'BELUM SCORING')
        df['Is_Scored'] = ~df['Scoring_Detail'].isin(['BELUM SCORING', 'nan'])
    
    # Time features
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['Minute'] = df['action_on_parsed'].dt.minute
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['MonthName'] = df['action_on_parsed'].dt.month_name()
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Date'] = df['action_on_parsed'].dt.date
        df['Year'] = df['action_on_parsed'].dt.year
    
    # Clean all string fields
    string_fields = ['apps_status', 'desc_status_apps', 'Produk', 'Pekerjaan', 'Jabatan', 
                    'Pekerjaan_Pasangan', 'JenisKendaraan', 'branch_name', 'Tujuan_Kredit',
                    'position_name', 'user_name']
    
    for field in string_fields:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
    return df

@st.cache_data
def load_data():
    try:
        if not Path(FILE_NAME).exists():
            st.error(f"❌ File '{FILE_NAME}' tidak ditemukan!")
            return None
        df = pd.read_excel(FILE_NAME)
        df_processed = preprocess_data(df)
        return df_processed
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

# ========== MAIN APP ==========

def main():
    st.title("🎯 Credit Analyst Analytics Dashboard - Complete")
    st.markdown("**Comprehensive Analytics - All Fields Analysis**")
    st.markdown("---")
    
    with st.spinner("Loading data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("❌ Failed to load data")
        st.stop()
    
    st.success(f"✅ Data loaded: {len(df):,} records | {len(df.columns)} columns")
    
    # ========== SIDEBAR FILTERS ==========
    st.sidebar.header("🔍 Filters")
    
    # Filter by Position
    positions = ['All']
    if 'position_name_clean' in df.columns:
        positions += sorted(df['position_name_clean'].unique().tolist())
    selected_position = st.sidebar.selectbox("🎯 Position Name", positions)
    
    # Filter by CA User
    users = ['All']
    if 'user_name_clean' in df.columns:
        users += sorted(df['user_name_clean'].unique().tolist())
    selected_user = st.sidebar.selectbox("👤 User Name (CA)", users)
    
    # Filter by Apps Status
    app_statuses = ['All']
    if 'apps_status_clean' in df.columns:
        app_statuses += sorted(df['apps_status_clean'].unique().tolist())
    selected_app_status = st.sidebar.selectbox("📊 Apps Status", app_statuses)
    
    # Filter by Product
    products = ['All']
    if 'Produk_clean' in df.columns:
        products += sorted(df['Produk_clean'].unique().tolist())
    selected_product = st.sidebar.selectbox("🚗 Produk", products)
    
    # Filter by Branch
    branches = ['All']
    if 'branch_name_clean' in df.columns:
        branches += sorted(df['branch_name_clean'].unique().tolist())
    selected_branch = st.sidebar.selectbox("🏢 Branch", branches)
    
    # Filter by OSPH
    osph_cats = ['All']
    if 'OSPH_Category' in df.columns:
        osph_cats += sorted([x for x in df['OSPH_Category'].unique() if x != 'Unknown'])
    selected_osph = st.sidebar.selectbox("💰 OSPH Range", osph_cats)
    
    # Filter by Scoring Detail
    scorings = ['All']
    if 'Scoring_Detail' in df.columns:
        scorings += sorted([x for x in df['Scoring_Detail'].unique() if x != 'BELUM SCORING'])
    selected_scoring = st.sidebar.selectbox("📋 Hasil Scoring", scorings)
    
    # Filter by Pekerjaan
    pekerjaan_list = ['All']
    if 'Pekerjaan_clean' in df.columns:
        pekerjaan_list += sorted(df['Pekerjaan_clean'].unique().tolist())
    selected_pekerjaan = st.sidebar.selectbox("💼 Pekerjaan", pekerjaan_list)
    
    # Filter by Vehicle Type
    vehicles = ['All']
    if 'JenisKendaraan_clean' in df.columns:
        vehicles += sorted(df['JenisKendaraan_clean'].unique().tolist())
    selected_vehicle = st.sidebar.selectbox("🚙 Jenis Kendaraan", vehicles)
    
    # Date Range
    date_range = None
    if 'action_on_parsed' in df.columns:
        df_dates = df[df['action_on_parsed'].notna()]
        if len(df_dates) > 0:
            min_date = df_dates['action_on_parsed'].min().date()
            max_date = df_dates['action_on_parsed'].max().date()
            date_range = st.sidebar.date_input("📅 Periode", value=(min_date, max_date))
    
    # Apply filters
    df_filtered = df.copy()
    
    if selected_position != 'All':
        df_filtered = df_filtered[df_filtered['position_name_clean'] == selected_position]
    if selected_user != 'All':
        df_filtered = df_filtered[df_filtered['user_name_clean'] == selected_user]
    if selected_app_status != 'All':
        df_filtered = df_filtered[df_filtered['apps_status_clean'] == selected_app_status]
    if selected_product != 'All':
        df_filtered = df_filtered[df_filtered['Produk_clean'] == selected_product]
    if selected_branch != 'All':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    if selected_osph != 'All':
        df_filtered = df_filtered[df_filtered['OSPH_Category'] == selected_osph]
    if selected_scoring != 'All':
        df_filtered = df_filtered[df_filtered['Scoring_Detail'] == selected_scoring]
    if selected_pekerjaan != 'All':
        df_filtered = df_filtered[df_filtered['Pekerjaan_clean'] == selected_pekerjaan]
    if selected_vehicle != 'All':
        df_filtered = df_filtered[df_filtered['JenisKendaraan_clean'] == selected_vehicle]
    
    if date_range and len(date_range) == 2:
        df_filtered = df_filtered[
            (df_filtered['action_on_parsed'].notna()) &
            (df_filtered['action_on_parsed'].dt.date >= date_range[0]) &
            (df_filtered['action_on_parsed'].dt.date <= date_range[1])
        ]
    
    st.info(f"📊 Showing: {len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}% of total)")
    
    # ========== KPI SECTION ==========
    st.header("📊 Key Performance Indicators")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_apps = df_filtered['apps_id'].nunique() if 'apps_id' in df_filtered.columns else 0
        st.metric("📝 Total Apps (Distinct)", f"{total_apps:,}")
    
    with col2:
        total_records = len(df_filtered)
        st.metric("📄 Total Records", f"{total_records:,}")
    
    with col3:
        avg_sla = df_filtered['SLA_Days'].mean() if 'SLA_Days' in df_filtered.columns else 0
        st.metric("⏱️ Avg SLA", f"{avg_sla:.1f}d" if not pd.isna(avg_sla) else "N/A")
    
    with col4:
        total_scored = len(df_filtered[df_filtered['Is_Scored'] == True]) if 'Is_Scored' in df_filtered.columns else 0
        st.metric("✅ Scored", f"{total_scored:,}")
    
    with col5:
        total_ca = df_filtered['user_name'].nunique() if 'user_name' in df_filtered.columns else 0
        st.metric("👥 Total CA", f"{total_ca:,}")
    
    col6, col7, col8, col9, col10 = st.columns(5)
    
    with col6:
        recommended = len(df_filtered[df_filtered['apps_status_clean'].str.contains('RECOMMENDED CA', case=False, na=False)])
        st.metric("👍 Recommended", f"{recommended:,}")
    
    with col7:
        not_recommended = len(df_filtered[df_filtered['apps_status_clean'].str.contains('NOT RECOMMENDED', case=False, na=False)])
        st.metric("❌ Not Recommended", f"{not_recommended:,}")
    
    with col8:
        pending = len(df_filtered[df_filtered['apps_status_clean'].str.contains('PENDING', case=False, na=False)])
        st.metric("⏳ Pending", f"{pending:,}")
    
    with col9:
        avg_osph = df_filtered['OSPH_clean'].mean() if 'OSPH_clean' in df_filtered.columns else 0
        st.metric("💰 Avg OSPH", f"Rp {avg_osph/1e6:.1f}M" if not pd.isna(avg_osph) else "N/A")
    
    with col10:
        avg_lastod = df_filtered['LastOD_clean'].mean() if 'LastOD_clean' in df_filtered.columns else 0
        st.metric("📊 Avg LastOD", f"{avg_lastod:.0f}" if not pd.isna(avg_lastod) else "N/A")
    
    st.markdown("---")
    
    # ========== TABS ==========
    tabs = st.tabs([
        "📋 Apps Status Analysis",
        "📊 Scoring Detail Analysis", 
        "💰 OSPH Breakdown",
        "👥 CA Performance",
        "🚗 Product Analysis",
        "💼 Occupation Analysis",
        "🚙 Vehicle Analysis",
        "🏢 Branch Analysis",
        "📈 Time Analysis",
        "🎯 Tujuan Kredit",
        "📊 OD Analysis",
        "📋 Complete Data"
    ])
    
    # TAB 1: Apps Status Analysis
    with tabs[0]:
        st.header("📋 Apps Status Analysis")
        
        if 'apps_status_clean' in df_filtered.columns:
            status_count = df_filtered['apps_status_clean'].value_counts().reset_index()
            status_count.columns = ['Status', 'Count']
            status_count['%'] = (status_count['Count'] / len(df_filtered) * 100).round(2)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(status_count, values='Count', names='Status', 
                           title="Apps Status Distribution", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(status_count, use_container_width=True, hide_index=True)
            
            # Breakdown by desc_status_apps
            if 'desc_status_apps_clean' in df_filtered.columns:
                st.subheader("Detail by Description Status")
                desc_count = df_filtered.groupby(['apps_status_clean', 'desc_status_apps_clean']).size().reset_index(name='Count')
                desc_count = desc_count.sort_values('Count', ascending=False)
                st.dataframe(desc_count, use_container_width=True, hide_index=True)
    
    # TAB 2: Scoring Detail Analysis
    with tabs[1]:
        st.header("📊 Scoring Detail Analysis (No Grouping)")
        
        if 'Scoring_Detail' in df_filtered.columns:
            scoring_count = df_filtered['Scoring_Detail'].value_counts().reset_index()
            scoring_count.columns = ['Scoring', 'Count']
            scoring_count['%'] = (scoring_count['Count'] / len(df_filtered) * 100).round(2)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(scoring_count, x='Scoring', y='Count', text='Count',
                           title="Hasil Scoring Distribution", color='Count',
                           color_continuous_scale='Viridis')
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(scoring_count, use_container_width=True, hide_index=True)
            
            # Scoring by Product
            if 'Produk_clean' in df_filtered.columns:
                st.subheader("Scoring by Product")
                scoring_prod = df_filtered.groupby(['Produk_clean', 'Scoring_Detail']).size().reset_index(name='Count')
                fig = px.bar(scoring_prod, x='Produk_clean', y='Count', color='Scoring_Detail',
                           title="Scoring Distribution by Product", barmode='stack')
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 3: OSPH Breakdown
    with tabs[2]:
        st.header("💰 OSPH Breakdown Analysis")
        
        if 'OSPH_Category' in df_filtered.columns:
            # Summary by Range
            st.subheader("Summary by OSPH Range")
            
            osph_summary = []
            for osph_range in df_filtered['OSPH_Category'].unique():
                df_range = df_filtered[df_filtered['OSPH_Category'] == osph_range]
                
                osph_summary.append({
                    'Range': osph_range,
                    'Total Apps': df_range['apps_id'].nunique(),
                    'Total Records': len(df_range),
                    'Min OSPH': f"Rp {df_range['OSPH_clean'].min()/1e6:.1f}M" if df_range['OSPH_clean'].notna().any() else '-',
                    'Max OSPH': f"Rp {df_range['OSPH_clean'].max()/1e6:.1f}M" if df_range['OSPH_clean'].notna().any() else '-',
                    'Avg OSPH': f"Rp {df_range['OSPH_clean'].mean()/1e6:.1f}M" if df_range['OSPH_clean'].notna().any() else '-',
                    'APPROVE': len(df_range[df_range['Scoring_Detail'] == 'APPROVE']),
                    'Approve 1': len(df_range[df_range['Scoring_Detail'] == 'Approve 1']),
                    'Approve 2': len(df_range[df_range['Scoring_Detail'] == 'Approve 2']),
                    'Reguler': len(df_range[df_range['Scoring_Detail'] == 'Reguler']),
                    'Reguler 1': len(df_range[df_range['Scoring_Detail'] == 'Reguler 1']),
                    'Reguler 2': len(df_range[df_range['Scoring_Detail'] == 'Reguler 2']),
                    'Reject': len(df_range[df_range['Scoring_Detail'] == 'Reject']),
                    'Reject 1': len(df_range[df_range['Scoring_Detail'] == 'Reject 1']),
                    'Reject 2': len(df_range[df_range['Scoring_Detail'] == 'Reject 2'])
                })
            
            osph_df = pd.DataFrame(osph_summary)
            st.dataframe(osph_df, use_container_width=True, hide_index=True)
            
            # Product → OSPH → Vehicle → Pekerjaan
            st.subheader("Hierarchy: Product → OSPH → Vehicle → Pekerjaan")
            
            if all(col in df_filtered.columns for col in ['Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean']):
                hierarchy = df_filtered.groupby([' Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean']).size().reset_index(name='Count')
                
                fig = px.sunburst(hierarchy, 
                                path=['Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean'],
                                values='Count',
                                title="Complete Hierarchy View")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(hierarchy.sort_values('Count', ascending=False).head(50), 
                           use_container_width=True, hide_index=True)
    
    # TAB 4: CA Performance
    with tabs[3]:
        st.header("👥 CA Performance Analysis")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = []
            for ca in df_filtered['user_name_clean'].unique():
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                position = df_ca['position_name_clean'].mode()[0] if 'position_name_clean' in df_ca.columns and len(df_ca) > 0 else 'Unknown'
                
                ca_perf.append({
                    'CA Name': ca,
                    'Position': position,
                    'Total Apps': df_ca['apps_id'].nunique(),
                    'Total Records': len(df_ca),
                    'Avg SLA': df_ca['SLA_Days'].mean() if 'SLA_Days' in df_ca.columns else 0,
                    'APPROVE': len(df_ca[df_ca['Scoring_Detail'] == 'APPROVE']),
                    'Approve 1': len(df_ca[df_ca['Scoring_Detail'] == 'Approve 1']),
                    'Approve 2': len(df_ca[df_ca['Scoring_Detail'] == 'Approve 2']),
                    'Reguler': len(df_ca[df_ca['Scoring_Detail'] == 'Reguler']),
                    'Reguler 1': len(df_ca[df_ca['Scoring_Detail'] == 'Reguler 1']),
                    'Reguler 2': len(df_ca[df_ca['Scoring_Detail'] == 'Reguler 2']),
                    'Reject': len(df_ca[df_ca['Scoring_Detail'] == 'Reject']),
                    'Reject 1': len(df_ca[df_ca['Scoring_Detail'] == 'Reject 1']),
                    'Reject 2': len(df_ca[df_ca['Scoring_Detail'] == 'Reject 2']),
                    'Scoring Progress': len(df_ca[df_ca['Scoring_Detail'] == 'Scoring in Progress']),
                    'Belum Scoring': len(df_ca[df_ca['Scoring_Detail'] == 'BELUM SCORING'])
                })
            
            ca_df = pd.DataFrame(ca_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(ca_df.head(10), x='CA Name', y='Total Apps',
                           title="Top 10 CA by Volume", color='Total Apps')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.scatter(ca_df, x='Avg SLA', y='APPROVE', size='Total Apps',
                               hover_data=['CA Name'], title="SLA vs Approval")
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 5: Product Analysis
    with tabs[4]:
        st.header("🚗 Product Analysis")
        
        if 'Produk_clean' in df_filtered.columns:
            prod_analysis = []
            for prod in df_filtered['Produk_clean'].unique():
                df_prod = df_filtered[df_filtered['Produk_clean'] == prod]
                
                prod_analysis.append({
                    'Product': prod,
                    'Total Apps': df_prod['apps_id'].nunique(),
                    'Total Records': len(df_prod),
                    'Avg OSPH': f"Rp {df_prod['OSPH_clean'].mean()/1e6:.1f}M" if 'OSPH_clean' in df_prod.columns else '-',
                    'Avg SLA': f"{df_prod['SLA_Days'].mean():.1f}" if 'SLA_Days' in df_prod.columns else '-',
                    'Recommended': len(df_prod[df_prod['apps_status_clean'].str.contains('RECOMMENDED CA', na=False)]),
                    'Not Recommended': len(df_prod[df_prod['apps_status_clean'].str.contains('NOT RECOMMENDED', na=False)]),
                    'APPROVE': len(df_prod[df_prod['Scoring_Detail'] == 'APPROVE']),
                    'Reguler': len(df_prod[df_prod['Scoring_Detail'].str.contains('Reguler', na=False)]),
                    'Reject': len(df_prod[df_prod['Scoring_Detail'].str.contains('Reject', na=False)])
                })
            
            prod_df = pd.DataFrame(prod_analysis)
            st.dataframe(prod_df, use_container_width=True, hide_index=True)
    
    # TAB 6: Occupation Analysis
    with tabs[5]:
        st.header("💼 Occupation Analysis")
        
        if 'Pekerjaan_clean' in df_filtered.columns:
            pek_count = df_filtered['Pekerjaan_clean'].value_counts().reset_index()
            pek_count.columns = ['Pekerjaan', 'Count']
            pek_count['%'] = (pek_count['Count'] / len(df_filtered) * 100).round(2)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(pek_count.head(15), x='Pekerjaan', y='Count',
                           title="Top 15 Pekerjaan", color='Count')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(pek_count, use_container_width=True, hide_index=True)
            
            # Pekerjaan vs Jabatan
            if 'Jabatan_clean' in df_filtered.columns:
                st.subheader("Pekerjaan vs Jabatan")
                pek_jab = df_filtered.groupby(['Pekerjaan_clean', 'Jabatan_clean']).size().reset_index(name='Count')
                pek_jab = pek_jab.sort_values('Count', ascending=False).head(30)
                st.dataframe(pek_jab, use_container_width=True, hide_index=True)
            
            # Pekerjaan Pasangan
            if 'Pekerjaan_Pasangan_clean' in df_filtered.columns:
                st.subheader("Pekerjaan Pasangan Distribution")
                pek_pasangan = df_filtered['Pekerjaan_Pasangan_clean'].value_counts().reset_index()
                pek_pasangan.columns = ['Pekerjaan Pasangan', 'Count']
                fig = px.pie(pek_pasangan.head(10), values='Count', names='Pekerjaan Pasangan',
                           title="Top 10 Pekerjaan Pasangan", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 7: Vehicle Analysis
    with tabs[6]:
        st.header("🚙 Vehicle Type Analysis")
        
        if 'JenisKendaraan_clean' in df_filtered.columns:
            vehicle_count = df_filtered['JenisKendaraan_clean'].value_counts().reset_index()
            vehicle_count.columns = ['Jenis Kendaraan', 'Count']
            vehicle_count['%'] = (vehicle_count['Count'] / len(df_filtered) * 100).round(2)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(vehicle_count, values='Count', names='Jenis Kendaraan',
                           title="Vehicle Type Distribution")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(vehicle_count, use_container_width=True, hide_index=True)
            
            # Vehicle by Product
            if 'Produk_clean' in df_filtered.columns:
                st.subheader("Vehicle Type by Product")
                veh_prod = df_filtered.groupby(['Produk_clean', 'JenisKendaraan_clean']).size().reset_index(name='Count')
                fig = px.bar(veh_prod, x='JenisKendaraan_clean', y='Count', color='Produk_clean',
                           title="Vehicle Distribution by Product", barmode='group')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 8: Branch Analysis
    with tabs[7]:
        st.header("🏢 Branch Performance Analysis")
        
        if 'branch_name_clean' in df_filtered.columns:
            branch_perf = []
            for branch in df_filtered['branch_name_clean'].unique():
                df_branch = df_filtered[df_filtered['branch_name_clean'] == branch]
                
                branch_perf.append({
                    'Branch': branch,
                    'Total Apps': df_branch['apps_id'].nunique(),
                    'Total Records': len(df_branch),
                    'Avg SLA': df_branch['SLA_Days'].mean() if 'SLA_Days' in df_branch.columns else 0,
                    'Avg OSPH': df_branch['OSPH_clean'].mean() if 'OSPH_clean' in df_branch.columns else 0,
                    'APPROVE': len(df_branch[df_branch['Scoring_Detail'] == 'APPROVE']),
                    'Reguler': len(df_branch[df_branch['Scoring_Detail'].str.contains('Reguler', na=False)]),
                    'Reject': len(df_branch[df_branch['Scoring_Detail'].str.contains('Reject', na=False)]),
                    'Recommended': len(df_branch[df_branch['apps_status_clean'].str.contains('RECOMMENDED CA', na=False)]),
                    'Not Recommended': len(df_branch[df_branch['apps_status_clean'].str.contains('NOT RECOMMENDED', na=False)])
                })
            
            branch_df = pd.DataFrame(branch_perf).sort_values('Total Apps', ascending=False)
            branch_df['Avg OSPH'] = branch_df['Avg OSPH'].apply(lambda x: f"Rp {x/1e6:.1f}M" if x > 0 else '-')
            branch_df['Avg SLA'] = branch_df['Avg SLA'].apply(lambda x: f"{x:.1f}d" if x > 0 else '-')
            
            st.dataframe(branch_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(branch_df.head(10), x='Branch', y='Total Apps',
                           title="Top 10 Branch by Volume", color='Total Apps')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(branch_df.head(10), x='Branch', 
                           y=['APPROVE', 'Reguler', 'Reject'],
                           title="Top 10 Branch Scoring Distribution", barmode='stack')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 9: Time Analysis
    with tabs[8]:
        st.header("📈 Time Series Analysis")
        
        if 'YearMonth' in df_filtered.columns:
            st.subheader("Monthly Trend")
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean'
            }).reset_index()
            monthly.columns = ['Month', 'Volume', 'Avg SLA']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=monthly['Month'], y=monthly['Volume'], name="Volume"), secondary_y=False)
            fig.add_trace(go.Scatter(x=monthly['Month'], y=monthly['Avg SLA'], name="Avg SLA", mode='lines+markers'), secondary_y=True)
            fig.update_layout(title="Monthly Volume & SLA Trend")
            st.plotly_chart(fig, use_container_width=True)
        
        if 'DayName' in df_filtered.columns:
            st.subheader("Weekly Pattern")
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekly = df_filtered.groupby('DayName').size().reset_index(name='Count')
            weekly['DayName'] = pd.Categorical(weekly['DayName'], categories=day_order, ordered=True)
            weekly = weekly.sort_values('DayName')
            
            fig = px.bar(weekly, x='DayName', y='Count', title="Weekly Pattern", color='Count')
            st.plotly_chart(fig, use_container_width=True)
        
        if 'Hour' in df_filtered.columns:
            st.subheader("Hourly Pattern")
            hourly = df_filtered.groupby('Hour').size().reset_index(name='Count')
            
            fig = px.line(hourly, x='Hour', y='Count', title="Hourly Distribution", markers=True)
            fig.add_vrect(x0=8.5, x1=15.5, fillcolor="green", opacity=0.1, annotation_text="Jam Kerja")
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 10: Tujuan Kredit
    with tabs[9]:
        st.header("🎯 Tujuan Kredit Analysis")
        
        if 'Tujuan_Kredit_clean' in df_filtered.columns:
            tujuan_count = df_filtered['Tujuan_Kredit_clean'].value_counts().reset_index()
            tujuan_count.columns = ['Tujuan Kredit', 'Count']
            tujuan_count['%'] = (tujuan_count['Count'] / len(df_filtered) * 100).round(2)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(tujuan_count, x='Tujuan Kredit', y='Count',
                           title="Tujuan Kredit Distribution", color='Count')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(tujuan_count, use_container_width=True, hide_index=True)
            
            # Tujuan Kredit by Product
            if 'Produk_clean' in df_filtered.columns:
                st.subheader("Tujuan Kredit by Product")
                tuj_prod = df_filtered.groupby(['Produk_clean', 'Tujuan_Kredit_clean']).size().reset_index(name='Count')
                fig = px.bar(tuj_prod, x='Tujuan_Kredit_clean', y='Count', color='Produk_clean',
                           title="Tujuan Kredit by Product", barmode='group')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 11: OD Analysis
    with tabs[10]:
        st.header("📊 Overdue (OD) Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'LastOD_clean' in df_filtered.columns:
                st.subheader("LastOD Statistics")
                lastod_stats = df_filtered['LastOD_clean'].describe()
                st.write(lastod_stats)
                
                fig = px.histogram(df_filtered, x='LastOD_clean', nbins=30,
                                 title="LastOD Distribution")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'max_OD_clean' in df_filtered.columns:
                st.subheader("Max OD Statistics")
                maxod_stats = df_filtered['max_OD_clean'].describe()
                st.write(maxod_stats)
                
                fig = px.histogram(df_filtered, x='max_OD_clean', nbins=30,
                                 title="Max OD Distribution")
                st.plotly_chart(fig, use_container_width=True)
        
        # OD vs Scoring
        if all(col in df_filtered.columns for col in ['LastOD_clean', 'max_OD_clean', 'Scoring_Detail']):
            st.subheader("OD vs Scoring Result")
            od_scoring = df_filtered.groupby('Scoring_Detail').agg({
                'LastOD_clean': 'mean',
                'max_OD_clean': 'mean'
            }).reset_index()
            
            fig = px.bar(od_scoring, x='Scoring_Detail', y=['LastOD_clean', 'max_OD_clean'],
                       title="Average OD by Scoring", barmode='group')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 12: Complete Data
    with tabs[11]:
        st.header("📋 Complete Data View")
        
        all_cols = [
            'apps_id', 'position_name_clean', 'user_name_clean', 'apps_status_clean', 
            'desc_status_apps_clean', 'Produk_clean', 'action_on', 'Initiation', 
            'RealisasiDate', 'OSPH_clean', 'OSPH_Category', 'Pekerjaan_clean', 
            'Jabatan_clean', 'Pekerjaan_Pasangan_clean', 'Scoring_Detail', 
            'JenisKendaraan_clean', 'branch_name_clean', 'Tujuan_Kredit_clean',
            'LastOD_clean', 'max_OD_clean', 'SLA_Days', 'YearMonth', 'DayName', 'Hour'
        ]
        
        available_cols = [col for col in all_cols if col in df_filtered.columns]
        
        selected_cols = st.multiselect(
            "Select columns to display",
            available_cols,
            default=available_cols[:10]
        )
        
        if selected_cols:
            search = st.text_input("🔍 Search in data")
            
            df_display = df_filtered[selected_cols].copy()
            
            if search:
                mask = df_display.astype(str).apply(
                    lambda x: x.str.contains(search, case=False, na=False)
                ).any(axis=1)
                df_display = df_display[mask]
            
            st.dataframe(df_display, use_container_width=True, height=500)
            
            # Download
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download CSV",
                csv,
                f"CA_Complete_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )
            
            # Summary
            st.subheader("Data Summary")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Rows", len(df_display))
            with col2:
                st.metric("Total Columns", len(selected_cols))
            with col3:
                st.metric("Unique Apps", df_display['apps_id'].nunique() if 'apps_id' in selected_cols else 'N/A')
            with col4:
                st.metric("Date Range", 
                         f"{df_display['action_on'].min().date()} - {df_display['action_on'].max().date()}" 
                         if 'action_on' in selected_cols and df_display['action_on'].notna().any() else 'N/A')
    
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: #666;'>
        <p>📊 Credit Analyst Analytics Dashboard - Complete Analysis</p>
        <p>All Fields Utilized | Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
