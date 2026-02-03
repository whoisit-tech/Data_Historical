import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(
    page_title="Analisis Kredit - Dashboard BCA Finance", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🏦"
)

FILE_NAME = "Historical_CA (1) (1).xlsx"

# BCA Finance Brand Colors
BCA_BLUE = "#003d7a"
BCA_LIGHT_BLUE = "#0066b3"
BCA_ACCENT = "#1e88e5"
BCA_GOLD = "#d4af37"

# ============================================================================
# STYLING - BCA FINANCE THEME
# ============================================================================
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    
    h1 { 
        color: #ffffff !important;
        text-align: center; 
        font-size: 36px; 
        margin-bottom: 10px;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    
    h2 { 
        color: #ffffff !important;
        border-bottom: 3px solid #0066b3; 
        padding-bottom: 10px;
        margin-top: 30px;
        font-weight: 600;
    }
    
    h3, h4 { 
        color: #ffffff !important;
        margin-top: 25px;
        font-weight: 600;
    }
    
    .metric-box {
        background: #1e2129;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #2d3139;
        border-left: 6px solid #0066b3;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    
    .metric-box:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 15px rgba(0,102,179,0.3);
        border-color: #0066b3;
    }
    
    .metric-box-success {
        background: #1e2129;
        border: 2px solid #2d3139;
        border-left: 6px solid #1e88e5;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    .metric-box-success:hover {
        box-shadow: 0 4px 15px rgba(30,136,229,0.3);
        border-color: #1e88e5;
    }
    
    .metric-box-warning {
        background: #1e2129;
        border: 2px solid #2d3139;
        border-left: 6px solid #ff9800;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    .metric-box-warning:hover {
        box-shadow: 0 4px 15px rgba(255,152,0,0.3);
        border-color: #ff9800;
    }
    
    .metric-box-danger {
        background: #1e2129;
        border: 2px solid #2d3139;
        border-left: 6px solid #f44336;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    .metric-box-danger:hover {
        box-shadow: 0 4px 15px rgba(244,67,54,0.3);
        border-color: #f44336;
    }
    
    .info-box {
        background: #1e2129;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #0066b3;
        border-left: 5px solid #0066b3;
        margin: 20px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    .info-box h4 {
        color: #4fc3f7 !important;
        margin-top: 0;
        margin-bottom: 10px;
    }
    
    .info-box p, .info-box ul, .info-box ol {
        color: #b0bec5 !important;
        line-height: 1.6;
    }
    
    .info-box li {
        color: #b0bec5 !important;
        margin-bottom: 8px;
    }
    
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    
    .dataframe th {
        background-color: #003d7a !important;
        color: white !important;
        font-weight: 600;
        padding: 12px !important;
    }
    
    .dataframe td {
        color: #e0e0e0 !important;
        padding: 10px !important;
        background-color: #1e2129 !important;
    }
    
    .dataframe tr:hover td {
        background-color: #262b35 !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #1e2129;
        border-right: 2px solid #2d3139;
        box-shadow: 2px 0 10px rgba(0,0,0,0.3);
    }
    
    [data-testid="stSidebar"] h2 {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown p {
        color: #b0bec5 !important;
    }
    
    [data-testid="stSidebar"] label {
        color: #e0e0e0 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        background-color: #262b35;
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1e2129;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #2d3139;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 14px 26px;
        background-color: #262b35;
        border: 2px solid #2d3139;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        color: #b0bec5 !important;
        font-size: 15px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #003d7a 0%, #0066b3 100%);
        color: white !important;
        border: 2px solid #0066b3;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #2d3139;
        border-color: #0066b3;
        color: #ffffff !important;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #003d7a 0%, #0066b3 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 12px 28px;
        font-size: 15px;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #0066b3 0%, #1e88e5 100%);
        box-shadow: 0 4px 12px rgba(0,102,179,0.4);
    }
    
    .stDownloadButton>button {
        background: linear-gradient(135deg, #003d7a 0%, #0066b3 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 12px 28px;
        font-size: 15px;
    }
    
    .stDownloadButton>button:hover {
        background: linear-gradient(135deg, #0066b3 0%, #1e88e5 100%);
    }
    
    [data-testid="stMetricValue"] {
        color: #4fc3f7 !important;
        font-weight: 700;
        font-size: 28px !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #b0bec5 !important;
        font-weight: 600;
    }
    
    [data-testid="stMetricDelta"] {
        color: #81c784 !important;
    }
    
    .stSelectbox [data-baseweb="select"] {
        background-color: #262b35 !important;
        border-color: #2d3139 !important;
    }
    
    .stSelectbox label {
        color: #e0e0e0 !important;
    }
    
    .stSelectbox [data-baseweb="select"] > div {
        background-color: #262b35 !important;
        color: #e0e0e0 !important;
    }
    
    .stMultiSelect [data-baseweb="select"] {
        background-color: #262b35 !important;
        border-color: #2d3139 !important;
    }
    
    .stMultiSelect label {
        color: #e0e0e0 !important;
    }
    
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #f44336 !important;
        color: white !important;
    }
    
    p, span, div {
        color: #e0e0e0 !important;
    }
    
    .stMarkdown p {
        color: #b0bec5 !important;
    }
    
    .stCaption {
        color: #90a4ae !important;
    }
    
    .header-container {
        background: linear-gradient(135deg, #003d7a 0%, #0066b3 100%);
        padding: 35px;
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(0,102,179,0.4);
    }
    
    .header-container h1 {
        color: white !important;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .header-container p {
        color: #e3f2fd !important;
        font-size: 16px;
        margin-top: 10px;
    }
    
    /* Input fields */
    .stTextInput input {
        background-color: #262b35 !important;
        color: #e0e0e0 !important;
        border-color: #2d3139 !important;
    }
    
    .stTextInput label {
        color: #e0e0e0 !important;
    }
    
    /* Success/Info/Warning/Error messages */
    .stSuccess {
        background-color: #1e2129 !important;
        border-left-color: #4caf50 !important;
        color: #81c784 !important;
    }
    
    .stInfo {
        background-color: #1e2129 !important;
        border-left-color: #2196f3 !important;
        color: #64b5f6 !important;
    }
    
    .stWarning {
        background-color: #1e2129 !important;
        border-left-color: #ff9800 !important;
        color: #ffb74d !important;
    }
    
    .stError {
        background-color: #1e2129 !important;
        border-left-color: #f44336 !important;
        color: #e57373 !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e2129;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2d3139;
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #0066b3;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TANGGAL MERAH (Holidays)
# ============================================================================
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

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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
    """Check if date is a working day"""
    if pd.isna(date):
        return False
    if not isinstance(date, datetime):
        date = pd.to_datetime(date)
    
    is_weekday = date.weekday() < 5
    is_not_holiday = date.date() not in TANGGAL_MERAH_DT
    
    return is_weekday and is_not_holiday

def convert_hours_to_hm(total_hours):
    """Convert decimal hours to HH:MM format"""
    if pd.isna(total_hours):
        return None
    hours = int(total_hours)
    minutes = int((total_hours - hours) * 60)
    return f"{hours} jam {minutes} menit"

def calculate_sla_working_hours(start_dt, end_dt):
    """Calculate SLA in working hours (08:30-15:30)"""
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        
        if end_dt <= start_dt:
            return None
        
        WORK_START = timedelta(hours=8, minutes=30)
        WORK_END = timedelta(hours=15, minutes=30)
        
        current = start_dt
        total_seconds = 0
        
        while current.date() <= end_dt.date():
            if not is_working_day(current):
                current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
                continue
            
            day_start = datetime.combine(current.date(), datetime.min.time()) + WORK_START
            day_end = datetime.combine(current.date(), datetime.min.time()) + WORK_END
            
            if current.date() == start_dt.date():
                if start_dt.time() < day_start.time():
                    day_actual_start = day_start
                elif start_dt.time() >= day_end.time():
                    current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
                    continue
                else:
                    day_actual_start = start_dt
            else:
                day_actual_start = day_start
            
            if current.date() == end_dt.date():
                if end_dt.time() < day_start.time():
                    break
                elif end_dt.time() > day_end.time():
                    day_actual_end = day_end
                else:
                    day_actual_end = end_dt
            else:
                day_actual_end = day_end
            
            if day_actual_end > day_actual_start:
                day_seconds = (day_actual_end - day_actual_start).total_seconds()
                total_seconds += day_seconds
            
            current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
        
        if total_seconds < 0:
            return None
        
        total_hours = total_seconds / 3600
        return {
            'total_hours': round(total_hours, 2),
            'formatted': convert_hours_to_hm(total_hours)
        }
    except:
        return None

def get_osph_category(osph_value):
    """Categorize Outstanding PH"""
    try:
        if pd.isna(osph_value):
            return "Tidak Tersedia"
        osph_value = float(osph_value)
        if osph_value <= 250000000:
            return "0 - 250 Juta"
        elif osph_value <= 500000000:
            return "250 - 500 Juta"
        else:
            return "Lebih dari 500 Juta"
    except:
        return "Tidak Tersedia"

def preprocess_data(df):
    """Clean and prepare data"""
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Recommendation']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Clean status
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Tidak Diketahui').astype(str).str.strip()
    
    # Clean OSPH
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(
            df['Outstanding_PH'].astype(str).str.replace(',', ''), 
            errors='coerce'
        )
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    # Clean OD
    for col in ['LastOD', 'max_OD']:
        if col in df.columns:
            df[f'{col}_clean'] = pd.to_numeric(df[col], errors='coerce')
    
    # Clean Scoring
    if 'Hasil_Scoring' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring'].fillna('(Semua)').astype(str).str.strip()
    
    # Clean Segmen
    if 'Segmen' in df.columns:
        df['Segmen_clean'] = df['Segmen'].fillna('-').astype(str).str.strip()
        df['Segmen_clean'] = df['Segmen_clean'].replace('Unknown', '-')
    
    # Clean JenisKendaraan
    if 'JenisKendaraan' in df.columns:
        df['JenisKendaraan_clean'] = df['JenisKendaraan'].fillna('Tidak Diketahui').astype(str).str.strip()
        df['JenisKendaraan_clean'] = df['JenisKendaraan_clean'].replace('-', 'Tidak Diketahui')
    
    # Clean Pekerjaan
    if 'Pekerjaan' in df.columns:
        df['Pekerjaan_clean'] = df['Pekerjaan'].fillna('-').astype(str).str.strip()
    
    # Time features
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Quarter'] = df['action_on_parsed'].dt.quarter
    
    # Clean categorical fields
    categorical_fields = [
        'desc_status_apps', 'Jabatan',
        'branch_name', 'Tujuan_Kredit', 'user_name', 'position_name'
    ]
    
    for field in categorical_fields:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Tidak Diketahui').astype(str).str.strip()
    
    #  TAMBAHAN: REMOVE DUPLICATE STATUS (SELECTIVE)
    df = remove_duplicate_status(df)
    
    return df


def calculate_sla_per_status(df):
    """
    Calculate SLA correctly based on progression:
    - If only 1 row for an apps_id: Recommendation to action_on (same row)
    - If multiple rows: From previous row's action_on to current row's action_on
    """
    df_with_sla = df.copy()
    
    # Sort by apps_id and action_on
    df_with_sla = df_with_sla.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
    
    # Initialize columns
    df_with_sla['SLA_Hours'] = None
    df_with_sla['SLA_Formatted'] = None
    df_with_sla['SLA_From'] = None
    df_with_sla['SLA_To'] = None
    
    # Group by apps_id
    for apps_id, group in df_with_sla.groupby('apps_id'):
        indices = group.index.tolist()
        
        for i, idx in enumerate(indices):
            if len(indices) == 1:
                # Single row: Recommendation to action_on
                recommendation_time = df_with_sla.loc[idx, 'Recommendation_parsed']
                action_time = df_with_sla.loc[idx, 'action_on_parsed']
                from_label = 'Recommendation'
                to_label = 'Action'
            else:
                # Multiple rows
                if i == 0:
                    # First row: Recommendation to action_on
                    recommendation_time = df_with_sla.loc[idx, 'Recommendation_parsed']
                    action_time = df_with_sla.loc[idx, 'action_on_parsed']
                    from_label = 'Recommendation'
                    to_label = 'Action'
                else:
                    # Subsequent rows: Previous action_on to current action_on
                    prev_idx = indices[i - 1]
                    recommendation_time = df_with_sla.loc[prev_idx, 'action_on_parsed']
                    action_time = df_with_sla.loc[idx, 'action_on_parsed']
                    prev_status = df_with_sla.loc[prev_idx, 'apps_status_clean']
                    curr_status = df_with_sla.loc[idx, 'apps_status_clean']
                    from_label = f"{prev_status}"
                    to_label = f"{curr_status}"
            
            if pd.notna(recommendation_time) and pd.notna(action_time):
                sla_result = calculate_sla_working_hours(recommendation_time, action_time)
                if sla_result:
                    df_with_sla.loc[idx, 'SLA_Hours'] = sla_result['total_hours']
                    df_with_sla.loc[idx, 'SLA_Formatted'] = sla_result['formatted']
            
            df_with_sla.loc[idx, 'SLA_From'] = from_label
            df_with_sla.loc[idx, 'SLA_To'] = to_label
    
    return df_with_sla


def remove_duplicate_status(df):
    """
    Remove duplicate status HANYA untuk RECOMMENDED CA dan RECOMMENDED CA WITH COND.
    Status lain seperti PENDING CA boleh double.
    
    Logic:
    - For RECOMMENDED CA: Keep hanya first occurrence (delete duplicates)
    - For other status: Keep all (allow duplicates)
    """
    df_dedup = df.copy()
    
    # Step 1: Sort untuk consistency
    df_dedup = df_dedup.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
    
    # Step 2: Define target status untuk deduplication
    status_to_deduplicate = [
        'RECOMMENDED CA',
        'RECOMMENDED CA WITH COND',
        'RECOMMENDED CA WITH CONDITION'
    ]
    
    # Step 3: Mark duplikasi dan target status
    df_dedup['_dup_count'] = df_dedup.groupby(['apps_id', 'apps_status_clean']).cumcount()
    df_dedup['_is_target'] = df_dedup['apps_status_clean'].isin(status_to_deduplicate)
    
    # Step 4: Filter dengan logic: Keep jika first (_dup_count==0) ATAU bukan target status
    keep_mask = (df_dedup['_dup_count'] == 0) | (~df_dedup['_is_target'])
    df_dedup = df_dedup[keep_mask].drop(['_dup_count', '_is_target'], axis=1).reset_index(drop=True)
    
    return df_dedup


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
            'Segmen', 'action_on', 'Outstanding_PH',
            'Pekerjaan', 'Jabatan', 'Hasil_Scoring',
            'JenisKendaraan', 'branch_name', 'Tujuan_Kredit',
            'Recommendation', 'LastOD', 'max_OD'
        ]
        
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"Kolom yang hilang: {', '.join(missing)}")
            return None
        
        df_clean = preprocess_data(df)
        df_clean = calculate_sla_per_status(df_clean)
        
        return df_clean
    except Exception as e:
        st.error(f"Error saat memuat data: {str(e)}")
        return None
# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main Streamlit application"""
    
    # BCA Finance Header - Simple Text Only
    st.markdown("""
    <div class="header-container">
        <div style="text-align: center;">
            <h1 style="margin: 0; font-size: 42px; letter-spacing: 1px; color: white !important;">Dashboard Analisis CA</h1>
            <p style="color: #e3f2fd !important; margin-top: 12px; font-size: 17px;">BCA Finance - Monitoring & Evaluasi Kinerja Credit Analyst</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    with st.spinner("Memuat data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("Tidak dapat memuat data")
        st.stop()
    
    # TOP METRICS
    st.markdown("### Ringkasan Utama")
    
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    sla_with_data = df['SLA_Hours'].notna().sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("Total Data", f"{total_records:,}")
        st.markdown('<p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">Total semua transaksi dalam sistem</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-box-success">', unsafe_allow_html=True)
        st.metric("Total AppID", f"{unique_apps:,}")
        st.markdown('<p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">Jumlah AppID Distinct</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-box-warning">', unsafe_allow_html=True)
        sla_pct = f"{sla_with_data/total_records*100:.1f}%"
        st.metric("Data SLA Lengkap", f"{sla_with_data:,}")
        st.markdown(f'<p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">Cakupan: {sla_pct} dari total data</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        sla_valid = df[df['SLA_Hours'].notna()]
        if len(sla_valid) > 0:
            avg_hours = sla_valid['SLA_Hours'].mean()
            avg_formatted = convert_hours_to_hm(avg_hours)
            st.markdown('<div class="metric-box-danger">', unsafe_allow_html=True)
            st.metric("Rata-rata Waktu Proses", avg_formatted)
            st.markdown('<p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">Per History</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # SIDEBAR FILTERS
    st.sidebar.markdown("## Filter Data")
    st.sidebar.markdown("---")
    
    if 'apps_status_clean' in df.columns:
        all_status = sorted([x for x in df['apps_status_clean'].unique() if x != 'Tidak Diketahui'])
        selected_status = st.sidebar.multiselect(
            "Status Aplikasi", 
            all_status, 
            default=all_status,
            help="Pilih satu atau lebih status aplikasi"
        )
    else:
        selected_status = []
    
    if 'Scoring_Detail' in df.columns:
        all_scoring = sorted([x for x in df['Scoring_Detail'].unique() if x != '(Semua)'])
        selected_scoring = st.sidebar.multiselect(
            "Hasil Penilaian", 
            all_scoring, 
            default=all_scoring,
            help="Filter berdasarkan hasil scoring"
        )
    else:
        selected_scoring = []
    
    if 'Segmen_clean' in df.columns:
        all_segmen = sorted(df['Segmen_clean'].unique().tolist())
        selected_segmen = st.sidebar.selectbox(
            "Segmen Kredit", 
            ['Semua Segmen'] + all_segmen,
            help="Pilih segmen kredit tertentu"
        )
    else:
        selected_segmen = 'Semua Segmen'
    
    if 'branch_name_clean' in df.columns:
        all_branches = sorted(df['branch_name_clean'].unique().tolist())
        selected_branch = st.sidebar.selectbox(
            "Cabang", 
            ['Semua Cabang'] + all_branches,
            help="Filter berdasarkan cabang"
        )
    else:
        selected_branch = 'Semua Cabang'
    
    # Apply filters
    df_filtered = df.copy()
    
    if selected_status:
        df_filtered = df_filtered[df_filtered['apps_status_clean'].isin(selected_status)]
    
    if selected_scoring:
        df_filtered = df_filtered[df_filtered['Scoring_Detail'].isin(selected_scoring)]
    
    if selected_segmen != 'Semua Segmen':
        df_filtered = df_filtered[df_filtered['Segmen_clean'] == selected_segmen]
    
    if selected_branch != 'Semua Cabang':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Hasil Filter")
    st.sidebar.success(f"**{len(df_filtered):,}** catatan ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f"**{df_filtered['apps_id'].nunique():,}** aplikasi unik")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        " Waktu Proses",
        " Data Detail",
        " Analisis Plafon",
        " Kinerja Cabang & CA",
        " Status & Penilaian",
        " Dampak Keterlambatan",
        " Insights & Rekomendasi",
        " Unduh Data"
    ])

    # ====== TAB 1: SLA ANALYSIS ======
    with tab1:
        st.markdown("## Analisis Waktu Proses Aplikasi")
        
        st.markdown("""
        <div class="info-box">
        <h4>Penjelasan Waktu Proses (SLA)</h4>
        <p><strong>SLA (Service Level Agreement)</strong> adalah target waktu yang ditetapkan untuk menyelesaikan proses kredit.</p>
        <ul>
            <li><strong>Perhitungan</strong>: Dari waktu Rekomendasi sampai waktu Aksi</li>
            <li><strong>Jam Kerja</strong>: 08:30 - 15:30 (tidak termasuk weekend & libur nasional)</li>
            <li><strong>Target</strong>: Maksimal 35 jam kerja (setara 5 hari kerja)</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Overall SLA stats
        sla_valid = df_filtered[df_filtered['SLA_Hours'].notna()]
        
        st.markdown("### Statistik Waktu Proses ")
        st.caption("*Perhitungan berdasarkan jam kerja 08:30 - 15:30, exclude weekend dan hari libur*")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if len(sla_valid) > 0:
                avg_hours = sla_valid['SLA_Hours'].mean()
                avg_formatted = convert_hours_to_hm(avg_hours)
                st.markdown('<div class="metric-box" style="text-align: center;">', unsafe_allow_html=True)
                st.markdown(f'<h3 style="color: #003d7a; margin-bottom: 10px;">Rata-rata</h3>', unsafe_allow_html=True)
                st.markdown(f'<h2 style="color: #0066b3; margin: 0;">{avg_formatted}</h2>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if len(sla_valid) > 0:
                median_hours = sla_valid['SLA_Hours'].median()
                median_formatted = convert_hours_to_hm(median_hours)
                st.markdown('<div class="metric-box-success" style="text-align: center;">', unsafe_allow_html=True)
                st.markdown(f'<h3 style="color: #003d7a; margin-bottom: 10px;">Nilai Tengah</h3>', unsafe_allow_html=True)
                st.markdown(f'<h2 style="color: #1e88e5; margin: 0;">{median_formatted}</h2>', unsafe_allow_html=True)
                st.markdown('<p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">50% data di bawah nilai ini</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        with col3:
            if len(sla_valid) > 0:
            # Calculate mode (most frequent value)
                mode_hours = sla_valid['SLA_Hours'].mode()
            if len(mode_hours) > 0:
                mode_formatted = convert_hours_to_hm(mode_hours.iloc[0])
            else:
                mode_formatted = "-"
            st.markdown('<div class="metric-box" style="min-height: 160px; display: flex; flex-direction: column; justify-content: space-between;">', unsafe_allow_html=True)
            st.metric("Modus Waktu Proses", mode_formatted)
            st.markdown('<p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">Waktu paling sering muncul</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            if len(sla_valid) > 0:
                min_hours = sla_valid['SLA_Hours'].min()
                min_formatted = convert_hours_to_hm(min_hours)
                st.markdown('<div class="metric-box-success" style="text-align: center;">', unsafe_allow_html=True)
                st.markdown(f'<h3 style="color: #003d7a; margin-bottom: 10px;">Tercepat</h3>', unsafe_allow_html=True)
                st.markdown(f'<h2 style="color: #1e88e5; margin: 0;">{min_formatted}</h2>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col5:
            if len(sla_valid) > 0:
                max_hours = sla_valid['SLA_Hours'].max()
                max_formatted = convert_hours_to_hm(max_hours)
                st.markdown('<div class="metric-box-danger" style="text-align: center;">', unsafe_allow_html=True)
                st.markdown(f'<h3 style="color: #003d7a; margin-bottom: 10px;">Terlama</h3>', unsafe_allow_html=True)
                st.markdown(f'<h2 style="color: #f44336; margin: 0;">{max_formatted}</h2>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # SLA TREND
        st.markdown("### Tren Waktu Proses Bulanan")
        st.caption("*Grafik menunjukkan rata-rata waktu proses per bulan*")
        
        if len(sla_valid) > 0 and 'action_on_parsed' in sla_valid.columns:
            sla_trend = sla_valid.copy()
            sla_trend['YearMonth'] = sla_trend['action_on_parsed'].dt.to_period('M').astype(str)
            
            monthly_avg = sla_trend.groupby('YearMonth')['SLA_Hours'].agg(['mean', 'count']).reset_index()
            monthly_avg.columns = ['Bulan', 'Rata-rata Waktu (Jam)', 'Jumlah Data']
            monthly_avg = monthly_avg.sort_values('Bulan')
            monthly_avg['Rata-rata Waktu (Teks)'] = monthly_avg['Rata-rata Waktu (Jam)'].apply(convert_hours_to_hm)
            
            # Display table
            display_monthly = monthly_avg.rename(columns={
                'Bulan': 'Bulan',
                'Rata-rata Waktu (Teks)': 'Waktu Rata-rata',
                'Jumlah Data': 'Jumlah Aplikasi'
            })
            
            st.dataframe(
                display_monthly[['Bulan', 'Waktu Rata-rata', 'Jumlah Aplikasi']], 
                use_container_width=True, 
                hide_index=True
            )
            
            # Line chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=monthly_avg['Bulan'],
                y=monthly_avg['Rata-rata Waktu (Jam)'],
                mode='lines+markers+text',
                name='Waktu Proses',
                text=[f"{val:.1f} jam" for val in monthly_avg['Rata-rata Waktu (Jam)']],
                textposition='top center',
                textfont=dict(size=11, color='#ffffff'),
                line=dict(color='#0066b3', width=4),
                marker=dict(
                    size=14, 
                    color='#0066b3',
                    line=dict(color='white', width=3),
                    symbol='circle'
                ),
                hovertemplate='<b>%{x}</b><br>' +
                              'Waktu: %{y:.1f} jam<br>' +
                              '<extra></extra>'
            ))
            
            fig.add_hline(
                y=35, 
                line_dash="dash", 
                line_color="#f44336",
                line_width=3,
                annotation_text=" Target: 35 jam",
                annotation_position="right",
                annotation_font_size=13,
                annotation_font_color="#f44336"
            )
            
            fig.update_layout(
                title={
                    'text': "Tren Waktu Proses per Bulan",
                    'font': {'size': 20, 'color': '#ffffff'},
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis_title="Bulan",
                yaxis_title="Waktu Proses (Jam Kerja)",
                hovermode='x unified',
                height=500,
                plot_bgcolor='#1e2129',
                paper_bgcolor='#1e2129',
                font=dict(family='Arial', size=13, color='#e0e0e0'),
                xaxis=dict(
                    showgrid=True,
                    gridcolor='#2d3139',
                    linecolor='#2d3139'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#2d3139',
                    linecolor='#2d3139'
                ),
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # SLA by Status
        st.markdown("### Waktu Proses Berdasarkan Status Aplikasi")
        st.caption("*Tabel menunjukkan perbandingan waktu proses untuk setiap status aplikasi*")
        
        if 'apps_status_clean' in df_filtered.columns:
            status_sla = []
            
            for status in sorted(df_filtered['apps_status_clean'].unique()):
                if status == 'Tidak Diketahui':
                    continue
                
                df_status = df_filtered[df_filtered['apps_status_clean'] == status]
                sla_status = df_status[df_status['SLA_Hours'].notna()]
                
                if len(sla_status) > 0:
                    avg_sla = sla_status['SLA_Hours'].mean()
                    median_sla = sla_status['SLA_Hours'].median()
                    max_sla = sla_status['SLA_Hours'].max()
                    min_sla = sla_status['SLA_Hours'].min()
                    
                    status_sla.append({
                        'Status Aplikasi': status,
                        'Total Data': len(df_status),
                        'Data Lengkap': len(sla_status),
                        'Cakupan': f"{len(sla_status)/len(df_status)*100:.1f}%",
                        'Rata-rata': convert_hours_to_hm(avg_sla),
                        'Nilai Tengah': convert_hours_to_hm(median_sla),
                        'Tercepat': convert_hours_to_hm(min_sla),
                        'Terlama': convert_hours_to_hm(max_sla),
                    })
            
            if status_sla:
                status_sla_df = pd.DataFrame(status_sla)
                st.dataframe(status_sla_df, use_container_width=True, hide_index=True, height=400)
    
    # ====== TAB 2: DETAIL RAW DATA ======
    with tab2:
        st.markdown("## Data Detail Aplikasi Kredit")
        
        st.markdown("""
        <div class="info-box">
        <h4>Cara Menggunakan</h4>
        <p>Tab ini menampilkan daftar lengkap semua aplikasi kredit yang ada dalam sistem.</p>
        <ul>
            <li>Lihat ringkasan semua aplikasi dalam tabel di bawah</li>
            <li>Gunakan kolom pencarian untuk menemukan aplikasi tertentu berdasarkan ID</li>
            <li>Klik untuk melihat detail lengkap setiap aplikasi</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Get all unique apps with their summary info
        apps_summary = []
        
        for app_id in sorted(df_filtered['apps_id'].unique()):
            app_data = df_filtered[df_filtered['apps_id'] == app_id]
            latest_record = app_data.sort_values('action_on_parsed', ascending=False).iloc[0]
            
            apps_summary.append({
                'ID Aplikasi': app_id,
                'Jumlah Catatan': len(app_data),
                'Status Terakhir': latest_record.get('apps_status_clean', 'N/A'),
                'Aksi Terakhir': latest_record.get('action_on_parsed', pd.NaT),
                'Segmen': latest_record.get('Segmen_clean', 'N/A'),
                'Kategori Plafon': latest_record.get('OSPH_Category', 'N/A'),
                'Cabang': latest_record.get('branch_name_clean', 'N/A'),
                'Credit Analyst': latest_record.get('user_name_clean', 'N/A')
            })
        
        apps_df = pd.DataFrame(apps_summary)
        apps_df = apps_df.sort_values('Aksi Terakhir', ascending=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-box-success" style="text-align: center; padding: 25px;">
            <h3 style="color: #003d7a; margin-bottom: 10px;">Total No Kontrak</h3>
            <h1 style="color: #1e88e5; margin: 10px 0; font-size: 48px;">{len(apps_df):,}</h1>
            <p style="color: #90a4ae; font-size: 14px;">Jumlah AppID</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_catatan = apps_df['Jumlah Catatan'].sum()
            st.markdown(f"""
            <div class="metric-box" style="text-align: center; padding: 25px;">
            <h3 style="color: #003d7a; margin-bottom: 10px;">Total Catatan</h3>
            <h1 style="color: #0066b3; margin: 10px 0; font-size: 48px;">{total_catatan:,}</h1>
            <p style="color: #90a4ae; font-size: 14px;">Total transaksi dalam sistem</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### Daftar Semua Aplikasi")
        
        # Display all apps in a table
        st.dataframe(
            apps_df.style.format({'Aksi Terakhir': lambda x: x.strftime('%d-%m-%Y %H:%M') if pd.notna(x) else 'N/A'}),
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.markdown("---")
        
        # Search and detail view
        st.markdown("### Cari Detail Aplikasi")
        
        col_search, col_empty = st.columns([2, 2])
        
        with col_search:
            search_input = st.text_input(
                "Masukkan ID Aplikasi:", 
                placeholder="Contoh: 5259031",
                help="Ketik ID aplikasi untuk melihat detail lengkap"
            )
        
        if search_input:
            try:
                search_id = int(search_input)
                app_records = df[df['apps_id'] == search_id].sort_values('action_on_parsed')
                
                if len(app_records) > 0:
                    st.success(f"Ditemukan **{len(app_records)}** catatan untuk ID Aplikasi: **{search_id}**")
                    
                    # Summary
                    st.markdown("#### Ringkasan Aplikasi")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        segmen = app_records['Segmen_clean'].iloc[0] if 'Segmen_clean' in app_records.columns else 'N/A'
                        st.markdown(f"""
                        <div class="metric-box" style="text-align: center; padding: 20px;">
                        <h4 style="color: #003d7a; margin-bottom: 10px;">Segmen</h4>
                        <h3 style="color: #0066b3; margin: 0;">{segmen}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        osph = app_records['OSPH_Category'].iloc[0] if 'OSPH_Category' in app_records.columns else 'N/A'
                        st.markdown(f"""
                        <div class="metric-box-warning" style="text-align: center; padding: 20px;">
                        <h4 style="color: #003d7a; margin-bottom: 10px;">Plafon</h4>
                        <h3 style="color: #d4af37; margin: 0;">{osph}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        branch = app_records['branch_name_clean'].iloc[0] if 'branch_name_clean' in app_records.columns else 'N/A'
                        st.markdown(f"""
                        <div class="metric-box-success" style="text-align: center; padding: 20px;">
                        <h4 style="color: #003d7a; margin-bottom: 10px;">Cabang</h4>
                        <h3 style="color: #1e88e5; margin: 0;">{branch}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col4:
                        ca = app_records['user_name_clean'].iloc[0] if 'user_name_clean' in app_records.columns else 'N/A'
                        st.markdown(f"""
                        <div class="metric-box" style="text-align: center; padding: 20px;">
                        <h4 style="color: #003d7a; margin-bottom: 10px;">CA</h4>
                        <h3 style="color: #0066b3; margin: 0;">{ca}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Display ALL records
                    st.markdown("#### Riwayat Lengkap Aplikasi")
                    
                    display_cols = [
                        'apps_status_clean', 'action_on_parsed', 'Recommendation_parsed',
                        'SLA_Hours', 'SLA_Formatted',
                        'Scoring_Detail', 'OSPH_clean', 'LastOD_clean',
                        'user_name_clean', 'Pekerjaan_clean', 'JenisKendaraan_clean'
                    ]
                    
                    col_rename = {
                        'apps_status_clean': 'Status',
                        'action_on_parsed': 'Waktu Aksi',
                        'Recommendation_parsed': 'Waktu Rekomendasi',
                        'SLA_Hours': 'SLA (Jam)',
                        'SLA_Formatted': 'SLA',
                        'Scoring_Detail': 'Hasil Penilaian',
                        'OSPH_clean': 'Plafon (Rp)',
                        'LastOD_clean': 'Tunggakan Terakhir (Hari)',
                        'user_name_clean': 'Credit Analyst',
                        'Pekerjaan_clean': 'Pekerjaan',
                        'JenisKendaraan_clean': 'Jenis Kendaraan'
                    }
                    
                    available_cols = [c for c in display_cols if c in app_records.columns]
                    display_df = app_records[available_cols].rename(columns=col_rename)
                    
                    st.dataframe(display_df.reset_index(drop=True), use_container_width=True, height=400)
                    
                else:
                    st.warning(f"Tidak ditemukan data untuk ID Aplikasi: {search_id}")
            
            except ValueError:
                st.error("Mohon masukkan ID Aplikasi yang valid (angka)")
    
    # ====== TAB 3: OSPH ANALYSIS ======
    with tab3:
        st.markdown("## Analisis Plafon Kredit (OSPH)")
        
        st.markdown("""
        <div class="info-box">
        <h4>Penjelasan Analisis</h4>
        <p><strong>OSPH (Outstanding Plafon Hutang)</strong> adalah total plafon kredit yang tersedia untuk nasabah.</p>
        <p>Analisis ini mengelompokkan aplikasi berdasarkan:</p>
        <ul>
            <li><strong>Kategori Plafon</strong>: 0-250 Juta, 250-500 Juta, dan >500 Juta</li>
            <li><strong>Dimensi Analisis</strong>: Pekerjaan, Status Aplikasi, Jenis Kendaraan, dan Hasil Scoring</li>
        </ul>
        <p><strong>Catatan:</strong> Perhitungan berdasarkan aplikasi unik (bukan duplikasi)</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Define OSPH ranges order
        osph_order = ['0 - 250 Juta', '250 - 500 Juta', 'Lebih dari 500 Juta']
        
        # Create subtabs for different analyses
        subtab1, subtab2, subtab3, subtab4 = st.tabs([
            " Berdasarkan Pekerjaan",
            " Berdasarkan Status",
            " Berdasarkan Jenis Kendaraan",
            " Berdasarkan Hasil Scoring"
        ])
        
        # SUBTAB 1: BY PEKERJAAN
        with subtab1:
            st.markdown("### Analisis Plafon Berdasarkan Pekerjaan")
            
            # Get top pekerjaan
            top_pekerjaan = df_filtered.drop_duplicates('apps_id')['Pekerjaan_clean'].value_counts().head(10).index.tolist()
            
            # Create pivot tables for each segment
            for idx, segmen in enumerate(['-', 'KKB', 'CS NEW', 'CS USED']):
                # Color coding for different segments
                if idx == 0:
                    header_color = "metric-box"
                elif idx == 1:
                    header_color = "metric-box-success"
                elif idx == 2:
                    header_color = "metric-box-warning"
                else:
                    header_color = "metric-box-danger"
                
                st.markdown(f"""
                <div class="{header_color}">
                <h3>Segmen: {segmen if segmen != '-' else 'DS'}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                df_segmen = df_filtered[df_filtered['Segmen_clean'] == segmen].drop_duplicates('apps_id')
                
                total_apps = len(df_segmen)
                total_records = len(df_filtered[df_filtered['Segmen_clean'] == segmen])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Aplikasi Unik", f"{total_apps:,}")
                with col2:
                    st.metric("Total Catatan", f"{total_records:,}")
                
                if len(df_segmen) > 0:
                    # Create pivot: OSPH Range x Pekerjaan
                    pivot_data = []
                    
                    for osph_range in osph_order:
                        df_osph = df_segmen[df_segmen['OSPH_Category'] == osph_range]
                        
                        row = {'Kategori Plafon': osph_range}
                        
                        for pekerjaan in top_pekerjaan:
                            count = len(df_osph[df_osph['Pekerjaan_clean'] == pekerjaan])
                            row[pekerjaan] = count if count > 0 else 0
                        
                        # Add total
                        row['TOTAL'] = len(df_osph)
                        
                        pivot_data.append(row)
                    
                    # Add TOTAL row
                    total_row = {'Kategori Plafon': 'TOTAL SEMUA'}
                    for pekerjaan in top_pekerjaan:
                        count = len(df_segmen[df_segmen['Pekerjaan_clean'] == pekerjaan])
                        total_row[pekerjaan] = count if count > 0 else 0
                    total_row['TOTAL'] = len(df_segmen)
                    pivot_data.append(total_row)
                    
                    pivot_df = pd.DataFrame(pivot_data)
                    
                    st.dataframe(pivot_df, use_container_width=True, hide_index=True, height=300)
                    
                    # Visualization
                    pivot_plot = pivot_df[pivot_df['Kategori Plafon'] != 'TOTAL SEMUA'].copy()
                    
                    if len(pivot_plot) > 0:
                        plot_data = []
                        for _, row in pivot_plot.iterrows():
                            osph = row['Kategori Plafon']
                            for col in pivot_plot.columns:
                                if col not in ['Kategori Plafon', 'TOTAL'] and row[col] > 0:
                                    plot_data.append({
                                        'Kategori Plafon': osph,
                                        'Pekerjaan': col,
                                        'Jumlah': row[col]
                                    })
                        
                        if plot_data:
                            plot_df = pd.DataFrame(plot_data)
                            fig = px.bar(
                                plot_df,
                                x='Kategori Plafon',
                                y='Jumlah',
                                color='Pekerjaan',
                                title=f"Distribusi Plafon untuk Segmen {segmen if segmen != '-' else 'DS'}",
                                barmode='group',
                                color_discrete_sequence=px.colors.qualitative.Set3,
                                text='Jumlah'
                            )
                            fig.update_traces(textposition='outside', textfont_size=11)
                            fig.update_layout(
                                height=400,
                                plot_bgcolor='#1e2129',
                                paper_bgcolor='#1e2129',
                                font=dict(family='Arial', size=12, color='#e0e0e0')
                            )
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"Tidak ada data untuk Segmen {segmen}")
                
                st.markdown("---")
        
        # SUBTAB 2: BY STATUS
        with subtab2:
            st.markdown("### Analisis Plafon Berdasarkan Status Aplikasi")
            
            # Get top status
            top_status = df_filtered.drop_duplicates('apps_id')['apps_status_clean'].value_counts().head(10).index.tolist()
            
            # Create pivot tables for each segment
            for idx, segmen in enumerate(['-', 'KKB', 'CS NEW', 'CS USED']):
                if idx == 0:
                    header_color = "metric-box"
                elif idx == 1:
                    header_color = "metric-box-success"
                elif idx == 2:
                    header_color = "metric-box-warning"
                else:
                    header_color = "metric-box-danger"
                
                st.markdown(f"""
                <div class="{header_color}">
                <h3>Segmen: {segmen if segmen != '-' else 'DS'}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                df_segmen = df_filtered[df_filtered['Segmen_clean'] == segmen].drop_duplicates('apps_id')
                
                total_apps = len(df_segmen)
                total_records = len(df_filtered[df_filtered['Segmen_clean'] == segmen])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Aplikasi Unik", f"{total_apps:,}")
                with col2:
                    st.metric("Total Catatan", f"{total_records:,}")
                
                if len(df_segmen) > 0:
                    # Create pivot: OSPH Range x Status
                    pivot_data = []
                    
                    for osph_range in osph_order:
                        df_osph = df_segmen[df_segmen['OSPH_Category'] == osph_range]
                        
                        row = {'Kategori Plafon': osph_range}
                        
                        for status in top_status:
                            count = len(df_osph[df_osph['apps_status_clean'] == status])
                            row[status] = count if count > 0 else 0
                        
                        row['TOTAL'] = len(df_osph)
                        
                        pivot_data.append(row)
                    
                    # Add TOTAL row
                    total_row = {'Kategori Plafon': 'TOTAL SEMUA'}
                    for status in top_status:
                        count = len(df_segmen[df_segmen['apps_status_clean'] == status])
                        total_row[status] = count if count > 0 else 0
                    total_row['TOTAL'] = len(df_segmen)
                    pivot_data.append(total_row)
                    
                    pivot_df = pd.DataFrame(pivot_data)
                    
                    st.dataframe(pivot_df, use_container_width=True, hide_index=True, height=300)
                    
                    # Visualization
                    pivot_plot = pivot_df[pivot_df['Kategori Plafon'] != 'TOTAL SEMUA'].copy()
                    
                    if len(pivot_plot) > 0:
                        plot_data = []
                        for _, row in pivot_plot.iterrows():
                            osph = row['Kategori Plafon']
                            for col in pivot_plot.columns:
                                if col not in ['Kategori Plafon', 'TOTAL'] and row[col] > 0:
                                    plot_data.append({
                                        'Kategori Plafon': osph,
                                        'Status': col,
                                        'Jumlah': row[col]
                                    })
                        
                        if plot_data:
                            plot_df = pd.DataFrame(plot_data)
                            fig = px.bar(
                                plot_df,
                                x='Kategori Plafon',
                                y='Jumlah',
                                color='Status',
                                title=f"Distribusi Plafon untuk Segmen {segmen if segmen != '-' else 'DS'}",
                                barmode='group',
                                color_discrete_sequence=px.colors.qualitative.Pastel,
                                text='Jumlah'
                            )
                            fig.update_traces(textposition='outside', textfont_size=11)
                            fig.update_layout(
                                height=400,
                                plot_bgcolor='#1e2129',
                                paper_bgcolor='#1e2129',
                                font=dict(family='Arial', size=12, color='#e0e0e0')
                            )
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"Tidak ada data untuk Segmen {segmen}")
                
                st.markdown("---")
        
        # SUBTAB 3: BY JENIS KENDARAAN
        with subtab3:
            st.markdown("### Analisis Plafon Berdasarkan Jenis Kendaraan")
            
            # Get top jenis kendaraan
            top_kendaraan = df_filtered.drop_duplicates('apps_id')['JenisKendaraan_clean'].value_counts().head(10).index.tolist()
            
            # Create pivot tables for each segment
            for idx, segmen in enumerate(['-', 'KKB', 'CS NEW', 'CS USED']):
                if idx == 0:
                    header_color = "metric-box"
                elif idx == 1:
                    header_color = "metric-box-success"
                elif idx == 2:
                    header_color = "metric-box-warning"
                else:
                    header_color = "metric-box-danger"
                
                st.markdown(f"""
                <div class="{header_color}">
                <h3>Segmen: {segmen if segmen != '-' else 'DS'}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                df_segmen = df_filtered[df_filtered['Segmen_clean'] == segmen].drop_duplicates('apps_id')
                
                total_apps = len(df_segmen)
                total_records = len(df_filtered[df_filtered['Segmen_clean'] == segmen])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Aplikasi Unik", f"{total_apps:,}")
                with col2:
                    st.metric("Total Catatan", f"{total_records:,}")
                
                if len(df_segmen) > 0:
                    # Create pivot: OSPH Range x Jenis Kendaraan
                    pivot_data = []
                    
                    for osph_range in osph_order:
                        df_osph = df_segmen[df_segmen['OSPH_Category'] == osph_range]
                        
                        row = {'Kategori Plafon': osph_range}
                        
                        for kendaraan in top_kendaraan:
                            count = len(df_osph[df_osph['JenisKendaraan_clean'] == kendaraan])
                            row[kendaraan] = count if count > 0 else 0
                        
                        row['TOTAL'] = len(df_osph)
                        
                        pivot_data.append(row)
                    
                    # Add TOTAL row
                    total_row = {'Kategori Plafon': 'TOTAL SEMUA'}
                    for kendaraan in top_kendaraan:
                        count = len(df_segmen[df_segmen['JenisKendaraan_clean'] == kendaraan])
                        total_row[kendaraan] = count if count > 0 else 0
                    total_row['TOTAL'] = len(df_segmen)
                    pivot_data.append(total_row)
                    
                    pivot_df = pd.DataFrame(pivot_data)
                    
                    st.dataframe(pivot_df, use_container_width=True, hide_index=True, height=300)
                    
                    # Visualization
                    pivot_plot = pivot_df[pivot_df['Kategori Plafon'] != 'TOTAL SEMUA'].copy()
                    
                    if len(pivot_plot) > 0:
                        plot_data = []
                        for _, row in pivot_plot.iterrows():
                            osph = row['Kategori Plafon']
                            for col in pivot_plot.columns:
                                if col not in ['Kategori Plafon', 'TOTAL'] and row[col] > 0:
                                    plot_data.append({
                                        'Kategori Plafon': osph,
                                        'Jenis Kendaraan': col,
                                        'Jumlah': row[col]
                                    })
                        
                        if plot_data:
                            plot_df = pd.DataFrame(plot_data)
                            fig = px.bar(
                                plot_df,
                                x='Kategori Plafon',
                                y='Jumlah',
                                color='Jenis Kendaraan',
                                title=f"Distribusi Plafon untuk Segmen {segmen if segmen != '-' else 'DS'}",
                                barmode='group',
                                color_discrete_sequence=px.colors.qualitative.Safe,
                                text='Jumlah'
                            )
                            fig.update_traces(textposition='outside', textfont_size=11)
                            fig.update_layout(
                                height=450,
                                plot_bgcolor='#1e2129',
                                paper_bgcolor='#1e2129',
                                showlegend=True,
                                font=dict(family='Arial', size=13, color='#e0e0e0'),
                                title_font_size=16,
                                title_font_color='#ffffff',
                                xaxis=dict(
                                    showgrid=False,
                                    title_font_size=14,
                                    tickangle=-45
                                ),
                                yaxis=dict(
                                    showgrid=True,
                                    gridcolor='#2d3139',
                                    title_font_size=14
                                )
                            )
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"Tidak ada data untuk Segmen {segmen}")
                
                st.markdown("---")
        
        # SUBTAB 4: BY HASIL SCORING (NEW)
        with subtab4:
            st.markdown("### Analisis Plafon Berdasarkan Hasil Scoring")
            
            # Get top scoring results
            top_scoring = df_filtered.drop_duplicates('apps_id')['Scoring_Detail'].value_counts().head(10).index.tolist()
            
            # Create pivot tables for each segment
            for idx, segmen in enumerate(['-', 'KKB', 'CS NEW', 'CS USED']):
                if idx == 0:
                    header_color = "metric-box"
                elif idx == 1:
                    header_color = "metric-box-success"
                elif idx == 2:
                    header_color = "metric-box-warning"
                else:
                    header_color = "metric-box-danger"
                
                st.markdown(f"""
                <div class="{header_color}">
                <h3>Segmen: {segmen if segmen != '-' else 'DS'}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                df_segmen = df_filtered[df_filtered['Segmen_clean'] == segmen].drop_duplicates('apps_id')
                
                total_apps = len(df_segmen)
                total_records = len(df_filtered[df_filtered['Segmen_clean'] == segmen])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Aplikasi Unik", f"{total_apps:,}")
                with col2:
                    st.metric("Total Catatan", f"{total_records:,}")
                
                if len(df_segmen) > 0:
                    # Create pivot: OSPH Range x Hasil Scoring
                    pivot_data = []
                    
                    for osph_range in osph_order:
                        df_osph = df_segmen[df_segmen['OSPH_Category'] == osph_range]
                        
                        row = {'Kategori Plafon': osph_range}
                        
                        for scoring in top_scoring:
                            count = len(df_osph[df_osph['Scoring_Detail'] == scoring])
                            row[scoring] = count if count > 0 else 0
                        
                        row['TOTAL'] = len(df_osph)
                        
                        pivot_data.append(row)
                    
                    # Add TOTAL row
                    total_row = {'Kategori Plafon': 'TOTAL SEMUA'}
                    for scoring in top_scoring:
                        count = len(df_segmen[df_segmen['Scoring_Detail'] == scoring])
                        total_row[scoring] = count if count > 0 else 0
                    total_row['TOTAL'] = len(df_segmen)
                    pivot_data.append(total_row)
                    
                    pivot_df = pd.DataFrame(pivot_data)
                    
                    st.dataframe(pivot_df, use_container_width=True, hide_index=True, height=300)
                    
                    # Visualization
                    pivot_plot = pivot_df[pivot_df['Kategori Plafon'] != 'TOTAL SEMUA'].copy()
                    
                    if len(pivot_plot) > 0:
                        plot_data = []
                        for _, row in pivot_plot.iterrows():
                            osph = row['Kategori Plafon']
                            for col in pivot_plot.columns:
                                if col not in ['Kategori Plafon', 'TOTAL'] and row[col] > 0:
                                    plot_data.append({
                                        'Kategori Plafon': osph,
                                        'Hasil Scoring': col,
                                        'Jumlah': row[col]
                                    })
                        
                        if plot_data:
                            plot_df = pd.DataFrame(plot_data)
                            fig = px.bar(
                                plot_df,
                                x='Kategori Plafon',
                                y='Jumlah',
                                color='Hasil Scoring',
                                title=f"Distribusi Plafon untuk Segmen {segmen if segmen != '-' else 'DS'}",
                                barmode='group',
                                color_discrete_sequence=px.colors.qualitative.Vivid,
                                text='Jumlah'
                            )
                            fig.update_traces(textposition='outside', textfont_size=11)
                            fig.update_layout(
                                height=450,
                                plot_bgcolor='#1e2129',
                                paper_bgcolor='#1e2129',
                                showlegend=True,
                                font=dict(family='Arial', size=13, color='#e0e0e0'),
                                title_font_size=16,
                                title_font_color='#ffffff',
                                xaxis=dict(
                                    showgrid=False,
                                    title_font_size=14,
                                    tickangle=-45
                                ),
                                yaxis=dict(
                                    showgrid=True,
                                    gridcolor='#2d3139',
                                    title_font_size=14
                                )
                            )
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"Tidak ada data untuk Segmen {segmen}")
                
                st.markdown("---")

    
    # ====== TAB 4: BRANCH & CA PERFORMANCE ======
    with tab4:
        st.markdown("## Analisis Kinerja Cabang & Credit Analyst")
        
        subtab1, subtab2 = st.tabs([" Kinerja Cabang", " Kinerja Credit Analyst"])
        
        # Branch Performance
        with subtab1:
            st.markdown("""
            <div class="info-box">
            <h4>Penjelasan Metrik Kinerja Cabang</h4>
            <ul>
                <li><strong>Total Aplikasi Unik</strong>: Jumlah pengajuan kredit berbeda (tanpa duplikasi)</li>
                <li><strong>Tingkat Persetujuan</strong>: Persentase aplikasi yang disetujui</li>
                <li><strong>Waktu Proses Rata-rata</strong>: Durasi proses kredit dalam jam kerja</li>
                <li><strong>Total Plafon</strong>: Akumulasi nilai plafon kredit</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            if 'branch_name_clean' in df_filtered.columns:
                branch_perf = []
                
                for branch in sorted(df_filtered['branch_name_clean'].unique()):
                    if branch == 'Tidak Diketahui':
                        continue
                    
                    df_branch = df_filtered[df_filtered['branch_name_clean'] == branch]
                    df_branch_distinct = df_branch.drop_duplicates('apps_id')
                    
                    total_apps = len(df_branch_distinct)
                    total_records = len(df_branch)
                    
                    approve = df_branch_distinct['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                    total_scored = len(df_branch_distinct[df_branch_distinct['Scoring_Detail'] != '(Semua)'])
                    approval_pct = f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "0%"
                    
                    branch_sla = df_branch[df_branch['SLA_Hours'].notna()]
                    avg_sla = convert_hours_to_hm(branch_sla['SLA_Hours'].mean()) if len(branch_sla) > 0 else "-"
                    
                    total_osph = df_branch_distinct['OSPH_clean'].sum()
                    
                    branch_perf.append({
                        'Cabang': branch,
                        'Total Aplikasi Unik': total_apps,
                        'Total Catatan': total_records,
                        'Disetujui': approve,
                        'Tingkat Persetujuan': approval_pct,
                        'Waktu Proses Rata-rata': avg_sla,
                        'Total Plafon': f"Rp {total_osph:,.0f}"
                    })
                
                branch_df = pd.DataFrame(branch_perf).sort_values('Total Aplikasi Unik', ascending=False)
                
                st.markdown("### Tabel Kinerja Seluruh Cabang")
                st.dataframe(branch_df, use_container_width=True, hide_index=True, height=400)
                
                # Charts
                if len(branch_df) > 0:
                    st.markdown("---")
                    st.markdown("### Visualisasi Kinerja Cabang")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig1 = px.bar(
                            branch_df.head(10),
                            x='Cabang',
                            y='Total Aplikasi Unik',
                            title="Top 10 Cabang - Volume Aplikasi Terbanyak",
                            color='Total Aplikasi Unik',
                            color_continuous_scale='Blues',
                            text='Total Aplikasi Unik'
                        )
                        fig1.update_traces(textposition='outside', textfont_size=11)
                        fig1.update_layout(
                            height=400,
                            plot_bgcolor='#1e2129',
                            paper_bgcolor='#1e2129',
                            showlegend=False,
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        branch_df_plot = branch_df.copy()
                        branch_df_plot['Approval_Numeric'] = branch_df_plot['Tingkat Persetujuan'].str.rstrip('%').astype(float)
                        
                        fig2 = px.bar(
                            branch_df_plot.head(10),
                            x='Cabang',
                            y='Approval_Numeric',
                            title="Top 10 Cabang - Tingkat Persetujuan Tertinggi",
                            color='Approval_Numeric',
                            color_continuous_scale='RdYlGn',
                            text=branch_df_plot.head(10)['Tingkat Persetujuan']
                        )
                        fig2.update_traces(textposition='outside', textfont_size=11)
                        fig2.update_layout(
                            yaxis_title="Tingkat Persetujuan (%)",
                            height=400,
                            plot_bgcolor='#1e2129',
                            paper_bgcolor='#1e2129',
                            showlegend=False,
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig2, use_container_width=True)
        
        # CA Performance
        with subtab2:
            st.markdown("""
            <div class="info-box">
            <h4>Penjelasan Metrik Kinerja Credit Analyst</h4>
            <ul>
                <li><strong>Total Aplikasi Unik</strong>: Jumlah pengajuan kredit yang ditangani</li>
                <li><strong>Tingkat Persetujuan</strong>: Persentase aplikasi yang berhasil disetujui</li>
                <li><strong>Waktu Proses Rata-rata</strong>: Efisiensi waktu dalam memproses aplikasi</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            if 'user_name_clean' in df_filtered.columns:
                ca_perf = []
                
                for ca in sorted(df_filtered['user_name_clean'].unique()):
                    if ca == 'Tidak Diketahui':
                        continue
                    
                    df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                    df_ca_distinct = df_ca.drop_duplicates('apps_id')
                    
                    total_apps = len(df_ca_distinct)
                    total_records = len(df_ca)
                    
                    approve = df_ca_distinct['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                    total_scored = len(df_ca_distinct[df_ca_distinct['Scoring_Detail'] != '(Semua)'])
                    approval_pct = f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "0%"
                    
                    ca_sla = df_ca[df_ca['SLA_Hours'].notna()]
                    avg_sla = convert_hours_to_hm(ca_sla['SLA_Hours'].mean()) if len(ca_sla) > 0 else "-"
                    
                    branches = df_ca['branch_name_clean'].unique()
                    main_branch = branches[0] if len(branches) > 0 else "Tidak Diketahui"
                    
                    ca_perf.append({
                        'Nama Credit Analyst': ca,
                        'Cabang': main_branch,
                        'Total Aplikasi Unik': total_apps,
                        'Total Catatan': total_records,
                        'Disetujui': approve,
                        'Tingkat Persetujuan': approval_pct,
                        'Waktu Proses Rata-rata': avg_sla
                    })
                
                ca_df = pd.DataFrame(ca_perf).sort_values('Total Aplikasi Unik', ascending=False)
                
                st.markdown("### Tabel Kinerja Seluruh Credit Analyst")
                st.dataframe(ca_df, use_container_width=True, hide_index=True, height=400)
                
                # Charts
                if len(ca_df) > 0:
                    st.markdown("---")
                    st.markdown("### Visualisasi Kinerja Credit Analyst")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig1 = px.bar(
                            ca_df.head(10),
                            x='Nama Credit Analyst',
                            y='Total Aplikasi Unik',
                            title="Top 10 CA - Volume Aplikasi Terbanyak",
                            color='Total Aplikasi Unik',
                            color_continuous_scale='Greens',
                            text='Total Aplikasi Unik'
                        )
                        fig1.update_traces(textposition='outside', textfont_size=11)
                        fig1.update_layout(
                            height=450,
                            plot_bgcolor='#1e2129',
                            paper_bgcolor='#1e2129',
                            showlegend=False,
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        ca_df_plot = ca_df.copy()
                        ca_df_plot['Approval_Numeric'] = ca_df_plot['Tingkat Persetujuan'].str.rstrip('%').astype(float)
                        
                        fig2 = px.bar(
                            ca_df_plot.head(10),
                            x='Nama Credit Analyst',
                            y='Approval_Numeric',
                            title="Top 10 CA - Tingkat Persetujuan Tertinggi",
                            color='Approval_Numeric',
                            color_continuous_scale='RdYlGn',
                            text=ca_df_plot.head(10)['Tingkat Persetujuan']
                        )
                        fig2.update_traces(textposition='outside', textfont_size=11)
                        fig2.update_layout(
                            yaxis_title="Tingkat Persetujuan (%)",
                            height=450,
                            plot_bgcolor='#1e2129',
                            paper_bgcolor='#1e2129',
                            showlegend=False,
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig2, use_container_width=True)
    
    # ====== TAB 5: STATUS & SCORING ======
    with tab5:
        st.markdown("## Analisis Status Aplikasi & Hasil Penilaian")
        
        st.markdown("""
        <div class="info-box">
        <h4>Penjelasan Tabel</h4>
        <p>Tabel ini menunjukkan hubungan antara <strong>Status Aplikasi</strong> dan <strong>Hasil Penilaian (Scoring)</strong>.</p>
        <ul>
            <li><strong>Baris</strong>: Menunjukkan status aplikasi (Approved, Rejected, dll)</li>
            <li><strong>Kolom</strong>: Menunjukkan hasil penilaian dari sistem scoring</li>
            <li><strong>Nilai</strong>: Jumlah aplikasi unik untuk setiap kombinasi</li>
        </ul>
        <p><strong>Catatan:</strong> Perhitungan berdasarkan aplikasi unik (tanpa duplikasi)</p>
        </div>
        """, unsafe_allow_html=True)
        
        df_distinct = df_filtered.drop_duplicates('apps_id')
        total_apps_distinct = len(df_distinct)
        total_records = len(df_filtered)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-box-success" style="text-align: center; padding: 25px;">
            <h3 style="color: #003d7a; margin-bottom: 10px;">Total Aplikasi Unik</h3>
            <h1 style="color: #1e88e5; margin: 10px 0; font-size: 48px;">{total_apps_distinct:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-box" style="text-align: center; padding: 25px;">
            <h3 style="color: #003d7a; margin-bottom: 10px;">Total Catatan</h3>
            <h1 style="color: #0066b3; margin: 10px 0; font-size: 48px;">{total_records:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### Tabel Silang: Status × Hasil Penilaian")
        
        if 'apps_status_clean' in df_distinct.columns and 'Scoring_Detail' in df_distinct.columns:
            cross_tab = pd.crosstab(
                df_distinct['apps_status_clean'],
                df_distinct['Scoring_Detail'],
                margins=True,
                margins_name='TOTAL'
            )
            
            cross_tab.index.name = 'Status Aplikasi'
            cross_tab.columns.name = 'Hasil Penilaian'
            
            st.dataframe(cross_tab, use_container_width=True, height=400)
            
            st.markdown("---")
            st.markdown("### Visualisasi Heatmap")
            
            cross_tab_no_total = cross_tab.drop('TOTAL', errors='ignore').drop('TOTAL', axis=1, errors='ignore')
            
            if len(cross_tab_no_total) > 0:
                fig = px.imshow(
                    cross_tab_no_total,
                    text_auto=True,
                    title="Distribusi Status × Hasil Penilaian",
                    color_continuous_scale="Blues",
                    aspect="auto"
                )
                fig.update_layout(
                    height=550,
                    xaxis_title="Hasil Penilaian",
                    yaxis_title="Status Aplikasi",
                    font=dict(family='Arial', size=13, color='#e0e0e0'),
                    title_font_size=16,
                    title_font_color='#ffffff'
                )
                fig.update_xaxes(side="bottom")
                st.plotly_chart(fig, use_container_width=True)
    
    # ====== TAB 6: OD IMPACT ======
    with tab6:
        st.markdown("## Analisis Dampak Keterlambatan Pembayaran")
        
        st.markdown("""
        <div class="info-box">
        <h4>Penjelasan Overdue Days (OD)</h4>
        <p><strong>Overdue Days</strong> adalah jumlah hari keterlambatan pembayaran kredit sebelumnya.</p>
        <ul>
            <li><strong>Last OD</strong>: Keterlambatan terakhir yang tercatat</li>
            <li><strong>Max OD</strong>: Keterlambatan terlama yang pernah terjadi</li>
        </ul>
        <p>Analisis ini menunjukkan bagaimana riwayat keterlambatan mempengaruhi persetujuan kredit baru.</p>
        </div>
        """, unsafe_allow_html=True)
        
        df_distinct = df_filtered.drop_duplicates('apps_id')
        total_apps_distinct = len(df_distinct)
        total_records = len(df_filtered)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-box-success" style="text-align: center; padding: 25px;">
            <h3 style="color: #003d7a; margin-bottom: 10px;">Total Aplikasi Unik</h3>
            <h1 style="color: #1e88e5; margin: 10px 0; font-size: 48px;">{total_apps_distinct:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-box" style="text-align: center; padding: 25px;">
            <h3 style="color: #003d7a; margin-bottom: 10px;">Total Catatan</h3>
            <h1 style="color: #0066b3; margin: 10px 0; font-size: 48px;">{total_records:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Keterlambatan Terakhir (Last OD)")
            
            if 'LastOD_clean' in df_distinct.columns:
                df_distinct_copy = df_distinct.copy()
                df_distinct_copy['LastOD_Category'] = pd.cut(
                    df_distinct_copy['LastOD_clean'],
                    bins=[-np.inf, 0, 10, 30, np.inf],
                    labels=['Tidak Ada', '1-10 Hari', '11-30 Hari', 'Lebih dari 30 Hari']
                )
                
                lastod_analysis = []
                
                for cat in ['Tidak Ada', '1-10 Hari', '11-30 Hari', 'Lebih dari 30 Hari']:
                    df_od = df_distinct_copy[df_distinct_copy['LastOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                        
                        lastod_analysis.append({
                            'Kategori': cat,
                            'Total Aplikasi': len(df_od),
                            'Disetujui': approve,
                            'Tingkat Persetujuan': approval_pct
                        })
                
                lastod_df = pd.DataFrame(lastod_analysis)
                st.dataframe(lastod_df, use_container_width=True, hide_index=True)
                
                if len(lastod_df) > 0:
                    lastod_df['Approval_Numeric'] = lastod_df['Tingkat Persetujuan'].str.rstrip('%').astype(float)
                    fig = px.bar(
                        lastod_df,
                        x='Kategori',
                        y='Approval_Numeric',
                        title="Tingkat Persetujuan Berdasarkan Last OD",
                        color='Approval_Numeric',
                        color_continuous_scale='RdYlGn',
                        text='Tingkat Persetujuan'
                    )
                    fig.update_traces(textposition='outside', textfont_size=12)
                    fig.update_layout(
                        yaxis_title="Tingkat Persetujuan (%)",
                        height=350,
                        showlegend=False,
                        plot_bgcolor='#1e2129',
                        paper_bgcolor='#1e2129'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### Keterlambatan Maksimum (Max OD)")
            
            if 'max_OD_clean' in df_distinct.columns:
                df_distinct_copy2 = df_distinct.copy()
                df_distinct_copy2['maxOD_Category'] = pd.cut(
                    df_distinct_copy2['max_OD_clean'],
                    bins=[-np.inf, 0, 15, 45, np.inf],
                    labels=['Tidak Ada', '1-15 Hari', '16-45 Hari', 'Lebih dari 45 Hari']
                )
                
                maxod_analysis = []
                
                for cat in ['Tidak Ada', '1-15 Hari', '16-45 Hari', 'Lebih dari 45 Hari']:
                    df_od = df_distinct_copy2[df_distinct_copy2['maxOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                        
                        maxod_analysis.append({
                            'Kategori': cat,
                            'Total Aplikasi': len(df_od),
                            'Disetujui': approve,
                            'Tingkat Persetujuan': approval_pct
                        })
                
                maxod_df = pd.DataFrame(maxod_analysis)
                st.dataframe(maxod_df, use_container_width=True, hide_index=True)
                
                if len(maxod_df) > 0:
                    maxod_df['Approval_Numeric'] = maxod_df['Tingkat Persetujuan'].str.rstrip('%').astype(float)
                    fig = px.bar(
                        maxod_df,
                        x='Kategori',
                        y='Approval_Numeric',
                        title="Tingkat Persetujuan Berdasarkan Max OD",
                        color='Approval_Numeric',
                        color_continuous_scale='RdYlGn',
                        text='Tingkat Persetujuan'
                    )
                    fig.update_traces(textposition='outside', textfont_size=12)
                    fig.update_layout(
                        yaxis_title="Tingkat Persetujuan (%)",
                        height=350,
                        showlegend=False,
                        plot_bgcolor='#1e2129',
                        paper_bgcolor='#1e2129'
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    # ====== TAB 7: INSIGHTS & RECOMMENDATIONS ======
    with tab7:
        st.markdown("## Insights & Rekomendasi Strategis")
        
        st.markdown("""
        <div class="info-box">
        <h4>Tentang Insights</h4>
        <p>Bagian ini menyajikan analisis mendalam dan rekomendasi strategis berdasarkan data aktual untuk membantu pengambilan keputusan bisnis.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        df_distinct = df_filtered.drop_duplicates('apps_id')
        
        # 1. SLA Performance Analysis
        st.markdown("### 1. Analisis Performa Waktu Proses (SLA)")
        
        sla_data = df_filtered[df_filtered['SLA_Hours'].notna()]
        if len(sla_data) > 0:
            avg_sla = sla_data['SLA_Hours'].mean()
            target_sla = 35
            sla_above_target = (sla_data['SLA_Hours'] > target_sla).sum()
            sla_pct_above = (sla_above_target / len(sla_data)) * 100
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status = "Baik" if avg_sla <= target_sla else "Perlu Perbaikan"
                color = "metric-box-success" if avg_sla <= target_sla else "metric-box-danger"
                st.markdown(f"""
                <div class="{color}" style="text-align: center; padding: 20px;">
                <h4 style="color: #003d7a; margin-bottom: 10px;">Status SLA</h4>
                <h3 style="margin: 0;">{status}</h3>
                <p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">Rata-rata: {avg_sla:.1f} jam (Target: 35 jam)</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-box-warning" style="text-align: center; padding: 20px;">
                <h4 style="color: #003d7a; margin-bottom: 10px;">Melebihi Target</h4>
                <h3 style="color: #d4af37; margin: 0;">{sla_pct_above:.1f}%</h3>
                <p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">{sla_above_target:,} dari {len(sla_data):,} aplikasi</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                if avg_sla > target_sla:
                    improvement = avg_sla - target_sla
                    st.markdown(f"""
                    <div class="metric-box" style="text-align: center; padding: 20px;">
                    <h4 style="color: #003d7a; margin-bottom: 10px;">Potensi Peningkatan</h4>
                    <h3 style="color: #0066b3; margin: 0;">{improvement:.1f} jam</h3>
                    <p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">Efisiensi yang bisa dicapai</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="metric-box-success" style="text-align: center; padding: 20px;">
                    <h4 style="color: #003d7a; margin-bottom: 10px;">Performa Optimal</h4>
                    <h3 style="color: #1e88e5; margin: 0;">Target Tercapai</h3>
                    <p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">SLA dalam batas normal</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("#### Rekomendasi SLA:")
            if avg_sla > target_sla:
                st.markdown("""
                - **Prioritas Tinggi**: Evaluasi proses bottleneck yang menyebabkan keterlambatan
                - Pertimbangkan penambahan resources atau redistribusi beban kerja
                - Implementasi sistem monitoring real-time untuk identifikasi dini aplikasi yang berisiko melebihi SLA
                - Training untuk CA dengan performa SLA di bawah target
                """)
            else:
                st.markdown("""
                - **Pertahankan**: Proses saat ini sudah optimal
                - Monitor konsistensi performa untuk memastikan sustainabilitas
                - Dokumentasikan best practices untuk replikasi ke tim lain
                """)
        
        st.markdown("---")
        
        # 2. Approval Rate Analysis
        st.markdown("### 2. Analisis Tingkat Persetujuan")
        
        approve_count = df_distinct['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
        total_scored = len(df_distinct[df_distinct['Scoring_Detail'] != '(Semua)'])
        
        if total_scored > 0:
            approval_rate = (approve_count / total_scored) * 100
            reject_count = total_scored - approve_count
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-box-success" style="text-align: center; padding: 20px;">
                <h4 style="color: #003d7a; margin-bottom: 10px;">Tingkat Persetujuan</h4>
                <h3 style="color: #1e88e5; margin: 0;">{approval_rate:.1f}%</h3>
                <p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">{approve_count:,} aplikasi disetujui</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-box-danger" style="text-align: center; padding: 20px;">
                <h4 style="color: #003d7a; margin-bottom: 10px;">Ditolak</h4>
                <h3 style="color: #f44336; margin: 0;">{100-approval_rate:.1f}%</h3>
                <p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">{reject_count:,} aplikasi ditolak</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                benchmark = 70
                vs_benchmark = approval_rate - benchmark
                color = "metric-box-success" if vs_benchmark >= 0 else "metric-box-warning"
                symbol = "+" if vs_benchmark >= 0 else ""
                st.markdown(f"""
                <div class="{color}" style="text-align: center; padding: 20px;">
                <h4 style="color: #003d7a; margin-bottom: 10px;">vs Benchmark</h4>
                <h3 style="margin: 0;">{symbol}{vs_benchmark:.1f}%</h3>
                <p style="color: #90a4ae; font-size: 14px; margin-top: 5px;">Benchmark industri: {benchmark}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("#### Rekomendasi Approval Rate:")
            if approval_rate < 60:
                st.markdown("""
                - **Prioritas Kritis**: Review kriteria scoring yang terlalu ketat
                - Analisis penyebab utama penolakan aplikasi
                - Pertimbangkan program pre-screening untuk meningkatkan kualitas aplikasi masuk
                - Evaluasi apakah target market sudah sesuai
                """)
            elif approval_rate < 70:
                st.markdown("""
                - **Perlu Perbaikan**: Tingkatkan kualitas assessment awal
                - Implementasi credit counseling untuk calon nasabah
                - Review kebijakan kredit untuk segmen tertentu
                """)
            else:
                st.markdown("""
                - **Performa Baik**: Tingkat persetujuan sudah sehat
                - Fokus pada kualitas portfolio dan menjaga NPL tetap rendah
                - Monitor untuk memastikan tidak ada penurunan kualitas assessment
                """)
        
        st.markdown("---")
        
        # Summary Recommendations
        st.markdown("### Ringkasan Rekomendasi Prioritas")
        
        st.markdown("""
        <div class="metric-box" style="padding: 25px;">
        <h4 style="color: #003d7a; margin-bottom: 15px;">Action Items - Prioritas Tinggi</h4>
        <ol style="color: #b0bec5; line-height: 2;">
            <li><strong>Optimasi SLA:</strong> Fokus pada cabang dan CA dengan SLA di atas target</li>
            <li><strong>Knowledge Transfer:</strong> Replikasi best practices dari top performers</li>
            <li><strong>Quality Control:</strong> Strengthen pre-screening process untuk meningkatkan approval rate</li>
            <li><strong>Risk Management:</strong> Implementasi stricter criteria untuk aplikant dengan high OD history</li>
            <li><strong>Training & Development:</strong> Program capacity building untuk CA dengan performa rendah</li>
            <li><strong>Technology:</strong> Pertimbangkan otomasi untuk proses yang repetitive untuk percepat SLA</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
    
    # ====== TAB 8: DATA EXPORT ======
    with tab8:
        st.markdown("## Unduh Data & Laporan")
        
        st.markdown("""
        <div class="info-box">
        <h4>Cara Mengunduh Data</h4>
        <p>Anda dapat mengunduh data dalam format CSV untuk analisis lebih lanjut:</p>
        <ul>
            <li><strong>Data Lengkap</strong>: Semua data yang sudah difilter dengan kolom penting</li>
            <li><strong>Ringkasan Statistik</strong>: Metrik utama dan ringkasan analisis</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### Pratinjau Data")
        st.caption("*Menampilkan 100 baris pertama dari data yang difilter*")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed',
            'Recommendation_parsed', 'SLA_Formatted', 'SLA_Hours',
            'Scoring_Detail', 'OSPH_Category', 'Segmen_clean',
            'JenisKendaraan_clean', 'Pekerjaan_clean', 'LastOD_clean',
            'user_name_clean', 'branch_name_clean'
        ]
        
        col_rename = {
            'apps_id': 'ID Aplikasi',
            'apps_status_clean': 'Status',
            'action_on_parsed': 'Waktu Aksi',
            'Recommendation_parsed': 'Waktu Rekomendasi',
            'SLA_Formatted': 'SLA',
            'SLA_Hours': 'SLA (Jam)',
            'Scoring_Detail': 'Hasil Penilaian',
            'OSPH_Category': 'Kategori Plafon',
            'Segmen_clean': 'Segmen',
            'JenisKendaraan_clean': 'Jenis Kendaraan',
            'Pekerjaan_clean': 'Pekerjaan',
            'LastOD_clean': 'Last OD (Hari)',
            'user_name_clean': 'Credit Analyst',
            'branch_name_clean': 'Cabang'
        }
        
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        display_df = df_filtered[available_cols].head(100).rename(columns=col_rename)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.caption(f"Menampilkan 100 dari {len(df_filtered):,} baris data")
        
        st.markdown("---")
        st.markdown("### Unduh File")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="metric-box-success" style="padding: 20px;">
            <h4 style="color: #003d7a; margin-bottom: 10px;">Data Lengkap</h4>
            <p style="color: #90a4ae;">Unduh semua data yang sudah difilter dalam format CSV</p>
            </div>
            """, unsafe_allow_html=True)
            
            csv_data = df_filtered[available_cols].to_csv(index=False)
            st.download_button(
                "📥 Unduh Data Lengkap (CSV)",
                csv_data,
                "data_analisis_kredit.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            st.markdown("""
            <div class="metric-box" style="padding: 20px;">
            <h4 style="color: #003d7a; margin-bottom: 10px;">Ringkasan Statistik</h4>
            <p style="color: #90a4ae;">Unduh metrik utama dan ringkasan dalam format CSV</p>
            </div>
            """, unsafe_allow_html=True)
            
            df_distinct_export = df_filtered.drop_duplicates('apps_id')
            approve_count = df_distinct_export['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
            total_scored = len(df_distinct_export[df_distinct_export['Scoring_Detail'] != '(Semua)'])
            
            summary_data = {
                'Metrik': [
                    'Total Catatan',
                    'Aplikasi Unik',
                    'Data SLA Lengkap',
                    'Rata-rata Waktu Proses (jam)',
                    'Tingkat Persetujuan'
                ],
                'Nilai': [
                    f"{len(df_filtered):,}",
                    f"{df_filtered['apps_id'].nunique():,}",
                    f"{df_filtered['SLA_Hours'].notna().sum():,}",
                    f"{df_filtered['SLA_Hours'].mean():.2f}" if df_filtered['SLA_Hours'].notna().any() else "0",
                    f"{approve_count / total_scored * 100:.1f}%" if total_scored > 0 else "0%"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            csv_summary = summary_df.to_csv(index=False)
            st.download_button(
                " Unduh Ringkasan (CSV)",
                csv_summary,
                "ringkasan_statistik.csv",
                "text/csv",
                use_container_width=True
            )

    
    st.markdown("---")
    
    # Footer
    st.markdown("""
    <div style="background: linear-gradient(135deg, #003d7a 0%, #0066b3 100%); padding: 30px; border-radius: 10px; margin-top: 30px; text-align: center;">
        <div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 20px;">
            <div style="color: white;">
                <h4 style="color: white !important; margin: 0;">Terakhir Diperbarui</h4>
                <p style="color: white !important; margin: 5px 0; font-size: 16px;">{}</p>
            </div>
            <div style="color: white;">
                <h4 style="color: white !important; margin: 0;">Total Data</h4>
                <p style="color: white !important; margin: 5px 0; font-size: 16px;">{:,} catatan</p>
            </div>
            <div style="color: white;">
                <h4 style="color: white !important; margin: 0;">Total AppID</h4>
                <p style="color: white !important; margin: 5px 0; font-size: 16px;">{:,}</p>
            </div>
        </div>
        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.3);">
            <p style="color: #e3f2fd !important; margin: 0; font-size: 14px;">© 2026 BCA Finance - Dashboard CA</p>
            <p style="color: #e3f2fd !important; margin: 5px 0 0 0; font-size: 12px;">Confidential - For Internal Use Only</p>
        </div>
    </div>
    """.format(
        datetime.now().strftime('%d %B %Y, %H:%M:%S'),
        len(df),
        df['apps_id'].nunique()
    ), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
