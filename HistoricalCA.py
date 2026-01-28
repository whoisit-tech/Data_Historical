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
    Hitung SLA dalam working hours (08:30 - 17:30)
    Exclude weekend dan tanggal merah
    
    Returns: dict dengan days, hours, minutes, seconds, working_days
    """
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        
        # Jika end sebelum start, return None
        if end_dt <= start_dt:
            return None
        
        # Working hours: 08:30 - 17:30 (9 jam = 540 menit per hari)
        WORK_START = timedelta(hours=8, minutes=30)
        WORK_END = timedelta(hours=17, minutes=30)
        WORK_HOURS_PER_DAY = 9 * 3600  # dalam detik
        
        current = start_dt
        total_seconds = 0
        working_days_count = 0
        
        # Loop per hari
        while current.date() <= end_dt.date():
            # Skip jika weekend atau holiday
            if not is_working_day(current):
                current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
                continue
            
            working_days_count += 1
            
            # Tentukan start dan end untuk hari ini
            day_start = datetime.combine(current.date(), datetime.min.time()) + WORK_START
            day_end = datetime.combine(current.date(), datetime.min.time()) + WORK_END
            
            # Sesuaikan dengan actual start/end time
            if current.date() == start_dt.date():
                # Hari pertama
                if start_dt.time() < day_start.time():
                    day_actual_start = day_start
                elif start_dt.time() > day_end.time():
                    # Start setelah jam kerja, skip hari ini
                    current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
                    working_days_count -= 1
                    continue
                else:
                    day_actual_start = start_dt
            else:
                day_actual_start = day_start
            
            if current.date() == end_dt.date():
                # Hari terakhir
                if end_dt.time() < day_start.time():
                    # End sebelum jam kerja mulai, skip hari ini
                    break
                elif end_dt.time() > day_end.time():
                    day_actual_end = day_end
                else:
                    day_actual_end = end_dt
            else:
                day_actual_end = day_end
            
            # Hitung detik untuk hari ini
            if day_actual_end > day_actual_start:
                day_seconds = (day_actual_end - day_actual_start).total_seconds()
                total_seconds += day_seconds
            
            # Next day
            current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
        
        # Convert ke days, hours, minutes, seconds
        days = int(total_seconds // 86400)
        remaining = int(total_seconds % 86400)
        hours = remaining // 3600
        remaining = remaining % 3600
        minutes = remaining // 60
        seconds = remaining % 60
        
        # Working days dalam business days (bukan calendar days)
        working_days_business = total_seconds / WORK_HOURS_PER_DAY
        
        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'working_days': round(working_days_business, 2),
            'total_seconds': total_seconds,
            'formatted': f"{days}d {hours}h {minutes}m {seconds}s"
        }
    except Exception as e:
        return None

def calculate_row_sla(df):
    """
    Calculate SLA per row berdasarkan logika:
    1. PENDING CA: action - Recommendation (baris yang sama)
    2. PENDING CA COMPLETED: action baris ini - action baris sebelumnya (apps_id sama)
    3. NOT RECOMMENDED/RECOMMENDED CA/RECOMMENDED CA WITH COND: 
       - Jika ada baris sebelumnya: action baris ini - action baris sebelumnya
       - Jika tidak ada baris sebelumnya: action - Recommendation (baris yang sama)
    
    Returns: DataFrame dengan kolom SLA tambahan
    """
    df_sorted = df.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
    
    # Initialize SLA columns
    df_sorted['SLA_Start'] = None
    df_sorted['SLA_End'] = None
    df_sorted['SLA_Days'] = None
    df_sorted['SLA_Formatted'] = '—'
    df_sorted['SLA_Logic'] = 'N/A'
    
    # Group by apps_id
    for app_id, group in df_sorted.groupby('apps_id'):
        group = group.reset_index(drop=True)
        
        for idx in range(len(group)):
            row_idx = group.index[idx]
            current_status = str(group.at[idx, 'apps_status_clean']).upper()
            current_action = group.at[idx, 'action_on_parsed']
            current_recommendation = group.at[idx, 'Recommendation_parsed']
            
            sla_start = None
            sla_end = current_action
            logic = 'N/A'
            
            # LOGIKA 1: PENDING CA
            if 'PENDING CA' in current_status and 'COMPLETED' not in current_status:
                if pd.notna(current_recommendation):
                    sla_start = current_recommendation
                    logic = 'PENDING CA: action - Recommendation (same row)'
                else:
                    logic = 'PENDING CA: No Recommendation data'
            
            # LOGIKA 2: PENDING CA COMPLETED
            elif 'PENDING CA COMPLETED' in current_status or 'PENDING CA COMPLETED' in current_status.replace(' ', ''):
                if idx > 0:
                    # Ada baris sebelumnya
                    prev_action = group.at[idx - 1, 'action_on_parsed']
                    sla_start = prev_action
                    logic = 'PENDING CA COMPLETED: action this row - action previous row'
                else:
                    # Baris pertama, cek recommendation
                    if pd.notna(current_recommendation):
                        sla_start = current_recommendation
                        logic = 'PENDING CA COMPLETED: action - Recommendation (first row)'
                    else:
                        logic = 'PENDING CA COMPLETED: First row, no Recommendation'
            
            # LOGIKA 3: Status lainnya (NOT RECOMMENDED, RECOMMENDED CA, RECOMMENDED CA WITH COND)
            elif any(status in current_status for status in ['NOT RECOMMENDED', 'RECOMMENDED CA']):
                if idx > 0:
                    # Ada baris sebelumnya
                    prev_action = group.at[idx - 1, 'action_on_parsed']
                    sla_start = prev_action
                    logic = f'{current_status}: action this row - action previous row'
                else:
                    # Baris pertama, gunakan recommendation
                    if pd.notna(current_recommendation):
                        sla_start = current_recommendation
                        logic = f'{current_status}: action - Recommendation (first row)'
                    else:
                        logic = f'{current_status}: First row, no Recommendation'
            
            # Hitung SLA jika ada start dan end
            if sla_start and sla_end and pd.notna(sla_start) and pd.notna(sla_end):
                sla_result = calculate_sla_working_hours(sla_start, sla_end)
                if sla_result:
                    df_sorted.at[row_idx, 'SLA_Start'] = sla_start
                    df_sorted.at[row_idx, 'SLA_End'] = sla_end
                    df_sorted.at[row_idx, 'SLA_Days'] = sla_result['working_days']
                    df_sorted.at[row_idx, 'SLA_Formatted'] = sla_result['formatted']
                    df_sorted.at[row_idx, 'SLA_Logic'] = logic
                else:
                    df_sorted.at[row_idx, 'SLA_Logic'] = logic + ' (calculation failed)'
            else:
                df_sorted.at[row_idx, 'SLA_Logic'] = logic
    
    return df_sorted

def get_osph_category(osph_value):
    """Categorize Outstanding PH into ranges"""
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
    """Calculate risk score based on multiple factors"""
    score = 0
    
    # OSPH risk contribution
    if pd.notna(row.get('OSPH_clean')):
        if row['OSPH_clean'] > 500000000:
            score += 30
        elif row['OSPH_clean'] > 250000000:
            score += 20
        else:
            score += 10
    
    # LastOD risk contribution
    if pd.notna(row.get('LastOD_clean')):
        if row['LastOD_clean'] > 30:
            score += 40
        elif row['LastOD_clean'] > 10:
            score += 25
        elif row['LastOD_clean'] > 0:
            score += 15
    
    # SLA risk contribution
    if pd.notna(row.get('SLA_Days')):
        if row['SLA_Days'] > 5:
            score += 20
        elif row['SLA_Days'] > 3:
            score += 10
    
    return min(score, 100)

def preprocess_data(df):
    """Clean and prepare data for analysis"""
    df = df.copy()
    
    # Parse dates - INCLUDING RECOMMENDATION
    for col in ['action_on', 'Initiation', 'RealisasiDate', 'Recommendation']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Clean apps_status
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
    # Clean Outstanding PH
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(
            df['Outstanding_PH'].astype(str).str.replace(',', ''), 
            errors='coerce'
        )
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    # Clean OD columns
    for col in ['LastOD', 'max_OD']:
        if col in df.columns:
            df[f'{col}_clean'] = pd.to_numeric(df[col], errors='coerce')
    
    # Clean Hasil_Scoring
    if 'Hasil_Scoring' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring'].fillna('(Pilih Semua)').astype(str).str.strip()
    
    # Clean Segmen
    if 'Segmen' in df.columns:
        df['Segmen_clean'] = df['Segmen'].fillna('Unknown').astype(str).str.strip()
    else:
        df['Segmen_clean'] = 'Unknown'
    
    # Extract time features
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Quarter'] = df['action_on_parsed'].dt.quarter
    
    # Clean categorical columns
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
    """Load and preprocess data from Excel file"""
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
        
        df_clean = preprocess_data(df)
        
        # Calculate SLA per row
        df_clean = calculate_row_sla(df_clean)
        
        # Calculate risk score SETELAH SLA
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

def create_osph_analysis_3d(df):
    """
    Create 3-dimensional OSPH analysis per Segmen:
    - Dimension 1: By Pekerjaan per Segmen
    - Dimension 2: By JenisKendaraan per Segmen
    - Dimension 3: By Hasil_Scoring per Segmen
    """
    analyses = {}
    
    # Filter valid data
    df_valid = df[
        (df['OSPH_clean'].notna()) & 
        (df['OSPH_Category'] != 'Unknown') &
        (df['Segmen_clean'] != 'Unknown')
    ].copy()
    
    if len(df_valid) == 0:
        return analyses
    
    # DIMENSION 1: OSPH by Pekerjaan per Segmen
    if 'Pekerjaan_clean' in df_valid.columns:
        dim1_data = df_valid.groupby(
            ['Segmen_clean', 'Pekerjaan_clean', 'OSPH_Category']
        ).agg({
            'apps_id': 'nunique',
            'OSPH_clean': 'mean'
        }).reset_index()
        dim1_data.columns = ['Segmen', 'Pekerjaan', 'OSPH_Category', 'Total_Apps', 'Avg_OSPH']
        
        # Add record count
        record_counts = df_valid.groupby(
            ['Segmen_clean', 'Pekerjaan_clean', 'OSPH_Category']
        ).size().reset_index(name='Total_Records')
        
        dim1_data = dim1_data.merge(
            record_counts, 
            left_on=['Segmen', 'Pekerjaan', 'OSPH_Category'],
            right_on=['Segmen_clean', 'Pekerjaan_clean', 'OSPH_Category'],
            how='left'
        )
        dim1_data = dim1_data.drop(['Segmen_clean', 'Pekerjaan_clean'], axis=1, errors='ignore')
        
        analyses['pekerjaan'] = dim1_data
    
    # DIMENSION 2: OSPH by JenisKendaraan per Segmen
    if 'JenisKendaraan_clean' in df_valid.columns:
        dim2_data = df_valid.groupby(
            ['Segmen_clean', 'JenisKendaraan_clean', 'OSPH_Category']
        ).agg({
            'apps_id': 'nunique',
            'OSPH_clean': 'mean'
        }).reset_index()
        dim2_data.columns = ['Segmen', 'JenisKendaraan', 'OSPH_Category', 'Total_Apps', 'Avg_OSPH']
        
        # Add record count
        record_counts = df_valid.groupby(
            ['Segmen_clean', 'JenisKendaraan_clean', 'OSPH_Category']
        ).size().reset_index(name='Total_Records')
        
        dim2_data = dim2_data.merge(
            record_counts,
            left_on=['Segmen', 'JenisKendaraan', 'OSPH_Category'],
            right_on=['Segmen_clean', 'JenisKendaraan_clean', 'OSPH_Category'],
            how='left'
        )
        dim2_data = dim2_data.drop(['Segmen_clean', 'JenisKendaraan_clean'], axis=1, errors='ignore')
        
        analyses['kendaraan'] = dim2_data
    
    # DIMENSION 3: OSPH by Hasil_Scoring per Segmen
    if 'Scoring_Detail' in df_valid.columns:
        # Filter out placeholder values
        df_scoring = df_valid[df_valid['Scoring_Detail'] != '(Pilih Semua)']
        
        dim3_data = df_scoring.groupby(
            ['Segmen_clean', 'Scoring_Detail', 'OSPH_Category']
        ).agg({
            'apps_id': 'nunique',
            'OSPH_clean': 'mean'
        }).reset_index()
        dim3_data.columns = ['Segmen', 'Hasil_Scoring', 'OSPH_Category', 'Total_Apps', 'Avg_OSPH']
        
        # Add record count
        record_counts = df_scoring.groupby(
            ['Segmen_clean', 'Scoring_Detail', 'OSPH_Category']
        ).size().reset_index(name='Total_Records')
        
        dim3_data = dim3_data.merge(
            record_counts,
            left_on=['Segmen', 'Hasil_Scoring', 'OSPH_Category'],
            right_on=['Segmen_clean', 'Scoring_Detail', 'OSPH_Category'],
            how='left'
        )
        dim3_data = dim3_data.drop(['Segmen_clean', 'Scoring_Detail'], axis=1, errors='ignore')
        
        analyses['scoring'] = dim3_data
    
    return analyses

def generate_analytical_insights(df):
    """Generate insights and warnings from data"""
    insights = []
    warnings = []
    
    # Insight 1: OSPH vs Approval Rate
    if 'OSPH_Category' in df.columns and 'Scoring_Detail' in df.columns:
        for osph in ['0 - 250 Juta', '250 - 500 Juta', '500 Juta+']:
            df_osph = df[df['OSPH_Category'] == osph]
            if len(df_osph) > 0:
                approve = df_osph['Scoring_Detail'].isin(
                    ['APPROVE', 'APPROVE 1', 'APPROVE 2']
                ).sum()
                total = len(df_osph[df_osph['Scoring_Detail'] != '(Pilih Semua)'])
                
                if total > 0:
                    rate = approve / total * 100
                    if rate < 30:
                        warnings.append(
                            f"Low approval rate {rate:.1f}% in {osph} segment"
                        )
                    elif rate > 60:
                        insights.append(
                            f"Strong approval rate {rate:.1f}% in {osph} segment"
                        )
    
    # Insight 2: SLA Performance
    if 'SLA_Days' in df.columns:
        sla_valid = df[df['SLA_Days'].notna()]
        if len(sla_valid) > 0:
            avg_sla = sla_valid['SLA_Days'].mean()
            if avg_sla > 5:
                warnings.append(
                    f"Average SLA is {avg_sla:.1f} working days (target: ≤5 days)"
                )
            else:
                insights.append(
                    f"Good SLA performance: {avg_sla:.1f} working days average"
                )
    
    # Insight 3: High Risk Cases
    if 'Risk_Category' in df.columns:
        high_risk = (df['Risk_Category'] == 'High Risk').sum()
        total = len(df[df['Risk_Category'].notna()])
        if total > 0:
            risk_pct = high_risk / total * 100
            if risk_pct > 20:
                warnings.append(
                    f"{risk_pct:.1f}% of cases are high risk (>20% threshold)"
                )
    
    return insights, warnings

def main():
    """Main application"""
    st.title(" CA Analytics Dashboard - Enhanced v2")
    st.markdown("** Per-Row SLA Calculation | 3D OSPH Analysis per Segmen**")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading dan processing data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    # Display data summary
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    sla_calculated = df['SLA_Days'].notna().sum()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(" Total Records", f"{total_records:,}")
    with col2:
        st.metric(" Unique Applications", f"{unique_apps:,}")
    with col3:
        st.metric(" SLA Calculated", f"{sla_calculated:,}")
    with col4:
        avg_sla = df[df['SLA_Days'].notna()]['SLA_Days'].mean()
        st.metric(" Average SLA", f"{avg_sla:.2f} days" if pd.notna(avg_sla) else "N/A")
    
    st.markdown("---")
    
    # Sidebar filters
    st.sidebar.title("Analytics Control Panel")
    
    # Status filter
    if 'apps_status_clean' in df.columns:
        all_status = sorted([
            x for x in df['apps_status_clean'].unique() 
            if x != 'Unknown'
        ])
        selected_status = st.sidebar.multiselect(
            "Application Status",
            all_status,
            default=all_status
        )
    else:
        selected_status = []
    
    # Scoring filter
    if 'Scoring_Detail' in df.columns:
        all_scoring = sorted([
            x for x in df['Scoring_Detail'].unique() 
            if x != '(Pilih Semua)'
        ])
        selected_scoring = st.sidebar.multiselect(
            "Scoring Result",
            all_scoring,
            default=all_scoring
        )
    else:
        selected_scoring = []
    
    # Segmen filter
    if 'Segmen_clean' in df.columns:
        all_segmen = sorted([x for x in df['Segmen_clean'].unique() if x != 'Unknown'])
        selected_segmen = st.sidebar.selectbox(
            "Segmen",
            ['All'] + all_segmen
        )
    else:
        selected_segmen = 'All'
    
    # Branch filter
    if 'branch_name_clean' in df.columns:
        all_branches = sorted(df['branch_name_clean'].unique().tolist())
        selected_branch = st.sidebar.selectbox(
            "Branch",
            ['All'] + all_branches
        )
    else:
        selected_branch = 'All'
    
    # CA filter
    if 'user_name_clean' in df.columns:
        all_cas = sorted(df['user_name_clean'].unique().tolist())
        selected_ca = st.sidebar.selectbox(
            "CA Name",
            ['All'] + all_cas
        )
    else:
        selected_ca = 'All'
    
    # Outstanding PH filter
    if 'OSPH_Category' in df.columns:
        all_osph = sorted([
            x for x in df['OSPH_Category'].unique() 
            if x != 'Unknown'
        ])
        selected_osph = st.sidebar.selectbox(
            "Outstanding PH",
            ['All'] + all_osph
        )
    else:
        selected_osph = 'All'
    
    # Apply filters
    df_filtered = df.copy()
    
    if selected_status:
        df_filtered = df_filtered[
            df_filtered['apps_status_clean'].isin(selected_status)
        ]
    
    if selected_scoring:
        df_filtered = df_filtered[
            df_filtered['Scoring_Detail'].isin(selected_scoring)
        ]
    
    if selected_segmen != 'All':
        df_filtered = df_filtered[
            df_filtered['Segmen_clean'] == selected_segmen
        ]
    
    if selected_branch != 'All':
        df_filtered = df_filtered[
            df_filtered['branch_name_clean'] == selected_branch
        ]
    
    if selected_ca != 'All':
        df_filtered = df_filtered[
            df_filtered['user_name_clean'] == selected_ca
        ]
    
    if selected_osph != 'All':
        df_filtered = df_filtered[
            df_filtered['OSPH_Category'] == selected_osph
        ]
    
    # Sidebar summary
    st.sidebar.markdown("---")
    st.sidebar.info(
        f"{len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)"
    )
    st.sidebar.info(
        f"{df_filtered['apps_id'].nunique():,} unique applications"
    )
    
    # Insights
    st.header(" Key Insights")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    if warnings:
        st.warning(" **Alerts:**\n" + "\n".join([f"• {w}" for w in warnings]))
    
    if insights:
        st.success(" **Positive Findings:**\n" + "\n".join([f"• {i}" for i in insights]))
    
    st.markdown("---")
    
    # Tabs
    (
        tab1, tab2, tab3, tab4
    ) = st.tabs([
        " SLA Overview",
        " OSPH Analysis 3D per Segmen",
        " Detailed View",
        " Raw Data"
    ])
    
    # Tab 1: SLA Overview
    with tab1:
        st.header("SLA Performance Overview")
        st.info(" SLA dihitung per row dengan logika yang benar")
        
        # SLA Metrics
        sla_valid = df_filtered[df_filtered['SLA_Days'].notna()]
        
        if len(sla_valid) > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Average SLA", f"{sla_valid['SLA_Days'].mean():.2f} days")
            
            with col2:
                st.metric("Median SLA", f"{sla_valid['SLA_Days'].median():.2f} days")
            
            with col3:
                st.metric("90th Percentile", f"{sla_valid['SLA_Days'].quantile(0.9):.2f} days")
            
            with col4:
                exceed_5 = (sla_valid['SLA_Days'] > 5).sum()
                pct = exceed_5 / len(sla_valid) * 100
                st.metric("Exceed 5 Days", f"{exceed_5} ({pct:.1f}%)")
            
            st.markdown("---")
            
            # SLA Distribution
            st.subheader("SLA Distribution")
            
            fig = px.histogram(
                sla_valid,
                x='SLA_Days',
                nbins=50,
                title="SLA Distribution (Working Days)",
                labels={'SLA_Days': 'Working Days'},
                color_discrete_sequence=['#667eea']
            )
            fig.add_vline(x=5, line_dash="dash", line_color="red", 
                         annotation_text="5 Days Target")
            st.plotly_chart(fig, use_container_width=True)
            
            # SLA by Status
            st.subheader("Average SLA by Status")
            
            sla_by_status = sla_valid.groupby('apps_status_clean').agg({
                'SLA_Days': ['mean', 'median', 'count']
            }).reset_index()
            sla_by_status.columns = ['Status', 'Avg_SLA', 'Median_SLA', 'Count']
            sla_by_status = sla_by_status.sort_values('Avg_SLA', ascending=False)
            
            st.dataframe(sla_by_status, use_container_width=True, hide_index=True)
            
            fig = px.bar(
                sla_by_status,
                x='Status',
                y='Avg_SLA',
                text='Count',
                title="Average SLA by Application Status",
                labels={'Avg_SLA': 'Average SLA (Days)'},
                color='Avg_SLA',
                color_continuous_scale='RdYlGn_r'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            # SLA Logic Distribution
            st.markdown("---")
            st.subheader("SLA Calculation Logic Distribution")
            
            logic_counts = sla_valid['SLA_Logic'].value_counts().reset_index()
            logic_counts.columns = ['Logic', 'Count']
            
            fig = px.pie(
                logic_counts,
                values='Count',
                names='Logic',
                title="Distribution of SLA Calculation Methods"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No SLA data available for current filters")
    
    # Tab 2: OSPH Analysis 3D per Segmen
    with tab2:
        st.header("OSPH Analysis - 3 Dimensi per Segmen")
        st.info("Analisis OSPH berdasarkan 3 dimensi: Pekerjaan, Jenis Kendaraan, dan Hasil Scoring - masing-masing per Segmen")
        
        # Generate OSPH analysis
        osph_analyses = create_osph_analysis_3d(df_filtered)
        
        if osph_analyses:
            # Sub-tabs for each dimension
            dim_tab1, dim_tab2, dim_tab3 = st.tabs([
                " Dimensi 1: Pekerjaan",
                " Dimensi 2: Jenis Kendaraan",
                " Dimensi 3: Hasil Scoring"
            ])
            
            # DIMENSION 1: Pekerjaan
            with dim_tab1:
                if 'pekerjaan' in osph_analyses:
                    df_pek = osph_analyses['pekerjaan']
                    
                    st.subheader("OSPH by Pekerjaan per Segmen")
                    st.markdown("**Tabel lengkap dengan Total Apps dan Total Records**")
                    
                    # Summary table
                    st.dataframe(
                        df_pek.sort_values(['Segmen', 'Total_Apps'], ascending=[True, False]),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown("---")
                    
                    # Sunburst visualization
                    st.subheader("Visualisasi Hierarki: Segmen → Pekerjaan → OSPH Range")
                    
                    fig = px.sunburst(
                        df_pek,
                        path=['Segmen', 'Pekerjaan', 'OSPH_Category'],
                        values='Total_Apps',
                        title="OSPH Distribution by Pekerjaan per Segmen",
                        color='Avg_OSPH',
                        color_continuous_scale='RdYlGn_r'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Bar charts per segmen
                    st.subheader("Detail per Segmen")
                    
                    for segmen in sorted(df_pek['Segmen'].unique()):
                        df_seg = df_pek[df_pek['Segmen'] == segmen]
                        
                        fig = px.bar(
                            df_seg,
                            x='Pekerjaan',
                            y='Total_Apps',
                            color='OSPH_Category',
                            title=f"Segmen: {segmen} - Pekerjaan Distribution",
                            barmode='stack',
                            text='Total_Apps'
                        )
                        fig.update_xaxes(tickangle=45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data available for Pekerjaan analysis")
            
            # DIMENSION 2: Jenis Kendaraan
            with dim_tab2:
                if 'kendaraan' in osph_analyses:
                    df_ken = osph_analyses['kendaraan']
                    
                    st.subheader("OSPH by Jenis Kendaraan per Segmen")
                    st.markdown("**Tabel lengkap dengan Total Apps dan Total Records**")
                    
                    # Summary table
                    st.dataframe(
                        df_ken.sort_values(['Segmen', 'Total_Apps'], ascending=[True, False]),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown("---")
                    
                    # Sunburst visualization
                    st.subheader("Visualisasi Hierarki: Segmen → Jenis Kendaraan → OSPH Range")
                    
                    fig = px.sunburst(
                        df_ken,
                        path=['Segmen', 'JenisKendaraan', 'OSPH_Category'],
                        values='Total_Apps',
                        title="OSPH Distribution by Jenis Kendaraan per Segmen",
                        color='Avg_OSPH',
                        color_continuous_scale='RdYlGn_r'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Bar charts per segmen
                    st.subheader("Detail per Segmen")
                    
                    for segmen in sorted(df_ken['Segmen'].unique()):
                        df_seg = df_ken[df_ken['Segmen'] == segmen]
                        
                        fig = px.bar(
                            df_seg,
                            x='JenisKendaraan',
                            y='Total_Apps',
                            color='OSPH_Category',
                            title=f"Segmen: {segmen} - Jenis Kendaraan Distribution",
                            barmode='stack',
                            text='Total_Apps'
                        )
                        fig.update_xaxes(tickangle=45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data available for Jenis Kendaraan analysis")
            
            # DIMENSION 3: Hasil Scoring
            with dim_tab3:
                if 'scoring' in osph_analyses:
                    df_scr = osph_analyses['scoring']
                    
                    st.subheader("OSPH by Hasil Scoring per Segmen")
                    st.markdown("**Tabel lengkap dengan Total Apps dan Total Records**")
                    
                    # Summary table
                    st.dataframe(
                        df_scr.sort_values(['Segmen', 'Total_Apps'], ascending=[True, False]),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown("---")
                    
                    # Sunburst visualization
                    st.subheader("Visualisasi Hierarki: Segmen → Hasil Scoring → OSPH Range")
                    
                    fig = px.sunburst(
                        df_scr,
                        path=['Segmen', 'Hasil_Scoring', 'OSPH_Category'],
                        values='Total_Apps',
                        title="OSPH Distribution by Hasil Scoring per Segmen",
                        color='Avg_OSPH',
                        color_continuous_scale='RdYlGn_r'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Bar charts per segmen
                    st.subheader("Detail per Segmen")
                    
                    for segmen in sorted(df_scr['Segmen'].unique()):
                        df_seg = df_scr[df_scr['Segmen'] == segmen]
                        
                        fig = px.bar(
                            df_seg,
                            x='Hasil_Scoring',
                            y='Total_Apps',
                            color='OSPH_Category',
                            title=f"Segmen: {segmen} - Hasil Scoring Distribution",
                            barmode='stack',
                            text='Total_Apps'
                        )
                        fig.update_xaxes(tickangle=45)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data available for Hasil Scoring analysis")
        else:
            st.warning("No data available for OSPH analysis with current filters")
    
    # Tab 3: Detailed View
    with tab3:
        st.header("Detailed SLA View per Application")
        
        # Select app to view
        sample_apps = sorted(df_filtered['apps_id'].unique())
        
        if len(sample_apps) > 0:
            selected_app = st.selectbox(
                "Select Application ID:",
                sample_apps,
                key='detailed_view_app'
            )
            
            if selected_app:
                app_data = df_filtered[df_filtered['apps_id'] == selected_app].sort_values('action_on_parsed')
                
                st.subheader(f"Application ID: {selected_app}")
                
                # Display key info
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'Segmen_clean' in app_data.columns:
                        st.info(f"**Segmen:** {app_data['Segmen_clean'].iloc[0]}")
                
                with col2:
                    if 'OSPH_Category' in app_data.columns:
                        st.info(f"**OSPH:** {app_data['OSPH_Category'].iloc[0]}")
                
                with col3:
                    if 'branch_name_clean' in app_data.columns:
                        st.info(f"**Branch:** {app_data['branch_name_clean'].iloc[0]}")
                
                st.markdown("---")
                
                # Timeline visualization
                st.subheader("Status Timeline")
                
                timeline_data = []
                for idx, row in app_data.iterrows():
                    timeline_data.append({
                        'Status': row['apps_status_clean'],
                        'Time': row['action_on_parsed'],
                        'SLA': row['SLA_Formatted'],
                        'Logic': row['SLA_Logic']
                    })
                
                timeline_df = pd.DataFrame(timeline_data)
                
                fig = px.scatter(
                    timeline_df,
                    x='Time',
                    y='Status',
                    text='SLA',
                    title=f"Status Progression for {selected_app}",
                    color='Status'
                )
                fig.update_traces(textposition='top center', marker=dict(size=15))
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed table
                st.subheader("Detailed Records")
                
                display_cols = [
                    'apps_status_clean', 'action_on_parsed', 'Recommendation_parsed',
                    'SLA_Start', 'SLA_End', 'SLA_Days', 'SLA_Formatted', 'SLA_Logic',
                    'Scoring_Detail', 'user_name_clean'
                ]
                
                available_cols = [c for c in display_cols if c in app_data.columns]
                
                st.dataframe(
                    app_data[available_cols],
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No applications available with current filters")
    
    # Tab 4: Raw Data
    with tab4:
        st.header("Raw Data Export")
        st.info("View and download filtered data")
        
        st.subheader("Data Preview (First 100 rows)")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed',
            'Recommendation_parsed', 'SLA_Start', 'SLA_End',
            'SLA_Days', 'SLA_Formatted', 'SLA_Logic',
            'Scoring_Detail', 'OSPH_clean', 'OSPH_Category',
            'Pekerjaan_clean', 'JenisKendaraan_clean',
            'LastOD_clean', 'user_name_clean', 'branch_name_clean',
            'Segmen_clean'
        ]
        
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        
        st.dataframe(
            df_filtered[available_cols].head(100),
            use_container_width=True,
            hide_index=True
        )
        
        st.info(f"Showing first 100 of {len(df_filtered):,} records")
        
        # Download options
        st.markdown("---")
        st.subheader("Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = df_filtered[available_cols].to_csv(index=False)
            st.download_button(
                " Download Filtered Data (CSV)",
                csv_data,
                "ca_analytics_filtered.csv",
                "text/csv"
            )
        
        with col2:
            # Create OSPH analysis export
            osph_analyses = create_osph_analysis_3d(df_filtered)
            if osph_analyses:
                # Combine all dimensions
                export_data = []
                
                for dim_name, dim_data in osph_analyses.items():
                    dim_data_copy = dim_data.copy()
                    dim_data_copy['Dimension'] = dim_name
                    export_data.append(dim_data_copy)
                
                if export_data:
                    osph_export = pd.concat(export_data, ignore_index=True)
                    csv_osph = osph_export.to_csv(index=False)
                    st.download_button(
                        " Download OSPH Analysis (CSV)",
                        csv_osph,
                        "osph_analysis_3d.csv",
                        "text/csv"
                    )
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
