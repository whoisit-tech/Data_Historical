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
    Hitung SLA dalam working hours (08:30 - 15:30)
    Exclude weekend dan tanggal merah
    
    PENTING: Jika start_dt di luar jam kerja, akan dimulai dari jam kerja berikutnya
    - Jika start > 15:30 → mulai dari 08:30 hari kerja berikutnya
    - Jika start < 08:30 → mulai dari 08:30 hari yang sama
    
    Returns: dict dengan total_hours (float), formatted (string dalam jam)
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
        
        # Working hours: 08:30 - 15:30 (7 jam per hari)
        WORK_START = timedelta(hours=8, minutes=30)
        WORK_END = timedelta(hours=15, minutes=30)
        
        current = start_dt
        total_seconds = 0
        
        # Loop per hari
        while current.date() <= end_dt.date():
            # Skip jika weekend atau holiday
            if not is_working_day(current):
                current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
                continue
            
            # Tentukan start dan end untuk hari ini
            day_start = datetime.combine(current.date(), datetime.min.time()) + WORK_START
            day_end = datetime.combine(current.date(), datetime.min.time()) + WORK_END
            
            # Sesuaikan dengan actual start/end time
            if current.date() == start_dt.date():
                # Hari pertama
                if start_dt.time() < day_start.time():
                    # Start sebelum jam kerja → mulai dari 08:30
                    day_actual_start = day_start
                elif start_dt.time() >= day_end.time():
                    # Start setelah/sama dengan jam kerja selesai (>= 15:30) → skip hari ini
                    current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
                    continue
                else:
                    # Start di dalam jam kerja
                    day_actual_start = start_dt
            else:
                day_actual_start = day_start
            
            if current.date() == end_dt.date():
                # Hari terakhir
                if end_dt.time() < day_start.time():
                    # End sebelum jam kerja mulai, skip hari ini
                    break
                elif end_dt.time() > day_end.time():
                    # End setelah jam kerja → potong sampai 15:30
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
        
        if total_seconds < 0:
            return None
        
        # Convert ke jam (float)
        total_hours = total_seconds / 3600
        
        # Format dalam jam, menit, detik
        hours = int(total_seconds // 3600)
        remaining = int(total_seconds % 3600)
        minutes = remaining // 60
        seconds = remaining % 60
        
        return {
            'total_hours': round(total_hours, 2),
            'total_seconds': total_seconds,
            'formatted': f"{hours}h {minutes}m {seconds}s"
        }
    except Exception as e:
        return None

def calculate_historical_sla(df):
    """
    Calculate SLA per transition yang SEBENARNYA terjadi
    
    LOGIKA BENAR:
    1. Sort by apps_id dan action_on_parsed
    2. Untuk PENDING CA: SLA = action_on - Recommendation
    3. Untuk PENDING CA COMPLETED: SLA = action_on - action_on PENDING CA sebelumnya
    4. Untuk RECOMMENDATION CA: SLA = action_on - action_on PENDING CA COMPLETED sebelumnya
    5. Status lain: SLA = action_on current - action_on previous
    
    ✅ SLA dalam JAM (bukan days)
    """
    # Sort dulu
    df_sorted = df.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
    sla_list = []
    
    # Group by apps_id untuk efisiensi
    for app_id, group in df_sorted.groupby('apps_id'):
        group = group.reset_index(drop=True)
        
        for idx in range(len(group)):
            row = group.iloc[idx]
            current_status = row.get('apps_status_clean', 'Unknown')
            current_time = row.get('action_on_parsed')
            recommendation_time = row.get('Recommendation_parsed')
            
            # Jika ini row pertama untuk app ini
            if idx == 0:
                # Untuk row pertama, cek apakah PENDING CA dengan Recommendation
                if current_status.upper() == 'PENDING CA' and pd.notna(recommendation_time):
                    # PENDING CA dengan Recommendation: SLA = action_on - Recommendation
                    sla_result = calculate_sla_working_hours(recommendation_time, current_time)
                    if sla_result:
                        sla_formatted = sla_result['formatted']
                        sla_hours = sla_result['total_hours']
                    else:
                        sla_formatted = '—'
                        sla_hours = None
                    transition = f"START → {current_status}"
                    start_time = recommendation_time
                else:
                    # Row pertama tanpa Recommendation atau bukan PENDING CA
                    sla_formatted = '—'
                    sla_hours = None
                    transition = f"START → {current_status}"
                    start_time = None
                
                sla_list.append({
                    'idx': row.name,  # original index
                    'apps_id': app_id,
                    'Transition': transition,
                    'From_Status': 'START',
                    'To_Status': current_status,
                    'SLA_Hours': sla_hours,
                    'SLA_Formatted': sla_formatted,
                    'Start_Time': start_time,
                    'End_Time': current_time,
                    'Recommendation': recommendation_time
                })
                continue
            
            # Ada previous row
            prev_row = group.iloc[idx - 1]
            prev_status = prev_row.get('apps_status_clean', 'Unknown')
            prev_time = prev_row.get('action_on_parsed')
            
            # Hitung SLA berdasarkan status
            sla_result = None
            sla_formatted = '—'
            start_time = prev_time
            transition = f"{prev_status} → {current_status}"
            
            # LOGIKA KHUSUS UNTUK PENDING CA
            if current_status.upper() == 'PENDING CA':
                if pd.notna(recommendation_time):
                    # PENDING CA dengan Recommendation: SLA = action_on - Recommendation
                    sla_result = calculate_sla_working_hours(recommendation_time, current_time)
                    if sla_result:
                        sla_formatted = sla_result['formatted']
                    start_time = recommendation_time
                    transition += " (from Rec)"
                else:
                    # PENDING CA tanpa Recommendation: pakai previous action
                    sla_result = calculate_sla_working_hours(prev_time, current_time)
                    if sla_result:
                        sla_formatted = sla_result['formatted']
            
            # LOGIKA KHUSUS UNTUK PENDING CA COMPLETED
            elif current_status.upper() == 'PENDING CA COMPLETED':
                # Cari PENDING CA terakhir
                pending_ca_rows = group[group['apps_status_clean'].str.upper() == 'PENDING CA']
                if len(pending_ca_rows) > 0:
                    last_pending_ca = pending_ca_rows.iloc[-1]
                    last_pending_ca_time = last_pending_ca.get('action_on_parsed')
                    sla_result = calculate_sla_working_hours(last_pending_ca_time, current_time)
                    if sla_result:
                        sla_formatted = sla_result['formatted']
                    start_time = last_pending_ca_time
                else:
                    # Fallback: pakai previous action
                    sla_result = calculate_sla_working_hours(prev_time, current_time)
                    if sla_result:
                        sla_formatted = sla_result['formatted']
            
            # LOGIKA KHUSUS UNTUK RECOMMENDATION CA
            elif current_status.upper() == 'RECOMMENDATION CA':
                # Cari PENDING CA COMPLETED terakhir
                pending_ca_comp_rows = group[group['apps_status_clean'].str.upper() == 'PENDING CA COMPLETED']
                if len(pending_ca_comp_rows) > 0:
                    last_pending_ca_comp = pending_ca_comp_rows.iloc[-1]
                    last_pending_ca_comp_time = last_pending_ca_comp.get('action_on_parsed')
                    sla_result = calculate_sla_working_hours(last_pending_ca_comp_time, current_time)
                    if sla_result:
                        sla_formatted = sla_result['formatted']
                    start_time = last_pending_ca_comp_time
                else:
                    # Fallback: pakai previous action
                    sla_result = calculate_sla_working_hours(prev_time, current_time)
                    if sla_result:
                        sla_formatted = sla_result['formatted']
            
            # STATUS LAINNYA: SLA normal (current - previous)
            else:
                sla_result = calculate_sla_working_hours(prev_time, current_time)
                if sla_result:
                    sla_formatted = sla_result['formatted']
            
            sla_list.append({
                'idx': row.name,  # original index
                'apps_id': app_id,
                'Transition': transition,
                'From_Status': prev_status,
                'To_Status': current_status,
                'SLA_Hours': sla_result['total_hours'] if sla_result else None,
                'SLA_Formatted': sla_formatted,
                'Start_Time': start_time,
                'End_Time': current_time,
                'Recommendation': recommendation_time
            })
    
    return pd.DataFrame(sla_list)

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
    """Clean and prepare data for analysis"""
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate', 'Recommendation', 'ApprovalCC1', 'ApprovalCC2']:
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
        'desc_status_apps', 'Pekerjaan', 'Jabatan',
        'JenisKendaraan', 'branch_name', 
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
            'Segmen', 'action_on', 'Initiation', 'RealisasiDate', 'Outstanding_PH',
            'Pekerjaan', 'Jabatan', 'Hasil_Scoring',
            'JenisKendaraan', 'branch_name', 'Tujuan_Kredit',
            'Recommendation', 'LastOD', 'max_OD'
        ]
        
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"Kolom tidak ditemukan: {', '.join(missing)}")
            return None
        
        df_clean = preprocess_data(df)
        
        # Calculate SLA setelah preprocessing
        sla_history = calculate_historical_sla(df_clean)
        
        # Merge SLA ke original dataframe
        for _, sla_row in sla_history.iterrows():
            idx = sla_row['idx']
            if idx < len(df_clean):
                df_clean.at[idx, 'SLA_Hours'] = sla_row['SLA_Hours']
                df_clean.at[idx, 'SLA_Formatted'] = sla_row['SLA_Formatted']
                df_clean.at[idx, 'Transition'] = sla_row['Transition']
        
        # Calculate risk score
        df_clean['Risk_Score'] = df_clean.apply(calculate_risk_score, axis=1)
        df_clean['Risk_Category'] = pd.cut(
            df_clean['Risk_Score'], 
            bins=[0, 30, 60, 100], 
            labels=['Low Risk', 'Medium Risk', 'High Risk']
        )
        
        return df_clean, sla_history
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None, None

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
    if 'SLA_Hours' in df.columns:
        avg_sla = df['SLA_Hours'].mean()
        if pd.notna(avg_sla):
            if avg_sla > 35:
                warnings.append(
                    f"Average SLA is {avg_sla:.1f} hours (target: ≤35 hours / 5 working days)"
                )
            else:
                insights.append(
                    f"Good SLA performance: {avg_sla:.1f} hours average"
                )
    
    return insights, warnings

