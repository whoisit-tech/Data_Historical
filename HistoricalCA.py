import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(page_title="CA Analytics Dashboard", layout="wide")

FILE_NAME = "Historical_CA (1).xlsx"

st.markdown("""
<style>
    h1 { color: #003366; text-align: center; font-size: 28px; margin-bottom: 5px; }
    h2 { color: #003366; border-bottom: 2px solid #003366; padding-bottom: 10px; }
    h3 { color: #003366; margin-top: 20px; }
    .metric-box {
        background: #f0f4f8;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #003366;
    }
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

def convert_hours_to_hm(total_hours):
    """Convert decimal hours to HH:MM format"""
    if pd.isna(total_hours):
        return None
    hours = int(total_hours)
    minutes = int((total_hours - hours) * 60)
    return f"{hours}h {minutes}m"

def calculate_sla_working_hours(start_dt, end_dt):
    """
    Calculate SLA dalam working hours (08:30 - 15:30)
    Exclude weekend dan tanggal merah
    
    Returns: dict dengan total_hours (float), formatted (string)
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
            'total_seconds': total_seconds,
            'formatted': convert_hours_to_hm(total_hours)
        }
    except Exception as e:
        return None

def calculate_historical_sla(df):
    """Calculate SLA per transition - untuk SEMUA rows"""
    df_sorted = df.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
    sla_list = []
    
    for app_id, group in df_sorted.groupby('apps_id'):
        group = group.reset_index(drop=True)
        
        for idx in range(len(group)):
            row = group.iloc[idx]
            current_status = row.get('apps_status_clean', 'Unknown')
            current_time = row.get('action_on_parsed')
            recommendation_time = row.get('Recommendation_parsed')
            
            sla_result = None
            sla_formatted = None
            start_time = None
            transition = None
            
            # FIRST ROW
            if idx == 0:
                # Jika Recommendation ada gunakan Recommendation, kalau tidak gunakan current_time
                if pd.notna(recommendation_time):
                    sla_result = calculate_sla_working_hours(recommendation_time, current_time)
                    start_time = recommendation_time
                else:
                    # Jika tidak ada Recommendation, SLA = 0 (baru mulai)
                    sla_result = None
                    start_time = None
                
                if sla_result:
                    sla_formatted = sla_result['formatted']
                    sla_hours = sla_result['total_hours']
                else:
                    sla_formatted = None
                    sla_hours = None
                
                transition = f"START to {current_status}"
            
            # ROW BERIKUTNYA - CALCULATE DARI PREVIOUS ACTION TIME
            else:
                prev_row = group.iloc[idx - 1]
                prev_status = prev_row.get('apps_status_clean', 'Unknown')
                prev_time = prev_row.get('action_on_parsed')
                
                transition = f"{prev_status} to {current_status}"
                
                # SEMUA status dihitung dari previous action time
                sla_result = calculate_sla_working_hours(prev_time, current_time)
                start_time = prev_time
                
                if sla_result:
                    sla_formatted = sla_result['formatted']
                    sla_hours = sla_result['total_hours']
                else:
                    sla_formatted = None
                    sla_hours = None
            
            sla_list.append({
                'idx': row.name,
                'apps_id': app_id,
                'Transition': transition,
                'SLA_Hours': sla_hours if sla_result else None,
                'SLA_Formatted': sla_formatted,
                'Start_Time': start_time,
                'End_Time': current_time,
            })
    
    return pd.DataFrame(sla_list)

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
        if row['SLA_Hours'] > 35:
            score += 20
        elif row['SLA_Hours'] > 21:
            score += 10
    
    return min(score, 100)

