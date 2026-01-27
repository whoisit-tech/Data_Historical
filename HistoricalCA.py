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
        st.warning(f"Error calculating SLA: {str(e)}")
        return None

# ============================================================
# FIXED: Logika calculate_historical_sla yang BENAR
# Berdasarkan kolom Recommendation untuk PENDING CA
# ============================================================
def calculate_historical_sla(df):
    """
    Calculate SLA per transition yang SEBENARNYA terjadi
    
    LOGIKA BENAR:
    1. Sort by apps_id dan action_on_parsed
    2. Untuk PENDING CA: SLA = action_on - Recommendation
    3. Untuk PENDING CA COMPLETED: SLA = action_on - action_on PENDING CA sebelumnya
    4. Untuk RECOMMENDATION CA: SLA = action_on - action_on PENDING CA COMPLETED sebelumnya
    5. Status lain: SLA = action_on current - action_on previous
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
                        sla_days = sla_result['working_days']
                    else:
                        sla_formatted = '—'
                        sla_days = None
                    transition = f"START → {current_status}"
                    start_time = recommendation_time
                else:
                    # Row pertama tanpa Recommendation atau bukan PENDING CA
                    sla_formatted = '—'
                    sla_days = None
                    transition = f"START → {current_status}"
                    start_time = None
                
                sla_list.append({
                    'idx': row.name,  # original index
                    'apps_id': app_id,
                    'Transition': transition,
                    'From_Status': 'START',
                    'To_Status': current_status,
                    'SLA_Days': sla_days,
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
                'SLA_Days': sla_result['working_days'] if sla_result else None,
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
                df_clean.at[idx, 'SLA_Days'] = sla_row['SLA_Days']
                df_clean.at[idx, 'SLA_Formatted'] = sla_row['SLA_Formatted']
                df_clean.at[idx, 'Transition'] = sla_row['Transition']
        
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
        avg_sla = df['SLA_Days'].mean()
        if pd.notna(avg_sla):
            if avg_sla > 5:
                warnings.append(
                    f"Average SLA is {avg_sla:.1f} working days (target: ≤5 days)"
                )
            else:
                insights.append(
                    f"Good SLA performance: {avg_sla:.1f} working days average"
                )
    
    return insights, warnings

def main():
    """Main application"""
    st.title("🎯 CA Analytics Dashboard (SLA FIXED v2)")
    st.markdown("**✅ SLA Calculation FIXED - Based on Recommendation Column**")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading dan processing data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    # Calculate historical SLA
    df_sla_history = calculate_historical_sla(df)
    
    # Display data summary
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Records", f"{total_records:,}")
    with col2:
        st.metric("📝 Unique Applications", f"{unique_apps:,}")
    with col3:
        avg_sla = df_sla_history['SLA_Days'].mean()
        st.metric("⏱️ Average SLA", f"{avg_sla:.2f} days" if pd.notna(avg_sla) else "N/A")
    
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
    
    
    # Filter SLA history based on apps that passed filters
    filtered_app_ids = df_filtered['apps_id'].unique()
    df_sla_history_filtered = df_sla_history[
        df_sla_history['apps_id'].isin(filtered_app_ids)
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
    st.header("💡 Key Insights")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    if warnings:
        st.warning("⚠️ **Alerts:**\n" + "\n".join([f"• {w}" for w in warnings]))
    
    if insights:
        st.success("✅ **Positive Findings:**\n" + "\n".join([f"• {i}" for i in insights]))
    
    st.markdown("---")
    
    # Tabs
    (
        tab1, tab2, tab3
    ) = st.tabs([
        "SLA Transitions (NEW)",
        "SLA Examples",
        "Raw Data"
    ])
    
    # Tab 1: SLA Transitions
    with tab1:
        st.header("SLA Transitions Analysis")
        st.info("✅ FIXED: SLA berdasarkan kolom Recommendation untuk PENDING CA")
        
        # SLA Overview
        st.subheader("SLA Performance Overview")
        
        col1, col2, col3 = st.columns(3)
        
        sla_valid = df_sla_history_filtered[df_sla_history_filtered['SLA_Days'].notna()]
        
        with col1:
            if len(sla_valid) > 0:
                st.metric("Average SLA", f"{sla_valid['SLA_Days'].mean():.2f} days")
        
        with col2:
            if len(sla_valid) > 0:
                st.metric("Median SLA", f"{sla_valid['SLA_Days'].median():.2f} days")
        
        with col3:
            if len(sla_valid) > 0:
                st.metric("90th Percentile", f"{sla_valid['SLA_Days'].quantile(0.9):.2f} days")
        
        st.markdown("---")
        
        # Statistics per Transition
        st.subheader("SLA Statistics per Transition")
        
        stats_data = []
        for transition in sorted(df_sla_history_filtered['Transition'].unique()):
            trans_data = df_sla_history_filtered[df_sla_history_filtered['Transition'] == transition]
            valid_sla = trans_data[trans_data['SLA_Days'].notna()]
            
            if len(valid_sla) > 0:
                stats_data.append({
                    'Transition': transition,
                    'Total Records': len(trans_data),
                    'With SLA': len(valid_sla),
                    'Avg SLA (days)': f"{valid_sla['SLA_Days'].mean():.2f}",
                    'Min': valid_sla['SLA_Formatted'].iloc[valid_sla['SLA_Days'].argmin()],
                    'Max': valid_sla['SLA_Formatted'].iloc[valid_sla['SLA_Days'].argmax()],
                })
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        # Distribution chart
        if len(sla_valid) > 0:
            st.markdown("---")
            st.subheader("SLA Distribution")
            
            fig = px.histogram(
                sla_valid,
                x='SLA_Days',
                nbins=50,
                title="SLA Distribution (Working Days)",
                labels={'SLA_Days': 'Working Days'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: SLA Examples
    with tab2:
        st.header("SLA Calculation Examples")
        st.info("Lihat contoh perhitungan SLA untuk apps tertentu")
        
        # Select app to view
        sample_apps = sorted(df_sla_history_filtered['apps_id'].unique())[:100]
        
        if len(sample_apps) > 0:
            selected_app = st.selectbox(
                "Pilih App ID untuk melihat detail SLA:",
                sample_apps
            )
            
            if selected_app:
                app_sla = df_sla_history_filtered[df_sla_history_filtered['apps_id'] == selected_app]
                
                st.subheader(f"SLA History untuk App ID: {selected_app}")
                
                display_cols = [
                    'Transition', 'From_Status', 'To_Status',
                    'Start_Time', 'End_Time', 'Recommendation',
                    'SLA_Formatted', 'SLA_Days'
                ]
                
                st.dataframe(
                    app_sla[display_cols],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Show raw data for this app
                st.markdown("---")
                st.subheader("Raw Data untuk App ini")
                
                app_raw = df[df['apps_id'] == selected_app].sort_values('action_on_parsed')
                
                raw_cols = [
                    'apps_status', 'action_on_parsed', 'Recommendation_parsed',
                    'user_name', 'Scoring_Detail'
                ]
                
                available_raw = [c for c in raw_cols if c in app_raw.columns]
                
                st.dataframe(
                    app_raw[available_raw],
                    use_container_width=True,
                    hide_index=True
                )
    
    # Tab 3: Raw Data
    with tab3:
        st.header("Raw Data Export")
        st.info("View and download filtered data")
        
        st.subheader("Data Preview (First 100 rows)")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed',
            'Recommendation_parsed', 'Transition', 'SLA_Formatted', 'SLA_Days',
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
        
        # Download options
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
