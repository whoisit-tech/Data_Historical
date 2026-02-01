import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import base64

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

def get_base64_image(image_path):
    """Convert image to base64 for embedding in HTML"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

# ============================================================================
# STYLING - BCA FINANCE THEME
# ============================================================================
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
    }
    
    h1 { 
        color: #003d7a !important;
        text-align: center; 
        font-size: 36px; 
        margin-bottom: 10px;
        font-weight: 700;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    h2 { 
        color: #003d7a !important;
        border-bottom: 3px solid #0066b3; 
        padding-bottom: 10px;
        margin-top: 30px;
        font-weight: 600;
    }
    
    h3, h4 { 
        color: #003d7a !important;
        margin-top: 25px;
        font-weight: 600;
    }
    
    .metric-box {
        background: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        border-left: 6px solid #0066b3;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s;
        margin-bottom: 10px;
    }
    
    .metric-box:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .metric-box-success {
        background: #ffffff;
        border: 2px solid #e0e0e0;
        border-left: 6px solid #1e88e5;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    
    .metric-box-warning {
        background: #ffffff;
        border: 2px solid #e0e0e0;
        border-left: 6px solid #ff9800;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    
    .metric-box-danger {
        background: #ffffff;
        border: 2px solid #e0e0e0;
        border-left: 6px solid #f44336;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    
    .info-box {
        background: #f5f9ff;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #0066b3;
        border-left: 5px solid #0066b3;
        margin: 20px 0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }
    
    .info-box h4 {
        color: #003d7a !important;
        margin-top: 0;
        margin-bottom: 10px;
    }
    
    .info-box p, .info-box ul, .info-box ol {
        color: #333333 !important;
        line-height: 1.6;
    }
    
    .info-box li {
        color: #333333 !important;
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
        color: #333333 !important;
        padding: 10px !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 2px solid #e0e0e0;
    }
    
    [data-testid="stSidebar"] h2 {
        color: #003d7a !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown p {
        color: #333333 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f5f5f5;
        padding: 12px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 14px 26px;
        background-color: #ffffff;
        border: 2px solid #e0e0e0;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        color: #003d7a !important;
        font-size: 15px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #003d7a 0%, #0066b3 100%);
        color: white !important;
        border: 2px solid #003d7a;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e3f2fd;
        border-color: #0066b3;
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
        background: linear-gradient(135deg, #002855 0%, #004d8a 100%);
        box-shadow: 0 4px 12px rgba(0,61,122,0.3);
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
        background: linear-gradient(135deg, #002855 0%, #004d8a 100%);
    }
    
    [data-testid="stMetricValue"] {
        color: #003d7a !important;
        font-weight: 700;
        font-size: 28px !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #333333 !important;
        font-weight: 600;
    }
    
    .header-container {
        background: linear-gradient(135deg, #003d7a 0%, #0066b3 100%);
        padding: 35px;
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,61,122,0.3);
    }
    
    .header-container h1 {
        color: white !important;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .header-container p {
        color: #e3f2fd !important;
        font-size: 16px;
        margin-top: 10px;
    }
    
    /* Fix for plotly charts */
    .js-plotly-plot, .plotly {
        background-color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TANGGAL MERAH (Holidays)
# ============================================================================
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
    
    return df

def calculate_sla_per_status(df):
    """Calculate SLA from Recommendation to action_on"""
    df_with_sla = df.copy()
    
    sla_hours_list = []
    sla_formatted_list = []
    
    for idx, row in df_with_sla.iterrows():
        recommendation_time = row.get('Recommendation_parsed')
        action_time = row.get('action_on_parsed')
        
        if pd.notna(recommendation_time) and pd.notna(action_time):
            sla_result = calculate_sla_working_hours(recommendation_time, action_time)
            if sla_result:
                sla_hours_list.append(sla_result['total_hours'])
                sla_formatted_list.append(sla_result['formatted'])
            else:
                sla_hours_list.append(None)
                sla_formatted_list.append(None)
        else:
            sla_hours_list.append(None)
            sla_formatted_list.append(None)
    
    df_with_sla['SLA_Hours'] = sla_hours_list
    df_with_sla['SLA_Formatted'] = sla_formatted_list
    
    return df_with_sla

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
    
    # BCA Finance Header with REAL LOGO
    logo_path = "/mnt/user-data/uploads/BCA_Finance_Logo__1_.png"
    logo_base64 = get_base64_image(logo_path)
    
    if logo_base64:
        st.markdown(f"""
        <div class="header-container">
            <div style="display: flex; align-items: center; justify-content: center; gap: 30px; flex-wrap: wrap;">
                <div style="background: white; padding: 15px 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    <img src="data:image/png;base64,{logo_base64}" style="height: 60px; width: auto;">
                </div>
                <div style="text-align: center;">
                    <h1 style="margin: 0; font-size: 42px; letter-spacing: 1px; color: white !important;">Dashboard Analisis Pengajuan Kredit</h1>
                    <p style="color: #e3f2fd !important; margin-top: 12px; font-size: 17px;">Monitoring & Evaluasi Kinerja Credit Analyst</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="header-container">
            <div style="text-align: center;">
                <h1 style="margin: 0; font-size: 42px; letter-spacing: 1px; color: white !important;">Dashboard Analisis Pengajuan Kredit</h1>
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
        st.metric("Total Catatan", f"{total_records:,}")
        st.markdown('<p style="color: #666; font-size: 14px; margin-top: 5px;">Total semua transaksi dalam sistem</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-box-success">', unsafe_allow_html=True)
        st.metric("Aplikasi Unik", f"{unique_apps:,}")
        st.markdown('<p style="color: #666; font-size: 14px; margin-top: 5px;">Jumlah pengajuan kredit unik</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-box-warning">', unsafe_allow_html=True)
        sla_pct = f"{sla_with_data/total_records*100:.1f}%"
        st.metric("Data SLA Lengkap", f"{sla_with_data:,}")
        st.markdown(f'<p style="color: #666; font-size: 14px; margin-top: 5px;">Cakupan: {sla_pct} dari total data</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        sla_valid = df[df['SLA_Hours'].notna()]
        if len(sla_valid) > 0:
            avg_hours = sla_valid['SLA_Hours'].mean()
            avg_formatted = convert_hours_to_hm(avg_hours)
            st.markdown('<div class="metric-box-danger">', unsafe_allow_html=True)
            st.metric("Rata-rata Waktu Proses", avg_formatted)
            st.markdown('<p style="color: #666; font-size: 14px; margin-top: 5px;">Dari rekomendasi ke aksi</p>', unsafe_allow_html=True)
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
        all_segmen = sorted([x for x in df['Segmen_clean'].unique()])
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
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Waktu Proses",
        "📋 Data Detail",
        "💰 Analisis Plafon",
        "🎯 Kinerja & Insights"
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
        
        st.markdown("### Statistik Waktu Proses: Rekomendasi ke Aksi")
        st.caption("*Perhitungan berdasarkan jam kerja 08:30 - 15:30, exclude weekend dan hari libur*")
        
        col1, col2, col3, col4 = st.columns(4)
        
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
                st.markdown('<p style="color: #666; font-size: 14px; margin-top: 5px;">50% data di bawah nilai ini</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            if len(sla_valid) > 0:
                min_hours = sla_valid['SLA_Hours'].min()
                min_formatted = convert_hours_to_hm(min_hours)
                st.markdown('<div class="metric-box-success" style="text-align: center;">', unsafe_allow_html=True)
                st.markdown(f'<h3 style="color: #003d7a; margin-bottom: 10px;">Tercepat</h3>', unsafe_allow_html=True)
                st.markdown(f'<h2 style="color: #1e88e5; margin: 0;">{min_formatted}</h2>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
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
                mode='lines+markers',
                name='Waktu Proses',
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
                annotation_text="🎯 Target: 35 jam",
                annotation_position="right",
                annotation_font_size=13,
                annotation_font_color="#f44336"
            )
            
            fig.update_layout(
                title={
                    'text': "Tren Waktu Proses per Bulan",
                    'font': {'size': 20, 'color': '#003d7a'},
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis_title="Bulan",
                yaxis_title="Waktu Proses (Jam Kerja)",
                hovermode='x unified',
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family='Arial', size=13, color='#333333'),
                xaxis=dict(
                    showgrid=True,
                    gridcolor='#e0e0e0',
                    linecolor='#666666'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#e0e0e0',
                    linecolor='#666666'
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
            <h3 style="color: #003d7a; margin-bottom: 10px;">Total Aplikasi</h3>
            <h1 style="color: #1e88e5; margin: 10px 0; font-size: 48px;">{len(apps_df):,}</h1>
            <p style="color: #666; font-size: 14px;">Aplikasi kredit unik dalam sistem</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_catatan = apps_df['Jumlah Catatan'].sum()
            st.markdown(f"""
            <div class="metric-box" style="text-align: center; padding: 25px;">
            <h3 style="color: #003d7a; margin-bottom: 10px;">Total Catatan</h3>
            <h1 style="color: #0066b3; margin: 10px 0; font-size: 48px;">{total_catatan:,}</h1>
            <p style="color: #666; font-size: 14px;">Total transaksi dalam sistem</p>
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
                    
                    # Rename columns for better readability
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
        <p>Analisis ini mengelompokkan aplikasi berdasarkan kategori plafon dan berbagai dimensi bisnis.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Define OSPH ranges order
        osph_order = ['0 - 250 Juta', '250 - 500 Juta', 'Lebih dari 500 Juta']
        
        # Overview
        df_distinct = df_filtered.drop_duplicates('apps_id')
        
        st.markdown("### Distribusi Portfolio Berdasarkan Plafon")
        
        if 'OSPH_Category' in df_distinct.columns:
            osph_dist = df_distinct['OSPH_Category'].value_counts()
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Create pie chart
                fig = px.pie(
                    values=osph_dist.values,
                    names=osph_dist.index,
                    title="Distribusi Aplikasi per Kategori Plafon",
                    color_discrete_sequence=['#1e88e5', '#d4af37', '#f44336']
                )
                fig.update_layout(
                    height=400,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Create bar chart
                fig = px.bar(
                    x=osph_dist.index,
                    y=osph_dist.values,
                    title="Jumlah Aplikasi per Kategori",
                    labels={'x': 'Kategori Plafon', 'y': 'Jumlah Aplikasi'},
                    color=osph_dist.values,
                    color_continuous_scale='Blues'
                )
                fig.update_layout(
                    height=400,
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # ====== TAB 4: PERFORMANCE & INSIGHTS ======
    with tab4:
        st.markdown("## Kinerja & Insights Strategis")
        
        subtab1, subtab2, subtab3 = st.tabs([
            "📈 Kinerja Cabang & CA",
            "📊 Status & Penilaian",
            "💡 Insights & Rekomendasi"
        ])
        
        # Branch & CA Performance
        with subtab1:
            st.markdown("### Analisis Kinerja")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Top 10 Cabang - Volume Aplikasi")
                
                if 'branch_name_clean' in df_filtered.columns:
                    branch_counts = df_filtered.drop_duplicates('apps_id')['branch_name_clean'].value_counts().head(10)
                    
                    fig = px.bar(
                        x=branch_counts.index,
                        y=branch_counts.values,
                        labels={'x': 'Cabang', 'y': 'Jumlah Aplikasi'},
                        color=branch_counts.values,
                        color_continuous_scale='Blues'
                    )
                    fig.update_layout(
                        height=400,
                        showlegend=False,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Top 10 Credit Analyst - Volume Aplikasi")
                
                if 'user_name_clean' in df_filtered.columns:
                    ca_counts = df_filtered.drop_duplicates('apps_id')['user_name_clean'].value_counts().head(10)
                    
                    fig = px.bar(
                        x=ca_counts.index,
                        y=ca_counts.values,
                        labels={'x': 'Credit Analyst', 'y': 'Jumlah Aplikasi'},
                        color=ca_counts.values,
                        color_continuous_scale='Greens'
                    )
                    fig.update_layout(
                        height=400,
                        showlegend=False,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # Status & Scoring
        with subtab2:
            st.markdown("### Analisis Status & Hasil Penilaian")
            
            df_distinct = df_filtered.drop_duplicates('apps_id')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Distribusi Status Aplikasi")
                
                if 'apps_status_clean' in df_distinct.columns:
                    status_dist = df_distinct['apps_status_clean'].value_counts()
                    
                    fig = px.pie(
                        values=status_dist.values,
                        names=status_dist.index,
                        title="Status Aplikasi"
                    )
                    fig.update_layout(
                        height=400,
                        plot_bgcolor='white',
                        paper_bgcolor='white'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Distribusi Hasil Penilaian")
                
                if 'Scoring_Detail' in df_distinct.columns:
                    scoring_dist = df_distinct['Scoring_Detail'].value_counts()
                    
                    fig = px.pie(
                        values=scoring_dist.values,
                        names=scoring_dist.index,
                        title="Hasil Scoring"
                    )
                    fig.update_layout(
                        height=400,
                        plot_bgcolor='white',
                        paper_bgcolor='white'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Cross-tabulation
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
                
                st.dataframe(cross_tab, use_container_width=True)
        
        # Insights
        with subtab3:
            st.markdown("### Insights & Rekomendasi Strategis")
            
            df_distinct = df_filtered.drop_duplicates('apps_id')
            
            # Calculate key metrics
            approve_count = df_distinct['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
            total_scored = len(df_distinct[df_distinct['Scoring_Detail'] != '(Semua)'])
            
            if total_scored > 0:
                approval_rate = (approve_count / total_scored) * 100
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-box-success" style="text-align: center; padding: 25px;">
                    <h4 style="color: #003d7a; margin-bottom: 10px;">Tingkat Persetujuan</h4>
                    <h1 style="color: #1e88e5; margin: 10px 0; font-size: 48px;">{approval_rate:.1f}%</h1>
                    <p style="color: #666; font-size: 14px;">{approve_count:,} dari {total_scored:,} aplikasi</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    sla_data = df_filtered[df_filtered['SLA_Hours'].notna()]
                    if len(sla_data) > 0:
                        avg_sla = sla_data['SLA_Hours'].mean()
                        status = "✅ Baik" if avg_sla <= 35 else "⚠️ Perlu Perbaikan"
                        st.markdown(f"""
                        <div class="metric-box" style="text-align: center; padding: 25px;">
                        <h4 style="color: #003d7a; margin-bottom: 10px;">Status SLA</h4>
                        <h1 style="color: #0066b3; margin: 10px 0; font-size: 32px;">{status}</h1>
                        <p style="color: #666; font-size: 14px;">Rata-rata: {avg_sla:.1f} jam (Target: 35 jam)</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col3:
                    total_apps = df_filtered['apps_id'].nunique()
                    st.markdown(f"""
                    <div class="metric-box-warning" style="text-align: center; padding: 25px;">
                    <h4 style="color: #003d7a; margin-bottom: 10px;">Total Aplikasi</h4>
                    <h1 style="color: #d4af37; margin: 10px 0; font-size: 48px;">{total_apps:,}</h1>
                    <p style="color: #666; font-size: 14px;">Aplikasi unik diproses</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Recommendations
            st.markdown("### Rekomendasi Strategis")
            
            st.markdown("""
            <div class="metric-box" style="padding: 25px;">
            <h4 style="color: #003d7a; margin-bottom: 15px;">🎯 Action Items Prioritas</h4>
            <ol style="color: #333333; line-height: 2;">
                <li><strong>Optimasi SLA:</strong> Fokus pada cabang dan CA dengan waktu proses di atas target</li>
                <li><strong>Knowledge Transfer:</strong> Replikasi best practices dari top performers</li>
                <li><strong>Quality Control:</strong> Strengthen pre-screening untuk meningkatkan approval rate</li>
                <li><strong>Training & Development:</strong> Program capacity building untuk CA dengan performa rendah</li>
                <li><strong>Technology:</strong> Pertimbangkan otomasi untuk percepat proses</li>
            </ol>
            </div>
            """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #003d7a 0%, #0066b3 100%); padding: 30px; border-radius: 10px; margin-top: 30px; text-align: center;">
        <div style="color: white;">
            <p style="margin: 0; font-size: 14px;">© 2026 BCA Finance - Dashboard Analisis Kredit</p>
            <p style="margin: 5px 0 0 0; font-size: 12px;">Terakhir diperbarui: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