def preprocess_data(df):
    """Clean and prepare data"""
    df = df.copy()
    
    for col in ['action_on', 'Initiation', 'RealisasiDate', 'Recommendation', 'ApprovalCC1', 'ApprovalCC2']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
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
    
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Quarter'] = df['action_on_parsed'].dt.quarter
    
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
    """Load and preprocess data"""
    try:
        if not Path(FILE_NAME).exists():
            st.error(f"File not found: {FILE_NAME}")
            return None, None
        
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
            st.error(f"Missing columns: {', '.join(missing)}")
            return None, None
        
        df_clean = preprocess_data(df)
        sla_history = calculate_historical_sla(df_clean)
        
        for _, sla_row in sla_history.iterrows():
            idx = sla_row['idx']
            if idx < len(df_clean):
                df_clean.at[idx, 'SLA_Hours'] = sla_row['SLA_Hours']
                df_clean.at[idx, 'SLA_Formatted'] = sla_row['SLA_Formatted']
        
        df_clean['Risk_Score'] = df_clean.apply(calculate_risk_score, axis=1)
        df_clean['Risk_Category'] = pd.cut(
            df_clean['Risk_Score'], 
            bins=[0, 30, 60, 100], 
            labels=['Low Risk', 'Medium Risk', 'High Risk']
        )
        
        return df_clean, sla_history
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def main():
    """Main application"""
    st.title("CA Analytics Dashboard")
    st.markdown("Application Credit Analysis - Executive Summary")
    st.markdown("---")
    
    with st.spinner("Loading data..."):
        result = load_data()
    
    if result[0] is None or result[0].empty:
        st.error("Unable to load data")
        st.stop()
    
    df, df_sla_history = result
    
    # TOP METRICS
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    sla_with_data = df['SLA_Hours'].notna().sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("Total Records", f"{total_records:,}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("Unique Applications", f"{unique_apps:,}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("SLA Calculated", f"{sla_with_data:,}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        sla_valid = df[df['SLA_Hours'].notna()]
        if len(sla_valid) > 0:
            avg_hours = sla_valid['SLA_Hours'].mean()
            avg_formatted = convert_hours_to_hm(avg_hours)
            st.markdown('<div class="metric-box">', unsafe_allow_html=True)
            st.metric("Average SLA", avg_formatted)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # FILTERS
    st.markdown("### Filter Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'apps_status_clean' in df.columns:
            all_status = sorted([x for x in df['apps_status_clean'].unique() if x != 'Unknown'])
            selected_status = st.multiselect("Application Status", all_status, default=all_status)
        else:
            selected_status = []
    
    with col2:
        if 'Scoring_Detail' in df.columns:
            all_scoring = sorted([x for x in df['Scoring_Detail'].unique() if x != '(Pilih Semua)'])
            selected_scoring = st.multiselect("Scoring Result", all_scoring, default=all_scoring)
        else:
            selected_scoring = []
    
    with col3:
        if 'OSPH_Category' in df.columns:
            all_osph = sorted([x for x in df['OSPH_Category'].unique() if x != 'Unknown'])
            selected_osph = st.multiselect("Outstanding PH", all_osph, default=all_osph)
        else:
            selected_osph = []
    
    # Apply filters
    df_filtered = df.copy()
    
    if selected_status:
        df_filtered = df_filtered[df_filtered['apps_status_clean'].isin(selected_status)]
    
    if selected_scoring:
        df_filtered = df_filtered[df_filtered['Scoring_Detail'].isin(selected_scoring)]
    
    if selected_osph:
        df_filtered = df_filtered[df_filtered['OSPH_Category'].isin(selected_osph)]
    
    filtered_app_ids = df_filtered['apps_id'].unique()
    df_sla_history_filtered = df_sla_history[df_sla_history['apps_id'].isin(filtered_app_ids)]
    
    st.markdown(f"**Filtered records:** {len(df_filtered):,} | **Unique apps:** {df_filtered['apps_id'].nunique():,}")
    st.markdown("---")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Outstanding PH Analysis",
        "Status & Scoring",
        "OD Impact Analysis",
        "CA Performance",
        "SLA Analysis",
        "Data Export"
    ])
    
    # TAB 1: OUTSTANDING PH
    with tab1:
        st.header("Outstanding PH Distribution Analysis")
        
        st.subheader("1. Outstanding PH vs Scoring Result")
        
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            dim1_data = []
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                row = {
                    'Outstanding PH': osph,
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                for scoring in ['APPROVE', 'APPROVE 1', 'APPROVE 2', 'REGULER', 'REGULER 1', 'REGULER 2', 'REJECT', 'REJECT 1', 'REJECT 2']:
                    count = len(df_osph[df_osph['Scoring_Detail'] == scoring])
                    if count > 0:
                        row[scoring] = count
                
                dim1_data.append(row)
            
            dim1_df = pd.DataFrame(dim1_data)
            st.dataframe(dim1_df, use_container_width=True, hide_index=True)
        
        st.subheader("2. Outstanding PH vs Application Status")
        
        if 'OSPH_Category' in df_filtered.columns and 'apps_status_clean' in df_filtered.columns:
            status_data = []
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                row = {
                    'Outstanding PH': osph,
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
        
        st.subheader("3. Outstanding PH vs Vehicle Type")
        
        if 'OSPH_Category' in df_filtered.columns and 'JenisKendaraan_clean' in df_filtered.columns:
            vehicle_data = []
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                row = {
                    'Outstanding PH': osph,
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                for vehicle in sorted([x for x in df_filtered['JenisKendaraan_clean'].unique() if x != 'Unknown']):
                    count = len(df_osph[df_osph['JenisKendaraan_clean'] == vehicle])
                    if count > 0:
                        row[vehicle] = count
                
                vehicle_data.append(row)
            
            vehicle_df = pd.DataFrame(vehicle_data)
            st.dataframe(vehicle_df, use_container_width=True, hide_index=True)
    
    # TAB 2: STATUS & SCORING
    with tab2:
        st.header("Application Status & Scoring Cross-Tabulation")
        
        if 'apps_status_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            cross_tab = pd.crosstab(
                df_filtered['apps_status_clean'],
                df_filtered['Scoring_Detail'],
                margins=True,
                margins_name='TOTAL'
            )
            st.dataframe(cross_tab, use_container_width=True)
            
            # Heatmap
            cross_tab_no_total = cross_tab.drop('TOTAL', errors='ignore').drop('TOTAL', axis=1, errors='ignore')
            
            if len(cross_tab_no_total) > 0:
                fig = px.imshow(
                    cross_tab_no_total,
                    text_auto=True,
                    title="Status vs Scoring Distribution",
                    color_continuous_scale="Blues",
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 3: OD IMPACT
    with tab3:
        st.header("Overdue Days Impact Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Last Overdue Days")
            
            if 'LastOD_clean' in df_filtered.columns:
                df_filtered['LastOD_Category'] = pd.cut(
                    df_filtered['LastOD_clean'],
                    bins=[-np.inf, 0, 10, 30, np.inf],
                    labels=['No OD', '1-10 days', '11-30 days', '>30 days']
                )
                
                lastod_analysis = []
                
                for cat in ['No OD', '1-10 days', '11-30 days', '>30 days']:
                    df_od = df_filtered[df_filtered['LastOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                        
                        lastod_analysis.append({
                            'LastOD Range': cat,
                            'Total Apps': df_od['apps_id'].nunique(),
                            'Total Records': len(df_od),
                            'Approved': approve,
                            'Approval Rate': approval_pct
                        })
                
                lastod_df = pd.DataFrame(lastod_analysis)
                st.dataframe(lastod_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Maximum Overdue Days")
            
            if 'max_OD_clean' in df_filtered.columns:
                df_filtered['maxOD_Category'] = pd.cut(
                    df_filtered['max_OD_clean'],
                    bins=[-np.inf, 0, 15, 45, np.inf],
                    labels=['No OD', '1-15 days', '16-45 days', '>45 days']
                )
                
                maxod_analysis = []
                
                for cat in ['No OD', '1-15 days', '16-45 days', '>45 days']:
                    df_od = df_filtered[df_filtered['maxOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                        
                        maxod_analysis.append({
                            'max_OD Range': cat,
                            'Total Apps': df_od['apps_id'].nunique(),
                            'Total Records': len(df_od),
                            'Approved': approve,
                            'Approval Rate': approval_pct
                        })
                
                maxod_df = pd.DataFrame(maxod_analysis)
                st.dataframe(maxod_df, use_container_width=True, hide_index=True)
    
    # TAB 4: CA PERFORMANCE
    with tab4:
        st.header("Credit Analyst Performance Summary")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = []
            
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                approve = df_ca['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                total_scored = len(df_ca[df_ca['Scoring_Detail'] != '(Pilih Semua)'])
                
                approval_pct = f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "0%"
                avg_risk = f"{df_ca['Risk_Score'].mean():.0f}" if df_ca['Risk_Score'].notna().any() else "-"
                
                ca_perf.append({
                    'CA Name': ca,
                    'Total Apps': df_ca['apps_id'].nunique(),
                    'Total Records': len(df_ca),
                    'Approved': approve,
                    'Approval Rate': approval_pct,
                    'Avg Risk Score': avg_risk
                })
            
            ca_df = pd.DataFrame(ca_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            # Chart
            if len(ca_df) > 0:
                fig = px.bar(
                    ca_df.head(10),
                    x='CA Name',
                    y='Total Apps',
                    title="Top 10 Credit Analysts by Application Volume"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 5: SLA ANALYSIS
    with tab5:
        st.header("SLA Performance Analysis")
        
        # Search detail
        st.subheader("Search Application Detail")
        search_app_id = st.text_input("Enter Application ID to view SLA details:")
        
        if search_app_id:
            try:
                search_id = int(search_app_id)
                app_sla_detail = df_sla_history_filtered[df_sla_history_filtered['apps_id'] == search_id]
                
                if len(app_sla_detail) > 0:
                    st.success(f"Found {len(app_sla_detail)} records for App ID {search_id}")
                    
                    detail_cols = ['Transition', 'SLA_Hours', 'SLA_Formatted', 'Start_Time', 'End_Time']
                    st.dataframe(app_sla_detail[detail_cols], use_container_width=True, hide_index=True)
                else:
                    st.warning(f"No records found for App ID {search_id}")
            except:
                st.error("Please enter a valid numeric App ID")
        
        st.markdown("---")
        
        sla_valid = df_sla_history_filtered[df_sla_history_filtered['SLA_Hours'].notna()]
        
        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if len(sla_valid) > 0:
                avg_hours = sla_valid['SLA_Hours'].mean()
                avg_formatted = convert_hours_to_hm(avg_hours)
                st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                st.metric("Average SLA", avg_formatted)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if len(sla_valid) > 0:
                median_hours = sla_valid['SLA_Hours'].median()
                median_formatted = convert_hours_to_hm(median_hours)
                st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                st.metric("Median SLA", median_formatted)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-box">', unsafe_allow_html=True)
            st.metric("SLA Count", f"{len(sla_valid):,}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            if len(sla_valid) > 0:
                exceed = (sla_valid['SLA_Hours'] > 35).sum()
                exceed_pct = f"{exceed/len(sla_valid)*100:.1f}%"
                st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                st.metric("Exceed Target (35h)", exceed_pct)
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Monthly trend
        st.subheader("SLA Monthly Trend")
        
        if len(sla_valid) > 0 and 'End_Time' in sla_valid.columns:
            sla_valid_copy = sla_valid.copy()
            sla_valid_copy['YearMonth'] = pd.to_datetime(sla_valid_copy['End_Time']).dt.to_period('M').astype(str)
            
            monthly_sla = sla_valid_copy.groupby('YearMonth').agg({
                'SLA_Hours': ['mean', 'count']
            }).reset_index()
            
            monthly_sla.columns = ['Month', 'Avg_SLA', 'Count']
            monthly_sla = monthly_sla.sort_values('Month')
            
            # Convert to hm for display
            monthly_sla['Avg_SLA_Formatted'] = monthly_sla['Avg_SLA'].apply(convert_hours_to_hm)
            
            st.dataframe(monthly_sla[['Month', 'Avg_SLA_Formatted', 'Count']], use_container_width=True, hide_index=True)
            
            # Line chart
            fig = px.line(
                monthly_sla,
                x='Month',
                y='Avg_SLA',
                title="Average SLA by Month",
                markers=True
            )
            fig.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="Target: 35 hours")
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # SLA by transition
        st.subheader("SLA Statistics by Transition")
        
        stats_data = []
        for transition in sorted(df_sla_history_filtered['Transition'].unique()):
            trans_data = df_sla_history_filtered[df_sla_history_filtered['Transition'] == transition]
            valid_sla = trans_data[trans_data['SLA_Hours'].notna()]
            
            if len(valid_sla) > 0:
                avg = convert_hours_to_hm(valid_sla['SLA_Hours'].mean())
                stats_data.append({
                    'Transition': transition,
                    'Total': len(trans_data),
                    'With SLA': len(valid_sla),
                    'Avg SLA': avg,
                })
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    # TAB 6: DATA EXPORT
    with tab6:
        st.header("Data Export")
        
        st.subheader("Filtered Data Preview")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed',
            'Recommendation_parsed', 'SLA_Formatted', 'SLA_Hours',
            'Scoring_Detail', 'OSPH_Category', 'LastOD_clean',
            'user_name_clean', 'branch_name_clean'
        ]
        
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        
        st.dataframe(
            df_filtered[available_cols].head(100),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown(f"Showing first 100 of {len(df_filtered):,} records")
        
        st.markdown("---")
        st.subheader("Download Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = df_filtered[available_cols].to_csv(index=False)
            st.download_button(
                "Download Filtered Data (CSV)",
                csv_data,
                "ca_analytics_data.csv",
                "text/csv"
            )
        
        with col2:
            csv_sla = df_sla_history_filtered.to_csv(index=False)
            st.download_button(
                "Download SLA History (CSV)",
                csv_sla,
                "sla_history.csv",
                "text/csv"
            )
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
