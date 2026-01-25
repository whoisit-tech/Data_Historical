import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

# ========== KONFIGURASI ==========
st.set_page_config(page_title="CA Analytics Dashboard", layout="wide", page_icon="📊")

FILE_NAME = "HistoricalCA.xlsx"

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .insight-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
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
    """Parse tanggal dengan berbagai format"""
    if pd.isna(date_str) or date_str == '-' or date_str == '':
        return None
    
    try:
        if isinstance(date_str, datetime):
            return date_str
        
        formats = ["%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y"]
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
    """Check apakah hari kerja (exclude weekend & tanggal merah)"""
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
    """
    Hitung SLA hari kerja dengan aturan:
    - Exclude weekend & tanggal merah
    - Jam kerja 08:30 - 15:30
    - Jika masuk di atas jam 15:30, dihitung besok pagi
    """
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        
        if pd.isna(start_dt) or pd.isna(end_dt):
            return None
        
        # Jika masuk di atas jam 15:30, mulai besok pagi jam 08:30
        start_adjusted = start_dt
        if start_dt.time() >= datetime.strptime("15:30", "%H:%M").time():
            start_adjusted = start_dt + timedelta(days=1)
            start_adjusted = start_adjusted.replace(hour=8, minute=30, second=0)
            while not is_working_day(start_adjusted):
                start_adjusted += timedelta(days=1)
        
        # Hitung hari kerja
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
    """Kategorisasi OSPH sesuai range"""
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

def map_scoring_group(x):
    """Mapping Hasil_Scoring_1 ke grup utama"""
    if pd.isna(x):
        return 'BELUM SCORING'
    
    x_str = str(x).strip().upper()
    
    if x_str in ['-', '', 'DATA HISTORICAL']:
        return 'BELUM SCORING'
    
    if 'APPROVE' in x_str:
        return 'APPROVE'
    
    if 'REGULER' in x_str:
        return 'REGULER'
    
    if 'REJECT' in x_str:
        return 'REJECT'
    
    if 'SCORING IN PROGRESS' in x_str:
        return 'SCORING IN PROGRESS'
    
    return 'OTHER'

def preprocess_data(df):
    """Preprocess data dengan error handling lengkap"""
    df = df.copy()
    
    # Parse dates
    date_cols = ['action_on', 'Initiation', 'RealisasiDate']
    for col in date_cols:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Calculate SLA
    if 'action_on_parsed' in df.columns and 'RealisasiDate_parsed' in df.columns:
        df['SLA_Days'] = df.apply(
            lambda row: calculate_sla_days(row['action_on_parsed'], row['RealisasiDate_parsed']), 
            axis=1
        )
    
    # Process OSPH
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(
            df['Outstanding_PH'].astype(str).str.replace(',', ''), 
            errors='coerce'
        )
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    # Process Scoring
    if 'Hasil_Scoring_1' in df.columns:
        df['Scoring_Raw'] = df['Hasil_Scoring_1']
        df['Scoring_Group'] = df['Hasil_Scoring_1'].apply(map_scoring_group)
        df['Is_Scored'] = df['Scoring_Group'] != 'BELUM SCORING'
    else:
        df['Scoring_Group'] = 'UNKNOWN'
        df['Is_Scored'] = False
    
    # Time features
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Date'] = df['action_on_parsed'].dt.date
    
    # Process apps_status
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('UNKNOWN').str.upper()
    else:
        df['apps_status_clean'] = 'UNKNOWN'
    
    return df

@st.cache_data
def load_data():
    """Load data dari Excel dengan error handling"""
    try:
        df = pd.read_excel(FILE_NAME)
        df_processed = preprocess_data(df)
        return df_processed
    except FileNotFoundError:
        st.error(f"❌ File '{FILE_NAME}' tidak ditemukan!")
        return None
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return None

# ========== MAIN APP ==========

