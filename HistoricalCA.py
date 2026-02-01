import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(page_title="Analisis Kredit - Dashboard", layout="wide", initial_sidebar_state="expanded")

FILE_NAME = "Historical_CA (1) (1).xlsx"

# ============================================================================
# STYLING - ENHANCED
# ============================================================================
st.markdown("""
<style>
    /* Main Title */
    h1 { 
        color: #1e3a8a; 
        text-align: center; 
        font-size: 36px; 
        margin-bottom: 10px;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Section Headers */
    h2 { 
        color: #1e40af; 
        border-bottom: 3px solid #3b82f6; 
        padding-bottom: 10px;
        margin-top: 30px;
        font-weight: 600;
    }
    
    h3 { 
        color: #2563eb; 
        margin-top: 25px;
        font-weight: 600;
    }
    
    /* Metric Boxes - Different colors */
    .metric-box {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    
    .metric-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    .metric-box-success {
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        border-left: 5px solid #22c55e;
    }
    
    .metric-box-warning {
        background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
        border-left: 5px solid #f59e0b;
    }
    
    .metric-box-danger {
        background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
        border-left: 5px solid #ef4444;
    }
    
    /* Info Boxes */
    .info-box {
        background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #0ea5e9;
        margin: 15px 0;
    }
    
    /* Tables */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #f8fafc;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        background-color: #f1f5f9;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6;
        color: white;
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

def calculate_sla_working_hours(start_dt, end_dt, use_end_time=True):
    """
    Calculate SLA in working hours
    
    Args:
        start_dt: Start datetime
        end_dt: End datetime
        use_end_time: If True, use 08:30-15:30 working hours (for Recommendation)
                     If False, use 08:30-end of day (for Action fields)
    """
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
        WORK_END = timedelta(hours=15, minutes=30) if use_end_time else timedelta(hours=23, minutes=59, seconds=59)
        
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
                elif start_dt.time() >= day_end.time() and use_end_time:
                    current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
                    continue
                else:
                    day_actual_start = start_dt
            else:
                day_actual_start = day_start
            
            if current.date() == end_dt.date():
                if end_dt.time() < day_start.time():
                    break
                elif end_dt.time() > day_end.time() and use_end_time:
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
        if row['SLA_Hours'] > 35:
            score += 20
        elif row['SLA_Hours'] > 21:
            score += 10
    
    return min(score, 100)

def preprocess_data(df):
    """Clean and prepare data"""
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate', 'Recommendation', 'ApprovalCC1', 'ApprovalCC2']:
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
    """Calculate SLA from Recommendation to action_on (with 08:30-15:30 limit)"""
    df_with_sla = df.copy()
    
    sla_hours_list = []
    sla_formatted_list = []
    
    for idx, row in df_with_sla.iterrows():
        recommendation_time = row.get('Recommendation_parsed')
        action_time = row.get('action_on_parsed')
        
        if pd.notna(recommendation_time) and pd.notna(action_time):
            sla_result = calculate_sla_working_hours(recommendation_time, action_time, use_end_time=True)
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

def calculate_additional_sla_fields(df):
    """Calculate additional SLA fields for Action-based calculations (with 08:30-end of day)"""
    df_with_additional = df.copy()
    
    # Calculate Initiation -> action_on
    initiation_hours_list = []
    initiation_formatted_list = []
    
    for idx, row in df_with_additional.iterrows():
        initiation_time = row.get('Initiation_parsed')
        action_time = row.get('action_on_parsed')
        
        if pd.notna(initiation_time) and pd.notna(action_time):
            sla_result = calculate_sla_working_hours(initiation_time, action_time, use_end_time=False)
            if sla_result:
                initiation_hours_list.append(sla_result['total_hours'])
                initiation_formatted_list.append(sla_result['formatted'])
            else:
                initiation_hours_list.append(None)
                initiation_formatted_list.append(None)
        else:
            initiation_hours_list.append(None)
            initiation_formatted_list.append(None)
    
    df_with_additional['Initiation_SLA_Hours'] = initiation_hours_list
    df_with_additional['Initiation_SLA_Formatted'] = initiation_formatted_list
    
    # Calculate ApprovalCC1 -> action_on
    approval1_hours_list = []
    approval1_formatted_list = []
    
    for idx, row in df_with_additional.iterrows():
        approval1_time = row.get('ApprovalCC1_parsed')
        action_time = row.get('action_on_parsed')
        
        if pd.notna(approval1_time) and pd.notna(action_time):
            sla_result = calculate_sla_working_hours(approval1_time, action_time, use_end_time=False)
            if sla_result:
                approval1_hours_list.append(sla_result['total_hours'])
                approval1_formatted_list.append(sla_result['formatted'])
            else:
                approval1_hours_list.append(None)
                approval1_formatted_list.append(None)
        else:
            approval1_hours_list.append(None)
            approval1_formatted_list.append(None)
    
    df_with_additional['ApprovalCC1_SLA_Hours'] = approval1_hours_list
    df_with_additional['ApprovalCC1_SLA_Formatted'] = approval1_formatted_list
    
    return df_with_additional

@st.cache_data
def load_data():
    """Load and preprocess data"""
    try:
        if not Path(FILE_NAME).exists():
            st.error(f"❌ File tidak ditemukan: {FILE_NAME}")
            return None
        
        df = pd.read_excel(FILE_NAME)
        
        required_cols = [
            'apps_id', 'position_name', 'user_name', 'apps_status', 'desc_status_apps',
            'Segmen', 'action_on', 'Initiation', 'RealisasiDate', 'Outstanding_PH',
            'Pekerjaan', 'Jabatan', 'Hasil_Scoring',
            'JenisKendaraan', 'branch_name', 'Tujuan_Kredit',
            'Recommendation', 'LastOD', 'max_OD'
        ]
        
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"❌ Kolom yang hilang: {', '.join(missing)}")
            return None
        
        df_clean = preprocess_data(df)
        df_clean = calculate_sla_per_status(df_clean)
        df_clean = calculate_additional_sla_fields(df_clean)
        
        df_clean['Risk_Score'] = df_clean.apply(calculate_risk_score, axis=1)
        df_clean['Risk_Category'] = pd.cut(
            df_clean['Risk_Score'], 
            bins=[0, 30, 60, 100], 
            labels=['Risiko Rendah', 'Risiko Menengah', 'Risiko Tinggi']
        )
        
        return df_clean
    except Exception as e:
        st.error(f"❌ Error saat memuat data: {str(e)}")
        return None

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main Streamlit application"""
    
    # Header with logo placeholder
    col_logo, col_title = st.columns([1, 4])
    
    with col_title:
        st.title("📊 Dashboard Analisis Pengajuan Kredit")
        st.markdown("**Monitoring & Evaluasi Kinerja Credit Analyst**")
    
    st.markdown("---")
    
    with st.spinner("⏳ Memuat data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("❌ Tidak dapat memuat data")
        st.stop()
    
    # TOP METRICS - ENHANCED
    st.markdown("### 📈 Ringkasan Utama")
    
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    sla_with_data = df['SLA_Hours'].notna().sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("📝 Total Catatan", f"{total_records:,}")
        st.caption("Total semua transaksi dalam sistem")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-box-success">', unsafe_allow_html=True)
        st.metric("🎯 Aplikasi Unik", f"{unique_apps:,}")
        st.caption("Jumlah pengajuan kredit unik")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-box-warning">', unsafe_allow_html=True)
        sla_pct = f"{sla_with_data/total_records*100:.1f}%"
        st.metric("⏱️ Data SLA Lengkap", f"{sla_with_data:,}")
        st.caption(f"Cakupan: {sla_pct} dari total data")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        sla_valid = df[df['SLA_Hours'].notna()]
        if len(sla_valid) > 0:
            avg_hours = sla_valid['SLA_Hours'].mean()
            avg_formatted = convert_hours_to_hm(avg_hours)
            st.markdown('<div class="metric-box-danger">', unsafe_allow_html=True)
            st.metric("⚡ Rata-rata Waktu Proses", avg_formatted)
            st.caption("Dari rekomendasi ke aksi")
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # SIDEBAR FILTERS - ENHANCED
    st.sidebar.markdown("## 🎛️ Filter Data")
    st.sidebar.markdown("---")
    
    if 'apps_status_clean' in df.columns:
        all_status = sorted([x for x in df['apps_status_clean'].unique() if x != 'Tidak Diketahui'])
        selected_status = st.sidebar.multiselect(
            "📋 Status Aplikasi", 
            all_status, 
            default=all_status,
            help="Pilih satu atau lebih status aplikasi"
        )
    else:
        selected_status = []
    
    if 'Scoring_Detail' in df.columns:
        all_scoring = sorted([x for x in df['Scoring_Detail'].unique() if x != '(Semua)'])
        selected_scoring = st.sidebar.multiselect(
            "✅ Hasil Penilaian", 
            all_scoring, 
            default=all_scoring,
            help="Filter berdasarkan hasil scoring"
        )
    else:
        selected_scoring = []
    
    if 'Segmen_clean' in df.columns:
        all_segmen = sorted([x for x in df['Segmen_clean'].unique()])
        selected_segmen = st.sidebar.selectbox(
            "🎯 Segmen Kredit", 
            ['Semua Segmen'] + all_segmen,
            help="Pilih segmen kredit tertentu"
        )
    else:
        selected_segmen = 'Semua Segmen'
    
    if 'branch_name_clean' in df.columns:
        all_branches = sorted(df['branch_name_clean'].unique().tolist())
        selected_branch = st.sidebar.selectbox(
            "🏢 Cabang", 
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
    st.sidebar.markdown("### 📊 Hasil Filter")
    st.sidebar.success(f"**{len(df_filtered):,}** catatan ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f"**{df_filtered['apps_id'].nunique():,}** aplikasi unik")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "⏱️ Waktu Proses",
        "📋 Data Detail",
        "💰 Analisis Plafon",
        "🏢 Kinerja Cabang & CA",
        "📊 Status & Penilaian",
        "⚠️ Dampak Keterlambatan",
        "📥 Unduh Data"
    ])

    # ====== TAB 1: SLA ANALYSIS ======
    with tab1:
        st.markdown("## ⏱️ Analisis Waktu Proses Aplikasi")
        
        st.markdown("""
        <div class="info-box">
        <h4>📖 Penjelasan Waktu Proses (SLA)</h4>
        <p><strong>SLA (Service Level Agreement)</strong> adalah target waktu yang ditetapkan untuk menyelesaikan proses kredit.</p>
        <ul>
            <li><strong>Rekomendasi → Aksi</strong>: Dihitung jam kerja 08:30 - 15:30 (tidak termasuk weekend & libur)</li>
            <li><strong>Pengajuan Awal → Aksi</strong>: Dihitung mulai jam 08:30 sampai akhir hari (tidak termasuk weekend & libur)</li>
            <li><strong>Persetujuan CC → Aksi</strong>: Dihitung mulai jam 08:30 sampai akhir hari (tidak termasuk weekend & libur)</li>
        </ul>
        <p><strong>Target:</strong> Maksimal 35 jam kerja (setara 5 hari kerja)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Overall SLA stats
        sla_valid = df_filtered[df_filtered['SLA_Hours'].notna()]
        
        st.markdown("### 📊 Waktu Proses: Rekomendasi → Aksi")
        st.caption("*Perhitungan berdasarkan jam kerja 08:30 - 15:30, exclude weekend dan hari libur*")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if len(sla_valid) > 0:
                avg_hours = sla_valid['SLA_Hours'].mean()
                avg_formatted = convert_hours_to_hm(avg_hours)
                st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                st.metric("📊 Rata-rata", avg_formatted)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if len(sla_valid) > 0:
                median_hours = sla_valid['SLA_Hours'].median()
                median_formatted = convert_hours_to_hm(median_hours)
                st.markdown('<div class="metric-box-success">', unsafe_allow_html=True)
                st.metric("📈 Nilai Tengah", median_formatted)
                st.caption("50% data di bawah nilai ini")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            if len(sla_valid) > 0:
                min_hours = sla_valid['SLA_Hours'].min()
                min_formatted = convert_hours_to_hm(min_hours)
                st.markdown('<div class="metric-box-success">', unsafe_allow_html=True)
                st.metric("⚡ Tercepat", min_formatted)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            if len(sla_valid) > 0:
                max_hours = sla_valid['SLA_Hours'].max()
                max_formatted = convert_hours_to_hm(max_hours)
                st.markdown('<div class="metric-box-danger">', unsafe_allow_html=True)
                st.metric("🐌 Terlama", max_formatted)
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Additional SLA Metrics
        st.markdown("### 📊 Waktu Proses: Pengajuan Awal → Aksi")
        st.caption("*Perhitungan dari jam 08:30 sampai akhir hari, exclude weekend dan hari libur*")
        
        initiation_valid = df_filtered[df_filtered['Initiation_SLA_Hours'].notna()]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if len(initiation_valid) > 0:
                avg_hours = initiation_valid['Initiation_SLA_Hours'].mean()
                avg_formatted = convert_hours_to_hm(avg_hours)
                st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                st.metric("📊 Rata-rata", avg_formatted)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if len(initiation_valid) > 0:
                median_hours = initiation_valid['Initiation_SLA_Hours'].median()
                median_formatted = convert_hours_to_hm(median_hours)
                st.markdown('<div class="metric-box-success">', unsafe_allow_html=True)
                st.metric("📈 Nilai Tengah", median_formatted)
                st.caption("50% data di bawah nilai ini")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            if len(initiation_valid) > 0:
                coverage = len(initiation_valid) / len(df_filtered) * 100
                st.markdown('<div class="metric-box-warning">', unsafe_allow_html=True)
                st.metric("📋 Cakupan Data", f"{coverage:.1f}%")
                st.caption(f"{len(initiation_valid):,} dari {len(df_filtered):,} data")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            if len(initiation_valid) > 0:
                above_target = (initiation_valid['Initiation_SLA_Hours'] > 35).sum()
                pct_above = above_target / len(initiation_valid) * 100
                st.markdown('<div class="metric-box-danger">', unsafe_allow_html=True)
                st.metric("⚠️ Melebihi Target", f"{pct_above:.1f}%")
                st.caption(f"{above_target:,} aplikasi > 35 jam")
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # SLA TREND
        st.markdown("### 📈 Tren Waktu Proses Bulanan")
        st.caption("*Grafik menunjukkan rata-rata waktu proses per bulan (Rekomendasi → Aksi)*")
        
        if len(sla_valid) > 0 and 'action_on_parsed' in sla_valid.columns:
            sla_trend = sla_valid.copy()
            sla_trend['YearMonth'] = sla_trend['action_on_parsed'].dt.to_period('M').astype(str)
            
            monthly_avg = sla_trend.groupby('YearMonth')['SLA_Hours'].agg(['mean', 'count']).reset_index()
            monthly_avg.columns = ['Bulan', 'Rata-rata Waktu (Jam)', 'Jumlah Data']
            monthly_avg = monthly_avg.sort_values('Bulan')
            monthly_avg['Rata-rata Waktu (Teks)'] = monthly_avg['Rata-rata Waktu (Jam)'].apply(convert_hours_to_hm)
            
            # Display table with better column names
            display_monthly = monthly_avg.rename(columns={
                'Bulan': '📅 Bulan',
                'Rata-rata Waktu (Teks)': '⏱️ Waktu Rata-rata',
                'Jumlah Data': '📊 Jumlah Aplikasi'
            })
            
            st.dataframe(
                display_monthly[['📅 Bulan', '⏱️ Waktu Rata-rata', '📊 Jumlah Aplikasi']], 
                use_container_width=True, 
                hide_index=True
            )
            
            # Line chart
            fig = go.Figure()
            
            hover_text = []
            for idx, row in monthly_avg.iterrows():
                hours = int(row['Rata-rata Waktu (Jam)'])
                minutes = int((row['Rata-rata Waktu (Jam)'] - hours) * 60)
                hover_text.append(f"<b>{row['Bulan']}</b><br>Waktu: {hours} jam {minutes} menit<br>Jumlah: {row['Jumlah Data']} aplikasi")
            
            fig.add_trace(go.Scatter(
                x=monthly_avg['Bulan'],
                y=monthly_avg['Rata-rata Waktu (Jam)'],
                mode='lines+markers+text',
                name='Rata-rata Waktu Proses',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=12, color='#3b82f6', line=dict(color='white', width=2)),
                text=[f"{int(h)} jam {int((h - int(h)) * 60)} mnt" for h in monthly_avg['Rata-rata Waktu (Jam)']],
                textposition='top center',
                textfont=dict(size=11, color='#1e40af', family='Arial Black'),
                hovertext=hover_text,
                hoverinfo='text'
            ))
            
            fig.add_hline(
                y=35, 
                line_dash="dash", 
                line_color="#ef4444",
                line_width=3,
                annotation_text="🎯 Target: 35 jam (5 hari kerja)",
                annotation_position="right",
                annotation_font_size=12,
                annotation_font_color="#ef4444"
            )
            
            fig.update_layout(
                title={
                    'text': "📊 Tren Waktu Proses - Rata-rata per Bulan",
                    'font': {'size': 18, 'color': '#1e3a8a'}
                },
                xaxis_title="Bulan",
                yaxis_title="Waktu Proses (Jam Kerja)",
                hovermode='x unified',
                height=500,
                plot_bgcolor='#f8fafc',
                paper_bgcolor='white',
                font=dict(family='Arial', size=12)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # SLA by Status
        st.markdown("### 📊 Waktu Proses Berdasarkan Status Aplikasi")
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
                        '📋 Status Aplikasi': status,
                        '📊 Total Data': len(df_status),
                        '✅ Data Lengkap': len(sla_status),
                        '📈 Cakupan': f"{len(sla_status)/len(df_status)*100:.1f}%",
                        '⏱️ Rata-rata': convert_hours_to_hm(avg_sla),
                        '📊 Nilai Tengah': convert_hours_to_hm(median_sla),
                        '⚡ Tercepat': convert_hours_to_hm(min_sla),
                        '🐌 Terlama': convert_hours_to_hm(max_sla),
                    })
            
            if status_sla:
                status_sla_df = pd.DataFrame(status_sla)
                st.dataframe(status_sla_df, use_container_width=True, hide_index=True, height=400)
    
    # ====== TAB 2: DETAIL RAW DATA ======
    with tab2:
        st.markdown("## 📋 Data Detail Aplikasi Kredit")
        
        st.markdown("""
        <div class="info-box">
        <h4>📖 Cara Menggunakan</h4>
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
                '🔢 ID Aplikasi': app_id,
                '📊 Jumlah Catatan': len(app_data),
                '📋 Status Terakhir': latest_record.get('apps_status_clean', 'N/A'),
                '📅 Aksi Terakhir': latest_record.get('action_on_parsed', pd.NaT),
                '🎯 Segmen': latest_record.get('Segmen_clean', 'N/A'),
                '💰 Kategori Plafon': latest_record.get('OSPH_Category', 'N/A'),
                '🏢 Cabang': latest_record.get('branch_name_clean', 'N/A'),
                '👤 Credit Analyst': latest_record.get('user_name_clean', 'N/A')
            })
        
        apps_df = pd.DataFrame(apps_summary)
        apps_df = apps_df.sort_values('📅 Aksi Terakhir', ascending=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-box-success">
            <h3>📊 Total Aplikasi</h3>
            <h1 style="color: #16a34a; margin: 0;">{len(apps_df):,}</h1>
            <p>Aplikasi kredit unik dalam sistem</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_catatan = apps_df['📊 Jumlah Catatan'].sum()
            st.markdown(f"""
            <div class="metric-box">
            <h3>📝 Total Catatan</h3>
            <h1 style="color: #3b82f6; margin: 0;">{total_catatan:,}</h1>
            <p>Total transaksi dalam sistem</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📊 Daftar Semua Aplikasi")
        
        # Display all apps in a table
        st.dataframe(
            apps_df.style.format({'📅 Aksi Terakhir': lambda x: x.strftime('%d-%m-%Y %H:%M') if pd.notna(x) else 'N/A'}),
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.markdown("---")
        
        # Search and detail view
        st.markdown("### 🔍 Cari Detail Aplikasi")
        
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
                    st.success(f"✅ Ditemukan **{len(app_records)}** catatan untuk ID Aplikasi: **{search_id}**")
                    
                    # Summary
                    st.markdown("#### 📊 Ringkasan Aplikasi")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        segmen = app_records['Segmen_clean'].iloc[0] if 'Segmen_clean' in app_records.columns else 'N/A'
                        st.markdown(f"""
                        <div class="metric-box">
                        <h4>🎯 Segmen</h4>
                        <h3>{segmen}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        osph = app_records['OSPH_Category'].iloc[0] if 'OSPH_Category' in app_records.columns else 'N/A'
                        st.markdown(f"""
                        <div class="metric-box-warning">
                        <h4>💰 Plafon</h4>
                        <h3>{osph}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        branch = app_records['branch_name_clean'].iloc[0] if 'branch_name_clean' in app_records.columns else 'N/A'
                        st.markdown(f"""
                        <div class="metric-box-success">
                        <h4>🏢 Cabang</h4>
                        <h3>{branch}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col4:
                        ca = app_records['user_name_clean'].iloc[0] if 'user_name_clean' in app_records.columns else 'N/A'
                        st.markdown(f"""
                        <div class="metric-box">
                        <h4>👤 CA</h4>
                        <h3>{ca}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Display ALL records with new SLA fields
                    st.markdown("#### 📝 Riwayat Lengkap Aplikasi")
                    
                    display_cols = [
                        'apps_status_clean', 'action_on_parsed', 'Recommendation_parsed',
                        'Initiation_parsed', 'SLA_Hours', 'SLA_Formatted',
                        'Initiation_SLA_Hours', 'Initiation_SLA_Formatted',
                        'ApprovalCC1_SLA_Hours', 'ApprovalCC1_SLA_Formatted',
                        'Scoring_Detail', 'OSPH_clean', 'LastOD_clean',
                        'user_name_clean', 'Pekerjaan_clean', 'JenisKendaraan_clean'
                    ]
                    
                    # Rename columns for better readability
                    col_rename = {
                        'apps_status_clean': '📋 Status',
                        'action_on_parsed': '📅 Waktu Aksi',
                        'Recommendation_parsed': '📝 Waktu Rekomendasi',
                        'Initiation_parsed': '🚀 Waktu Pengajuan',
                        'SLA_Hours': '⏱️ SLA (Jam)',
                        'SLA_Formatted': '⏱️ SLA',
                        'Initiation_SLA_Hours': '⏱️ SLA Pengajuan (Jam)',
                        'Initiation_SLA_Formatted': '⏱️ SLA Pengajuan',
                        'ApprovalCC1_SLA_Hours': '⏱️ SLA Approval (Jam)',
                        'ApprovalCC1_SLA_Formatted': '⏱️ SLA Approval',
                        'Scoring_Detail': '✅ Hasil Penilaian',
                        'OSPH_clean': '💰 Plafon (Rp)',
                        'LastOD_clean': '⚠️ Tunggakan Terakhir (Hari)',
                        'user_name_clean': '👤 Credit Analyst',
                        'Pekerjaan_clean': '💼 Pekerjaan',
                        'JenisKendaraan_clean': '🚗 Jenis Kendaraan'
                    }
                    
                    available_cols = [c for c in display_cols if c in app_records.columns]
                    display_df = app_records[available_cols].rename(columns=col_rename)
                    
                    st.dataframe(display_df.reset_index(drop=True), use_container_width=True, height=400)
                    
                else:
                    st.warning(f"⚠️ Tidak ditemukan data untuk ID Aplikasi: {search_id}")
            
            except ValueError:
                st.error("❌ Mohon masukkan ID Aplikasi yang valid (angka)")
    
    # ====== TAB 3: OSPH PIVOT BY PEKERJAAN ======
    with tab3:
        st.markdown("## 💰 Analisis Plafon Kredit Berdasarkan Pekerjaan")
        
        st.markdown("""
        <div class="info-box">
        <h4>📖 Penjelasan Analisis</h4>
        <p><strong>OSPH (Outstanding Plafon Hutang)</strong> adalah total plafon kredit yang tersedia untuk nasabah.</p>
        <p>Analisis ini mengelompokkan aplikasi berdasarkan:</p>
        <ul>
            <li><strong>Kategori Plafon</strong>: 0-250 Juta, 250-500 Juta, dan >500 Juta</li>
            <li><strong>Jenis Pekerjaan</strong>: Top 10 pekerjaan dengan jumlah aplikasi terbanyak</li>
            <li><strong>Segmen Kredit</strong>: KKB, CS NEW, CS USED, dan lainnya</li>
        </ul>
        <p><strong>Catatan:</strong> Perhitungan berdasarkan aplikasi unik (bukan duplikasi)</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Define OSPH ranges order
        osph_order = ['0 - 250 Juta', '250 - 500 Juta', 'Lebih dari 500 Juta']
        
        # Get top pekerjaan
        top_pekerjaan = df_filtered.drop_duplicates('apps_id')['Pekerjaan_clean'].value_counts().head(10).index.tolist()
        
        # Create 4 pivot tables
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
            <h3>📊 Segmen: {segmen if segmen != '-' else 'Lainnya'}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            df_segmen = df_filtered[df_filtered['Segmen_clean'] == segmen].drop_duplicates('apps_id')
            
            total_apps = len(df_segmen)
            total_records = len(df_filtered[df_filtered['Segmen_clean'] == segmen])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🎯 Total Aplikasi Unik", f"{total_apps:,}")
            with col2:
                st.metric("📝 Total Catatan", f"{total_records:,}")
            
            if len(df_segmen) > 0:
                # Create pivot: OSPH Range x Pekerjaan
                pivot_data = []
                
                for osph_range in osph_order:
                    df_osph = df_segmen[df_segmen['OSPH_Category'] == osph_range]
                    
                    row = {'💰 Kategori Plafon': osph_range}
                    
                    for pekerjaan in top_pekerjaan:
                        count = len(df_osph[df_osph['Pekerjaan_clean'] == pekerjaan])
                        row[f"👤 {pekerjaan}"] = count if count > 0 else 0
                    
                    # Add total
                    row['📊 TOTAL'] = len(df_osph)
                    
                    pivot_data.append(row)
                
                # Add TOTAL row
                total_row = {'💰 Kategori Plafon': '📊 TOTAL SEMUA'}
                for pekerjaan in top_pekerjaan:
                    count = len(df_segmen[df_segmen['Pekerjaan_clean'] == pekerjaan])
                    total_row[f"👤 {pekerjaan}"] = count if count > 0 else 0
                total_row['📊 TOTAL'] = len(df_segmen)
                pivot_data.append(total_row)
                
                pivot_df = pd.DataFrame(pivot_data)
                
                st.dataframe(pivot_df, use_container_width=True, hide_index=True, height=300)
                
                # Visualization
                pivot_plot = pivot_df[pivot_df['💰 Kategori Plafon'] != '📊 TOTAL SEMUA'].copy()
                
                if len(pivot_plot) > 0:
                    plot_data = []
                    for _, row in pivot_plot.iterrows():
                        osph = row['💰 Kategori Plafon']
                        for col in pivot_plot.columns:
                            if col.startswith('👤') and row[col] > 0:
                                pek = col.replace('👤 ', '')
                                plot_data.append({
                                    'Kategori Plafon': osph,
                                    'Pekerjaan': pek,
                                    'Jumlah': row[col]
                                })
                    
                    if plot_data:
                        plot_df = pd.DataFrame(plot_data)
                        fig = px.bar(
                            plot_df,
                            x='Kategori Plafon',
                            y='Jumlah',
                            color='Pekerjaan',
                            title=f"📊 Distribusi Plafon untuk Segmen {segmen if segmen != '-' else 'Lainnya'}",
                            barmode='group',
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        fig.update_layout(
                            height=400,
                            plot_bgcolor='#f8fafc',
                            paper_bgcolor='white',
                            font=dict(family='Arial', size=12)
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"ℹ️ Tidak ada data untuk Segmen {segmen}")
            
            st.markdown("---")
    
    # ====== TAB 4: BRANCH & CA PERFORMANCE ======
    with tab4:
        st.markdown("## 🏢 Analisis Kinerja Cabang & Credit Analyst")
        
        subtab1, subtab2 = st.tabs(["🏢 Kinerja Cabang", "👥 Kinerja Credit Analyst"])
        
        # Branch Performance
        with subtab1:
            st.markdown("""
            <div class="info-box">
            <h4>📖 Penjelasan Metrik Kinerja Cabang</h4>
            <ul>
                <li><strong>Total Aplikasi Unik</strong>: Jumlah pengajuan kredit berbeda (tanpa duplikasi)</li>
                <li><strong>Tingkat Persetujuan</strong>: Persentase aplikasi yang disetujui</li>
                <li><strong>Skor Risiko Rata-rata</strong>: Indikator tingkat risiko portofolio (0-100)</li>
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
                    
                    avg_risk = f"{df_branch_distinct['Risk_Score'].mean():.0f}" if df_branch_distinct['Risk_Score'].notna().any() else "-"
                    
                    branch_sla = df_branch[df_branch['SLA_Hours'].notna()]
                    avg_sla = convert_hours_to_hm(branch_sla['SLA_Hours'].mean()) if len(branch_sla) > 0 else "-"
                    
                    total_osph = df_branch_distinct['OSPH_clean'].sum()
                    
                    branch_perf.append({
                        '🏢 Cabang': branch,
                        '🎯 Total Aplikasi Unik': total_apps,
                        '📝 Total Catatan': total_records,
                        '✅ Disetujui': approve,
                        '📊 Tingkat Persetujuan': approval_pct,
                        '⚠️ Skor Risiko Rata-rata': avg_risk,
                        '⏱️ Waktu Proses Rata-rata': avg_sla,
                        '💰 Total Plafon': f"Rp {total_osph:,.0f}"
                    })
                
                branch_df = pd.DataFrame(branch_perf).sort_values('🎯 Total Aplikasi Unik', ascending=False)
                
                st.markdown("### 📊 Tabel Kinerja Seluruh Cabang")
                st.dataframe(branch_df, use_container_width=True, hide_index=True, height=400)
                
                # Charts
                if len(branch_df) > 0:
                    st.markdown("---")
                    st.markdown("### 📈 Visualisasi Kinerja Cabang")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig1 = px.bar(
                            branch_df.head(10),
                            x='🏢 Cabang',
                            y='🎯 Total Aplikasi Unik',
                            title="🏆 Top 10 Cabang - Volume Aplikasi Terbanyak",
                            color='🎯 Total Aplikasi Unik',
                            color_continuous_scale='Blues'
                        )
                        fig1.update_layout(
                            height=400,
                            plot_bgcolor='#f8fafc',
                            paper_bgcolor='white',
                            showlegend=False
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        branch_df_plot = branch_df.copy()
                        branch_df_plot['Approval_Numeric'] = branch_df_plot['📊 Tingkat Persetujuan'].str.rstrip('%').astype(float)
                        
                        fig2 = px.bar(
                            branch_df_plot.head(10),
                            x='🏢 Cabang',
                            y='Approval_Numeric',
                            title="✅ Top 10 Cabang - Tingkat Persetujuan Tertinggi",
                            color='Approval_Numeric',
                            color_continuous_scale='RdYlGn'
                        )
                        fig2.update_layout(
                            yaxis_title="Tingkat Persetujuan (%)",
                            height=400,
                            plot_bgcolor='#f8fafc',
                            paper_bgcolor='white',
                            showlegend=False
                        )
                        st.plotly_chart(fig2, use_container_width=True)
        
        # CA Performance
        with subtab2:
            st.markdown("""
            <div class="info-box">
            <h4>📖 Penjelasan Metrik Kinerja Credit Analyst</h4>
            <ul>
                <li><strong>Total Aplikasi Unik</strong>: Jumlah pengajuan kredit yang ditangani</li>
                <li><strong>Tingkat Persetujuan</strong>: Persentase aplikasi yang berhasil disetujui</li>
                <li><strong>Skor Risiko Rata-rata</strong>: Indikator kualitas analisis risiko</li>
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
                    
                    avg_risk = f"{df_ca_distinct['Risk_Score'].mean():.0f}" if df_ca_distinct['Risk_Score'].notna().any() else "-"
                    
                    ca_sla = df_ca[df_ca['SLA_Hours'].notna()]
                    avg_sla = convert_hours_to_hm(ca_sla['SLA_Hours'].mean()) if len(ca_sla) > 0 else "-"
                    
                    branches = df_ca['branch_name_clean'].unique()
                    main_branch = branches[0] if len(branches) > 0 else "Tidak Diketahui"
                    
                    ca_perf.append({
                        '👤 Nama Credit Analyst': ca,
                        '🏢 Cabang': main_branch,
                        '🎯 Total Aplikasi Unik': total_apps,
                        '📝 Total Catatan': total_records,
                        '✅ Disetujui': approve,
                        '📊 Tingkat Persetujuan': approval_pct,
                        '⚠️ Skor Risiko Rata-rata': avg_risk,
                        '⏱️ Waktu Proses Rata-rata': avg_sla
                    })
                
                ca_df = pd.DataFrame(ca_perf).sort_values('🎯 Total Aplikasi Unik', ascending=False)
                
                st.markdown("### 📊 Tabel Kinerja Seluruh Credit Analyst")
                st.dataframe(ca_df, use_container_width=True, hide_index=True, height=400)
                
                # Charts
                if len(ca_df) > 0:
                    st.markdown("---")
                    st.markdown("### 📈 Visualisasi Kinerja Credit Analyst")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig1 = px.bar(
                            ca_df.head(10),
                            x='👤 Nama Credit Analyst',
                            y='🎯 Total Aplikasi Unik',
                            title="🏆 Top 10 CA - Volume Aplikasi Terbanyak",
                            color='🎯 Total Aplikasi Unik',
                            color_continuous_scale='Greens'
                        )
                        fig1.update_layout(
                            height=400,
                            plot_bgcolor='#f8fafc',
                            paper_bgcolor='white',
                            showlegend=False
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        ca_df_plot = ca_df.copy()
                        ca_df_plot['Approval_Numeric'] = ca_df_plot['📊 Tingkat Persetujuan'].str.rstrip('%').astype(float)
                        
                        fig2 = px.bar(
                            ca_df_plot.head(10),
                            x='👤 Nama Credit Analyst',
                            y='Approval_Numeric',
                            title="✅ Top 10 CA - Tingkat Persetujuan Tertinggi",
                            color='Approval_Numeric',
                            color_continuous_scale='RdYlGn'
                        )
                        fig2.update_layout(
                            yaxis_title="Tingkat Persetujuan (%)",
                            height=400,
                            plot_bgcolor='#f8fafc',
                            paper_bgcolor='white',
                            showlegend=False
                        )
                        st.plotly_chart(fig2, use_container_width=True)
    
    # ====== TAB 5: STATUS & SCORING ======
    with tab5:
        st.markdown("## 📊 Analisis Status Aplikasi & Hasil Penilaian")
        
        st.markdown("""
        <div class="info-box">
        <h4>📖 Penjelasan Tabel</h4>
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
            <div class="metric-box-success">
            <h3>🎯 Total Aplikasi Unik</h3>
            <h1 style="color: #16a34a; margin: 0;">{total_apps_distinct:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-box">
            <h3>📝 Total Catatan</h3>
            <h1 style="color: #3b82f6; margin: 0;">{total_records:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📊 Tabel Silang: Status × Hasil Penilaian")
        
        if 'apps_status_clean' in df_distinct.columns and 'Scoring_Detail' in df_distinct.columns:
            cross_tab = pd.crosstab(
                df_distinct['apps_status_clean'],
                df_distinct['Scoring_Detail'],
                margins=True,
                margins_name='📊 TOTAL'
            )
            
            # Rename index and columns for better readability
            cross_tab.index.name = '📋 Status Aplikasi'
            cross_tab.columns.name = '✅ Hasil Penilaian'
            
            st.dataframe(cross_tab, use_container_width=True, height=400)
            
            st.markdown("---")
            st.markdown("### 🔥 Visualisasi Heatmap")
            
            # Heatmap
            cross_tab_no_total = cross_tab.drop('📊 TOTAL', errors='ignore').drop('📊 TOTAL', axis=1, errors='ignore')
            
            if len(cross_tab_no_total) > 0:
                fig = px.imshow(
                    cross_tab_no_total,
                    text_auto=True,
                    title="📊 Distribusi Status × Hasil Penilaian (Aplikasi Unik)",
                    color_continuous_scale="Blues",
                    aspect="auto"
                )
                fig.update_layout(
                    height=500,
                    xaxis_title="Hasil Penilaian",
                    yaxis_title="Status Aplikasi",
                    font=dict(family='Arial', size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # ====== TAB 6: OD IMPACT ======
    with tab6:
        st.markdown("## ⚠️ Analisis Dampak Keterlambatan Pembayaran")
        
        st.markdown("""
        <div class="info-box">
        <h4>📖 Penjelasan Overdue Days (OD)</h4>
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
            <div class="metric-box-success">
            <h3>🎯 Total Aplikasi Unik</h3>
            <h1 style="color: #16a34a; margin: 0;">{total_apps_distinct:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-box">
            <h3>📝 Total Catatan</h3>
            <h1 style="color: #3b82f6; margin: 0;">{total_records:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Keterlambatan Terakhir (Last OD)")
            
            if 'LastOD_clean' in df_distinct.columns:
                df_distinct_copy = df_distinct.copy()
                df_distinct_copy['LastOD_Category'] = pd.cut(
                    df_distinct_copy['LastOD_clean'],
                    bins=[-np.inf, 0, 10, 30, np.inf],
                    labels=['✅ Tidak Ada', '⚠️ 1-10 Hari', '🔶 11-30 Hari', '🔴 Lebih dari 30 Hari']
                )
                
                lastod_analysis = []
                
                for cat in ['✅ Tidak Ada', '⚠️ 1-10 Hari', '🔶 11-30 Hari', '🔴 Lebih dari 30 Hari']:
                    df_od = df_distinct_copy[df_distinct_copy['LastOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                        
                        lastod_analysis.append({
                            '⚠️ Kategori': cat,
                            '🎯 Total Aplikasi': len(df_od),
                            '✅ Disetujui': approve,
                            '📊 Tingkat Persetujuan': approval_pct
                        })
                
                lastod_df = pd.DataFrame(lastod_analysis)
                st.dataframe(lastod_df, use_container_width=True, hide_index=True)
                
                # Visualization
                if len(lastod_df) > 0:
                    lastod_df['Approval_Numeric'] = lastod_df['📊 Tingkat Persetujuan'].str.rstrip('%').astype(float)
                    fig = px.bar(
                        lastod_df,
                        x='⚠️ Kategori',
                        y='Approval_Numeric',
                        title="Tingkat Persetujuan Berdasarkan Last OD",
                        color='Approval_Numeric',
                        color_continuous_scale='RdYlGn',
                        text='📊 Tingkat Persetujuan'
                    )
                    fig.update_layout(
                        yaxis_title="Tingkat Persetujuan (%)",
                        height=350,
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Keterlambatan Maksimum (Max OD)")
            
            if 'max_OD_clean' in df_distinct.columns:
                df_distinct_copy2 = df_distinct.copy()
                df_distinct_copy2['maxOD_Category'] = pd.cut(
                    df_distinct_copy2['max_OD_clean'],
                    bins=[-np.inf, 0, 15, 45, np.inf],
                    labels=['✅ Tidak Ada', '⚠️ 1-15 Hari', '🔶 16-45 Hari', '🔴 Lebih dari 45 Hari']
                )
                
                maxod_analysis = []
                
                for cat in ['✅ Tidak Ada', '⚠️ 1-15 Hari', '🔶 16-45 Hari', '🔴 Lebih dari 45 Hari']:
                    df_od = df_distinct_copy2[df_distinct_copy2['maxOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                        
                        maxod_analysis.append({
                            '⚠️ Kategori': cat,
                            '🎯 Total Aplikasi': len(df_od),
                            '✅ Disetujui': approve,
                            '📊 Tingkat Persetujuan': approval_pct
                        })
                
                maxod_df = pd.DataFrame(maxod_analysis)
                st.dataframe(maxod_df, use_container_width=True, hide_index=True)
                
                # Visualization
                if len(maxod_df) > 0:
                    maxod_df['Approval_Numeric'] = maxod_df['📊 Tingkat Persetujuan'].str.rstrip('%').astype(float)
                    fig = px.bar(
                        maxod_df,
                        x='⚠️ Kategori',
                        y='Approval_Numeric',
                        title="Tingkat Persetujuan Berdasarkan Max OD",
                        color='Approval_Numeric',
                        color_continuous_scale='RdYlGn',
                        text='📊 Tingkat Persetujuan'
                    )
                    fig.update_layout(
                        yaxis_title="Tingkat Persetujuan (%)",
                        height=350,
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    
    # ====== TAB 7: DATA EXPORT ======
    with tab7:
        st.markdown("## 📥 Unduh Data & Laporan")
        
        st.markdown("""
        <div class="info-box">
        <h4>📖 Cara Mengunduh Data</h4>
        <p>Anda dapat mengunduh data dalam format CSV untuk analisis lebih lanjut:</p>
        <ul>
            <li><strong>Data Lengkap</strong>: Semua data yang sudah difilter dengan kolom penting</li>
            <li><strong>Ringkasan Statistik</strong>: Metrik utama dan ringkasan analisis</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 👀 Pratinjau Data")
        st.caption("*Menampilkan 100 baris pertama dari data yang difilter*")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed',
            'Recommendation_parsed', 'SLA_Formatted', 'SLA_Hours',
            'Initiation_parsed', 'Initiation_SLA_Formatted', 'Initiation_SLA_Hours',
            'ApprovalCC1_SLA_Formatted', 'ApprovalCC1_SLA_Hours',
            'Scoring_Detail', 'OSPH_Category', 'Segmen_clean',
            'JenisKendaraan_clean', 'Pekerjaan_clean', 'LastOD_clean',
            'user_name_clean', 'branch_name_clean'
        ]
        
        # Rename for better display
        col_rename = {
            'apps_id': '🔢 ID Aplikasi',
            'apps_status_clean': '📋 Status',
            'action_on_parsed': '📅 Waktu Aksi',
            'Recommendation_parsed': '📝 Waktu Rekomendasi',
            'SLA_Formatted': '⏱️ SLA Rekomendasi',
            'SLA_Hours': '⏱️ SLA (Jam)',
            'Initiation_parsed': '🚀 Waktu Pengajuan',
            'Initiation_SLA_Formatted': '⏱️ SLA Pengajuan',
            'Initiation_SLA_Hours': '⏱️ SLA Pengajuan (Jam)',
            'ApprovalCC1_SLA_Formatted': '⏱️ SLA Approval',
            'ApprovalCC1_SLA_Hours': '⏱️ SLA Approval (Jam)',
            'Scoring_Detail': '✅ Hasil Penilaian',
            'OSPH_Category': '💰 Kategori Plafon',
            'Segmen_clean': '🎯 Segmen',
            'JenisKendaraan_clean': '🚗 Jenis Kendaraan',
            'Pekerjaan_clean': '💼 Pekerjaan',
            'LastOD_clean': '⚠️ Last OD (Hari)',
            'user_name_clean': '👤 Credit Analyst',
            'branch_name_clean': '🏢 Cabang'
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
        st.markdown("### 📥 Unduh File")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="metric-box-success">
            <h4>📊 Data Lengkap</h4>
            <p>Unduh semua data yang sudah difilter dalam format CSV</p>
            </div>
            """, unsafe_allow_html=True)
            
            csv_data = df_filtered[available_cols].to_csv(index=False)
            st.download_button(
                "⬇️ Unduh Data Lengkap (CSV)",
                csv_data,
                "data_analisis_kredit.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            st.markdown("""
            <div class="metric-box">
            <h4>📈 Ringkasan Statistik</h4>
            <p>Unduh metrik utama dan ringkasan dalam format CSV</p>
            </div>
            """, unsafe_allow_html=True)
            
            df_distinct_export = df_filtered.drop_duplicates('apps_id')
            approve_count = df_distinct_export['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
            total_scored = len(df_distinct_export[df_distinct_export['Scoring_Detail'] != '(Semua)'])
            
            summary_data = {
                '📊 Metrik': [
                    'Total Catatan',
                    'Aplikasi Unik',
                    'Data SLA Lengkap',
                    'Rata-rata Waktu Proses (jam)',
                    'Tingkat Persetujuan'
                ],
                '📈 Nilai': [
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
                "⬇️ Unduh Ringkasan (CSV)",
                csv_summary,
                "ringkasan_statistik.csv",
                "text/csv",
                use_container_width=True
            )
    
    st.markdown("---")
    
    # Footer
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"📅 **Terakhir Diperbarui:** {datetime.now().strftime('%d %B %Y, %H:%M:%S')}")
    with col2:
        st.caption(f"📊 **Total Data:** {len(df):,} catatan")
    with col3:
        st.caption(f"🎯 **Aplikasi Unik:** {df['apps_id'].nunique():,}")

if __name__ == "__main__":
    main()
