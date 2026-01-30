import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(page_title="CA Analytics Dashboard", layout="wide")

FILE_NAME = "Historical_CA (1) (1).xlsx"

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
        df['Segmen_clean'] = df['Segmen'].fillna('-').astype(str).str.strip()
        df['Segmen_clean'] = df['Segmen_clean'].replace('Unknown', '-')
    
    # Clean JenisKendaraan
    if 'JenisKendaraan' in df.columns:
        df['JenisKendaraan_clean'] = df['JenisKendaraan'].fillna('Unknown').astype(str).str.strip()
        df['JenisKendaraan_clean'] = df['JenisKendaraan_clean'].replace('-', 'Unknown')
    
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
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
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
    st.markdown("**Credit Application Analytics - Improved Version**")
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
        all_segmen = sorted([x for x in df['Segmen_clean'].unique()])
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
    st.sidebar.info(f" {len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f" {df_filtered['apps_id'].nunique():,} unique applications")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        " SLA Analysis",
        " Detail Raw Data",
        " OSPH",
        " Branch & CA Performance",
        " Status & Scoring",
        " OD Impact",
        " Export"
    ])

    # ====== TAB 1: SLA ANALYSIS ======
    with tab1:
        st.header(" SLA Performance Analysis")
        
        st.info("""
        **SLA Calculation Method:**
        - SLA dihitung dari waktu Recommendation sampai action_on
        - Hanya dihitung jika kedua timestamp tersedia
        - Menggunakan working hours (08:30 - 15:30)
        - Exclude weekend dan tanggal merah
        """)
        
        # Overall SLA stats
        sla_valid = df_filtered[df_filtered['SLA_Hours'].notna()]
        
        col1, col2, col3 = st.columns(3)
        
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

        
        st.markdown("---")
        
        # SLA TREND
        st.subheader(" SLA Trend - Average per Month")
        
        if len(sla_valid) > 0 and 'action_on_parsed' in sla_valid.columns:
            sla_trend = sla_valid.copy()
            sla_trend['YearMonth'] = sla_trend['action_on_parsed'].dt.to_period('M').astype(str)
            
            monthly_avg = sla_trend.groupby('YearMonth')['SLA_Hours'].agg(['mean', 'count']).reset_index()
            monthly_avg.columns = ['Month', 'Avg_SLA_Hours', 'Count']
            monthly_avg = monthly_avg.sort_values('Month')
            monthly_avg['Avg_SLA_Formatted'] = monthly_avg['Avg_SLA_Hours'].apply(convert_hours_to_hm)
            
            # Display table
            st.dataframe(monthly_avg[['Month', 'Avg_SLA_Formatted', 'Avg_SLA_Hours', 'Count']], 
                        use_container_width=True, hide_index=True)
            
            # Line chart - IMPROVED
            fig = go.Figure()
            
            # Create formatted hover text
            hover_text = []
            for idx, row in monthly_avg.iterrows():
                hours = int(row['Avg_SLA_Hours'])
                minutes = int((row['Avg_SLA_Hours'] - hours) * 60)
                hover_text.append(f"{hours} jam {minutes} menit<br>({row['Count']} records)")
            
            fig.add_trace(go.Scatter(
                x=monthly_avg['Month'],
                y=monthly_avg['Avg_SLA_Hours'],
                mode='lines+markers+text',
                name='Average SLA',
                line=dict(color='#003366', width=3),
                marker=dict(size=10, color='#003366'),
                text=[f"{int(h)} jam {int((h - int(h)) * 60)} menit" for h in monthly_avg['Avg_SLA_Hours']],
                textposition='top center',
                textfont=dict(size=10, color='#003366'),
                hovertext=hover_text,
                hoverinfo='text'
            ))
            
            fig.add_hline(
                y=35, 
                line_dash="dash", 
                line_color="red",
                line_width=2,
                annotation_text="Target: 35 jam (5 hari kerja)",
                annotation_position="right",
                annotation_font_color="red"
            )
            
            fig.update_layout(
                title="SLA Trend - Average per Month (dalam jam)",
                xaxis_title="Month",
                yaxis_title="Average SLA (jam)",
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # SLA by Status
        st.subheader(" SLA Statistics by Application Status")
        
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
    
    # ====== TAB 2: DETAIL RAW DATA - ALL APPS ID ======
    with tab2:
        st.header(" Detail Raw Data - All Applications")
        
        st.markdown("""
        **Browse all applications:**
        - Click on any Application ID to view all its records
        - Sorted by latest action date
        """)
        
        # Get all unique apps with their summary info
        apps_summary = []
        
        for app_id in sorted(df_filtered['apps_id'].unique()):
            app_data = df_filtered[df_filtered['apps_id'] == app_id]
            latest_record = app_data.sort_values('action_on_parsed', ascending=False).iloc[0]
            
            apps_summary.append({
                'apps_id': app_id,
                'Total Records': len(app_data),
                'Latest Status': latest_record.get('apps_status_clean', 'N/A'),
                'Latest Action': latest_record.get('action_on_parsed', pd.NaT),
                'Segmen': latest_record.get('Segmen_clean', 'N/A'),
                'OSPH Category': latest_record.get('OSPH_Category', 'N/A'),
                'Branch': latest_record.get('branch_name_clean', 'N/A'),
                'CA': latest_record.get('user_name_clean', 'N/A')
            })
        
        apps_df = pd.DataFrame(apps_summary)
        apps_df = apps_df.sort_values('Latest Action', ascending=False)
        
        st.info(f" Total Applications: **{len(apps_df):,}**")
        
        # Display all apps in a table
        st.dataframe(
            apps_df.style.format({'Latest Action': lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) else 'N/A'}),
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.markdown("---")
        
        # Search and detail view
        st.subheader(" Application Detail Viewer")
        
        search_input = st.text_input(" Enter Application ID:", placeholder="e.g., 5259031")
        
        if search_input:
            try:
                search_id = int(search_input)
                app_records = df[df['apps_id'] == search_id].sort_values('action_on_parsed')
                
                if len(app_records) > 0:
                    st.success(f" Found **{len(app_records)}** records for Application ID: **{search_id}**")
                    
                    # Summary
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        segmen = app_records['Segmen_clean'].iloc[0] if 'Segmen_clean' in app_records.columns else 'N/A'
                        st.info(f"**Segmen:** {segmen}")
                    
                    with col2:
                        osph = app_records['OSPH_Category'].iloc[0] if 'OSPH_Category' in app_records.columns else 'N/A'
                        st.info(f"**OSPH:** {osph}")
                    
                    with col3:
                        branch = app_records['branch_name_clean'].iloc[0] if 'branch_name_clean' in app_records.columns else 'N/A'
                        st.info(f"**Branch:** {branch}")
                    
                    with col4:
                        ca = app_records['user_name_clean'].iloc[0] if 'user_name_clean' in app_records.columns else 'N/A'
                        st.info(f"**CA:** {ca}")
                    
                    st.markdown("---")
                    
                    # Display ALL records
                    st.subheader(" All Records")
                    
                    display_cols = [
                        'apps_status_clean', 'action_on_parsed', 'Recommendation_parsed',
                        'Initiation_parsed', 'SLA_Hours', 'SLA_Formatted',
                        'Scoring_Detail', 'OSPH_clean', 'LastOD_clean',
                        'user_name_clean', 'Pekerjaan_clean', 'JenisKendaraan_clean'
                    ]
                    
                    available_cols = [c for c in display_cols if c in app_records.columns]
                    st.dataframe(app_records[available_cols].reset_index(drop=True), use_container_width=True)
                    
                else:
                    st.warning(f" No records found for Application ID: {search_id}")
            
            except ValueError:
                st.error(" Please enter a valid numeric Application ID")
    
    # ====== TAB 3: OSPH PIVOT BY PEKERJAAN ======
    with tab3:
        st.header(" Outstanding PH Pivot by Pekerjaan")
        
        st.markdown("""
        **4 Pivot Tables: Row=OSPH Range, Column=Pekerjaan**
        - Calculations based on **distinct apps_id**
        - Table shows unique applications per category
        """)
        
        st.markdown("---")
        
        # Define OSPH ranges order
        osph_order = ['0 - 250 Juta', '250 - 500 Juta', '500 Juta+']
        
        # Get top pekerjaan
        top_pekerjaan = df_filtered.drop_duplicates('apps_id')['Pekerjaan_clean'].value_counts().head(10).index.tolist()
        
        # Create 4 pivot tables
        for segmen in ['-', 'KKB', 'CS NEW', 'CS USED']:
            st.subheader(f"Segmen: {segmen}")
            
            df_segmen = df_filtered[df_filtered['Segmen_clean'] == segmen].drop_duplicates('apps_id')
            
            total_apps = len(df_segmen)
            total_records = len(df_filtered[df_filtered['Segmen_clean'] == segmen])
            
            st.caption(f" Total Apps (Distinct): **{total_apps:,}** | Total Records: **{total_records:,}**")
            
            if len(df_segmen) > 0:
                # Create pivot: OSPH Range x Pekerjaan
                pivot_data = []
                
                for osph_range in osph_order:
                    df_osph = df_segmen[df_segmen['OSPH_Category'] == osph_range]
                    
                    row = {'OSPH Range': osph_range}
                    
                    for pekerjaan in top_pekerjaan:
                        count = len(df_osph[df_osph['Pekerjaan_clean'] == pekerjaan])
                        row[pekerjaan] = count if count > 0 else 0
                    
                    # Add total
                    row['TOTAL'] = len(df_osph)
                    
                    pivot_data.append(row)
                
                # Add TOTAL row
                total_row = {'OSPH Range': 'TOTAL'}
                for pekerjaan in top_pekerjaan:
                    count = len(df_segmen[df_segmen['Pekerjaan_clean'] == pekerjaan])
                    total_row[pekerjaan] = count if count > 0 else 0
                total_row['TOTAL'] = len(df_segmen)
                pivot_data.append(total_row)
                
                pivot_df = pd.DataFrame(pivot_data)
                
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)
                
                # Visualization
                pivot_plot = pivot_df[pivot_df['OSPH Range'] != 'TOTAL'].copy()
                
                if len(pivot_plot) > 0:
                    plot_data = []
                    for _, row in pivot_plot.iterrows():
                        osph = row['OSPH Range']
                        for pek in top_pekerjaan:
                            if pek in row and row[pek] > 0:
                                plot_data.append({
                                    'OSPH Range': osph,
                                    'Pekerjaan': pek,
                                    'Count': row[pek]
                                })
                    
                    if plot_data:
                        plot_df = pd.DataFrame(plot_data)
                        fig = px.bar(
                            plot_df,
                            x='OSPH Range',
                            y='Count',
                            color='Pekerjaan',
                            title=f"Distribution for Segmen {segmen}",
                            barmode='group'
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No data available for Segmen {segmen}")
            
            st.markdown("---")
    
    # ====== TAB 4: BRANCH & CA PERFORMANCE ======
    with tab4:
        st.header(" Branch & CA Performance")
        
        subtab1, subtab2 = st.tabs([" Branch Analysis", "👥 CA Analysis"])
        
        # Branch Performance
        with subtab1:
            st.subheader("Branch Performance Summary")
            
            st.caption(" Calculations based on **distinct apps_id**")
            
            if 'branch_name_clean' in df_filtered.columns:
                branch_perf = []
                
                for branch in sorted(df_filtered['branch_name_clean'].unique()):
                    if branch == 'Unknown':
                        continue
                    
                    df_branch = df_filtered[df_filtered['branch_name_clean'] == branch]
                    df_branch_distinct = df_branch.drop_duplicates('apps_id')
                    
                    total_apps = len(df_branch_distinct)
                    total_records = len(df_branch)
                    
                    approve = df_branch_distinct['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                    total_scored = len(df_branch_distinct[df_branch_distinct['Scoring_Detail'] != '(Pilih Semua)'])
                    approval_pct = f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "0%"
                    
                    avg_risk = f"{df_branch_distinct['Risk_Score'].mean():.0f}" if df_branch_distinct['Risk_Score'].notna().any() else "-"
                    
                    branch_sla = df_branch[df_branch['SLA_Hours'].notna()]
                    avg_sla = convert_hours_to_hm(branch_sla['SLA_Hours'].mean()) if len(branch_sla) > 0 else "-"
                    
                    total_osph = df_branch_distinct['OSPH_clean'].sum()
                    
                    branch_perf.append({
                        'Branch': branch,
                        'Total Apps (Distinct)': total_apps,
                        'Total Records': total_records,
                        'Approved': approve,
                        'Approval Rate': approval_pct,
                        'Avg Risk Score': avg_risk,
                        'Avg SLA': avg_sla,
                        'Total OSPH': f"Rp {total_osph:,.0f}"
                    })
                
                branch_df = pd.DataFrame(branch_perf).sort_values('Total Apps (Distinct)', ascending=False)
                st.dataframe(branch_df, use_container_width=True, hide_index=True)
                
                # Charts
                if len(branch_df) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig1 = px.bar(
                            branch_df.head(10),
                            x='Branch',
                            y='Total Apps (Distinct)',
                            title="Top 10 Branches by Volume (Distinct Apps)"
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        branch_df_plot = branch_df.copy()
                        branch_df_plot['Approval_Numeric'] = branch_df_plot['Approval Rate'].str.rstrip('%').astype(float)
                        
                        fig2 = px.bar(
                            branch_df_plot.head(10),
                            x='Branch',
                            y='Approval_Numeric',
                            title="Top 10 Branches by Approval Rate",
                            color='Approval_Numeric',
                            color_continuous_scale='RdYlGn'
                        )
                        fig2.update_layout(yaxis_title="Approval Rate (%)")
                        st.plotly_chart(fig2, use_container_width=True)
        
        # CA Performance
        with subtab2:
            st.subheader("Credit Analyst Performance Summary")
            
            st.caption(" Calculations based on **distinct apps_id**")
            
            if 'user_name_clean' in df_filtered.columns:
                ca_perf = []
                
                for ca in sorted(df_filtered['user_name_clean'].unique()):
                    if ca == 'Unknown':
                        continue
                    
                    df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                    df_ca_distinct = df_ca.drop_duplicates('apps_id')
                    
                    total_apps = len(df_ca_distinct)
                    total_records = len(df_ca)
                    
                    approve = df_ca_distinct['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                    total_scored = len(df_ca_distinct[df_ca_distinct['Scoring_Detail'] != '(Pilih Semua)'])
                    approval_pct = f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "0%"
                    
                    avg_risk = f"{df_ca_distinct['Risk_Score'].mean():.0f}" if df_ca_distinct['Risk_Score'].notna().any() else "-"
                    
                    ca_sla = df_ca[df_ca['SLA_Hours'].notna()]
                    avg_sla = convert_hours_to_hm(ca_sla['SLA_Hours'].mean()) if len(ca_sla) > 0 else "-"
                    
                    branches = df_ca['branch_name_clean'].unique()
                    main_branch = branches[0] if len(branches) > 0 else "Unknown"
                    
                    ca_perf.append({
                        'CA Name': ca,
                        'Branch': main_branch,
                        'Total Apps (Distinct)': total_apps,
                        'Total Records': total_records,
                        'Approved': approve,
                        'Approval Rate': approval_pct,
                        'Avg Risk Score': avg_risk,
                        'Avg SLA': avg_sla
                    })
                
                ca_df = pd.DataFrame(ca_perf).sort_values('Total Apps (Distinct)', ascending=False)
                st.dataframe(ca_df, use_container_width=True, hide_index=True)
                
                # Charts
                if len(ca_df) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig1 = px.bar(
                            ca_df.head(10),
                            x='CA Name',
                            y='Total Apps (Distinct)',
                            title="Top 10 CAs by Application Volume (Distinct Apps)"
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        ca_df_plot = ca_df.copy()
                        ca_df_plot['Approval_Numeric'] = ca_df_plot['Approval Rate'].str.rstrip('%').astype(float)
                        
                        fig2 = px.bar(
                            ca_df_plot.head(10),
                            x='CA Name',
                            y='Approval_Numeric',
                            title="Top 10 CAs by Approval Rate",
                            color='Approval_Numeric',
                            color_continuous_scale='RdYlGn'
                        )
                        fig2.update_layout(yaxis_title="Approval Rate (%)")
                        st.plotly_chart(fig2, use_container_width=True)
    
    # ====== TAB 5: STATUS & SCORING ======
    with tab5:
        st.header(" Application Status & Scoring Analysis")
        
        st.caption(" Calculations based on **distinct apps_id**")
        
        df_distinct = df_filtered.drop_duplicates('apps_id')
        total_apps_distinct = len(df_distinct)
        total_records = len(df_filtered)
        
        st.info(f" Total Apps (Distinct): **{total_apps_distinct:,}** | Total Records: **{total_records:,}**")
        
        if 'apps_status_clean' in df_distinct.columns and 'Scoring_Detail' in df_distinct.columns:
            cross_tab = pd.crosstab(
                df_distinct['apps_status_clean'],
                df_distinct['Scoring_Detail'],
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
                    title="Status vs Scoring Distribution Heatmap (Distinct Apps)",
                    color_continuous_scale="Blues",
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # ====== TAB 6: OD IMPACT ======
    with tab6:
        st.header(" Overdue Days Impact Analysis")
        
        st.caption(" Calculations based on **distinct apps_id**")
        
        df_distinct = df_filtered.drop_duplicates('apps_id')
        total_apps_distinct = len(df_distinct)
        total_records = len(df_filtered)
        
        st.info(f" Total Apps (Distinct): **{total_apps_distinct:,}** | Total Records: **{total_records:,}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Last Overdue Days")
            
            if 'LastOD_clean' in df_distinct.columns:
                df_distinct_copy = df_distinct.copy()
                df_distinct_copy['LastOD_Category'] = pd.cut(
                    df_distinct_copy['LastOD_clean'],
                    bins=[-np.inf, 0, 10, 30, np.inf],
                    labels=['No OD', '1-10 days', '11-30 days', '>30 days']
                )
                
                lastod_analysis = []
                
                for cat in ['No OD', '1-10 days', '11-30 days', '>30 days']:
                    df_od = df_distinct_copy[df_distinct_copy['LastOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                        
                        lastod_analysis.append({
                            'LastOD Range': cat,
                            'Total Apps (Distinct)': len(df_od),
                            'Approved': approve,
                            'Approval Rate': approval_pct
                        })
                
                lastod_df = pd.DataFrame(lastod_analysis)
                st.dataframe(lastod_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Maximum Overdue Days")
            
            if 'max_OD_clean' in df_distinct.columns:
                df_distinct_copy2 = df_distinct.copy()
                df_distinct_copy2['maxOD_Category'] = pd.cut(
                    df_distinct_copy2['max_OD_clean'],
                    bins=[-np.inf, 0, 15, 45, np.inf],
                    labels=['No OD', '1-15 days', '16-45 days', '>45 days']
                )
                
                maxod_analysis = []
                
                for cat in ['No OD', '1-15 days', '16-45 days', '>45 days']:
                    df_od = df_distinct_copy2[df_distinct_copy2['maxOD_Category'] == cat]
                    
                    if len(df_od) > 0:
                        approve = df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = f"{approve/total*100:.1f}%" if total > 0 else "0%"
                        
                        maxod_analysis.append({
                            'max_OD Range': cat,
                            'Total Apps (Distinct)': len(df_od),
                            'Approved': approve,
                            'Approval Rate': approval_pct
                        })
                
                maxod_df = pd.DataFrame(maxod_analysis)
                st.dataframe(maxod_df, use_container_width=True, hide_index=True)
    
    
    # ====== TAB 7: DATA EXPORT ======
    with tab7:
        st.header(" Data Export")
        
        st.subheader("Filtered Data Preview")
        
        display_cols = [
            'apps_id', 'apps_status_clean', 'action_on_parsed',
            'Recommendation_parsed', 'SLA_Formatted', 'SLA_Hours',
            'Scoring_Detail', 'OSPH_Category', 'Segmen_clean',
            'JenisKendaraan_clean', 'Pekerjaan_clean', 'LastOD_clean',
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
                " Download Filtered Data (CSV)",
                csv_data,
                "ca_analytics_data.csv",
                "text/csv"
            )
        
        with col2:
            df_distinct_export = df_filtered.drop_duplicates('apps_id')
            approve_count = df_distinct_export['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
            total_scored = len(df_distinct_export[df_distinct_export['Scoring_Detail'] != '(Pilih Semua)'])
            
            summary_data = {
                'Metric': [
                    'Total Records',
                    'Unique Applications',
                    'SLA Calculated',
                    'Average SLA (hours)',
                    'Approval Rate'
                ],
                'Value': [
                    len(df_filtered),
                    df_filtered['apps_id'].nunique(),
                    df_filtered['SLA_Hours'].notna().sum(),
                    f"{df_filtered['SLA_Hours'].mean():.2f}" if df_filtered['SLA_Hours'].notna().any() else "0",
                    f"{approve_count / total_scored * 100:.1f}%" if total_scored > 0 else "0%"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            csv_summary = summary_df.to_csv(index=False)
            st.download_button(
                " Download Summary Stats (CSV)",
                csv_summary,
                "summary_stats.csv",
                "text/csv"
            )
    
    st.markdown("---")
    st.caption(f"Dashboard last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total records: {len(df):,}")

if __name__ == "__main__":
    main()