def main():
    st.title("🎯 Credit Analyst Analytics Dashboard")
    st.markdown("**Comprehensive Analytics for Board Presentation**")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("❌ Failed to load data")
        st.stop()
    
    st.success(f"✅ Data loaded: {len(df):,} records")
    
    # ========== SIDEBAR FILTERS ==========
    st.sidebar.header("🔍 Filters")
    
    # Filter Posisi CA
    ca_positions = ['All']
    if 'user_name' in df.columns:
        ca_positions += sorted(df['user_name'].dropna().unique().tolist())
    selected_ca = st.sidebar.selectbox("👤 Posisi CA", ca_positions)
    
    # Filter Produk
    products = ['All']
    if 'Produk' in df.columns:
        products += sorted(df['Produk'].dropna().unique().tolist())
    selected_product = st.sidebar.selectbox("🚗 Produk", products)
    
    # Filter Branch
    branches = ['All']
    if 'branch_name' in df.columns:
        branches += sorted(df['branch_name'].dropna().unique().tolist())
    selected_branch = st.sidebar.selectbox("🏢 Branch", branches)
    
    # Filter OSPH Category
    osph_cats = ['All']
    if 'OSPH_Category' in df.columns:
        osph_cats += sorted(df['OSPH_Category'].unique().tolist())
    selected_osph = st.sidebar.selectbox("💰 OSPH Category", osph_cats)
    
    # Date filter
    if 'action_on_parsed' in df.columns:
        df_dates = df[df['action_on_parsed'].notna()]
        if len(df_dates) > 0:
            min_date = df_dates['action_on_parsed'].min().date()
            max_date = df_dates['action_on_parsed'].max().date()
            date_range = st.sidebar.date_input(
                "📅 Periode",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        else:
            date_range = None
    else:
        date_range = None
    
    # Apply filters
    df_filtered = df.copy()
    
    if selected_ca != 'All' and 'user_name' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['user_name'] == selected_ca]
    
    if selected_product != 'All' and 'Produk' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Produk'] == selected_product]
    
    if selected_branch != 'All' and 'branch_name' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['branch_name'] == selected_branch]
    
    if selected_osph != 'All' and 'OSPH_Category' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['OSPH_Category'] == selected_osph]
    
    if date_range and len(date_range) == 2 and 'action_on_parsed' in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered['action_on_parsed'].notna()) &
            (df_filtered['action_on_parsed'].dt.date >= date_range[0]) &
            (df_filtered['action_on_parsed'].dt.date <= date_range[1])
        ]
    
    # ========== KPI SECTION ==========
    st.header("📊 Key Performance Indicators")
    
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    with kpi1:
        total_apps = df_filtered['apps_id'].nunique() if 'apps_id' in df_filtered.columns else 0
        st.metric("📝 Total Apps (Distinct)", f"{total_apps:,}")
    
    with kpi2:
        avg_sla = df_filtered['SLA_Days'].mean() if 'SLA_Days' in df_filtered.columns else 0
        st.metric("⏱️ Avg SLA (Hari Kerja)", f"{avg_sla:.1f}d" if not pd.isna(avg_sla) else "N/A")
    
    with kpi3:
        total_scored = df_filtered[df_filtered['Is_Scored'] == True]['apps_id'].nunique() if 'apps_id' in df_filtered.columns else 0
        st.metric("✅ Total Scored", f"{total_scored:,}")
    
    with kpi4:
        recommended = len(df_filtered[df_filtered['apps_status_clean'].str.contains('RECOMMENDED CA', na=False)])
        st.metric("👍 Recommended CA", f"{recommended:,}")
    
    with kpi5:
        not_recommended = len(df_filtered[df_filtered['apps_status_clean'].str.contains('NOT RECOMMENDED', na=False)])
        st.metric("❌ Not Recommended", f"{not_recommended:,}")
    
    # Additional KPIs
    st.markdown("### 📌 Additional Metrics")
    kpi6, kpi7, kpi8, kpi9 = st.columns(4)
    
    with kpi6:
        pending = len(df_filtered[df_filtered['apps_status_clean'].str.contains('PENDING', na=False)])
        st.metric("⏳ Pending", f"{pending:,}")
    
    with kpi7:
        total_ca = df_filtered['user_name'].nunique() if 'user_name' in df_filtered.columns else 0
        st.metric("👥 Total CA", f"{total_ca:,}")
    
    with kpi8:
        if 'Hour' in df_filtered.columns:
            within_hours = len(df_filtered[(df_filtered['Hour'] >= 8) & (df_filtered['Hour'] <= 15)])
            compliance = within_hours / len(df_filtered) * 100 if len(df_filtered) > 0 else 0
            st.metric("🕐 Jam Kerja Compliance", f"{compliance:.1f}%")
        else:
            st.metric("🕐 Jam Kerja", "N/A")
    
    with kpi9:
        if 'apps_id' in df_filtered.columns and 'user_name' in df_filtered.columns:
            apps_per_ca = df_filtered.groupby('apps_id')['user_name'].nunique().mean()
            st.metric("📊 Avg CA per AppID", f"{apps_per_ca:.2f}")
        else:
            st.metric("📊 Avg CA per AppID", "N/A")
    
    st.markdown("---")
    
    # ========== BREAKDOWN ANALYSIS ==========
    st.header("📊 OSPH Breakdown Analysis")
    
    breakdown_tabs = st.tabs([
        "📈 Overview by Range",
        "🚗 Produk → OSPH → Kendaraan",
        "👔 Produk → OSPH → Pekerjaan",
        "📊 Detail Matrix"
    ])
    
    # TAB 1: Overview
    with breakdown_tabs[0]:
        if 'OSPH_Category' in df_filtered.columns:
            st.subheader("Distribution by OSPH Range")
            
            # Summary table
            range_summary = df_filtered.groupby('OSPH_Category').agg({
                'apps_id': 'nunique',
                'OSPH_clean': ['min', 'max', 'mean']
            }).reset_index()
            
            range_summary.columns = ['Range', 'Total Apps', 'Min', 'Max', 'Avg']
            range_summary['% dari Total'] = (range_summary['Total Apps'] / total_apps * 100).round(1)
            
            # Add scoring breakdown
            for score_type in ['APPROVE', 'REGULER', 'REJECT']:
                range_summary[score_type] = range_summary['Range'].apply(
                    lambda x: len(df_filtered[
                        (df_filtered['OSPH_Category'] == x) & 
                        (df_filtered['Scoring_Group'] == score_type)
                    ])
                )
            
            range_summary['Min'] = range_summary['Min'].apply(lambda x: f"Rp {x/1e6:,.0f}M" if pd.notna(x) else "-")
            range_summary['Max'] = range_summary['Max'].apply(lambda x: f"Rp {x/1e6:,.0f}M" if pd.notna(x) else "-")
            range_summary['Avg'] = range_summary['Avg'].apply(lambda x: f"Rp {x/1e6:,.0f}M" if pd.notna(x) else "-")
            
            st.dataframe(range_summary, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    range_summary, 
                    values='Total Apps', 
                    names='Range',
                    title="Distribution by OSPH Range",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                score_data = df_filtered[df_filtered['Scoring_Group'].isin(['APPROVE', 'REGULER', 'REJECT'])]
                score_dist = score_data.groupby(['OSPH_Category', 'Scoring_Group']).size().reset_index(name='Count')
                
                fig = px.bar(
                    score_dist,
                    x='OSPH_Category',
                    y='Count',
                    color='Scoring_Group',
                    title="Scoring Results by OSPH Range",
                    barmode='group',
                    color_discrete_map={
                        'APPROVE': '#10b981',
                        'REGULER': '#f59e0b',
                        'REJECT': '#ef4444'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 2: Produk → OSPH → Kendaraan
    with breakdown_tabs[1]:
        if all(col in df_filtered.columns for col in ['Produk', 'OSPH_Category', 'JenisKendaraan']):
            st.subheader("Breakdown: Produk → OSPH → Jenis Kendaraan")
            
            # Sunburst chart
            hierarchy_data = df_filtered.groupby(['Produk', 'OSPH_Category', 'JenisKendaraan']).size().reset_index(name='Count')
            
            fig = px.sunburst(
                hierarchy_data,
                path=['Produk', 'OSPH_Category', 'JenisKendaraan'],
                values='Count',
                title="Hierarchical View: Produk → OSPH → Kendaraan"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Detail table per produk
            for produk in df_filtered['Produk'].unique():
                with st.expander(f"📋 Detail {produk}"):
                    df_prod = df_filtered[df_filtered['Produk'] == produk]
                    
                    detail_table = df_prod.groupby(['OSPH_Category', 'JenisKendaraan']).agg({
                        'apps_id': 'nunique',
                        'Scoring_Group': lambda x: (x == 'APPROVE').sum()
                    }).reset_index()
                    
                    detail_table.columns = ['OSPH Range', 'Jenis Kendaraan', 'Total Apps', 'Approved']
                    detail_table['Approval Rate'] = (detail_table['Approved'] / detail_table['Total Apps'] * 100).round(1)
                    detail_table['Approval Rate'] = detail_table['Approval Rate'].apply(lambda x: f"{x}%")
                    
                    st.dataframe(detail_table, use_container_width=True, hide_index=True)
    
    # TAB 3: Produk → OSPH → Pekerjaan
    with breakdown_tabs[2]:
        if all(col in df_filtered.columns for col in ['Produk', 'OSPH_Category', 'Pekerjaan']):
            st.subheader("Breakdown: Produk → OSPH → Pekerjaan")
            
            # Sunburst chart
            hierarchy_data = df_filtered.groupby(['Produk', 'OSPH_Category', 'Pekerjaan']).size().reset_index(name='Count')
            
            fig = px.sunburst(
                hierarchy_data,
                path=['Produk', 'OSPH_Category', 'Pekerjaan'],
                values='Count',
                title="Hierarchical View: Produk → OSPH → Pekerjaan"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Heatmap
            pivot_data = df_filtered.pivot_table(
                index='OSPH_Category',
                columns='Pekerjaan',
                values='apps_id',
                aggfunc='nunique',
                fill_value=0
            )
            
            fig = px.imshow(
                pivot_data,
                text_auto=True,
                aspect="auto",
                title="Heatmap: OSPH vs Pekerjaan",
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 4: Detail Matrix
    with breakdown_tabs[3]:
        st.subheader("Detail Matrix Analysis")
        
        if all(col in df_filtered.columns for col in ['Produk', 'OSPH_Category', 'JenisKendaraan', 'Pekerjaan']):
            matrix_data = df_filtered.groupby(['Produk', 'OSPH_Category', 'JenisKendaraan', 'Pekerjaan']).agg({
                'apps_id': 'nunique',
                'Scoring_Group': lambda x: (x == 'APPROVE').sum()
            }).reset_index()
            
            matrix_data.columns = ['Produk', 'OSPH', 'Kendaraan', 'Pekerjaan', 'Total Apps', 'Approved']
            matrix_data['Approval %'] = (matrix_data['Approved'] / matrix_data['Total Apps'] * 100).round(1)
            matrix_data = matrix_data.sort_values('Total Apps', ascending=False)
            
            st.dataframe(matrix_data, use_container_width=True, hide_index=True)
            
            # Top combinations
            st.markdown("#### 🏆 Top 10 Kombinasi")
            top10 = matrix_data.nlargest(10, 'Total Apps')
            
            fig = px.bar(
                top10,
                x='Total Apps',
                y=top10['Produk'] + ' - ' + top10['OSPH'] + ' - ' + top10['Kendaraan'],
                orientation='h',
                title="Top 10 Kombinasi (Produk-OSPH-Kendaraan)",
                color='Approval %',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ========== CA PERFORMANCE ==========
    st.header("👥 CA Performance Analysis")
    
    ca_tabs = st.tabs(["📊 Overview", "📈 Trend", "🔍 Detail per CA"])
    
    with ca_tabs[0]:
        if 'user_name' in df_filtered.columns:
            ca_perf = df_filtered.groupby('user_name').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean',
                'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
            }).reset_index()
            
            ca_perf.columns = ['CA Name', 'Total Apps', 'Avg SLA', 'Approval Rate']
            ca_perf = ca_perf.sort_values('Total Apps', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    ca_perf.head(10),
                    x='CA Name',
                    y='Total Apps',
                    title="Top 10 CA by Volume",
                    color='Total Apps',
                    color_continuous_scale='Blues'
                )
                fig.update_xaxes(tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.scatter(
                    ca_perf,
                    x='Avg SLA',
                    y='Approval Rate',
                    size='Total Apps',
                    hover_data=['CA Name'],
                    title="SLA vs Approval Rate (bubble = volume)",
                    color='Approval Rate',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(ca_perf, use_container_width=True, hide_index=True)
    
    with ca_tabs[1]:
        if all(col in df_filtered.columns for col in ['YearMonth', 'user_name']):
            ca_trend = df_filtered.groupby(['YearMonth', 'user_name']).size().reset_index(name='Count')
            
            fig = px.line(
                ca_trend,
                x='YearMonth',
                y='Count',
                color='user_name',
                title="CA Activity Trend",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with ca_tabs[2]:
        if 'user_name' in df_filtered.columns:
            selected_ca_detail = st.selectbox(
                "Pilih CA untuk detail",
                df_filtered['user_name'].dropna().unique()
            )
            
            df_ca = df_filtered[df_filtered['user_name'] == selected_ca_detail]
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Apps", df_ca['apps_id'].nunique())
            with col2:
                avg_sla_ca = df_ca['SLA_Days'].mean()
                st.metric("Avg SLA", f"{avg_sla_ca:.1f}d" if not pd.isna(avg_sla_ca) else "N/A")
            with col3:
                approval_ca = (df_ca['Scoring_Group'] == 'APPROVE').sum() / len(df_ca) * 100 if len(df_ca) > 0 else 0
                st.metric("Approval Rate", f"{approval_ca:.1f}%")
            with col4:
                reject_ca = (df_ca['Scoring_Group'] == 'REJECT').sum() / len(df_ca) * 100 if len(df_ca) > 0 else 0
                st.metric("Reject Rate", f"{reject_ca:.1f}%")
            
            # Scoring distribution
            score_dist = df_ca['Scoring_Group'].value_counts().reset_index()
            score_dist.columns = ['Scoring', 'Count']
            
            fig = px.pie(
                score_dist,
                values='Count',
                names='Scoring',
                title=f"Scoring Distribution - {selected_ca_detail}"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ========== TREND ANALYSIS ==========
    st.header("📈 Trend & Pattern Analysis")
    
    trend_tabs = st.tabs(["📅 Monthly", "📊 Weekly", "🕐 Hourly", "🔄 Correlation"])
    
    with trend_tabs[0]:
        if 'YearMonth' in df_filtered.columns:
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean',
                'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
            }).reset_index()
            
            monthly.columns = ['Month', 'Volume', 'Avg SLA', 'Approval %']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Bar(x=monthly['Month'], y=monthly['Volume'], name="Volume"),
                secondary_y=False
            )
            fig.add_trace(
                go.Scatter(x=monthly['Month'], y=monthly['Approval %'], name="Approval %", mode='lines+markers'),
                secondary_y=True
            )
            fig.update_layout(title="Monthly Volume & Approval Rate")
            st.plotly_chart(fig, use_container_width=True)
    
    with trend_tabs[1]:
        if 'DayOfWeek' in df_filtered.columns:
            dow_names = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
            weekly = df_filtered.groupby('DayOfWeek').size().reset_index(name='Count')
            weekly['Day'] = weekly['DayOfWeek'].apply(lambda x: dow_names[x])
            
            fig = px.bar(
                weekly,
                x='Day',
                y='Count',
                title="Weekly Pattern",
                color='Count',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with trend_tabs[2]:
        if 'Hour' in df_filtered.columns:
            hourly = df_filtered.groupby('Hour').size().reset_index(name='Count')
            
            fig = px.line(
                hourly,
                x='Hour',
                y='Count',
                title="Hourly Pattern",
                markers=True
            )
            fig.add_vrect(x0=8.5, x1=15.5, fillcolor="green", opacity=0.1, annotation_text="Jam Kerja")
            st.plotly_chart(fig, use_container_width=True)
    
    with trend_tabs[3]:
        if all(col in df_filtered.columns for col in ['OSPH_clean', 'SLA_Days']):
            corr_cols = ['OSPH_clean', 'SLA_Days']
            if 'LastOD' in df_filtered.columns:
                corr_cols.append('LastOD')
            if 'max_OD' in df_filtered.columns:
                corr_cols.append('max_OD')
            
            df_corr = df_filtered[corr_cols].dropna()
            
            if len(df_corr) > 0:
                corr_matrix = df_corr.corr()
                
                fig = px.imshow(
                    corr_matrix,
                    text_auto=True,
                    aspect="auto",
                    title="Correlation Matrix",
                    color_continuous_scale='RdBu_r'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ========== INSIGHTS ==========
    st.header("💡 Key Insights & Recommendations")
    
    insights = []
    
    # Best OSPH segment
    if 'OSPH_Category' in df_filtered.columns and 'Scoring_Group' in df_filtered.columns:
        osph_approval = df_filtered.groupby('OSPH_Category')['Scoring_Group'].apply(
            lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        ).to_dict()
        if osph_approval:
            best_osph = max(osph_approval, key=osph_approval.get)
            insights.append(f"🎯 **Best OSPH Segment**: {best_osph} dengan approval rate {osph_approval[best_osph]:.1f}%")
    
    # SLA performance
    if 'SLA_Days' in df_filtered.columns:
        target_sla = 3
        within_sla = (df_filtered['SLA_Days'] <= target_sla).sum()
        total_sla = df_filtered['SLA_Days'].notna().sum()
        if total_sla > 0:
            within_sla_pct = within_sla / total_sla * 100
            insights.append(f"⏱️ **SLA Performance**: {within_sla_pct:.1f}% aplikasi diproses dalam {target_sla} hari kerja")
    
    # Best CA
    if 'user_name' in df_filtered.columns and 'Scoring_Group' in df_filtered.columns:
        ca_approval = df_filtered.groupby('user_name')['Scoring_Group'].apply(
            lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        ).to_dict()
        if ca_approval:
            best_ca = max(ca_approval, key=ca_approval.get)
            insights.append(f"👔 **Best CA**: {best_ca} dengan approval rate {ca_approval[best_ca]:.1f}%")
    
    # Product performance
    if 'Produk' in df_filtered.columns and 'Scoring_Group' in df_filtered.columns:
        prod_approval = df_filtered.groupby('Produk')['Scoring_Group'].apply(
            lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        ).to_dict()
        if prod_approval:
            best_prod = max(prod_approval, key=prod_approval.get)
            insights.append(f"🚗 **Best Product**: {best_prod} dengan approval rate {prod_approval[best_prod]:.1f}%")
    
    for insight in insights:
        st.markdown(f'<div class="insight-box">{insight}</div>', unsafe_allow_html=True)
    
    # Recommendations
    st.subheader("📋 Recommendations")
    
    recommendations = [
        "1. **Optimize Peak Hours**: Alokasi CA lebih banyak pada jam 10-14 (peak hours)",
        "2. **Focus on High-Value Segment**: Prioritas handling untuk segment 250-500 Juta (balance volume & value)",
        "3. **CA Training**: Share best practice dari top performer CA ke team",
        "4. **SLA Improvement**: Target 95% aplikasi selesai dalam 3 hari kerja",
        "5. **Risk-Based Approach**: Automated approval untuk low-risk segment (OSPH < 100 Juta + good profile)"
    ]
    
    for rec in recommendations:
        st.markdown(rec)
    
    st.markdown("---")
    
    # ========== RAW DATA ==========
    st.header("📋 Raw Data Explorer")
    
    display_cols = st.multiselect(
        "Pilih kolom untuk ditampilkan",
        df_filtered.columns.tolist(),
        default=['apps_id', 'Produk', 'OSPH_Category', 'user_name', 'Scoring_Group', 'apps_status_clean', 'SLA_Days']
    )
    
    if display_cols:
        search = st.text_input("🔍 Search")
        
        df_display = df_filtered[display_cols].copy()
        
        if search:
            mask = df_display.astype(str).apply(
                lambda x: x.str.contains(search, case=False, na=False)
            ).any(axis=1)
            df_display = df_display[mask]
        
        st.dataframe(df_display, use_container_width=True, height=400)
        
        # Download
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            csv,
            f"CA_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv"
        )
    
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: #666;'>
        <p>📊 Credit Analyst Analytics Dashboard | Production Ready</p>
        <p>Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