def main():
    """Main application"""
    st.title("🎯 CA Analytics Dashboard (COMPLETE v2)")
    st.markdown("**✅ SLA Calculation FIXED - Based on Recommendation Column | 9 Complete Analysis Tabs**")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading dan processing data..."):
        result = load_data()
    
    if result[0] is None or result[0].empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    df, df_sla_history = result
    
    # Display data summary
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Records", f"{total_records:,}")
    with col2:
        st.metric("📝 Unique Applications", f"{unique_apps:,}")
    with col3:
        avg_sla = df_sla_history['SLA_Hours'].mean()
        st.metric("⏱️ Average SLA", f"{avg_sla:.1f} hours" if pd.notna(avg_sla) else "N/A")
    
    st.markdown("---")
    
    # Sidebar filters
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
    
    # Filter SLA history
    filtered_app_ids = df_filtered['apps_id'].unique()
    df_sla_history_filtered = df_sla_history[df_sla_history['apps_id'].isin(filtered_app_ids)]
    
    # Sidebar summary
    st.sidebar.markdown("---")
    st.sidebar.info(f"{len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f"{df_filtered['apps_id'].nunique():,} unique applications")
    
    # Insights
    st.header("💡 Key Insights")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    if warnings:
        st.warning("⚠️ **Alerts:**\n" + "\n".join([f"• {w}" for w in warnings]))
    
    if insights:
        st.success("✅ **Positive Findings:**\n" + "\n".join([f"• {i}" for i in insights]))
    
    st.markdown("---")
    
    # TABS - ORIGINAL + SLA FIXED
    (
        tab1, tab2, tab3, tab4, tab5, 
        tab6, tab7, tab8, tab9
    ) = st.tabs([
        "Outstanding PH Analysis",
        "OD Impact Analysis",
        "Status & Scoring Matrix",
        "CA Performance",
        "Predictive Patterns",
        "Trends & Forecasting",
        "SLA Transitions (FIXED)",
        "Duplicate Applications",
        "Raw Data"
    ])
    
    # ====================== TAB 1: OUTSTANDING PH ANALYSIS ======================
    with tab1:
        st.header("Outstanding PH Analysis - 4 Dimensions")
        st.info("Comprehensive analysis of Outstanding PH with 4 analytical dimensions")
        
        # Dimension 1
        st.subheader("Dimension 1: Outstanding PH vs Scoring Result")
        st.markdown("**Purpose**: Understand scoring decision patterns across Outstanding PH ranges")
        
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            dim1_data = []
            
            osph_ranges = sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown'])
            
            for osph in osph_ranges:
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                harga_min = df_osph['OSPH_clean'].min() if 'OSPH_clean' in df_osph.columns else 0
                harga_max = df_osph['OSPH_clean'].max() if 'OSPH_clean' in df_osph.columns else 0
                
                row = {
                    'Range': osph,
                    'Min Value': f"Rp {harga_min:,.0f}",
                    'Max Value': f"Rp {harga_max:,.0f}",
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                scoring_values = [
                    '(Pilih Semua)', '-', 'APPROVE', 'APPROVE 1', 'APPROVE 2',
                    'REGULER', 'REGULER 1', 'REGULER 2',
                    'REJECT', 'REJECT 1', 'REJECT 2', 'SCORING IN PROGRESS'
                ]
                
                for scoring in scoring_values:
                    count = len(df_osph[df_osph['Scoring_Detail'] == scoring])
                    if count > 0:
                        row[scoring] = count
                
                dim1_data.append(row)
            
            dim1_df = pd.DataFrame(dim1_data)
            st.dataframe(dim1_df, use_container_width=True, hide_index=True)
            
            # Heatmap
            scoring_cols = [c for c in dim1_df.columns if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', 'Total Records']]
            
            if scoring_cols:
                heatmap_data = dim1_df[['Range'] + scoring_cols].set_index('Range')
                fig = px.imshow(
                    heatmap_data.T,
                    text_auto=True,
                    title="Outstanding PH vs Scoring Result Distribution",
                    labels=dict(x="Outstanding PH Range", y="Scoring Result", color="Count"),
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Dimension 2
        st.markdown("---")
        st.subheader("Dimension 2: Outstanding PH vs Application Status")
        st.markdown("**Purpose**: Distribution of application status across Outstanding PH ranges")
        
        if 'OSPH_Category' in df_filtered.columns and 'apps_status_clean' in df_filtered.columns:
            status_data = []
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                row = {
                    'Range': osph, 
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                for status in sorted(df_filtered['apps_status_clean'].unique()):
                    if status != 'Unknown':
                        count = len(df_osph[df_osph['apps_status_clean'] == status])
                        if count > 0:
                            row[status] = count
                
                status_data.append(row)
            
            status_df = pd.DataFrame(status_data)
            st.dataframe(status_df, use_container_width=True, hide_index=True)
            
            status_cols = [c for c in status_df.columns if c not in ['Range', 'Total Apps', 'Total Records']]
            
            if status_cols:
                heatmap_status = status_df[['Range'] + status_cols].set_index('Range')
                fig = px.imshow(
                    heatmap_status.T,
                    text_auto=True,
                    title="Outstanding PH vs Application Status",
                    labels=dict(x="Outstanding PH Range", y="Application Status", color="Count"),
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Dimension 3
        st.markdown("---")
        st.subheader("Dimension 3: Outstanding PH vs Job Type (Pekerjaan)")
        st.markdown("**Purpose**: Occupation profile across Outstanding PH ranges")
        
        if 'OSPH_Category' in df_filtered.columns and 'Pekerjaan_clean' in df_filtered.columns:
            dim3_data = []
            all_pekerjaan = sorted([x for x in df_filtered['Pekerjaan_clean'].unique() if x != 'Unknown'])
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                harga_min = df_osph['OSPH_clean'].min() if 'OSPH_clean' in df_osph.columns else 0
                harga_max = df_osph['OSPH_clean'].max() if 'OSPH_clean' in df_osph.columns else 0
                
                row = {
                    'Range': osph,
                    'Min Value': f"Rp {harga_min:,.0f}",
                    'Max Value': f"Rp {harga_max:,.0f}",
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                for pekerjaan in all_pekerjaan:
                    count = len(df_osph[df_osph['Pekerjaan_clean'] == pekerjaan])
                    if count > 0:
                        row[pekerjaan] = count
                
                dim3_data.append(row)
            
            dim3_df = pd.DataFrame(dim3_data)
            st.dataframe(dim3_df, use_container_width=True, hide_index=True)
            
            pekerjaan_cols = [c for c in dim3_df.columns if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', 'Total Records']]
            
            if pekerjaan_cols:
                fig = px.bar(
                    dim3_df,
                    x='Range',
                    y=pekerjaan_cols,
                    title="Job Type Distribution by Outstanding PH Range",
                    barmode='stack'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Dimension 4
        st.markdown("---")
        st.subheader("Dimension 4: Outstanding PH vs Vehicle Type (Mb. Beban / Mb. Penumpang)")
        st.markdown("**Purpose**: Vehicle preference and risk profile by Outstanding PH range")
        
        if 'OSPH_Category' in df_filtered.columns and 'JenisKendaraan_clean' in df_filtered.columns:
            dim4_data = []
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                harga_min = df_osph['OSPH_clean'].min() if 'OSPH_clean' in df_osph.columns else 0
                harga_max = df_osph['OSPH_clean'].max() if 'OSPH_clean' in df_osph.columns else 0
                
                row = {
                    'Range': osph,
                    'Min Value': f"Rp {harga_min:,.0f}",
                    'Max Value': f"Rp {harga_max:,.0f}",
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                for vehicle_type in sorted(df_filtered['JenisKendaraan_clean'].unique()):
                    if vehicle_type != 'Unknown':
                        count = len(df_osph[df_osph['JenisKendaraan_clean'] == vehicle_type])
                        if count > 0:
                            row[vehicle_type] = count
                
                dim4_data.append(row)
            
            dim4_df = pd.DataFrame(dim4_data)
            st.dataframe(dim4_df, use_container_width=True, hide_index=True)
            
            vehicle_cols = [c for c in dim4_df.columns if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', 'Total Records']]
            
            if vehicle_cols:
                fig = px.bar(
                    dim4_df,
                    x='Range',
                    y=vehicle_cols,
                    title="Vehicle Type Distribution by Outstanding PH Range",
                    barmode='group'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # ====================== TAB 2: OD IMPACT ANALYSIS ======================
    with tab2:
        st.header("OD Impact Analysis - LastOD & max_OD")
        st.info("Analysis of how Overdue Days (OD) impact scoring decisions and risk profiles")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("LastOD Analysis")
            st.markdown("**Purpose**: Understand LastOD impact on approval rates")
            
            if 'LastOD_clean' in df_filtered.columns:
                df_filtered['LastOD_Category'] = pd.cut(
                    df_filtered['LastOD_clean'],
                    bins=[-np.inf, 0, 10, 30, np.inf],
                    labels=['0 (No OD)', '1-10 days', '11-30 days', '>30 days']
                )
                
                lastod_analysis = []
                
                for cat in ['0 (No OD)', '1-10 days', '11-30 days', '>30 days']:
                    df_od = df_filtered[df_filtered['LastOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        reject = df_od['Scoring_Detail'].isin(['REJECT', 'REJECT 1', 'REJECT 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "-"
                        avg_risk = f"{df_od['Risk_Score'].mean():.1f}" if df_od['Risk_Score'].notna().any() else "-"
                        
                        lastod_analysis.append({
                            'LastOD Range': cat,
                            'Total Apps': df_od['apps_id'].nunique(),
                            'Total Records': len(df_od),
                            'Approve': approve,
                            'Reject': reject,
                            'Approval %': approval_pct,
                            'Avg Risk': avg_risk
                        })
                
                lastod_df = pd.DataFrame(lastod_analysis)
                st.dataframe(lastod_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("max_OD Analysis")
            st.markdown("**Purpose**: Understand max_OD impact on approval rates")
            
            if 'max_OD_clean' in df_filtered.columns:
                df_filtered['maxOD_Category'] = pd.cut(
                    df_filtered['max_OD_clean'],
                    bins=[-np.inf, 0, 15, 45, np.inf],
                    labels=['0', '1-15 days', '16-45 days', '>45 days']
                )
                
                maxod_analysis = []
                
                for cat in ['0', '1-15 days', '16-45 days', '>45 days']:
                    df_od = df_filtered[df_filtered['maxOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        reject = df_od['Scoring_Detail'].isin(['REJECT', 'REJECT 1', 'REJECT 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "-"
                        avg_risk = f"{df_od['Risk_Score'].mean():.1f}" if df_od['Risk_Score'].notna().any() else "-"
                        
                        maxod_analysis.append({
                            'max_OD Range': cat,
                            'Total Apps': df_od['apps_id'].nunique(),
                            'Total Records': len(df_od),
                            'Approve': approve,
                            'Reject': reject,
                            'Approval %': approval_pct,
                            'Avg Risk': avg_risk
                        })
                
                maxod_df = pd.DataFrame(maxod_analysis)
                st.dataframe(maxod_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("OD Trend Analysis: LastOD vs max_OD")
        st.markdown("**Purpose**: Identify if customer OD is improving or worsening")
        
        if 'LastOD_clean' in df_filtered.columns and 'max_OD_clean' in df_filtered.columns:
            df_filtered['OD_Trend'] = df_filtered['LastOD_clean'] - df_filtered['max_OD_clean']
            
            df_filtered['OD_Trend_Category'] = pd.cut(
                df_filtered['OD_Trend'],
                bins=[-np.inf, -10, -1, 0, 10, np.inf],
                labels=['Significant Improvement', 'Slight Improvement', 'Stable', 'Slight Worsening', 'Significant Worsening']
            )
            
            trend_analysis = df_filtered.groupby('OD_Trend_Category').agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (x.isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum() / len(x[x != '(Pilih Semua)']) * 100) if len(x[x != '(Pilih Semua)']) > 0 else 0,
                'Risk_Score': 'mean'
            }).reset_index()
            
            trend_analysis.columns = ['OD Trend', 'Total Apps', 'Approval %', 'Avg Risk']
            trend_analysis['Total Records'] = df_filtered.groupby('OD_Trend_Category').size().values
            
            st.dataframe(trend_analysis, use_container_width=True, hide_index=True)
            
            fig = px.bar(
                trend_analysis,
                x='OD Trend',
                y='Approval %',
                color='Avg Risk',
                title="OD Trend Impact on Approval Rate"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # ====================== TAB 3: STATUS & SCORING MATRIX ======================
    with tab3:
        st.header("Status & Scoring Matrix")
        st.info("Complete cross-tabulation of application status and scoring results")
        
        st.subheader("Cross-Tabulation Matrix")
        st.markdown("**Purpose**: See relationship between status and scoring outcome")
        
        if 'apps_status_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            cross_tab = pd.crosstab(
                df_filtered['apps_status_clean'],
                df_filtered['Scoring_Detail'],
                margins=True,
                margins_name='TOTAL'
            )
            st.dataframe(cross_tab, use_container_width=True)
            
            cross_tab_no_total = cross_tab.drop('TOTAL', errors='ignore').drop('TOTAL', axis=1, errors='ignore')
            
            if len(cross_tab_no_total) > 0:
                fig = px.imshow(
                    cross_tab_no_total,
                    text_auto=True,
                    title="Application Status vs Scoring Result Heatmap",
                    labels=dict(x="Scoring Result", y="Application Status", color="Count"),
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Application Status Summary")
            st.markdown("**Metrics per Status**: Total Apps, Total Records, and Risk")
            
            if 'apps_status_clean' in df_filtered.columns:
                status_detail = df_filtered.groupby('apps_status_clean').agg({'apps_id': 'nunique'}).reset_index()
                status_detail.insert(2, 'Total Records', df_filtered.groupby('apps_status_clean').size().values)
                status_detail.insert(3, 'Avg Risk', df_filtered.groupby('apps_status_clean')['Risk_Score'].mean().values)
                status_detail.columns = ['Status', 'Total Apps', 'Total Records', 'Avg Risk']
                status_detail = status_detail.sort_values('Total Apps', ascending=False)
                st.dataframe(status_detail, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Scoring Result Summary")
            st.markdown("**Distribution of Scoring Outcomes with Apps & Records**")
            
            if 'Scoring_Detail' in df_filtered.columns:
                scoring_detail = []
                for scoring in sorted(df_filtered['Scoring_Detail'].unique()):
                    if scoring != '(Pilih Semua)':
                        df_scoring = df_filtered[df_filtered['Scoring_Detail'] == scoring]
                        scoring_detail.append({
                            'Scoring Result': scoring,
                            'Total Apps': df_scoring['apps_id'].nunique(),
                            'Total Records': len(df_scoring),
                            'Percentage': f"{len(df_scoring)/len(df_filtered)*100:.1f}%"
                        })
                
                scoring_df = pd.DataFrame(scoring_detail)
                st.dataframe(scoring_df, use_container_width=True, hide_index=True)
    
    # ====================== TAB 4: CA PERFORMANCE ======================
    with tab4:
        st.header("CA Performance Analytics")
        st.info("Individual CA performance metrics and comparison")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = []
            
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                approve = df_ca['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                reject = df_ca['Scoring_Detail'].isin(['REJECT', 'REJECT 1', 'REJECT 2']).sum()
                total_scored = len(df_ca[df_ca['Scoring_Detail'] != '(Pilih Semua)'])
                other = total_scored - approve - reject
                
                avg_risk = f"{df_ca['Risk_Score'].mean():.0f}" if df_ca['Risk_Score'].notna().any() else "-"
                approval_pct = f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "-"
                
                ca_perf.append({
                    'CA Name': ca,
                    'Total Apps': df_ca['apps_id'].nunique(),
                    'Total Records': len(df_ca),
                    'Approve': approve,
                    'Reject': reject,
                    'Other': other,
                    'Approval %': approval_pct,
                    'Avg Risk Score': avg_risk
                })
            
            ca_df = pd.DataFrame(ca_perf).sort_values('Total Apps', ascending=False)
            
            st.subheader("CA Performance Table")
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Top 10 CA by Volume")
                fig = px.bar(
                    ca_df.head(10),
                    x='CA Name',
                    y='Total Apps',
                    title="CA Volume Distribution"
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Volume vs Approval Rate")
                ca_df_plot = ca_df.copy()
                ca_df_plot['Approval_num'] = ca_df_plot['Approval %'].str.replace('%', '').replace('-', '0').astype(float)
                
                fig = px.scatter(
                    ca_df_plot,
                    x='Total Apps',
                    y='Approval_num',
                    size='Total Apps',
                    hover_data=['CA Name'],
                    title="CA Performance Scatter",
                    labels={'Approval_num': 'Approval %'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # ====================== TAB 5: PREDICTIVE PATTERNS ======================
    with tab5:
        st.header("Predictive Pattern Recognition")
        st.info("Identification of patterns that predict approval or rejection outcomes")
        
        st.subheader("High-Impact Combinations: Outstanding PH + OD Segment + Job Type")
        st.markdown("**Purpose**: Find best and worst segment combinations")
        
        if all(c in df_filtered.columns for c in ['OSPH_Category', 'LastOD_clean', 'Pekerjaan_clean', 'Scoring_Detail']):
            df_filtered['LastOD_Segment'] = pd.cut(
                df_filtered['LastOD_clean'],
                bins=[-np.inf, 0, 30, np.inf],
                labels=['No OD', 'OD 1-30', 'OD >30']
            )
            
            pattern_analysis = df_filtered.groupby(['OSPH_Category', 'LastOD_Segment', 'Pekerjaan_clean']).agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (x.isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum() / len(x[x != '(Pilih Semua)']) * 100) if len(x[x != '(Pilih Semua)']) > 0 else 0
            }).reset_index()
            
            pattern_analysis['Total Records'] = df_filtered.groupby(['OSPH_Category', 'LastOD_Segment', 'Pekerjaan_clean']).size().values
            
            pattern_analysis.columns = ['Outstanding PH', 'OD Segment', 'Job Type', 'Total Apps', 'Approval %', 'Total Records']
            
            pattern_analysis = pattern_analysis.sort_values('Total Apps', ascending=False).head(15)
            
            st.dataframe(pattern_analysis, use_container_width=True, hide_index=True)
            
            if len(pattern_analysis) > 0:
                best = pattern_analysis.iloc[0]
                worst = pattern_analysis.iloc[-1]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(
                        f'<div class="success-card">'
                        f'<h4>Highest Volume Combination</h4>'
                        f'<strong>Outstanding PH:</strong> {best["Outstanding PH"]}<br>'
                        f'<strong>OD Segment:</strong> {best["OD Segment"]}<br>'
                        f'<strong>Job Type:</strong> {best["Job Type"]}<br>'
                        f'<strong>Total Apps:</strong> {best["Total Apps"]}<br>'
                        f'<strong>Total Records:</strong> {best["Total Records"]}<br>'
                        f'<strong>Approval Rate:</strong> {best["Approval %"]:.1f}%'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown(
                        f'<div class="warning-card">'
                        f'<h4>Lowest Volume Combination</h4>'
                        f'<strong>Outstanding PH:</strong> {worst["Outstanding PH"]}<br>'
                        f'<strong>OD Segment:</strong> {worst["OD Segment"]}<br>'
                        f'<strong>Job Type:</strong> {worst["Job Type"]}<br>'
                        f'<strong>Total Apps:</strong> {worst["Total Apps"]}<br>'
                        f'<strong>Total Records:</strong> {worst["Total Records"]}<br>'
                        f'<strong>Approval Rate:</strong> {worst["Approval %"]:.1f}%'
                        f'</div>',
                        unsafe_allow_html=True
                    )
    
    # ====================== TAB 6: TRENDS & FORECASTING ======================
    with tab6:
        st.header("Trends & Time-Series Analysis")
        st.info("Monthly trends in volume, SLA, and approval rates")
        
        if 'YearMonth' in df_filtered.columns:
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (x.isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum() / len(x[x != '(Pilih Semua)']) * 100) if len(x[x != '(Pilih Semua)']) > 0 else 0
            }).reset_index()
            
            monthly['Total Records'] = df_filtered.groupby('YearMonth').size().values
            monthly.columns = ['Month', 'Volume', 'Approval %', 'Total Records']
            
            st.subheader("Monthly Performance Metrics")
            st.dataframe(monthly, use_container_width=True, hide_index=True)
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Bar(x=monthly['Month'], y=monthly['Volume'], name="Application Volume"),
                secondary_y=False
            )
            
            fig.add_trace(
                go.Scatter(x=monthly['Month'], y=monthly['Approval %'], name="Approval Rate %", mode='lines+markers'),
                secondary_y=True
            )
            
            fig.update_layout(
                title="Monthly Trend: Volume & Approval Rate",
                height=500,
                hovermode='x unified'
            )
            
            fig.update_yaxes(title_text="Volume", secondary_y=False)
            fig.update_yaxes(title_text="Approval %", secondary_y=True)
            
            st.plotly_chart(fig, use_container_width=True)
    
    # ====================== TAB 7: SLA TRANSITIONS (FIXED) ======================
    with tab7:
        st.header("SLA Transitions Analysis (FIXED ✅)")
        st.info("✅ SLA dalam JAM | Jam kerja 08:30-15:30 (7 jam/hari) | Based on Recommendation Column")
        
        # SLA Overview
        st.subheader("SLA Performance Overview")
        
        col1, col2, col3 = st.columns(3)
        
        sla_valid = df_sla_history_filtered[df_sla_history_filtered['SLA_Hours'].notna()]
        
        with col1:
            if len(sla_valid) > 0:
                st.metric("Average SLA", f"{sla_valid['SLA_Hours'].mean():.1f} hours")
        
        with col2:
            if len(sla_valid) > 0:
                st.metric("Median SLA", f"{sla_valid['SLA_Hours'].median():.1f} hours")
        
        with col3:
            if len(sla_valid) > 0:
                st.metric("90th Percentile", f"{sla_valid['SLA_Hours'].quantile(0.9):.1f} hours")
        
        st.markdown("---")
        
        # Monthly SLA Trend
        st.subheader("📈 Average SLA per Month (Line Chart)")
        
        if len(sla_valid) > 0 and 'End_Time' in sla_valid.columns:
            sla_valid_copy = sla_valid.copy()
            sla_valid_copy['YearMonth'] = pd.to_datetime(sla_valid_copy['End_Time']).dt.to_period('M').astype(str)
            
            monthly_sla = sla_valid_copy.groupby('YearMonth').agg({
                'SLA_Hours': ['mean', 'median', 'count']
            }).reset_index()
            
            monthly_sla.columns = ['Month', 'Avg_SLA', 'Median_SLA', 'Count']
            monthly_sla = monthly_sla.sort_values('Month')
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=monthly_sla['Month'],
                y=monthly_sla['Avg_SLA'],
                mode='lines+markers',
                name='Average SLA',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8)
            ))
            
            fig.add_trace(go.Scatter(
                x=monthly_sla['Month'],
                y=monthly_sla['Median_SLA'],
                mode='lines+markers',
                name='Median SLA',
                line=dict(color='#ff7f0e', width=2, dash='dash'),
                marker=dict(size=6)
            ))
            
            fig.add_hline(
                y=35,
                line_dash="dot",
                line_color="red",
                annotation_text="Target: 35 hours (5 days)"
            )
            
            fig.update_layout(
                title="Monthly SLA Trend",
                xaxis_title="Month",
                yaxis_title="SLA (hours)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(monthly_sla, use_container_width=True, hide_index=True)
        else:
            st.warning("No SLA data with valid timestamps")
        
        st.markdown("---")
        
        # Pivot Table
        st.subheader("Pivot: App ID → Historical Status & SLA")
        
        pivot_data = []
        sample_apps = sorted(df_sla_history_filtered['apps_id'].unique())[:50]
        
        for app_id in sample_apps:
            app_sla = df_sla_history_filtered[df_sla_history_filtered['apps_id'] == app_id]
            row_data = {'App ID': app_id}
            
            for idx, trans in app_sla.iterrows():
                trans_label = trans['Transition']
                sla_formatted = trans['SLA_Formatted']
                
                if pd.notna(sla_formatted):
                    row_data[trans_label] = sla_formatted
                else:
                    row_data[trans_label] = '—'
            
            pivot_data.append(row_data)
        
        if pivot_data:
            pivot_df = pd.DataFrame(pivot_data)
            st.dataframe(pivot_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Statistics per Transition
        st.subheader("SLA Statistics per Transition")
        
        stats_data = []
        for transition in sorted(df_sla_history_filtered['Transition'].unique()):
            trans_data = df_sla_history_filtered[df_sla_history_filtered['Transition'] == transition]
            valid_sla = trans_data[trans_data['SLA_Hours'].notna()]
            
            if len(valid_sla) > 0:
                stats_data.append({
                    'Transition': transition,
                    'Total Records': len(trans_data),
                    'With SLA': len(valid_sla),
                    'Avg SLA (hours)': f"{valid_sla['SLA_Hours'].mean():.1f}",
                    'Min': valid_sla['SLA_Formatted'].iloc[valid_sla['SLA_Hours'].argmin()],
                    'Max': valid_sla['SLA_Formatted'].iloc[valid_sla['SLA_Hours'].argmax()],
                })
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        # SLA Examples
        st.markdown("---")
        st.subheader("SLA Calculation Examples")
        st.info("Lihat contoh perhitungan SLA untuk apps tertentu")
        
        sample_apps_detail = sorted(df_sla_history_filtered['apps_id'].unique())[:100]
        
        if len(sample_apps_detail) > 0:
            selected_app = st.selectbox("Pilih App ID untuk melihat detail SLA:", sample_apps_detail)
            
            if selected_app:
                app_sla = df_sla_history_filtered[df_sla_history_filtered['apps_id'] == selected_app]
                
                st.subheader(f"SLA History untuk App ID: {selected_app}")
                
                display_cols = [
                    'Transition', 'From_Status', 'To_Status',
                    'Start_Time', 'End_Time', 'Recommendation',
                    'SLA_Formatted', 'SLA_Hours'
                ]
                
                st.dataframe(app_sla[display_cols], use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("Raw Data untuk App ini")
                
                app_raw = df[df['apps_id'] == selected_app].sort_values('action_on_parsed')
                
                raw_cols = ['apps_status', 'action_on_parsed', 'Recommendation_parsed', 'user_name', 'Scoring_Detail']
                available_raw = [c for c in raw_cols if c in app_raw.columns]
                
                st.dataframe(app_raw[available_raw], use_container_width=True, hide_index=True)
    
    # ====================== TAB 8: DUPLICATE APPLICATIONS ======================
    with tab8:
        st.header("Duplicate Applications Analysis")
        st.info("Identify applications with multiple submissions")
        
        if 'apps_id' in df_filtered.columns:
            app_counts = df_filtered['apps_id'].value_counts()
            duplicates = app_counts[app_counts > 1]
            
            st.metric("Total Duplicate Apps", len(duplicates))
            st.metric("Total Duplicate Records", duplicates.sum())
            
            if len(duplicates) > 0:
                st.subheader("Top 20 Most Duplicated Applications")
                
                dup_analysis = []
                for app_id in duplicates.head(20).index:
                    df_app = df_filtered[df_filtered['apps_id'] == app_id]
                    
                    dup_analysis.append({
                        'App ID': app_id,
                        'Count': len(df_app),
                        'Statuses': ', '.join(df_app['apps_status_clean'].unique()[:3]),
                        'First Action': df_app['action_on_parsed'].min().strftime('%Y-%m-%d') if df_app['action_on_parsed'].notna().any() else 'N/A',
                        'Last Action': df_app['action_on_parsed'].max().strftime('%Y-%m-%d') if df_app['action_on_parsed'].notna().any() else 'N/A'
                    })
                
                dup_df = pd.DataFrame(dup_analysis)
                st.dataframe(dup_df, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("Detailed View")
                
                selected_app = st.selectbox("Select App ID to see details", duplicates.head(20).index)
                
                if selected_app:
                    df_detail = df_filtered[df_filtered['apps_id'] == selected_app]
                    
                    detail_cols = ['action_on_parsed', 'apps_status_clean', 'Scoring_Detail', 'user_name_clean', 'Transition', 'SLA_Formatted']
                    available_detail_cols = [c for c in detail_cols if c in df_detail.columns]
                    
                    st.dataframe(
                        df_detail[available_detail_cols].sort_values('action_on_parsed'),
                        use_container_width=True,
                        hide_index=True
                    )
    
    # ====================== TAB 9: RAW DATA ======================
    with tab9:
        st.header("Raw Data Export")
        st.info("View and download filtered data")
        
        st.subheader("Data Preview (First 100 rows)")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed',
            'Recommendation_parsed', 'Transition', 'SLA_Formatted', 'SLA_Hours',
            'Scoring_Detail', 'OSPH_clean', 'LastOD_clean',
            'user_name_clean', 'branch_name_clean'
        ]
        
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        
        st.dataframe(
            df_filtered[available_cols].head(100),
            use_container_width=True,
            hide_index=True
        )
        
        st.info(f"Showing first 100 of {len(df_filtered):,} records")
        
        st.markdown("---")
        st.subheader("Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = df_filtered[available_cols].to_csv(index=False)
            st.download_button(
                "📥 Download Filtered Data (CSV)",
                csv_data,
                "ca_analytics_filtered.csv",
                "text/csv"
            )
        
        with col2:
            csv_sla = df_sla_history_filtered.to_csv(index=False)
            st.download_button(
                "📥 Download SLA History (CSV)",
                csv_sla,
                "sla_history.csv",
                "text/csv"
            )
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
