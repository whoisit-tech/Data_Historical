import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(page_title="CA Analytics", layout="wide")

FILE_NAME = "Historical_CA (1).xlsx"

st.markdown("""
<style>
    .insight-card { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
        padding: 20px; 
        border-radius: 15px; 
        color: white; 
        margin: 10px 0; 
    }
    .warning-card { 
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
        padding: 20px; 
        border-radius: 15px; 
        color: white; 
        margin: 10px 0; 
    }
    .success-card { 
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
        padding: 20px; 
        border-radius: 15px; 
        color: white; 
        margin: 10px 0; 
    }
    h1 { color: #667eea; text-align: center; }
    h2 { color: #764ba2; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

TANGGAL_MERAH = [
    "01-01-2024", "08-02-2024", "10-02-2024", "11-03-2024",
    "29-03-2024", "31-03-2024", "10-04-2024", "11-04-2024",
    "01-05-2024", "09-05-2024", "23-05-2024", "01-06-2024",
    "17-06-2024", "07-07-2024", "17-08-2024", "16-09-2024",
    "25-12-2024", "09-02-2024", "12-03-2024", "08-04-2024", 
    "09-04-2024", "12-04-2024", "10-05-2024", "24-05-2024", 
    "18-06-2024", "26-12-2024", "01-01-2025", "27-01-2025", 
    "28-01-2025", "29-01-2025", "28-03-2025", "31-03-2025",
    "01-04-2025", "02-04-2025", "03-04-2025", "04-04-2025", 
    "07-04-2025", "18-04-2025", "01-05-2025", "12-05-2025", 
    "29-05-2025", "06-06-2025", "09-06-2025", "27-06-2025",
    "18-08-2025", "05-09-2025", "25-12-2025", "26-12-2025", 
    "31-12-2025", "01-01-2026", "02-01-2026", "16-01-2026", 
    "16-02-2026", "17-02-2026", "18-03-2026", "19-03-2026", 
    "20-03-2026", "23-03-2026", "24-03-2026", "03-04-2026", 
    "01-05-2026", "14-05-2026", "27-05-2026", "28-05-2026", 
    "01-06-2026", "16-06-2026", "17-08-2026", "25-08-2026", 
    "25-12-2026", "31-12-2026"
]
TANGGAL_MERAH_DT = [datetime.strptime(d, "%d-%m-%Y").date() for d in TANGGAL_MERAH]

def parse_date(date_str):
    """Parse date string in various formats"""
    if pd.isna(date_str) or date_str == '-':
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        
        date_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%Y-%m-%d",
            "%d-%m-%Y"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_str).split('.')[0], fmt)
            except:
                continue
        
        return pd.to_datetime(date_str, errors='coerce').to_pydatetime()
    except:
        return None

def is_working_day(date):
    """Check if date is a working day (exclude weekends and holidays)"""
    if pd.isna(date):
        return False
    if not isinstance(date, datetime):
        date = pd.to_datetime(date)
    
    is_weekday = date.weekday() < 5
    is_not_holiday = date.date() not in TANGGAL_MERAH_DT
    
    return is_weekday and is_not_holiday

def calculate_sla_working_hours(start_dt, end_dt):
    """
    Calculate working hours between two timestamps
    Working hours: 8:30 AM - 3:30 PM (7 hours/day)
    Excludes weekends and holidays (TANGGAL_MERAH)
    
    Returns: dict with working_hours (float), working_seconds (int), formatted string
    """
    if pd.isna(start_dt) or pd.isna(end_dt):
        return None

    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)

    if end_dt <= start_dt:
        return None

    WORK_START = timedelta(hours=8, minutes=30)
    WORK_END = timedelta(hours=15, minutes=30)

    current = start_dt
    working_seconds = 0

    while current < end_dt:
        if not is_working_day(current):
            current = datetime.combine(
                current.date() + timedelta(days=1),
                datetime.min.time()
            )
            continue

        day_start = datetime.combine(current.date(), datetime.min.time()) + WORK_START
        day_end = datetime.combine(current.date(), datetime.min.time()) + WORK_END

        if current < day_start:
            current = day_start
        
        if current >= day_end:
            current = datetime.combine(
                current.date() + timedelta(days=1),
                datetime.min.time()
            )
            continue

        interval_end = min(day_end, end_dt)
        working_seconds += max((interval_end - current).total_seconds(), 0)
        current = interval_end

    if working_seconds < 0:
        return None

    working_hours = round(working_seconds / 3600, 2)
    total_minutes = int(working_seconds // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    return {
        "working_seconds": working_seconds,
        "working_hours": working_hours,
        "formatted": f"{hours}h {minutes}m"
    }


def calculate_row_sla(df):
    """Calculate SLA per row with proper initialization"""
    df_sorted = df.sort_values(['apps_id', 'action_on_parsed'], na_position='last').copy()
    df_sorted = df_sorted.reset_index(drop=True)
    
    # Initialize SLA columns with default values
    df_sorted['SLA_Start'] = None
    df_sorted['SLA_End'] = None
    df_sorted['SLA_Hours'] = np.nan
    df_sorted['SLA_Formatted'] = '—'
    df_sorted['SLA_Logic'] = 'N/A'
    
    has_recommendation = 'Recommendation_parsed' in df_sorted.columns
    
    for app_id in df_sorted['apps_id'].unique():
        mask = df_sorted['apps_id'] == app_id
        app_indices = df_sorted[mask].index.tolist()
        
        for group_position, current_idx in enumerate(app_indices):
            current_status = str(df_sorted.at[current_idx, 'apps_status_clean']).upper()
            current_action = df_sorted.at[current_idx, 'action_on_parsed']
            
            if has_recommendation:
                current_recommendation = df_sorted.at[current_idx, 'Recommendation_parsed']
            else:
                current_recommendation = None
            
            sla_start = None
            sla_end = current_action
            logic = 'N/A'
            has_previous = group_position > 0
            
            # PENDING CA (without COMPLETED)
            if 'PENDING CA' in current_status and 'COMPLETED' not in current_status:
                if has_recommendation and pd.notna(current_recommendation):
                    sla_start = current_recommendation
                    logic = 'PENDING CA: Recommendation → action_on'
                else:
                    logic = 'PENDING CA: No Recommendation'
            
            # PENDING CA COMPLETED
            elif 'COMPLETED' in current_status and 'PENDING' in current_status:
                if has_previous:
                    prev_idx = app_indices[group_position - 1]
                    prev_action = df_sorted.at[prev_idx, 'action_on_parsed']
                    sla_start = prev_action
                    logic = 'PENDING CA COMPLETED: prev action_on → current'
                else:
                    if has_recommendation and pd.notna(current_recommendation):
                        sla_start = current_recommendation
                        logic = 'PENDING CA COMPLETED: Recommendation (first row)'
                    else:
                        logic = 'PENDING CA COMPLETED: First row, no Recommendation'
            
            # NOT RECOMMENDED / RECOMMENDED CA / WITH COND
            elif 'NOT RECOMMENDED' in current_status or 'RECOMMENDED' in current_status:
                if has_previous:
                    prev_idx = app_indices[group_position - 1]
                    prev_action = df_sorted.at[prev_idx, 'action_on_parsed']
                    sla_start = prev_action
                    logic = f'{current_status}: prev action_on → current'
                else:
                    if has_recommendation and pd.notna(current_recommendation):
                        sla_start = current_recommendation
                        logic = f'{current_status}: Recommendation (first row)'
                    else:
                        logic = f'{current_status}: First row, no Recommendation'
            
            # Calculate SLA if timestamps are valid
            if (sla_start is not None and sla_end is not None and
                pd.notna(sla_start) and pd.notna(sla_end) and sla_end > sla_start):
                
                sla_result = calculate_sla_working_hours(sla_start, sla_end)
                if sla_result:
                    df_sorted.at[current_idx, 'SLA_Start'] = sla_start
                    df_sorted.at[current_idx, 'SLA_End'] = sla_end
                    df_sorted.at[current_idx, 'SLA_Hours'] = sla_result['working_hours']
                    df_sorted.at[current_idx, 'SLA_Formatted'] = sla_result['formatted']
                    df_sorted.at[current_idx, 'SLA_Logic'] = logic
                else:
                    df_sorted.at[current_idx, 'SLA_Logic'] = logic + ' (calc failed)'
            else:
                df_sorted.at[current_idx, 'SLA_Logic'] = logic + ' (missing ts)'
    
    return df_sorted

def get_osph_category(osph_value):
    """Categorize Outstanding PH"""
    try:
        if pd.isna(osph_value):
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

def calculate_risk_score(row):
    """Calculate risk score"""
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
    
    if pd.notna(row.get('SLA_Hours')):
        if row['SLA_Hours'] > 40:
            score += 20
        elif row['SLA_Hours'] > 24:
            score += 10
    
    return min(score, 100)

def preprocess_data(df):
    """Clean and prepare data"""
    df = df.copy()
    
    for col in ['action_on', 'Initiation', 'RealisasiDate', 'Recommendation']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
        else:
            df[f'{col}_parsed'] = None
    
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(
            df['Outstanding_PH'].astype(str).str.replace(',', ''), 
            errors='coerce'
        )
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    for col in ['LastOD', 'max_OD']:
        if col in df.columns:
            df[f'{col}_clean'] = pd.to_numeric(df[col], errors='coerce')
    
    if 'Hasil_Scoring' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring'].fillna('(Pilih Semua)').astype(str).str.strip()
    
    if 'Segmen' in df.columns:
        df['Segmen_clean'] = df['Segmen'].fillna('Unknown').astype(str).str.strip()
    else:
        df['Segmen_clean'] = 'Unknown'
    
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Quarter'] = df['action_on_parsed'].dt.quarter
    
    categorical_fields = [
        'desc_status_apps', 'Produk', 'Pekerjaan', 'Jabatan',
        'Pekerjaan_Pasangan', 'JenisKendaraan', 'branch_name', 
        'Tujuan_Kredit', 'user_name', 'position_name'
    ]
    
    for field in categorical_fields:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
    return df

@st.cache_data
def load_data():
    """Load and preprocess data"""
    try:
        if not Path(FILE_NAME).exists():
            st.error(f"File tidak ditemukan: {FILE_NAME}")
            return None
        
        df = pd.read_excel(FILE_NAME)
        
        required_cols = [
            'apps_id', 'position_name', 'user_name', 'apps_status', 'desc_status_apps',
            'action_on', 'Initiation', 'RealisasiDate', 'Outstanding_PH',
            'Pekerjaan', 'Jabatan', 'Hasil_Scoring',
            'JenisKendaraan', 'branch_name', 'Tujuan_Kredit', 'LastOD', 'max_OD'
        ]
        
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"Kolom tidak ditemukan: {', '.join(missing)}")
            return None
        
        if 'Recommendation' not in df.columns:
            st.warning("Kolom 'Recommendation' tidak ditemukan - SLA dari Recommendation akan kosong")
            df['Recommendation'] = None
        
        df_clean = preprocess_data(df)
        df_clean = calculate_row_sla(df_clean)
        
        df_clean['Risk_Score'] = df_clean.apply(calculate_risk_score, axis=1)
        df_clean['Risk_Category'] = pd.cut(
            df_clean['Risk_Score'], 
            bins=[0, 30, 60, 100], 
            labels=['Low Risk', 'Medium Risk', 'High Risk']
        )
        
        return df_clean
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

def create_osph_pivot_analysis(df):
    """Create OSPH pivot tables"""
    pivots = {}
    
    df_valid = df[
        (df['OSPH_clean'].notna()) & 
        (df['OSPH_Category'] != 'Unknown') &
        (df['Segmen_clean'] != 'Unknown')
    ].copy()
    
    if len(df_valid) == 0:
        return pivots
    
    if 'Pekerjaan_clean' in df_valid.columns:
        pivot1 = {}
        for segmen in sorted(df_valid['Segmen_clean'].unique()):
            df_seg = df_valid[df_valid['Segmen_clean'] == segmen]
            pivot_table = pd.crosstab(
                df_seg['OSPH_Category'],
                df_seg['Pekerjaan_clean'],
                values=df_seg['apps_id'],
                aggfunc='nunique',
                margins=True,
                margins_name='TOTAL'
            )
            pivot1[segmen] = pivot_table
        pivots['pekerjaan'] = pivot1
    
    if 'JenisKendaraan_clean' in df_valid.columns:
        pivot2 = {}
        for segmen in sorted(df_valid['Segmen_clean'].unique()):
            df_seg = df_valid[df_valid['Segmen_clean'] == segmen]
            pivot_table = pd.crosstab(
                df_seg['OSPH_Category'],
                df_seg['JenisKendaraan_clean'],
                values=df_seg['apps_id'],
                aggfunc='nunique',
                margins=True,
                margins_name='TOTAL'
            )
            pivot2[segmen] = pivot_table
        pivots['kendaraan'] = pivot2
    
    if 'Scoring_Detail' in df_valid.columns:
        df_scoring = df_valid[df_valid['Scoring_Detail'] != '(Pilih Semua)']
        pivot3 = {}
        for segmen in sorted(df_scoring['Segmen_clean'].unique()):
            df_seg = df_scoring[df_scoring['Segmen_clean'] == segmen]
            pivot_table = pd.crosstab(
                df_seg['OSPH_Category'],
                df_seg['Scoring_Detail'],
                values=df_seg['apps_id'],
                aggfunc='nunique',
                margins=True,
                margins_name='TOTAL'
            )
            pivot3[segmen] = pivot_table
        pivots['scoring'] = pivot3
    
    return pivots

def generate_analytical_insights(df):
    """Generate insights and warnings"""
    insights = []
    warnings = []
    
    if 'OSPH_Category' in df.columns and 'Scoring_Detail' in df.columns:
        for osph in ['0 - 250 Juta', '250 - 500 Juta', '500 Juta+']:
            df_osph = df[df['OSPH_Category'] == osph]
            if len(df_osph) > 0:
                approve = df_osph['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                total = len(df_osph[df_osph['Scoring_Detail'] != '(Pilih Semua)'])
                if total > 0:
                    rate = approve / total * 100
                    insights.append(f"Approval rate {rate:.1f}% in {osph} segment")
    
    if 'SLA_Hours' in df.columns:
        sla_valid = df[df['SLA_Hours'].notna()]
        if len(sla_valid) > 0:
            avg_sla = sla_valid['SLA_Hours'].mean()
            sla_count = len(sla_valid)
            total = len(df)
            pct = (sla_count / total * 100) if total > 0 else 0
            
            if avg_sla > 35:
                warnings.append(f"Average SLA: {avg_sla:.1f}h (target: ≤35h) | {sla_count:,}/{total:,} ({pct:.1f}%)")
            else:
                insights.append(f"Average SLA: {avg_sla:.1f}h | {sla_count:,}/{total:,} ({pct:.1f}%)")
    
    return insights, warnings

def main():
    """Main app"""
    st.title("📊 CA Analytics Dashboard")
    st.markdown("**SLA in Hours | Accurate Timestamp Calculation | OSPH Pivot Tables per Segmen**")
    st.markdown("---")
    
    with st.spinner("Loading dan processing data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    sla_calculated = df['SLA_Hours'].notna().sum() if 'SLA_Hours' in df.columns else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Total Records", f"{total_records:,}")
        st.caption("Total kontrak/apps")
    with col2:
        st.metric("📄 Unique Applications", f"{unique_apps:,}")
        st.caption("Distinct apps_id")
    with col3:
        sla_pct = (sla_calculated / total_records * 100) if total_records > 0 else 0
        st.metric("⏱️ SLA Calculated", f"{sla_calculated:,} ({sla_pct:.1f}%)")
        st.caption("Rows dengan SLA terhitung")
    with col4:
        if 'SLA_Hours' in df.columns:
            avg_sla = df[df['SLA_Hours'].notna()]['SLA_Hours'].mean()
            st.metric("⏰ Average SLA", f"{avg_sla:.1f}h" if pd.notna(avg_sla) else "N/A")
        else:
            st.metric("⏰ Average SLA", "N/A")
        st.caption("Rata-rata jam kerja")
    
    st.markdown("---")
    
    # Filters
    st.sidebar.title("Analytics Control Panel")
    
    if 'apps_status_clean' in df.columns:
        all_status = sorted([x for x in df['apps_status_clean'].unique() if x != 'Unknown'])
        selected_status = st.sidebar.multiselect("Application Status", all_status, default=all_status)
    else:
        selected_status = []
    
    if 'Scoring_Detail' in df.columns:
        all_scoring = sorted([x for x in df['Scoring_Detail'].unique() if x != '(Pilih Semua)'])
        selected_scoring = st.sidebar.multiselect("Scoring Result", all_scoring, default=all_scoring)
    else:
        selected_scoring = []
    
    if 'Segmen_clean' in df.columns:
        all_segmen = sorted([x for x in df['Segmen_clean'].unique() if x != 'Unknown'])
        selected_segmen = st.sidebar.selectbox("Segmen", ['All'] + all_segmen)
    else:
        selected_segmen = 'All'
    
    if 'branch_name_clean' in df.columns:
        all_branches = sorted(df['branch_name_clean'].unique().tolist())
        selected_branch = st.sidebar.selectbox("Branch", ['All'] + all_branches)
    else:
        selected_branch = 'All'
    
    if 'user_name_clean' in df.columns:
        all_cas = sorted(df['user_name_clean'].unique().tolist())
        selected_ca = st.sidebar.selectbox("CA Name", ['All'] + all_cas)
    else:
        selected_ca = 'All'
    
    if 'OSPH_Category' in df.columns:
        all_osph = sorted([x for x in df['OSPH_Category'].unique() if x != 'Unknown'])
        selected_osph = st.sidebar.selectbox("Outstanding PH", ['All'] + all_osph)
    else:
        selected_osph = 'All'
    
    # Apply filters
    df_filtered = df.copy()
    
    if selected_status:
        df_filtered = df_filtered[df_filtered['apps_status_clean'].isin(selected_status)]
    if selected_scoring:
        df_filtered = df_filtered[df_filtered['Scoring_Detail'].isin(selected_scoring)]
    if selected_segmen != 'All':
        df_filtered = df_filtered[df_filtered['Segmen_clean'] == selected_segmen]
    if selected_branch != 'All':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    if selected_ca != 'All':
        df_filtered = df_filtered[df_filtered['user_name_clean'] == selected_ca]
    if selected_osph != 'All':
        df_filtered = df_filtered[df_filtered['OSPH_Category'] == selected_osph]
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"{len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f"{df_filtered['apps_id'].nunique():,} unique applications")
    
    # Insights
    st.header("💡 Key Insights")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    if warnings:
        st.warning("\n".join([f"• {w}" for w in warnings]))
    if insights:
        st.success("\n".join([f"• {i}" for i in insights]))
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⏱️ SLA Overview",
        "📊 OSPH Pivot Analysis",
        "👥 CA Performance",
        "🔍 Detailed View",
        "📥 Raw Data"
    ])
    
    # Tab 1: SLA Overview
    with tab1:
        st.header("SLA Performance Overview")
        
        if 'SLA_Hours' not in df_filtered.columns:
            st.error("SLA_Hours column tidak ditemukan!")
        else:
            sla_valid = df_filtered[df_filtered['SLA_Hours'].notna()]
            
            if len(sla_valid) > 0:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Average SLA", f"{sla_valid['SLA_Hours'].mean():.1f}h")
                with col2:
                    st.metric("Median SLA", f"{sla_valid['SLA_Hours'].median():.1f}h")
                with col3:
                    exceed = (sla_valid['SLA_Hours'] > 35).sum()
                    pct = exceed / len(sla_valid) * 100 if len(sla_valid) > 0 else 0
                    st.metric("Exceed 35h", f"{exceed} ({pct:.1f}%)")
                with col4:
                    within = (sla_valid['SLA_Hours'] <= 35).sum()
                    pct = within / len(sla_valid) * 100 if len(sla_valid) > 0 else 0
                    st.metric("Within Target", f"{within} ({pct:.1f}%)")
                
                st.markdown("---")
                st.subheader("Average SLA by Status")
                
                sla_by_status = sla_valid.groupby('apps_status_clean').agg({
                    'SLA_Hours': ['mean', 'median', 'max', 'min'],
                    'apps_id': 'nunique'
                }).reset_index()
                
                record_counts = sla_valid.groupby('apps_status_clean').size().reset_index(name='Total_Records')
                
                sla_by_status.columns = ['Status', 'Avg_SLA', 'Median_SLA', 'Max_SLA', 'Min_SLA', 'Distinct_Apps']
                sla_by_status = sla_by_status.merge(record_counts, left_on='Status', right_on='apps_status_clean', how='left')
                sla_by_status = sla_by_status.drop('apps_status_clean', axis=1)
                sla_by_status = sla_by_status[['Status', 'Avg_SLA', 'Median_SLA', 'Min_SLA', 'Max_SLA', 'Total_Records', 'Distinct_Apps']]
                sla_by_status = sla_by_status.sort_values('Avg_SLA', ascending=False)
                
                st.dataframe(sla_by_status, use_container_width=True, hide_index=True)
                
                fig = px.bar(
                    sla_by_status, x='Status', y='Avg_SLA', 
                    title="Average SLA (hours) by Application Status",
                    color='Avg_SLA', color_continuous_scale='RdYlGn_r',
                    labels={'Avg_SLA': 'Average SLA (hours)'}
                )
                fig.update_xaxes(tickangle=45)
                fig.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="Target: 35h")
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📈 Average SLA Trend by Month")
                
                sla_by_month = sla_valid.groupby('YearMonth').agg({
                    'SLA_Hours': 'mean',
                    'apps_id': 'count'
                }).reset_index()
                sla_by_month.columns = ['Month', 'Avg_SLA_Hours', 'Record_Count']
                
                fig_line = px.line(
                    sla_by_month, x='Month', y='Avg_SLA_Hours',
                    title='Average SLA Trend by Month',
                    markers=True,
                    labels={'Avg_SLA_Hours': 'Average SLA (hours)', 'Month': 'Year-Month'}
                )
                fig_line.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="Target: 35h")
                fig_line.update_xaxes(tickangle=45)
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.warning("No SLA data available for selected filters")
    
    # Tab 2: OSPH Pivot
    with tab2:
        st.header("OSPH Pivot Tables per Segmen")
        
        osph_pivots = create_osph_pivot_analysis(df_filtered)
        
        if osph_pivots:
            pivot_tab1, pivot_tab2, pivot_tab3 = st.tabs(["OSPH x Pekerjaan", "OSPH x Jenis Kendaraan", "OSPH x Hasil Scoring"])
            
            with pivot_tab1:
                if 'pekerjaan' in osph_pivots:
                    for segmen, pivot_table in osph_pivots['pekerjaan'].items():
                        st.subheader(f"Segmen: {segmen}")
                        st.dataframe(pivot_table, use_container_width=True)
                        st.markdown("---")
                else:
                    st.info("No data available")
            
            with pivot_tab2:
                if 'kendaraan' in osph_pivots:
                    for segmen, pivot_table in osph_pivots['kendaraan'].items():
                        st.subheader(f"Segmen: {segmen}")
                        st.dataframe(pivot_table, use_container_width=True)
                        st.markdown("---")
                else:
                    st.info("No data available")
            
            with pivot_tab3:
                if 'scoring' in osph_pivots:
                    for segmen, pivot_table in osph_pivots['scoring'].items():
                        st.subheader(f"Segmen: {segmen}")
                        st.dataframe(pivot_table, use_container_width=True)
                        st.markdown("---")
                else:
                    st.info("No data available")
        else:
            st.warning("No pivot data available")
    
    # Tab 3: CA Performance
    with tab3:
        st.header("CA Performance Analysis")
        
        if 'user_name_clean' in df_filtered.columns:
            st.info("Detailed performance metrics per Credit Analyst")
            
            ca_perf = []
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                total_apps = df_ca['apps_id'].nunique()
                
                approve = df_ca['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                reject = df_ca['Scoring_Detail'].isin(['REJECT', 'REJECT 1', 'REJECT 2']).sum()
                
                if 'SLA_Hours' in df_ca.columns:
                    df_ca_sla = df_ca[df_ca['SLA_Hours'].notna()]
                    avg_sla = f"{df_ca_sla['SLA_Hours'].mean():.1f}h" if len(df_ca_sla) > 0 else "N/A"
                else:
                    avg_sla = "N/A"
                
                ca_perf.append({
                    'CA Name': ca,
                    'Total Apps': total_apps,
                    'APPROVE': approve,
                    'REJECT': reject,
                    'Avg SLA': avg_sla
                })
            
            if ca_perf:
                ca_df = pd.DataFrame(ca_perf)
                st.dataframe(ca_df, use_container_width=True, hide_index=True)
                
                csv = ca_df.to_csv(index=False)
                st.download_button("Download CA Report", csv, "ca_performance.csv", "text/csv")
            else:
                st.info("No CA data available")
        else:
            st.warning("CA data not found")
    
    # Tab 4: Detailed View
    with tab4:
        st.header("Detailed SLA View per Application")
        
        sample_apps = sorted(df_filtered['apps_id'].unique())
        
        if len(sample_apps) > 0:
            selected_app = st.selectbox("Select Application ID:", sample_apps)
            
            app_data = df_filtered[df_filtered['apps_id'] == selected_app].sort_values('action_on_parsed')
            
            st.subheader(f"Application ID: {selected_app}")
            st.dataframe(app_data[['apps_status_clean', 'action_on_parsed', 'SLA_Hours', 'SLA_Formatted', 'SLA_Logic']].reset_index(drop=True), use_container_width=True)
        else:
            st.info("No applications available")
    
    # Tab 5: Raw Data
    with tab5:
        st.header("Raw Data Export")
        
        cols_to_show = [
            'apps_id', 'apps_status_clean', 'action_on_parsed', 
            'SLA_Hours', 'SLA_Formatted', 'Scoring_Detail', 'OSPH_Category'
        ]
        available = [c for c in cols_to_show if c in df_filtered.columns]
        
        st.dataframe(df_filtered[available].head(100), use_container_width=True, hide_index=True)
        
        csv = df_filtered[available].to_csv(index=False)
        st.download_button("📥 Download Filtered Data", csv, "ca_analytics_data.csv", "text/csv")
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
