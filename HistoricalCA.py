import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(page_title="CA Analytics", layout="wide")

FILE_NAME = "HistoricalCA.xlsx"

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

def calculate_sla_details(start_dt, end_dt):
    """
    Calculate SLA dengan detail hari, jam, menit
    Returns: (days, hours, minutes) tuple atau None jika error
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
        
        start_adjusted = start_dt
        
        # If start time is after 3:30 PM, move to next working day at 8:30 AM
        if start_dt.time() >= datetime.strptime("15:30", "%H:%M").time():
            start_adjusted = start_dt + timedelta(days=1)
            start_adjusted = start_adjusted.replace(hour=8, minute=30, second=0)
            while not is_working_day(start_adjusted):
                start_adjusted += timedelta(days=1)
        
        # Hitung total waktu
        total_delta = end_dt - start_adjusted
        total_seconds = total_delta.total_seconds()
        
        if total_seconds < 0:
            return None
        
        # Extract komponen
        days = int(total_delta.days)
        hours = int((total_seconds % (24 * 3600)) // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return (days, hours, minutes)
    except:
        return None

def format_sla_display(sla_tuple):
    """Format SLA tuple (days, hours, minutes) menjadi string yang readable"""
    if sla_tuple is None or (isinstance(sla_tuple, float) and pd.isna(sla_tuple)):
        return "—"
    
    try:
        days, hours, minutes = sla_tuple
        
        parts = []
        if days > 0:
            parts.append(f"{days}h" if days == 1 else f"{days}d")
        if hours > 0:
            parts.append(f"{hours}j")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        if not parts:
            return "0m"
        
        return " ".join(parts)
    except:
        return "—"

def calculate_historical_sla(df):
    """Calculate SLA per row berdasarkan transition dari row sebelumnya untuk app_id yang sama"""
    df_sorted = df.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
    sla_list = []
    
    for idx, row in df_sorted.iterrows():
        app_id = row['apps_id']
        current_status = row.get('apps_status_clean', 'Unknown')
        current_time = row.get('action_on_parsed')
        recommendation = row.get('Recommendation', '')
        
        # Cari row sebelumnya untuk app_id yang sama
        prev_rows = df_sorted[(df_sorted['apps_id'] == app_id) & (df_sorted.index < idx)]
        
        if len(prev_rows) > 0:
            prev_row = prev_rows.iloc[-1]
            prev_status = prev_row.get('apps_status_clean', 'Unknown')
            prev_time = prev_row.get('action_on_parsed')
            
            # Special handling untuk PENDING CA
            if 'PENDING' in str(current_status).upper():
                if pd.isna(recommendation) or recommendation == '' or recommendation == '-':
                    # Belum ada rekomendasi, SLA = None
                    sla_tuple = None
                    transition = f"{prev_status} → {current_status} (Menunggu Rekomendasi)"
                else:
                    # Ada rekomendasi, hitung SLA
                    sla_tuple = calculate_sla_details(prev_time, current_time)
                    transition = f"{prev_status} → {current_status}"
            else:
                # Status lain, hitung SLA normal
                sla_tuple = calculate_sla_details(prev_time, current_time)
                transition = f"{prev_status} → {current_status}"
        else:
            # Row pertama untuk app ini
            sla_tuple = None
            transition = f"START → {current_status}"
        
        sla_list.append({
            'idx': idx,
            'apps_id': app_id,
            'Transition': transition,
            'From_Status': prev_rows.iloc[-1].get('apps_status_clean', 'Unknown') if len(prev_rows) > 0 else 'START',
            'To_Status': current_status,
            'SLA_Tuple': sla_tuple,
            'Has_Recommendation': not pd.isna(recommendation) and recommendation != '' and recommendation != '-'
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
    
    return min(score, 100)

def preprocess_data(df):
    """Clean and prepare data for analysis"""
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Calculate historical SLA per row
    if all(c in df.columns for c in ['apps_id', 'action_on_parsed', 'apps_status_clean']):
        sla_history = calculate_historical_sla(df)
        # Merge SLA ke original dataframe
        for _, sla_row in sla_history.iterrows():
            if sla_row['idx'] < len(df):
                df.at[sla_row['idx'], 'SLA_Tuple'] = sla_row['SLA_Tuple']
                df.at[sla_row['idx'], 'Transition'] = sla_row['Transition']
    
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
    
    # Clean apps_status
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
    # Clean Hasil_Scoring
    if 'Hasil_Scoring' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring'].fillna('(Pilih Semua)').astype(str).str.strip()
    
    # Clean Recommendation field
    if 'Recommendation' in df.columns:
        df['Recommendation'] = df['Recommendation'].fillna('').astype(str).str.strip()
    else:
        df['Recommendation'] = ''
    
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
        'desc_status_apps', 'Segmen', 'Pekerjaan', 'Jabatan',
        'JenisKendaraan', 'branch_name', 'Tujuan_Kredit', 
        'user_name', 'position_name'
    ]
    
    for field in categorical_fields:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
    # Calculate risk score
    df['Risk_Score'] = df.apply(calculate_risk_score, axis=1)
    df['Risk_Category'] = pd.cut(
        df['Risk_Score'], 
        bins=[0, 30, 60, 100], 
        labels=['Low Risk', 'Medium Risk', 'High Risk']
    )
    
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
            'apps_id', 'position_name', 'user_name', 'apps_status',
            'action_on', 'Outstanding_PH', 'Pekerjaan', 'Jabatan',
            'Hasil_Scoring', 'JenisKendaraan', 'branch_name',
            'LastOD', 'max_OD'
        ]
        
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"Kolom tidak ditemukan: {', '.join(missing)}")
            return None
        
        return preprocess_data(df)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
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
    
    # Insight 2: LastOD Impact
    if 'LastOD_clean' in df.columns and 'Scoring_Detail' in df.columns:
        high_od = df[df['LastOD_clean'] > 30]
        if len(high_od) > 0:
            reject_count = high_od['Scoring_Detail'].isin(
                ['REJECT', 'REJECT 1', 'REJECT 2']
            ).sum()
            reject_rate = (reject_count / len(high_od)) * 100
            
            warnings.append(
                f"High LastOD (>30 days): {reject_rate:.1f}% rejection rate"
            )
    
    return insights, warnings

def main():
    """Main application"""
    st.title("CA Analytics Dashboard")
    st.markdown(
        "Advanced Business Intelligence - Performance Analysis & Monitoring"
    )
    st.markdown("---")
    
    # Load data
    df = load_data()
    if df is None or df.empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    # Calculate historical SLA
    df_sla_history = calculate_historical_sla(df)
    
    # Display data summary
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    total_fields = len(df.columns)
    
    st.success(
        f"{total_records:,} records | "
        f"{unique_apps:,} unique applications | "
        f"{total_fields} fields"
    )
    
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
    
    # Segment filter (was Produk)
    if 'Segmen_clean' in df.columns:
        all_segments = sorted(df['Segmen_clean'].unique().tolist())
        selected_segment = st.sidebar.selectbox(
            "Segment",
            ['All'] + all_segments
        )
    else:
        selected_segment = 'All'
    
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
    
    if selected_segment != 'All':
        df_filtered = df_filtered[
            df_filtered['Segmen_clean'] == selected_segment
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
    
    # Filter SLA history
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
    
    # Analytical insights
    st.header("Key Insights & Alerts")
    insights, warnings = generate_analytical_insights(df_filtered)

    st.markdown(
    '<div class="warning-card"><h3>Risk Alerts</h3>',
    unsafe_allow_html=True
    )
    if warnings:
        for warning in warnings:
            st.markdown(f"**{warning}**")
    else:
        st.markdown("All metrics within acceptable range")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # KPIs
    st.header("Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        total_apps = df_filtered['apps_id'].nunique()
        st.metric("Total Applications", f"{total_apps:,}")
    
    with kpi2:
        avg_sla_display = "N/A"
        if len(df_sla_history_filtered) > 0:
            valid_slas = [s for s in df_sla_history_filtered['SLA_Tuple'] if s is not None]
            if valid_slas:
                # Hitung rata-rata dari tuple (days, hours, minutes)
                avg_days = np.mean([s[0] for s in valid_slas])
                avg_sla_display = f"{avg_days:.1f}d"
        st.metric("Average SLA", avg_sla_display)
    
    with kpi3:
        if 'Scoring_Detail' in df_filtered.columns:
            approve_count = df_filtered['Scoring_Detail'].isin(
                ['APPROVE', 'APPROVE 1', 'APPROVE 2']
            ).sum()
            total_scored = len(
                df_filtered[df_filtered['Scoring_Detail'] != '(Pilih Semua)']
            )
            approval_rate = (approve_count / total_scored * 100) if total_scored > 0 else 0
            st.metric("Approval Rate", f"{approval_rate:.1f}%")
    
    with kpi4:
        avg_osph = df_filtered['OSPH_clean'].mean()
        osph_display = (
            f"Rp {avg_osph/1e6:.0f}M" 
            if not pd.isna(avg_osph) 
            else "N/A"
        )
        st.metric("Average Outstanding PH", osph_display)
    
    with kpi5:
        if 'LastOD_clean' in df_filtered.columns:
            avg_last_od = df_filtered['LastOD_clean'].mean()
            last_od_display = (
                f"{avg_last_od:.1f}" 
                if not pd.isna(avg_last_od) 
                else "N/A"
            )
            st.metric("Average LastOD", last_od_display)
    
    with kpi6:
        if 'max_OD_clean' in df_filtered.columns:
            avg_max_od = df_filtered['max_OD_clean'].mean()
            max_od_display = (
                f"{avg_max_od:.1f}" 
                if not pd.isna(avg_max_od) 
                else "N/A"
            )
            st.metric("Average max_OD", max_od_display)
    
    st.markdown("---")
    
    # Tabs
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
        "SLA Transitions",
        "Duplicate Applications",
        "Raw Data"
    ])
    
    # Tab 1: Outstanding PH Analysis
    with tab1:
        st.header("Outstanding PH Analysis")
        st.info("Comprehensive analysis of Outstanding PH")
        
        st.subheader("Outstanding PH vs Scoring Result")
        
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            dim1_data = []
            
            osph_ranges = sorted([
                x for x in df_filtered['OSPH_Category'].unique() 
                if x != 'Unknown'
            ])
            
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
                
                scoring_values = ['APPROVE', 'APPROVE 1', 'APPROVE 2', 'REJECT', 'REJECT 1', 'REJECT 2', '-']
                
                for scoring in scoring_values:
                    count = len(df_osph[df_osph['Scoring_Detail'] == scoring])
                    if count > 0:
                        row[scoring] = count
                
                dim1_data.append(row)
            
            dim1_df = pd.DataFrame(dim1_data)
            st.dataframe(dim1_df, use_container_width=True, hide_index=True)
            
            scoring_cols = [c for c in dim1_df.columns if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', 'Total Records']]
            
            if scoring_cols:
                heatmap_data = dim1_df[['Range'] + scoring_cols].set_index('Range')
                fig = px.imshow(heatmap_data.T, text_auto=True, title="Outstanding PH vs Scoring", aspect="auto")
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: OD Impact Analysis
    with tab2:
        st.header("OD Impact Analysis")
        st.info("Analysis of LastOD and max_OD impact")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("LastOD Analysis")
            
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
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "-"
                        
                        lastod_analysis.append({
                            'Range': cat,
                            'Total Apps': df_od['apps_id'].nunique(),
                            'Approve': approve,
                            'Approval %': approval_pct
                        })
                
                lastod_df = pd.DataFrame(lastod_analysis)
                st.dataframe(lastod_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("max_OD Analysis")
            
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
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "-"
                        
                        maxod_analysis.append({
                            'Range': cat,
                            'Total Apps': df_od['apps_id'].nunique(),
                            'Approve': approve,
                            'Approval %': approval_pct
                        })
                
                maxod_df = pd.DataFrame(maxod_analysis)
                st.dataframe(maxod_df, use_container_width=True, hide_index=True)
    
    # Tab 3: Status & Scoring Matrix
    with tab3:
        st.header("Status & Scoring Matrix")
        
        if 'apps_status_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            cross_tab = pd.crosstab(df_filtered['apps_status_clean'], df_filtered['Scoring_Detail'])
            st.dataframe(cross_tab, use_container_width=True)
            
            if len(cross_tab) > 0:
                fig = px.imshow(cross_tab, text_auto=True, title="Status vs Scoring Heatmap", aspect="auto")
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 4: CA Performance
    with tab4:
        st.header("CA Performance Analytics")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = []
            
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                approve = df_ca['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                total_scored = len(df_ca[df_ca['Scoring_Detail'] != '(Pilih Semua)'])
                
                approval_pct = f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "-"
                
                ca_perf.append({
                    'CA Name': ca,
                    'Total Apps': df_ca['apps_id'].nunique(),
                    'Approve': approve,
                    'Approval %': approval_pct
                })
            
            ca_df = pd.DataFrame(ca_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            if len(ca_df) > 0:
                fig = px.bar(ca_df.head(10), x='CA Name', y='Total Apps', title="Top 10 CA by Volume")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 5: Predictive Patterns
    with tab5:
        st.header("Predictive Pattern Recognition")
        st.info("Top patterns by volume")
        
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
            
            pattern_analysis.columns = ['Outstanding PH', 'OD Segment', 'Job Type', 'Total Apps', 'Approval %']
            pattern_analysis = pattern_analysis.sort_values('Total Apps', ascending=False).head(15)
            
            st.dataframe(pattern_analysis, use_container_width=True, hide_index=True)
    
    # Tab 6: Trends & Forecasting
    with tab6:
        st.header("Trends & Time-Series Analysis")
        
        if 'YearMonth' in df_filtered.columns:
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (x.isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum() / len(x[x != '(Pilih Semua)']) * 100) if len(x[x != '(Pilih Semua)']) > 0 else 0
            }).reset_index()
            
            monthly.columns = ['Month', 'Volume', 'Approval %']
            
            st.subheader("Monthly Performance")
            st.dataframe(monthly, use_container_width=True, hide_index=True)
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Bar(x=monthly['Month'], y=monthly['Volume'], name="Volume"),
                secondary_y=False
            )
            
            fig.add_trace(
                go.Scatter(x=monthly['Month'], y=monthly['Approval %'], name="Approval %", mode='lines+markers'),
                secondary_y=True
            )
            
            fig.update_layout(title="Monthly Trend", height=500, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 7: SLA Transitions
    with tab7:
        st.header("SLA Transitions Analysis")
        st.info("📊 Format SLA: Hari (d) + Jam (j) + Menit (m). Contoh: 2d 3j 15m = 2 hari, 3 jam, 15 menit")
        
        if 'apps_id' in df_filtered.columns and 'action_on_parsed' in df_filtered.columns:
            df_filtered_sorted = df_filtered.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
            sla_transitions = []
            
            for idx, row in df_filtered_sorted.iterrows():
                app_id = row['apps_id']
                current_status = row.get('apps_status_clean', 'Unknown')
                current_time = row.get('action_on_parsed')
                recommendation = row.get('Recommendation', '')
                
                prev_rows = df_filtered_sorted[(df_filtered_sorted['apps_id'] == app_id) & (df_filtered_sorted.index < idx)]
                
                if len(prev_rows) > 0:
                    prev_row = prev_rows.iloc[-1]
                    prev_status = prev_row.get('apps_status_clean', 'Unknown')
                    prev_time = prev_row.get('action_on_parsed')
                    
                    sla_tuple = None
                    
                    if 'PENDING' in str(current_status).upper():
                        if not pd.isna(recommendation) and recommendation != '' and recommendation != '-':
                            sla_tuple = calculate_sla_details(prev_time, current_time)
                    else:
                        sla_tuple = calculate_sla_details(prev_time, current_time)
                    
                    transition = f"{prev_status} → {current_status}"
                else:
                    sla_tuple = None
                    transition = f"START → {current_status}"
                
                sla_transitions.append({
                    'apps_id': app_id,
                    'transition': transition,
                    'sla_tuple': sla_tuple,
                    'recommendation': recommendation
                })
            
            sla_df = pd.DataFrame(sla_transitions)
            
            st.subheader("SLA Details (Hari, Jam, Menit)")
            
            # Create pivot table
            pivot_data = []
            for app_id in sorted(sla_df['apps_id'].unique()):
                app_data = sla_df[sla_df['apps_id'] == app_id]
                row_data = {'App ID': app_id}
                
                for idx, trans_row in app_data.iterrows():
                    trans_label = trans_row['transition']
                    sla_tuple = trans_row['sla_tuple']
                    sla_display = format_sla_display(sla_tuple)
                    row_data[trans_label] = sla_display
                
                pivot_data.append(row_data)
            
            pivot_df = pd.DataFrame(pivot_data)
            st.dataframe(pivot_df, use_container_width=True, hide_index=True)
            
            # Summary statistics
            st.markdown("---")
            st.subheader("SLA Statistics")
            
            stats_data = []
            for transition in sorted(sla_df['transition'].unique()):
                trans_sla = sla_df[sla_df['transition'] == transition]['sla_tuple']
                trans_valid = [s for s in trans_sla if s is not None]
                total_trans = len(sla_df[sla_df['transition'] == transition])
                
                if len(trans_valid) > 0:
                    avg_days = np.mean([s[0] for s in trans_valid])
                    min_days = min([s[0] for s in trans_valid])
                    max_days = max([s[0] for s in trans_valid])
                    median_days = np.median([s[0] for s in trans_valid])
                else:
                    avg_days = min_days = max_days = median_days = 'N/A'
                
                stats_data.append({
                    'Transition': transition,
                    'Total': total_trans,
                    'Valid': len(trans_valid),
                    'N/A': total_trans - len(trans_valid),
                    'Avg (days)': f"{avg_days:.1f}" if isinstance(avg_days, (int, float)) else avg_days,
                    'Min': f"{int(min_days)}" if isinstance(min_days, (int, float)) else min_days,
                    'Max': f"{int(max_days)}" if isinstance(max_days, (int, float)) else max_days,
                    'Median': f"{int(median_days)}" if isinstance(median_days, (int, float)) else median_days
                })
            
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
            
            # Chart
            st.markdown("---")
            chart_data = []
            for transition in sorted(sla_df['transition'].unique()):
                trans_sla = sla_df[sla_df['transition'] == transition]['sla_tuple']
                trans_valid = [s for s in trans_sla if s is not None]
                if len(trans_valid) > 0:
                    avg_days = np.mean([s[0] for s in trans_valid])
                    chart_data.append({'Transition': transition, 'Avg SLA (days)': avg_days, 'Count': len(trans_valid)})
            
            if chart_data:
                chart_df = pd.DataFrame(chart_data)
                fig = px.bar(chart_df, x='Transition', y='Avg SLA (days)', color='Count', title="Average SLA per Transition")
                fig.update_layout(xaxis_tickangle=-45, height=500)
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 8: Duplicate Applications
    with tab8:
        st.header("Duplicate Applications Analysis")
        
        if 'apps_id' in df.columns:
            app_counts = df['apps_id'].value_counts()
            duplicates = app_counts[app_counts > 1]
            
            if len(duplicates) > 0:
                st.info(f"Found {len(duplicates)} duplicate application IDs with {duplicates.sum()} total records")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Duplicate IDs", len(duplicates))
                
                with col2:
                    st.metric("Max Records per ID", duplicates.max())
                
                with col3:
                    st.metric("Total Records", duplicates.sum())
                
                with col4:
                    st.metric("Avg Records per ID", f"{duplicates.mean():.1f}")
                
                dup_dist = duplicates.value_counts().sort_index()
                fig = px.bar(x=dup_dist.index, y=dup_dist.values, labels={'x': 'Records per App', 'y': 'Count'}, title="Duplicate Distribution")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("No duplicates found")
    
    # Tab 9: Raw Data
    with tab9:
        st.header("Raw Data Export")
        
        display_cols = [
            'apps_id', 'user_name', 'apps_status', 'Scoring_Detail',
            'action_on', 'RealisasiDate', 'Outstanding_PH', 'Recommendation',
            'LastOD', 'max_OD', 'Risk_Score'
        ]
        
        avail_cols = [c for c in display_cols if c in df_filtered.columns]
        
        st.dataframe(df_filtered[avail_cols], use_container_width=True, height=500)
        
        csv = df_filtered[avail_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"CA_Analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#666'>"
        f"CA Analytics Dashboard | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
