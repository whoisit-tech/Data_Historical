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

def calculate_sla_days(start_dt, end_dt):
    """Calculate SLA in working days only"""
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        
        start_adjusted = start_dt
        
        # If start time is after 3:30 PM, move to next working day at 8:30 AM
        if start_dt.time() >= datetime.strptime("15:30", "%H:%M").time():
            start_adjusted = start_dt + timedelta(days=1)
            start_adjusted = start_adjusted.replace(hour=8, minute=30, second=0)
            while not is_working_day(start_adjusted):
                start_adjusted += timedelta(days=1)
        
        working_days = 0
        current = start_adjusted.date()
        end_date = end_dt.date()
        
        while current <= end_date:
            if is_working_day(datetime.combine(current, datetime.min.time())):
                working_days += 1
            current += timedelta(days=1)
        
        return working_days
    except:
        return None

def calculate_historical_sla(df):
    """Calculate SLA per status transition"""
    sla_records = []
    
    for app_id, group in df.groupby('apps_id'):
        group = group.sort_values('action_on_parsed').reset_index(drop=True)
        
        for idx in range(len(group) - 1):
            current_row = group.iloc[idx]
            next_row = group.iloc[idx + 1]
            
            from_status = current_row.get('apps_status_clean', 'Unknown')
            to_status = next_row.get('apps_status_clean', 'Unknown')
            
            start_time = current_row.get('action_on_parsed')
            end_time = next_row.get('action_on_parsed')
            
            sla_days = calculate_sla_days(start_time, end_time)
            
            sla_records.append({
                'apps_id': app_id,
                'Transition': f"{from_status} → {to_status}",
                'From_Status': from_status,
                'To_Status': to_status,
                'Start_Date': start_time,
                'End_Date': end_time,
                'SLA_Days': sla_days,
                'Outstanding_PH': current_row.get('OSPH_clean'),
                'LastOD': current_row.get('LastOD_clean'),
                'Produk': current_row.get('Produk_clean'),
                'User': current_row.get('user_name_clean'),
                'Branch': current_row.get('branch_name_clean'),
                'Scoring': next_row.get('Scoring_Detail')
            })
    
    return pd.DataFrame(sla_records)

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
    
    return min(score, 100)

