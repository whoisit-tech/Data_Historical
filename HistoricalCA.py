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
        WORK_END = timedelta(hours=15, minutes=30)
        WORK_HOURS_PER_DAY = 7 * 3600
        
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
                elif start_dt.time() > day_end.time():
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
        
        days = int(total_seconds // 86400)
        remaining = int(total_seconds % 86400)
        hours = remaining // 3600
        remaining = remaining % 3600
        minutes = remaining // 60
        seconds = remaining % 60
        
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
    except:
        return None

def calculate_row_sla(df):
    """
    Calculate SLA per row per apps_id dengan logika:
    
    1. PENDING CA: 
       action - Recommendation (baris yang sama)
    
    2. PENDING CA COMPLETED:
       - Jika ada row sebelumnya: action baris ini - action baris sebelumnya
       - Jika TIDAK ada row sebelumnya (first row): action - Recommendation (baris yang sama)
    
    3. NOT RECOMMENDED / RECOMMENDED CA / RECOMMENDED CA WITH COND:
       - Jika ada row sebelumnya: action baris ini - action baris sebelumnya
       - Jika TIDAK ada row sebelumnya (first row): action - Recommendation (baris yang sama)
    """
    df_sorted = df.sort_values(['apps_id', 'action_on_parsed'], na_position='last').copy()
    df_sorted = df_sorted.reset_index(drop=True)
    
    # Initialize SLA columns
    df_sorted['SLA_Start'] = None
    df_sorted['SLA_End'] = None
    df_sorted['SLA_Days'] = None
    df_sorted['SLA_Formatted'] = '—'
    df_sorted['SLA_Logic'] = 'N/A'
    
    # Check if Recommendation_parsed exists
    has_recommendation = 'Recommendation_parsed' in df_sorted.columns
    
    # Process each apps_id group
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
            
            # Check if there's a previous row
            has_previous = group_position > 0
            
            # ========== LOGIKA 1: PENDING CA ==========
            if 'PENDING CA' in current_status and 'COMPLETED' not in current_status:
                # SELALU gunakan Recommendation untuk PENDING CA
                if has_recommendation and pd.notna(current_recommendation):
                    sla_start = current_recommendation
                    logic = 'PENDING CA: action - Recommendation (same row)'
                else:
                    logic = 'PENDING CA: No Recommendation available'
            
            # ========== LOGIKA 2: PENDING CA COMPLETED ==========
            elif 'COMPLETED' in current_status and 'PENDING' in current_status:
                if has_previous:
                    # Ada row sebelumnya
                    prev_idx = app_indices[group_position - 1]
                    prev_action = df_sorted.at[prev_idx, 'action_on_parsed']
                    sla_start = prev_action
                    logic = 'PENDING CA COMPLETED: action this - action previous'
                else:
                    # First row - gunakan Recommendation
                    if has_recommendation and pd.notna(current_recommendation):
                        sla_start = current_recommendation
                        logic = 'PENDING CA COMPLETED: action - Recommendation (first row)'
                    else:
                        logic = 'PENDING CA COMPLETED: First row, no Recommendation'
            
            # ========== LOGIKA 3: NOT RECOMMENDED / RECOMMENDED CA / RECOMMENDED CA WITH COND ==========
            elif any(keyword in current_status for keyword in ['NOT RECOMMENDED', 'RECOMMENDED']):
                if has_previous:
                    # Ada row sebelumnya
                    prev_idx = app_indices[group_position - 1]
                    prev_action = df_sorted.at[prev_idx, 'action_on_parsed']
                    sla_start = prev_action
                    logic = f'{current_status}: action this - action previous'
                else:
                    # First row - gunakan Recommendation
                    if has_recommendation and pd.notna(current_recommendation):
                        sla_start = current_recommendation
                        logic = f'{current_status}: action - Recommendation (first row)'
                    else:
                        logic = f'{current_status}: First row, no Recommendation'
            
            # Hitung SLA
            if sla_start and sla_end and pd.notna(sla_start) and pd.notna(sla_end):
                sla_result = calculate_sla_working_hours(sla_start, sla_end)
                if sla_result:
                    df_sorted.at[current_idx, 'SLA_Start'] = sla_start
                    df_sorted.at[current_idx, 'SLA_End'] = sla_end
                    df_sorted.at[current_idx, 'SLA_Days'] = sla_result['working_days']
                    df_sorted.at[current_idx, 'SLA_Formatted'] = sla_result['formatted']
                    df_sorted.at[current_idx, 'SLA_Logic'] = logic
                else:
                    df_sorted.at[current_idx, 'SLA_Logic'] = logic + ' (calc failed)'
            else:
                df_sorted.at[current_idx, 'SLA_Logic'] = logic
    
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
    """Clean and prepare data for analysis"""
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
        
        if 'Recommendation' not in df.columns:
            st.warning(" Kolom 'Recommendation' tidak ditemukan.")
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
    """
    Create OSPH PIVOT tables per Segmen:
    - Pivot 1: OSPH_Category (rows) x Pekerjaan (columns) per Segmen
    - Pivot 2: OSPH_Category (rows) x JenisKendaraan (columns) per Segmen
    - Pivot 3: OSPH_Category (rows) x Hasil_Scoring (columns) per Segmen
    
    OSPH Range sebagai ROW, dimensi lain sebagai COLUMN
    """
    pivots = {}
    
    df_valid = df[
        (df['OSPH_clean'].notna()) & 
        (df['OSPH_Category'] != 'Unknown') &
        (df['Segmen_clean'] != 'Unknown')
    ].copy()
    
    if len(df_valid) == 0:
        return pivots
    
    # PIVOT 1: OSPH_Category (rows) x Pekerjaan (columns) per Segmen
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
    
    # PIVOT 2: OSPH_Category (rows) x JenisKendaraan (columns) per Segmen
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
    
    # PIVOT 3: OSPH_Category (rows) x Hasil_Scoring (columns) per Segmen
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
    """Generate insights and warnings from data"""
    insights = []
    warnings = []
    
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
                    # Always show approval rate without "Low" or "Strong" label
                    insights.append(f"Approval rate {rate:.1f}% in {osph} segment")
    
    if 'SLA_Days' in df.columns:
        sla_valid = df[df['SLA_Days'].notna()]
        if len(sla_valid) > 0:
            avg_sla = sla_valid['SLA_Days'].mean()
            if avg_sla > 5:
                warnings.append(f"Average SLA is {avg_sla:.1f} working days (target: ≤5 days)")
            else:
                insights.append(f"Average SLA: {avg_sla:.1f} working days")
    
    return insights, warnings

def main():
    """Main application"""
    st.title(" CA Analytics Dashboard - Final Version")
    st.markdown("** Correct Per-Row SLA | OSPH Pivot Tables per Segmen**")
    st.markdown("---")
    
    with st.spinner("Loading dan processing data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    sla_calculated = df['SLA_Days'].notna().sum()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(" Total Records", f"{total_records:,}")
    with col2:
        st.metric(" Unique Applications", f"{unique_apps:,}")
    with col3:
        avg_sla = df[df['SLA_Days'].notna()]['SLA_Days'].mean()
        st.metric(" Average SLA", f"{avg_sla:.2f} days" if pd.notna(avg_sla) else "N/A")
    
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
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"{len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f"{df_filtered['apps_id'].nunique():,} unique applications")
    
    # Insights
    st.header(" Key Insights")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    if warnings:
        st.warning(" **Alerts:**\n" + "\n".join([f"• {w}" for w in warnings]))
    
    if insights:
        st.success(" **Positive Findings:**\n" + "\n".join([f"• {i}" for i in insights]))
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        " SLA Overview",
        " OSPH Pivot Analysis per Segmen",
        " CA Performance Analysis",
        " Detailed View",
        " Raw Data"
    ])
    
    # Tab 1: SLA Overview
    with tab1:
        st.header("SLA Performance Overview")
        st.info(" SLA dihitung per row dengan logika yang BENAR")
        
        sla_valid = df_filtered[df_filtered['SLA_Days'].notna()]
        
        if len(sla_valid) > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Average SLA", f"{sla_valid['SLA_Days'].mean():.2f} days")
            with col2:
                st.metric("Median SLA", f"{sla_valid['SLA_Days'].median():.2f} days")
            with col3:
                exceed_5 = (sla_valid['SLA_Days'] > 5).sum()
                pct = exceed_5 / len(sla_valid) * 100
                st.metric("Exceed 5 Days", f"{exceed_5} ({pct:.1f}%)")
            
            st.markdown("---")
            
            fig = px.histogram(
                sla_valid, x='SLA_Days', nbins=50,
                title="SLA Distribution (Working Days)",
                color_discrete_sequence=['#667eea']
            )
            fig.add_vline(x=5, line_dash="dash", line_color="red", annotation_text="5 Days Target")
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Average SLA by Status")
            
            sla_by_status = sla_valid.groupby('apps_status_clean').agg({
                'SLA_Days': ['mean', 'median'],
                'apps_id': 'nunique'
            }).reset_index()
            
            # Add total records count
            record_counts = sla_valid.groupby('apps_status_clean').size().reset_index(name='Total_Records')
            
            sla_by_status.columns = ['Status', 'Avg_SLA', 'Median_SLA', 'Distinct_Apps']
            sla_by_status = sla_by_status.merge(record_counts, left_on='Status', right_on='apps_status_clean', how='left')
            sla_by_status = sla_by_status.drop('apps_status_clean', axis=1)
            sla_by_status = sla_by_status[['Status', 'Avg_SLA', 'Median_SLA', 'Distinct_Apps', 'Total_Records']]
            sla_by_status = sla_by_status.sort_values('Avg_SLA', ascending=False)
            
            st.dataframe(sla_by_status, use_container_width=True, hide_index=True)
            
            fig = px.bar(
                sla_by_status, x='Status', y='Avg_SLA', text='Total_Records',
                title="Average SLA by Application Status",
                color='Avg_SLA', color_continuous_scale='RdYlGn_r'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("SLA Calculation Logic Distribution")
            
            logic_counts = sla_valid['SLA_Logic'].value_counts().reset_index()
            logic_counts.columns = ['Logic', 'Count']
            
            fig = px.pie(logic_counts, values='Count', names='Logic',
                        title="Distribution of SLA Calculation Methods")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No SLA data available")
    
    # Tab 2: OSPH Pivot Analysis
    with tab2:
        st.header("OSPH Pivot Tables per Segmen")
        st.info(" Pivot tables showing unique apps count for each combination")
        
        osph_pivots = create_osph_pivot_analysis(df_filtered)
        
        if osph_pivots:
            pivot_tab1, pivot_tab2, pivot_tab3 = st.tabs([
                " OSPH x Pekerjaan",
                " OSPH x Jenis Kendaraan",
                " OSPH x Hasil Scoring"
            ])
            
            # PIVOT 1: OSPH x Pekerjaan
            with pivot_tab1:
                if 'pekerjaan' in osph_pivots:
                    st.subheader("Pivot: OSPH Range (Rows) x Pekerjaan (Columns) per Segmen")
                    
                    for segmen, pivot_table in osph_pivots['pekerjaan'].items():
                        st.markdown(f"### Segmen: **{segmen}**")
                        st.dataframe(pivot_table, use_container_width=True)
                        st.markdown("---")
                else:
                    st.info("No data available")
            
            # PIVOT 2: OSPH x Jenis Kendaraan
            with pivot_tab2:
                if 'kendaraan' in osph_pivots:
                    st.subheader("Pivot: OSPH Range (Rows) x Jenis Kendaraan (Columns) per Segmen")
                    
                    for segmen, pivot_table in osph_pivots['kendaraan'].items():
                        st.markdown(f"### Segmen: **{segmen}**")
                        st.dataframe(pivot_table, use_container_width=True)
                        st.markdown("---")
                else:
                    st.info("No data available")
            
            # PIVOT 3: OSPH x Hasil Scoring
            with pivot_tab3:
                if 'scoring' in osph_pivots:
                    st.subheader("Pivot: OSPH Range (Rows) x Hasil Scoring (Columns) per Segmen")
                    
                    for segmen, pivot_table in osph_pivots['scoring'].items():
                        st.markdown(f"### Segmen: **{segmen}**")
                        st.dataframe(pivot_table, use_container_width=True)
                        st.markdown("---")
                else:
                    st.info("No data available")
        else:
            st.warning("No data available for pivot analysis")
    
    # Tab 3: CA Performance Analysis
    with tab3:
        st.header("CA Performance Analysis")
        st.info(" Detailed performance metrics per Credit Analyst")
        
        if 'user_name_clean' in df_filtered.columns:
            # Create comprehensive CA performance data
            ca_performance = []
            
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                # Basic metrics
                total_apps = df_ca['apps_id'].nunique()
                total_records = len(df_ca)
                
                # Scoring breakdown
                approve = df_ca['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                reject = df_ca['Scoring_Detail'].isin(['REJECT', 'REJECT 1', 'REJECT 2']).sum()
                reguler = df_ca['Scoring_Detail'].isin(['REGULER', 'REGULER 1', 'REGULER 2']).sum()
                in_progress = df_ca['Scoring_Detail'].isin(['SCORING IN PROGRESS']).sum()
                no_scoring = df_ca['Scoring_Detail'].isin(['(Pilih Semua)', '-']).sum()
                
                total_scored = approve + reject + reguler
                
                # Calculate rates
                if total_scored > 0:
                    approve_rate = f"{approve/total_scored*100:.1f}%"
                    reject_rate = f"{reject/total_scored*100:.1f}%"
                    reguler_rate = f"{reguler/total_scored*100:.1f}%"
                else:
                    approve_rate = "0.0%"
                    reject_rate = "0.0%"
                    reguler_rate = "0.0%"
                
                # SLA metrics
                df_ca_sla = df_ca[df_ca['SLA_Days'].notna()]
                if len(df_ca_sla) > 0:
                    avg_sla = f"{df_ca_sla['SLA_Days'].mean():.2f}"
                    median_sla = f"{df_ca_sla['SLA_Days'].median():.2f}"
                    max_sla = f"{df_ca_sla['SLA_Days'].max():.2f}"
                else:
                    avg_sla = "N/A"
                    median_sla = "N/A"
                    max_sla = "N/A"
                
                # OSPH average
                if df_ca['OSPH_clean'].notna().any():
                    avg_osph = df_ca['OSPH_clean'].mean()
                    avg_osph_display = f"Rp {avg_osph/1e6:.1f}M"
                else:
                    avg_osph_display = "N/A"
                
                ca_performance.append({
                    'CA Name': ca,
                    'Total Apps': total_apps,
                    'Total Records': total_records,
                    'APPROVE': approve,
                    'REJECT': reject,
                    'REGULER': reguler,
                    'In Progress': in_progress,
                    'No Scoring': no_scoring,
                    'Approve Rate': approve_rate,
                    'Reject Rate': reject_rate,
                    'Reguler Rate': reguler_rate,
                    'Avg SLA': avg_sla,
                    'Median SLA': median_sla,
                    'Max SLA': max_sla,
                    'Avg OSPH': avg_osph_display
                })
            
            ca_df = pd.DataFrame(ca_performance)
            
            # Summary metrics
            st.subheader(" CA Performance Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total CAs", len(ca_df))
            with col2:
                total_apps_all = ca_df['Total Apps'].sum()
                st.metric("Total Apps Handled", f"{total_apps_all:,}")
            with col3:
                total_approve = ca_df['APPROVE'].sum()
                st.metric("Total Approvals", f"{total_approve:,}")
            with col4:
                total_reject = ca_df['REJECT'].sum()
                st.metric("Total Rejections", f"{total_reject:,}")
            
            st.markdown("---")
            
            # Detailed table
            st.subheader(" Detailed CA Performance Table")
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # Visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Top 10 CAs by Volume")
                top_10 = ca_df.nlargest(10, 'Total Apps')
                
                fig = px.bar(
                    top_10,
                    x='CA Name',
                    y='Total Apps',
                    title="Top 10 CAs by Total Applications",
                    color='Total Apps',
                    color_continuous_scale='Blues'
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Approval vs Rejection Distribution")
                
                # Create stacked bar chart
                top_10_stacked = top_10[['CA Name', 'APPROVE', 'REJECT', 'REGULER']].copy()
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name='APPROVE',
                    x=top_10_stacked['CA Name'],
                    y=top_10_stacked['APPROVE'],
                    marker_color='#4CAF50'
                ))
                fig.add_trace(go.Bar(
                    name='REJECT',
                    x=top_10_stacked['CA Name'],
                    y=top_10_stacked['REJECT'],
                    marker_color='#F44336'
                ))
                fig.add_trace(go.Bar(
                    name='REGULER',
                    x=top_10_stacked['CA Name'],
                    y=top_10_stacked['REGULER'],
                    marker_color='#FFC107'
                ))
                
                fig.update_layout(
                    barmode='stack',
                    title='Top 10 CAs: Scoring Distribution',
                    xaxis_tickangle=45
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # CA comparison by approval rate
            st.subheader(" CA Approval Rate Comparison")
            
            # Convert percentage strings to float for sorting
            ca_df_sorted = ca_df.copy()
            ca_df_sorted['Approve_Rate_Numeric'] = ca_df_sorted['Approve Rate'].str.replace('%', '').astype(float)
            ca_df_sorted = ca_df_sorted.sort_values('Approve_Rate_Numeric', ascending=False).head(15)
            
            fig = px.bar(
                ca_df_sorted,
                x='CA Name',
                y='Approve_Rate_Numeric',
                title='Top 15 CAs by Approval Rate',
                labels={'Approve_Rate_Numeric': 'Approval Rate (%)'},
                color='Approve_Rate_Numeric',
                color_continuous_scale='RdYlGn'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # SLA Performance by CA
            st.subheader(" CA SLA Performance")
            
            # Filter CAs with valid SLA data
            ca_df_sla = ca_df[ca_df['Avg SLA'] != 'N/A'].copy()
            if len(ca_df_sla) > 0:
                ca_df_sla['Avg_SLA_Numeric'] = ca_df_sla['Avg SLA'].astype(float)
                ca_df_sla = ca_df_sla.sort_values('Avg_SLA_Numeric', ascending=True).head(15)
                
                fig = px.bar(
                    ca_df_sla,
                    x='CA Name',
                    y='Avg_SLA_Numeric',
                    title='Top 15 CAs with Best Average SLA',
                    labels={'Avg_SLA_Numeric': 'Average SLA (days)'},
                    color='Avg_SLA_Numeric',
                    color_continuous_scale='RdYlGn_r'
                )
                fig.add_hline(y=5, line_dash="dash", line_color="red", 
                             annotation_text="5 Days Target")
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No SLA data available for CAs")
            
            # Download CA performance report
            st.markdown("---")
            st.subheader(" Export CA Performance Report")
            
            csv_ca = ca_df.to_csv(index=False)
            st.download_button(
                "Download CA Performance Report (CSV)",
                csv_ca,
                "ca_performance_report.csv",
                "text/csv"
            )
        else:
            st.warning("No CA data available")
    
    # Tab 4: Detailed View
    with tab4:
        st.header("Detailed SLA View per Application")
        
        sample_apps = sorted(df_filtered['apps_id'].unique())
        
        if len(sample_apps) > 0:
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_app = st.selectbox("Select Application ID:", sample_apps, key='app_select')
            with col2:
                search_app = st.text_input("Or search:", key='search_app')
                if search_app and int(search_app) in sample_apps:
                    selected_app = int(search_app)
            
            if selected_app:
                app_data = df_filtered[df_filtered['apps_id'] == selected_app].sort_values('action_on_parsed')
                
                st.subheader(f"Application ID: {selected_app}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if 'Segmen_clean' in app_data.columns:
                        st.info(f"**Segmen:** {app_data['Segmen_clean'].iloc[0]}")
                with col2:
                    if 'OSPH_Category' in app_data.columns:
                        st.info(f"**OSPH:** {app_data['OSPH_Category'].iloc[0]}")
                with col3:
                    st.info(f"**Total Rows:** {len(app_data)}")
                
                st.markdown("---")
                st.subheader(" Chronological History")
                
                raw_cols = ['apps_status_clean', 'action_on_parsed', 'Recommendation_parsed', 'user_name_clean']
                available_raw = [c for c in raw_cols if c in app_data.columns]
                st.dataframe(app_data[available_raw].reset_index(drop=True), use_container_width=True)
                
                st.markdown("---")
                st.subheader(" SLA Calculation Details")
                
                sla_cols = ['apps_status_clean', 'SLA_Start', 'SLA_End', 'SLA_Days', 'SLA_Formatted', 'SLA_Logic']
                available_sla = [c for c in sla_cols if c in app_data.columns]
                st.dataframe(app_data[available_sla].reset_index(drop=True), use_container_width=True)
        else:
            st.info("No applications available")
    
    # Tab 5: Raw Data
    with tab5:
        st.header("Raw Data Export")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed', 'Recommendation_parsed',
            'SLA_Start', 'SLA_End', 'SLA_Days', 'SLA_Formatted', 'SLA_Logic',
            'Scoring_Detail', 'OSPH_clean', 'OSPH_Category',
            'Pekerjaan_clean', 'JenisKendaraan_clean',
            'Segmen_clean', 'user_name_clean', 'branch_name_clean'
        ]
        
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        
        st.dataframe(df_filtered[available_cols].head(100), use_container_width=True, hide_index=True)
        st.info(f"Showing first 100 of {len(df_filtered):,} records")
        
        st.markdown("---")
        
        csv_data = df_filtered[available_cols].to_csv(index=False)
        st.download_button(
            " Download Filtered Data (CSV)",
            csv_data,
            "ca_analytics_filtered.csv",
            "text/csv"
        )
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
