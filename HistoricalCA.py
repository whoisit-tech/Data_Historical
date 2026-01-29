import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(page_title="CA Analytics Dashboard", layout="wide")

FILE_NAME = "Historical_CA (1).xlsx"

# ============================================================================
# STYLING
# ============================================================================
st.markdown("""
<style>
    h1 { color: #003366; text-align: center; font-size: 28px; margin-bottom: 5px; }
    h2 { color: #003366; border-bottom: 2px solid #003366; padding-bottom: 10px; }
    h3 { color: #003366; margin-top: 20px; }
    .metric-box {
        background: linear-gradient(135deg, #f0f4f8 0%, #e0e8f0 100%);
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #003366;
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
    return f"{hours}h {minutes}m"

def calculate_sla_working_hours(start_dt, end_dt):
    """Calculate SLA in working hours (08:30 - 15:30)"""
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
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate', 'Recommendation', 'ApprovalCC1', 'ApprovalCC2']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Clean status
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
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
        df['Scoring_Detail'] = df['Hasil_Scoring'].fillna('(Pilih Semua)').astype(str).str.strip()
    
    # Clean Segmen
    if 'Segmen' in df.columns:
        df['Segmen_clean'] = df['Segmen'].fillna('Unknown').astype(str).str.strip()
        df['Segmen_clean'] = df['Segmen_clean'].replace('-', 'Unknown')
    
    # Clean JenisKendaraan
    if 'JenisKendaraan' in df.columns:
        df['JenisKendaraan_clean'] = df['JenisKendaraan'].fillna('Unknown').astype(str).str.strip()
        df['JenisKendaraan_clean'] = df['JenisKendaraan_clean'].replace('-', 'Unknown')
    
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
        'desc_status_apps', 'Pekerjaan', 'Jabatan',
        'branch_name', 'Tujuan_Kredit', 'user_name', 'position_name'
    ]
    
    for field in categorical_fields:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
    return df

def calculate_sla_per_status(df):
    """
    Calculate SLA per status (simplified approach)
    For each record, calculate time from Recommendation to action_on
    """
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
            st.error(f"File not found: {FILE_NAME}")
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
            st.error(f"Missing columns: {', '.join(missing)}")
            return None
        
        df_clean = preprocess_data(df)
        df_clean = calculate_sla_per_status(df_clean)
        
        df_clean['Risk_Score'] = df_clean.apply(calculate_risk_score, axis=1)
        df_clean['Risk_Category'] = pd.cut(
            df_clean['Risk_Score'], 
            bins=[0, 30, 60, 100], 
            labels=['Low Risk', 'Medium Risk', 'High Risk']
        )
        
        return df_clean
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main Streamlit application"""
    st.title("CA Analytics Dashboard")
    st.markdown("**Credit Application Analytics - Fixed Version**")
    st.markdown("---")
    
    with st.spinner("Loading data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("Unable to load data")
        st.stop()
    
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
        sla_pct = f"{sla_with_data/total_records*100:.1f}%"
        st.metric("SLA Calculated", f"{sla_with_data:,} ({sla_pct})")
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
    
    # SIDEBAR FILTERS
    st.sidebar.title("Filters")
    
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
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 {len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f"📝 {df_filtered['apps_id'].nunique():,} unique applications")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Outstanding PH Analysis",
        "Status & Scoring",
        "OD Impact Analysis",
        "CA Performance",
        "SLA Analysis",
        "Data Export"
    ])
    
    # ====== TAB 1: OUTSTANDING PH ======
    with tab1:
        st.header("📊 Outstanding PH Distribution Analysis")
        
        # 1. OSPH vs Segmen
        st.subheader("1. Outstanding PH vs Segmen/Produk")
        
        if 'OSPH_Category' in df_filtered.columns and 'Segmen_clean' in df_filtered.columns:
            osph_segmen_data = []
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                row = {
                    'Outstanding PH': osph,
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                for segmen in sorted([x for x in df_filtered['Segmen_clean'].unique() if x != 'Unknown']):
                    count = len(df_osph[df_osph['Segmen_clean'] == segmen])
                    if count > 0:
                        row[segmen] = count
                
                osph_segmen_data.append(row)
            
            osph_segmen_df = pd.DataFrame(osph_segmen_data)
            st.dataframe(osph_segmen_df, use_container_width=True, hide_index=True)
            
            # Visualization
            if len(osph_segmen_df) > 0:
                plot_data = []
                for _, row in osph_segmen_df.iterrows():
                    osph = row['Outstanding PH']
                    for col in osph_segmen_df.columns:
                        if col not in ['Outstanding PH', 'Total Apps', 'Total Records']:
                            if col in row and pd.notna(row[col]):
                                plot_data.append({
                                    'OSPH': osph,
                                    'Segmen': col,
                                    'Count': row[col]
                                })
                
                if plot_data:
                    plot_df = pd.DataFrame(plot_data)
                    fig = px.bar(
                        plot_df,
                        x='OSPH',
                        y='Count',
                        color='Segmen',
                        title="Outstanding PH vs Segmen Distribution",
                        barmode='group'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 2. OSPH vs JenisKendaraan
        st.subheader("2. Outstanding PH vs Jenis Kendaraan")
        
        if 'OSPH_Category' in df_filtered.columns and 'JenisKendaraan_clean' in df_filtered.columns:
            osph_vehicle_data = []
            
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
                
                osph_vehicle_data.append(row)
            
            osph_vehicle_df = pd.DataFrame(osph_vehicle_data)
            st.dataframe(osph_vehicle_df, use_container_width=True, hide_index=True)
            
            # Visualization
            if len(osph_vehicle_df) > 0:
                plot_data = []
                for _, row in osph_vehicle_df.iterrows():
                    osph = row['Outstanding PH']
                    for col in osph_vehicle_df.columns:
                        if col not in ['Outstanding PH', 'Total Apps', 'Total Records']:
                            if col in row and pd.notna(row[col]):
                                plot_data.append({
                                    'OSPH': osph,
                                    'Vehicle': col,
                                    'Count': row[col]
                                })
                
                if plot_data:
                    plot_df = pd.DataFrame(plot_data)
                    fig = px.bar(
                        plot_df,
                        x='OSPH',
                        y='Count',
                        color='Vehicle',
                        title="Outstanding PH vs Jenis Kendaraan Distribution",
                        barmode='group'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 3. OSPH vs Scoring
        st.subheader("3. Outstanding PH vs Scoring Result")
        
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            osph_scoring_data = []
            
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
                
                # Calculate approval rate
                approve = df_osph['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                total = len(df_osph[df_osph['Scoring_Detail'] != '(Pilih Semua)'])
                row['Approval Rate'] = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                
                osph_scoring_data.append(row)
            
            osph_scoring_df = pd.DataFrame(osph_scoring_data)
            st.dataframe(osph_scoring_df, use_container_width=True, hide_index=True)
    
    # ====== TAB 2: STATUS & SCORING ======
    with tab2:
        st.header("📋 Application Status & Scoring Cross-Tabulation")
        
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
                    title="Status vs Scoring Distribution Heatmap",
                    color_continuous_scale="Blues",
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # ====== TAB 3: OD IMPACT ======
    with tab3:
        st.header("⏰ Overdue Days Impact Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Last Overdue Days")
            
            if 'LastOD_clean' in df_filtered.columns:
                df_filtered_copy = df_filtered.copy()
                df_filtered_copy['LastOD_Category'] = pd.cut(
                    df_filtered_copy['LastOD_clean'],
                    bins=[-np.inf, 0, 10, 30, np.inf],
                    labels=['No OD', '1-10 days', '11-30 days', '>30 days']
                )
                
                lastod_analysis = []
                
                for cat in ['No OD', '1-10 days', '11-30 days', '>30 days']:
                    df_od = df_filtered_copy[df_filtered_copy['LastOD_Category'] == cat]
                    
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
                df_filtered_copy2 = df_filtered.copy()
                df_filtered_copy2['maxOD_Category'] = pd.cut(
                    df_filtered_copy2['max_OD_clean'],
                    bins=[-np.inf, 0, 15, 45, np.inf],
                    labels=['No OD', '1-15 days', '16-45 days', '>45 days']
                )
                
                maxod_analysis = []
                
                for cat in ['No OD', '1-15 days', '16-45 days', '>45 days']:
                    df_od = df_filtered_copy2[df_filtered_copy2['maxOD_Category'] == cat]
                    
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
    
    # ====== TAB 4: CA PERFORMANCE ======
    with tab4:
        st.header("👥 Credit Analyst Performance Summary")
        
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
                
                # Calculate avg SLA for this CA
                ca_sla = df_ca[df_ca['SLA_Hours'].notna()]
                if len(ca_sla) > 0:
                    avg_sla = convert_hours_to_hm(ca_sla['SLA_Hours'].mean())
                else:
                    avg_sla = "-"
                
                ca_perf.append({
                    'CA Name': ca,
                    'Total Apps': df_ca['apps_id'].nunique(),
                    'Total Records': len(df_ca),
                    'Approved': approve,
                    'Approval Rate': approval_pct,
                    'Avg Risk Score': avg_risk,
                    'Avg SLA': avg_sla
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
    
    # ====== TAB 5: SLA ANALYSIS (SIMPLIFIED) ======
    with tab5:
        st.header("⏱️ SLA Performance Analysis")
        
        st.info("""
        **SLA Calculation Method:**
        - SLA dihitung dari waktu Recommendation sampai action_on
        - Hanya dihitung jika kedua timestamp tersedia
        - Menggunakan working hours (08:30 - 15:30)
        - Exclude weekend dan tanggal merah
        """)
        
        # Overall SLA stats
        sla_valid = df_filtered[df_filtered['SLA_Hours'].notna()]
        
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
            sla_pct = f"{len(sla_valid)/len(df_filtered)*100:.1f}%" if len(df_filtered) > 0 else "0%"
            st.metric("Data Coverage", f"{len(sla_valid):,} ({sla_pct})")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            if len(sla_valid) > 0:
                exceed = (sla_valid['SLA_Hours'] > 35).sum()
                exceed_pct = f"{exceed/len(sla_valid)*100:.1f}%"
                st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                st.metric("Exceed Target (>35h)", exceed_pct)
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # SLA by Status (SIMPLIFIED - Main request)
        st.subheader("📊 SLA Statistics by Application Status")
        
        if 'apps_status_clean' in df_filtered.columns:
            status_sla = []
            
            for status in sorted(df_filtered['apps_status_clean'].unique()):
                if status == 'Unknown':
                    continue
                
                df_status = df_filtered[df_filtered['apps_status_clean'] == status]
                sla_status = df_status[df_status['SLA_Hours'].notna()]
                
                if len(sla_status) > 0:
                    avg_sla = sla_status['SLA_Hours'].mean()
                    median_sla = sla_status['SLA_Hours'].median()
                    max_sla = sla_status['SLA_Hours'].max()
                    min_sla = sla_status['SLA_Hours'].min()
                    
                    status_sla.append({
                        'Status': status,
                        'Total Records': len(df_status),
                        'With SLA': len(sla_status),
                        'Coverage': f"{len(sla_status)/len(df_status)*100:.1f}%",
                        'Avg SLA': convert_hours_to_hm(avg_sla),
                        'Median SLA': convert_hours_to_hm(median_sla),
                        'Min SLA': convert_hours_to_hm(min_sla),
                        'Max SLA': convert_hours_to_hm(max_sla),
                    })
            
            if status_sla:
                status_sla_df = pd.DataFrame(status_sla)
                st.dataframe(status_sla_df, use_container_width=True, hide_index=True)
                
                # Visualization
                plot_data = []
                for _, row in status_sla_df.iterrows():
                    # Extract hours from formatted string
                    avg_str = row['Avg SLA']
                    if avg_str and 'h' in avg_str:
                        hours = float(avg_str.split('h')[0])
                        plot_data.append({
                            'Status': row['Status'],
                            'Avg SLA (hours)': hours
                        })
                
                if plot_data:
                    plot_df = pd.DataFrame(plot_data)
                    fig = px.bar(
                        plot_df,
                        x='Status',
                        y='Avg SLA (hours)',
                        title="Average SLA by Application Status",
                        color='Avg SLA (hours)',
                        color_continuous_scale='RdYlGn_r'
                    )
                    fig.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="Target: 35h")
                    st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Monthly trend
        st.subheader("📈 SLA Monthly Trend")
        
        if len(sla_valid) > 0 and 'action_on_parsed' in sla_valid.columns:
            sla_valid_copy = sla_valid.copy()
            sla_valid_copy['YearMonth'] = sla_valid_copy['action_on_parsed'].dt.to_period('M').astype(str)
            
            monthly_sla = sla_valid_copy.groupby('YearMonth').agg({
                'SLA_Hours': ['mean', 'count']
            }).reset_index()
            
            monthly_sla.columns = ['Month', 'Avg_SLA', 'Count']
            monthly_sla = monthly_sla.sort_values('Month')
            monthly_sla['Avg_SLA_Formatted'] = monthly_sla['Avg_SLA'].apply(convert_hours_to_hm)
            
            st.dataframe(monthly_sla[['Month', 'Avg_SLA_Formatted', 'Count']], use_container_width=True, hide_index=True)
            
            # Line chart
            fig = px.line(
                monthly_sla,
                x='Month',
                y='Avg_SLA',
                title="Average SLA Trend by Month",
                markers=True
            )
            fig.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="Target: 35 hours")
            st.plotly_chart(fig, use_container_width=True)
    
    # ====== TAB 6: DATA EXPORT ======
    with tab6:
        st.header("💾 Data Export")
        
        st.subheader("Filtered Data Preview")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed',
            'Recommendation_parsed', 'SLA_Formatted', 'SLA_Hours',
            'Scoring_Detail', 'OSPH_Category', 'Segmen_clean',
            'JenisKendaraan_clean', 'LastOD_clean',
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
        st.subheader("Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = df_filtered[available_cols].to_csv(index=False)
            st.download_button(
                "📥 Download Filtered Data (CSV)",
                csv_data,
                "ca_analytics_data.csv",
                "text/csv"
            )
        
        with col2:
            # Summary stats for download
            summary_data = {
                'Metric': [
                    'Total Records',
                    'Unique Applications',
                    'SLA Calculated',
                    'Average SLA (hours)',
                    'Records with Recommendation',
                    'Approval Rate'
                ],
                'Value': [
                    len(df_filtered),
                    df_filtered['apps_id'].nunique(),
                    df_filtered['SLA_Hours'].notna().sum(),
                    df_filtered['SLA_Hours'].mean() if df_filtered['SLA_Hours'].notna().any() else 0,
                    df_filtered['Recommendation_parsed'].notna().sum(),
                    f"{df_filtered['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum() / len(df_filtered[df_filtered['Scoring_Detail'] != '(Pilih Semua)']) * 100:.1f}%"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            csv_summary = summary_df.to_csv(index=False)
            st.download_button(
                "📊 Download Summary Stats (CSV)",
                csv_summary,
                "summary_stats.csv",
                "text/csv"
            )
    
    st.markdown("---")
    st.caption(f"Dashboard last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total records in database: {len(df):,}")

if __name__ == "__main__":
    main()