def preprocess_data(df):
    """Clean and prepare data for analysis"""
    df = df.copy()
    
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(
            df['Outstanding_PH'].astype(str).str.replace(',', ''), 
            errors='coerce'
        )
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    for col in ['LastOD', 'max_OD']:
        if col in df.columns:
            df[f'{col}_clean'] = pd.to_numeric(df[col], errors='coerce')
    
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
    if 'Hasil_Scoring' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring'].fillna('(Pilih Semua)').astype(str).str.strip()
    
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
            'apps_id', 'position_name', 'user_name', 'apps_status', 'desc_status_apps',
            'Produk', 'action_on', 'Initiation', 'RealisasiDate', 'Outstanding_PH',
            'Pekerjaan', 'Jabatan', 'Pekerjaan_Pasangan', 'Hasil_Scoring',
            'JenisKendaraan', 'branch_name', 'Tujuan_Kredit', 'LastOD', 'max_OD'
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
    st.markdown("Advanced Business Intelligence - Performance Analysis & Monitoring")
    st.markdown("---")
    
    df = load_data()
    if df is None or df.empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    df_sla_history = calculate_historical_sla(df)
    
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    total_fields = len(df.columns)
    
    st.success(f"{total_records:,} records | {unique_apps:,} unique applications | {total_fields} fields")
    
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
    
    if 'Produk_clean' in df.columns:
        all_products = sorted(df['Produk_clean'].unique().tolist())
        selected_product = st.sidebar.selectbox("Product", ['All'] + all_products)
    else:
        selected_product = 'All'
    
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
    
    df_filtered = df.copy()
    
    if selected_status:
        df_filtered = df_filtered[df_filtered['apps_status_clean'].isin(selected_status)]
    if selected_scoring:
        df_filtered = df_filtered[df_filtered['Scoring_Detail'].isin(selected_scoring)]
    if selected_product != 'All':
        df_filtered = df_filtered[df_filtered['Produk_clean'] == selected_product]
    if selected_branch != 'All':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    if selected_ca != 'All':
        df_filtered = df_filtered[df_filtered['user_name_clean'] == selected_ca]
    if selected_osph != 'All':
        df_filtered = df_filtered[df_filtered['OSPH_Category'] == selected_osph]
    
    filtered_app_ids = df_filtered['apps_id'].unique()
    df_sla_history_filtered = df_sla_history[df_sla_history['apps_id'].isin(filtered_app_ids)]
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"{len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    st.sidebar.info(f"{df_filtered['apps_id'].nunique():,} unique applications")
    
    st.header("Key Insights & Alerts")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    st.markdown('<div class="warning-card"><h3>Risk Alerts</h3>', unsafe_allow_html=True)
    if warnings:
        for warning in warnings:
            st.markdown(f"**{warning}**")
    else:
        st.markdown("All metrics within acceptable range")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.header("Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        total_apps = df_filtered['apps_id'].nunique()
        st.metric("Total Applications", f"{total_apps:,}")
    with kpi2:
        avg_sla = df_sla_history_filtered['SLA_Days'].mean()
        st.metric("Average SLA (days)", f"{avg_sla:.1f}" if not pd.isna(avg_sla) else "N/A")
    with kpi3:
        if 'Scoring_Detail' in df_filtered.columns:
            approve_count = df_filtered['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum()
            total_scored = len(df_filtered[df_filtered['Scoring_Detail'] != '(Pilih Semua)'])
            approval_rate = (approve_count / total_scored * 100) if total_scored > 0 else 0
            st.metric("Approval Rate", f"{approval_rate:.1f}%")
    with kpi4:
        avg_osph = df_filtered['OSPH_clean'].mean()
        st.metric("Average Outstanding PH", f"Rp {avg_osph/1e6:.0f}M" if not pd.isna(avg_osph) else "N/A")
    with kpi5:
        if 'LastOD_clean' in df_filtered.columns:
            avg_last_od = df_filtered['LastOD_clean'].mean()
            st.metric("Average LastOD", f"{avg_last_od:.1f}" if not pd.isna(avg_last_od) else "N/A")
    with kpi6:
        if 'max_OD_clean' in df_filtered.columns:
            avg_max_od = df_filtered['max_OD_clean'].mean()
            st.metric("Average max_OD", f"{avg_max_od:.1f}" if not pd.isna(avg_max_od) else "N/A")
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "Outstanding PH Analysis", "OD Impact Analysis", "Status & Scoring Matrix",
        "CA Performance", "Predictive Patterns", "Trends & Forecasting",
        "SLA Transitions", "Duplicate Applications", "Raw Data"
    ])
    
    # TAB 1: Outstanding PH Analysis
    with tab1:
        st.header("Outstanding PH Analysis")
        
        st.subheader("Dimension 1: OSPH vs Scoring Result")
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            dim1_data = []
            osph_ranges = sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown'])
            
            for osph in osph_ranges:
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                row = {
                    'Range': osph,
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                for scoring in ['APPROVE', 'APPROVE 1', 'APPROVE 2', 'REJECT', 'REJECT 1', 'REJECT 2', 'REGULER']:
                    count = len(df_osph[df_osph['Scoring_Detail'] == scoring])
                    if count > 0:
                        row[scoring] = count
                dim1_data.append(row)
            
            dim1_df = pd.DataFrame(dim1_data)
            st.dataframe(dim1_df, use_container_width=True, hide_index=True)
    
    # TAB 2: OD Impact Analysis
    with tab2:
        st.header("OD Impact Analysis")
        
        if 'LastOD_clean' in df_filtered.columns:
            df_filtered['LastOD_Category'] = pd.cut(df_filtered['LastOD_clean'],
                bins=[-np.inf, 0, 10, 30, np.inf],
                labels=['0 (No OD)', '1-10 days', '11-30 days', '>30 days'])
            
            lastod_data = []
            for cat in ['0 (No OD)', '1-10 days', '11-30 days', '>30 days']:
                df_od = df_filtered[df_filtered['LastOD_Category'] == cat]
                if len(df_od) > 0:
                    lastod_data.append({
                        'LastOD Range': cat,
                        'Total Apps': df_od['apps_id'].nunique(),
                        'Total Records': len(df_od),
                        'Approve': df_od['Scoring_Detail'].isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum(),
                        'Reject': df_od['Scoring_Detail'].isin(['REJECT', 'REJECT 1', 'REJECT 2']).sum()
                    })
            st.dataframe(pd.DataFrame(lastod_data), use_container_width=True, hide_index=True)
    
    # TAB 3: Status & Scoring Matrix
    with tab3:
        st.header("Status & Scoring Matrix")
        if 'apps_status_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            cross_tab = pd.crosstab(df_filtered['apps_status_clean'], df_filtered['Scoring_Detail'])
            st.dataframe(cross_tab, use_container_width=True)
    
    # TAB 4: CA Performance
    with tab4:
        st.header("CA Performance")
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = df_filtered.groupby('user_name_clean').agg({
                'apps_id': 'nunique',
                'Risk_Score': 'mean'
            }).reset_index()
            ca_perf['Total Records'] = df_filtered.groupby('user_name_clean').size().values
            ca_perf.columns = ['CA Name', 'Total Apps', 'Avg Risk', 'Total Records']
            st.dataframe(ca_perf.sort_values('Total Apps', ascending=False), use_container_width=True, hide_index=True)
    
    # TAB 5: Predictive Patterns
    with tab5:
        st.header("Predictive Pattern Recognition")
        st.info("High-Impact Combinations Analysis")
    
    # TAB 6: Trends
    with tab6:
        st.header("Trends & Time-Series Analysis")
        if 'YearMonth' in df_filtered.columns:
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique'
            }).reset_index()
            monthly.columns = ['Month', 'Volume']
            st.dataframe(monthly, use_container_width=True, hide_index=True)
    
    # TAB 7: SLA Transitions
    with tab7:
        st.header("SLA Transitions Analysis")
        st.info("Historical SLA per Status Transition")
        
        if len(df_sla_history_filtered) > 0:
            transition_sla = df_sla_history_filtered.groupby('Transition').agg({
                'apps_id': 'nunique',
                'SLA_Days': ['mean', 'max', 'min']
            }).reset_index()
            transition_sla.columns = ['Transition', 'Total Apps', 'Avg SLA Days', 'Max SLA', 'Min SLA']
            transition_sla['Total Records'] = df_sla_history_filtered.groupby('Transition').size().values
            st.dataframe(transition_sla.sort_values('Total Apps', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No SLA transition data available")
    
    # TAB 8: Duplicates
    with tab8:
        st.header("Duplicate Applications Analysis")
        app_counts = df['apps_id'].value_counts()
        duplicates = app_counts[app_counts > 1]
        
        if len(duplicates) > 0:
            st.info(f"Found {len(duplicates)} duplicate IDs with {duplicates.sum()} total records")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Duplicate IDs", len(duplicates))
            with col2:
                st.metric("Max Records per ID", duplicates.max())
            with col3:
                st.metric("Total Duplicate Records", duplicates.sum())
        else:
            st.success("No duplicate application IDs found")
    
    # TAB 9: Raw Data
    with tab9:
        st.header("Complete Raw Data Export")
        display_cols = [c for c in ['apps_id', 'user_name', 'apps_status', 'Scoring_Detail',
                                     'Outstanding_PH', 'LastOD', 'max_OD'] if c in df_filtered.columns]
        st.dataframe(df_filtered[display_cols], use_container_width=True, height=500)
        
        csv = df_filtered[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button("Download Dataset (CSV)", data=csv,
                          file_name=f"CA_Analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                          mime="text/csv")
    
    st.markdown("---")
    st.markdown(f"<div style='text-align:center;color:#666'>CA Analytics Dashboard | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
