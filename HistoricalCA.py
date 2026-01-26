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
    """Calculate SLA in working days only. Return tuple (days, hours) untuk handling same-day"""
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None, None
    
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
        
        # Hitung hours jika same day (working_days = 1, berarti hanya 1 hari)
        hours = None
        if start_adjusted.date() == end_dt.date():
            # Same day - hitung selisih jam langsung
            hours = (end_dt - start_adjusted).total_seconds() / 3600
            working_days = 0  # Set ke 0 untuk indicate same day
        
        return working_days, hours
    except:
        return None, None

def calculate_historical_sla(df):
    """Calculate SLA per row berdasarkan transition dari row sebelumnya untuk app_id yang sama
    
    Special case: Jika status adalah PENDING CA, SLA dihitung sampai ada value di field Rekomendasi
    """
    df_sorted = df.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
    sla_list = []
    
    for idx, row in df_sorted.iterrows():
        app_id = row['apps_id']
        current_status = row.get('apps_status_clean', 'Unknown')
        current_time = row.get('action_on_parsed')
        rekomendasi = row.get('Rekomendasi')
        
        # Cari row sebelumnya untuk app_id yang sama
        prev_rows = df_sorted[(df_sorted['apps_id'] == app_id) & (df_sorted.index < idx)]
        
        if len(prev_rows) > 0:
            prev_row = prev_rows.iloc[-1]
            prev_status = prev_row.get('apps_status_clean', 'Unknown')
            prev_time = prev_row.get('action_on_parsed')
            
            # Special handling untuk PENDING CA
            if current_status == 'PENDING CA' or current_status == 'Pending CA':
                if pd.isna(rekomendasi) or rekomendasi == '' or rekomendasi == '-':
                    # Belum ada rekomendasi, SLA = None (masih pending)
                    sla_days = None
                    transition = f"{prev_status} → {current_status} (Menunggu Rekomendasi)"
                else:
                    # Ada rekomendasi, hitung SLA
                    sla_days = calculate_sla_days(prev_time, current_time)
                    transition = f"{prev_status} → {current_status} (Rekomendasi: {rekomendasi})"
            else:
                # Status lain, hitung SLA normal
                sla_days = calculate_sla_days(prev_time, current_time)
                transition = f"{prev_status} → {current_status}"
        else:
            # Row pertama untuk app ini, tidak ada transition
            sla_days = None
            transition = f"START → {current_status}"
        
        sla_list.append({
            'idx': idx,
            'apps_id': app_id,
            'Transition': transition,
            'From_Status': prev_status if len(prev_rows) > 0 else 'START',
            'To_Status': current_status,
            'SLA_Days': sla_days,
            'Has_Rekomendasi': not pd.isna(rekomendasi) and rekomendasi != '' and rekomendasi != '-'
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
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Calculate historical SLA per row
    if all(c in df.columns for c in ['apps_id', 'action_on_parsed', 'apps_status_clean']):
        sla_history = calculate_historical_sla(df)
        # Merge SLA ke original dataframe berdasarkan index
        for _, sla_row in sla_history.iterrows():
            if sla_row['idx'] < len(df):
                df.at[sla_row['idx'], 'SLA_Days_Transition'] = sla_row['SLA_Days']
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
    
    # Clean Rekomendasi field (jika ada)
    if 'Rekomendasi' in df.columns:
        df['Rekomendasi'] = df['Rekomendasi'].fillna('').astype(str).str.strip()
    else:
        df['Rekomendasi'] = ''
    
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
                            f"Low approval rate {rate:.1f}% in {osph} segment - "
                            f"Investigate scoring criteria"
                        )
                    elif rate > 60:
                        insights.append(
                            f"Strong approval rate {rate:.1f}% in {osph} segment - "
                            f"Best performing tier"
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
                f"High LastOD (>30 days): {reject_rate:.1f}% rejection rate - "
                f"Strong negative impact on approvals"
            )
    
    # Insight 3: SLA Performance
    if 'SLA_Days' in df.columns and 'apps_status_clean' in df.columns:
        for status in sorted(df['apps_status_clean'].unique())[:5]:
            if status == 'Unknown':
                continue
            
            df_status = df[df['apps_status_clean'] == status]
            sla_avg = df_status['SLA_Days'].mean()
            
            if pd.notna(sla_avg) and sla_avg > 5:
                warnings.append(
                    f"{status}: Average SLA is {sla_avg:.1f} days "
                    f"(above 5-day target)"
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
    
    # Product filter
    if 'Produk_clean' in df.columns:
        all_products = sorted(df['Produk_clean'].unique().tolist())
        selected_product = st.sidebar.selectbox(
            "Product",
            ['All'] + all_products
        )
    else:
        selected_product = 'All'
    
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
    
    if selected_product != 'All':
        df_filtered = df_filtered[
            df_filtered['Produk_clean'] == selected_product
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
        avg_sla = None
        if len(df_sla_history_filtered) > 0 and 'SLA_Days' in df_sla_history_filtered.columns:
            # Ambil kolom pertama yang bukan apps_id
            sla_col = [c for c in df_sla_history_filtered.columns if c != 'apps_id'][0] if len(df_sla_history_filtered.columns) > 1 else None
            if sla_col:
                try:
                    avg_sla = df_sla_history_filtered[sla_col].mean()
                except:
                    avg_sla = None
        
        sla_display = f"{avg_sla:.1f}" if not pd.isna(avg_sla) else "N/A"
        st.metric("Average SLA (days)", sla_display)
    
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
        st.header("Outstanding PH Analysis - 4 Dimensions")
        st.info(
            "Comprehensive analysis of Outstanding PH "
            "with 4 analytical dimensions"
        )
        
        # Dimension 1
        st.subheader("Dimension 1: Outstanding PH vs Scoring Result")
        st.markdown(
            "**Purpose**: Understand scoring decision patterns "
            "across Outstanding PH ranges"
        )
        
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            dim1_data = []
            
            osph_ranges = sorted([
                x for x in df_filtered['OSPH_Category'].unique() 
                if x != 'Unknown'
            ])
            
            for osph in osph_ranges:
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                harga_min = (
                    df_osph['OSPH_clean'].min() 
                    if 'OSPH_clean' in df_osph.columns 
                    else 0
                )
                harga_max = (
                    df_osph['OSPH_clean'].max() 
                    if 'OSPH_clean' in df_osph.columns 
                    else 0
                )
                
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
            scoring_cols = [
                c for c in dim1_df.columns 
                if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', 'Total Records']
            ]
            
            if scoring_cols:
                heatmap_data = dim1_df[['Range'] + scoring_cols].set_index('Range')
                fig = px.imshow(
                    heatmap_data.T,
                    text_auto=True,
                    title="Outstanding PH vs Scoring Result Distribution",
                    labels=dict(
                        x="Outstanding PH Range",
                        y="Scoring Result",
                        color="Count"
                    ),
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Dimension 2
        st.markdown("---")
        st.subheader("Dimension 2: Outstanding PH vs Application Status")
        st.markdown(
            "**Purpose**: Distribution of application status "
            "across Outstanding PH ranges"
        )
        
        if 'OSPH_Category' in df_filtered.columns and 'apps_status_clean' in df_filtered.columns:
            status_data = []
            
            for osph in sorted([
                x for x in df_filtered['OSPH_Category'].unique() 
                if x != 'Unknown'
            ]):
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
            
            status_cols = [
                c for c in status_df.columns 
                if c not in ['Range', 'Total Apps', 'Total Records']
            ]
            
            if status_cols:
                heatmap_status = status_df[['Range'] + status_cols].set_index('Range')
                fig = px.imshow(
                    heatmap_status.T,
                    text_auto=True,
                    title="Outstanding PH vs Application Status",
                    labels=dict(
                        x="Outstanding PH Range",
                        y="Application Status",
                        color="Count"
                    ),
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Dimension 3
        st.markdown("---")
        st.subheader("Dimension 3: Outstanding PH vs Job Type (Pekerjaan)")
        st.markdown(
            "**Purpose**: Occupation profile across Outstanding PH ranges"
        )
        
        if 'OSPH_Category' in df_filtered.columns and 'Pekerjaan_clean' in df_filtered.columns:
            dim3_data = []
            all_pekerjaan = sorted([
                x for x in df_filtered['Pekerjaan_clean'].unique() 
                if x != 'Unknown'
            ])
            
            for osph in sorted([
                x for x in df_filtered['OSPH_Category'].unique() 
                if x != 'Unknown'
            ]):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                harga_min = (
                    df_osph['OSPH_clean'].min() 
                    if 'OSPH_clean' in df_osph.columns 
                    else 0
                )
                harga_max = (
                    df_osph['OSPH_clean'].max() 
                    if 'OSPH_clean' in df_osph.columns 
                    else 0
                )
                
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
            
            pekerjaan_cols = [
                c for c in dim3_df.columns 
                if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', 'Total Records']
            ]
            
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
        st.subheader(
            "Dimension 4: Outstanding PH vs Vehicle Type "
            "(Mb. Beban / Mb. Penumpang)"
        )
        st.markdown(
            "**Purpose**: Vehicle preference and risk profile "
            "by Outstanding PH range"
        )
        
        if 'OSPH_Category' in df_filtered.columns and 'JenisKendaraan_clean' in df_filtered.columns:
            dim4_data = []
            
            for osph in sorted([
                x for x in df_filtered['OSPH_Category'].unique() 
                if x != 'Unknown'
            ]):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                harga_min = (
                    df_osph['OSPH_clean'].min() 
                    if 'OSPH_clean' in df_osph.columns 
                    else 0
                )
                harga_max = (
                    df_osph['OSPH_clean'].max() 
                    if 'OSPH_clean' in df_osph.columns 
                    else 0
                )
                
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
            
            vehicle_cols = [
                c for c in dim4_df.columns 
                if c not in ['Range', 'Min Value', 'Max Value', 'Total Apps', 'Total Records']
            ]
            
            if vehicle_cols:
                fig = px.bar(
                    dim4_df,
                    x='Range',
                    y=vehicle_cols,
                    title="Vehicle Type Distribution by Outstanding PH Range",
                    barmode='group'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: OD Impact Analysis
    with tab2:
        st.header("OD Impact Analysis - LastOD & max_OD")
        st.info(
            "Analysis of how Overdue Days (OD) impact scoring "
            "decisions and risk profiles"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("LastOD Analysis")
            st.markdown(
                "**Purpose**: Understand LastOD impact on approval rates"
            )
            
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
                        approve = df_od['Scoring_Detail'].isin(
                            ['APPROVE', 'APPROVE 1', 'APPROVE 2']
                        ).sum()
                        
                        reject = df_od['Scoring_Detail'].isin(
                            ['REJECT', 'REJECT 1', 'REJECT 2']
                        ).sum()
                        
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = (
                            f"{approve/total*100:.1f}%" 
                            if total > 0 
                            else "-"
                        )
                        
                        avg_risk = (
                            f"{df_od['Risk_Score'].mean():.1f}" 
                            if df_od['Risk_Score'].notna().any() 
                            else "-"
                        )
                        
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
            st.markdown(
                "**Purpose**: Understand max_OD impact on approval rates"
            )
            
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
                        approve = df_od['Scoring_Detail'].isin(
                            ['APPROVE', 'APPROVE 1', 'APPROVE 2']
                        ).sum()
                        
                        reject = df_od['Scoring_Detail'].isin(
                            ['REJECT', 'REJECT 1', 'REJECT 2']
                        ).sum()
                        
                        total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                        
                        approval_pct = (
                            f"{approve/total*100:.1f}%" 
                            if total > 0 
                            else "-"
                        )
                        
                        avg_risk = (
                            f"{df_od['Risk_Score'].mean():.1f}" 
                            if df_od['Risk_Score'].notna().any() 
                            else "-"
                        )
                        
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
        st.markdown(
            "**Purpose**: Identify if customer OD is improving or worsening"
        )
        
        if 'LastOD_clean' in df_filtered.columns and 'max_OD_clean' in df_filtered.columns:
            df_filtered['OD_Trend'] = (
                df_filtered['LastOD_clean'] - df_filtered['max_OD_clean']
            )
            
            df_filtered['OD_Trend_Category'] = pd.cut(
                df_filtered['OD_Trend'],
                bins=[-np.inf, -10, -1, 0, 10, np.inf],
                labels=[
                    'Significant Improvement',
                    'Slight Improvement',
                    'Stable',
                    'Slight Worsening',
                    'Significant Worsening'
                ]
            )
            
            trend_analysis = df_filtered.groupby('OD_Trend_Category').agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (
                    x.isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum() / 
                    len(x[x != '(Pilih Semua)']) * 100
                ) if len(x[x != '(Pilih Semua)']) > 0 else 0,
                'Risk_Score': 'mean'
            }).reset_index()
            
            trend_analysis.columns = [
                'OD Trend',
                'Total Apps',
                'Approval %',
                'Avg Risk'
            ]
            
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
    
    # Tab 3: Status & Scoring Matrix
    with tab3:
        st.header("Status & Scoring Matrix")
        st.info(
            "Complete cross-tabulation of application status "
            "and scoring results"
        )
        
        st.subheader("Cross-Tabulation Matrix")
        st.markdown(
            "**Purpose**: See relationship between status and scoring outcome"
        )
        
        if 'apps_status_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            cross_tab = pd.crosstab(
                df_filtered['apps_status_clean'],
                df_filtered['Scoring_Detail'],
                margins=True,
                margins_name='TOTAL'
            )
            st.dataframe(cross_tab, use_container_width=True)
            
            cross_tab_no_total = cross_tab.drop('TOTAL', errors='ignore').drop(
                'TOTAL',
                axis=1,
                errors='ignore'
            )
            
            if len(cross_tab_no_total) > 0:
                fig = px.imshow(
                    cross_tab_no_total,
                    text_auto=True,
                    title="Application Status vs Scoring Result Heatmap",
                    labels=dict(
                        x="Scoring Result",
                        y="Application Status",
                        color="Count"
                    ),
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Application Status Summary")
            st.markdown(
                "**Metrics per Status**: Total Apps, Total Records, and Risk"
            )
            
            if 'apps_status_clean' in df_filtered.columns:
                status_detail = df_filtered.groupby('apps_status_clean').agg({
                    'apps_id': 'nunique'
                }).reset_index()
                
                status_detail.insert(2, 'Total Records', df_filtered.groupby('apps_status_clean').size().values)
                status_detail.insert(3, 'Avg Risk', df_filtered.groupby('apps_status_clean')['Risk_Score'].mean().values)
                
                status_detail.columns = [
                    'Status',
                    'Total Apps',
                    'Total Records',
                    'Avg Risk'
                ]
                
                status_detail = status_detail.sort_values(
                    'Total Apps',
                    ascending=False
                )
                
                st.dataframe(status_detail, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Scoring Result Summary")
            st.markdown(
                "**Distribution of Scoring Outcomes with Apps & Records**"
            )
            
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
                st.dataframe(
                    scoring_df,
                    use_container_width=True,
                    hide_index=True
                )
    
    # Tab 4: CA Performance
    with tab4:
        st.header("CA Performance Analytics")
        st.info(
            "Individual CA performance metrics and comparison"
        )
        
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = []
            
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                approve = df_ca['Scoring_Detail'].isin(
                    ['APPROVE', 'APPROVE 1', 'APPROVE 2']
                ).sum()
                
                reject = df_ca['Scoring_Detail'].isin(
                    ['REJECT', 'REJECT 1', 'REJECT 2']
                ).sum()
                
                total_scored = len(
                    df_ca[df_ca['Scoring_Detail'] != '(Pilih Semua)']
                )
                
                other = total_scored - approve - reject
                
                avg_risk = (
                    f"{df_ca['Risk_Score'].mean():.0f}" 
                    if df_ca['Risk_Score'].notna().any() 
                    else "-"
                )
                
                approval_pct = (
                    f"{approve/total_scored*100:.1f}%" 
                    if total_scored > 0 
                    else "-"
                )
                
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
            
            ca_df = pd.DataFrame(ca_perf).sort_values(
                'Total Apps',
                ascending=False
            )
            
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
                ca_df_plot['Approval_num'] = ca_df_plot['Approval %'].str.replace(
                    '%', ''
                ).replace('-', '0').astype(float)
                
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
    
    # Tab 5: Predictive Patterns
    with tab5:
        st.header("Predictive Pattern Recognition")
        st.info(
            "Identification of patterns that predict "
            "approval or rejection outcomes"
        )
        
        st.subheader(
            "High-Impact Combinations: "
            "Outstanding PH + OD Segment + Job Type"
        )
        st.markdown(
            "**Purpose**: Find best and worst segment combinations"
        )
        
        if all(c in df_filtered.columns for c in [
            'OSPH_Category', 'LastOD_clean', 'Pekerjaan_clean', 'Scoring_Detail'
        ]):
            df_filtered['LastOD_Segment'] = pd.cut(
                df_filtered['LastOD_clean'],
                bins=[-np.inf, 0, 30, np.inf],
                labels=['No OD', 'OD 1-30', 'OD >30']
            )
            
            pattern_analysis = df_filtered.groupby([
                'OSPH_Category',
                'LastOD_Segment',
                'Pekerjaan_clean'
            ]).agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (
                    x.isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum() / 
                    len(x[x != '(Pilih Semua)']) * 100
                ) if len(x[x != '(Pilih Semua)']) > 0 else 0
            }).reset_index()
            
            pattern_analysis['Total Records'] = df_filtered.groupby([
                'OSPH_Category',
                'LastOD_Segment',
                'Pekerjaan_clean'
            ]).size().values
            
            pattern_analysis.columns = [
                'Outstanding PH',
                'OD Segment',
                'Job Type',
                'Total Apps',
                'Approval %',
                'Total Records'
            ]
            
            pattern_analysis = pattern_analysis.sort_values(
                'Total Apps',
                ascending=False
            ).head(15)
            
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
    
    # Tab 6: Trends & Forecasting
    with tab6:
        st.header("Trends & Time-Series Analysis")
        st.info(
            "Monthly trends in volume, SLA, and approval rates"
        )
        
        if 'YearMonth' in df_filtered.columns:
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'Scoring_Detail': lambda x: (
                    x.isin(['APPROVE', 'APPROVE 1', 'APPROVE 2']).sum() /
                    len(x[x != '(Pilih Semua)']) * 100
                ) if len(x[x != '(Pilih Semua)']) > 0 else 0
            }).reset_index()
            
            monthly['Total Records'] = df_filtered.groupby('YearMonth').size().values
            monthly.columns = ['Month', 'Volume', 'Approval %', 'Total Records']
            
            st.subheader("Monthly Performance Metrics")
            st.dataframe(monthly, use_container_width=True, hide_index=True)
            
            fig = make_subplots(
                specs=[[{"secondary_y": True}]]
            )
            
            fig.add_trace(
                go.Bar(
                    x=monthly['Month'],
                    y=monthly['Volume'],
                    name="Application Volume"
                ),
                secondary_y=False
            )
            
            fig.add_trace(
                go.Scatter(
                    x=monthly['Month'],
                    y=monthly['Approval %'],
                    name="Approval Rate %",
                    mode='lines+markers'
                ),
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
    
    # Tab 7: SLA Transitions
    with tab7:
        st.header("SLA Transitions Analysis - Pivot by App ID")
        st.info("Lihat historical status dan SLA untuk setiap app_id. Status urutan fixed: NOT RECOMMENDED CA → PENDING CA → Pending CA Completed → RECOMMENDED CA → RECOMMENDED CA WITH COND")
        
        if 'apps_id' in df_filtered.columns and 'action_on_parsed' in df_filtered.columns:
            # Define status order
            status_order = [
                'NOT RECOMMENDED CA',
                'PENDING CA',
                'Pending CA Completed',
                'RECOMMENDED CA',
                'RECOMMENDED CA WITH COND'
            ]
            
            df_filtered_sorted = df_filtered.sort_values(['apps_id', 'action_on_parsed']).reset_index(drop=True)
            sla_transitions = []
            
            for idx, row in df_filtered_sorted.iterrows():
                app_id = row['apps_id']
                current_status = row.get('apps_status_clean', 'Unknown')
                current_time = row.get('action_on_parsed')
                realisasi_date = row.get('RealisasiDate_parsed')
                rekomendasi = row.get('Rekomendasi', '')
                action_on = row.get('action_on', '')
                
                # Cari row sebelumnya untuk app_id yang sama
                prev_rows = df_filtered_sorted[(df_filtered_sorted['apps_id'] == app_id) & (df_filtered_sorted.index < idx)]
                
                if len(prev_rows) > 0:
                    prev_row = prev_rows.iloc[-1]
                    prev_status = prev_row.get('apps_status_clean', 'Unknown')
                    prev_time = prev_row.get('action_on_parsed')
                    
                    # Hitung SLA dengan special rules
                    sla_days = None
                    
                    # PENDING CA: hanya hitung jika ada Rekomendasi
                    if current_status == 'PENDING CA' or current_status == 'Pending CA':
                        if not pd.isna(rekomendasi) and rekomendasi != '' and rekomendasi != '-':
                            sla_days = calculate_sla_days(prev_time, current_time)
                    
                    # Pending Ca Completed: hitung normal
                    elif current_status == 'Pending Ca Completed':
                        sla_days = calculate_sla_days(prev_time, current_time)
                    
                    # RECOMMENDED CA atau RECOMMENDED CA WITH COND: hanya jika ada RealisasiDate
                    elif current_status in ['RECOMMENDED CA', 'RECOMMENDED CA WITH COND']:
                        if not pd.isna(realisasi_date):
                            sla_days = calculate_sla_days(prev_time, current_time)
                    
                    # Status lain: hitung normal
                    else:
                        sla_days = calculate_sla_days(prev_time, current_time)
                    
                    transition = f"{prev_status} → {current_status}"
                else:
                    sla_days = None
                    transition = f"START → {current_status}"
                
                sla_transitions.append({
                    'apps_id': app_id,
                    'from_status': prev_status if len(prev_rows) > 0 else 'START',
                    'to_status': current_status,
                    'transition': transition,
                    'action_on': action_on,
                    'sla_days': sla_days,
                    'realisasi_date': row.get('RealisasiDate'),
                    'rekomendasi': rekomendasi
                })
            
            sla_df = pd.DataFrame(sla_transitions)
            
            # Buat pivot table dengan urutan status yang fixed
            st.subheader("Pivot Table: App ID → Historical Status & SLA")
            
            pivot_data = []
            for app_id in sorted(sla_df['apps_id'].unique()):
                app_data = sla_df[sla_df['apps_id'] == app_id]
                row_data = {'App ID': app_id}
                
                # Get all transitions untuk app ini
                for idx, trans_row in app_data.iterrows():
                    trans_label = trans_row['transition']
                    sla_val = trans_row['sla_days']
                    
                    # Format SLA value
                    if pd.isna(sla_val):
                        sla_display = '—'
                    else:
                        sla_display = f"{int(sla_val)}d"
                    
                    row_data[trans_label] = sla_display
                
                pivot_data.append(row_data)
            
            pivot_df = pd.DataFrame(pivot_data)
            
            # Tampilkan pivot table
            st.dataframe(pivot_df, use_container_width=True, hide_index=True)
            
            # Summary statistics per transition
            st.markdown("---")
            st.subheader("SLA Statistics per Transition")
            
            stats_data = []
            for transition in sorted(sla_df['transition'].unique()):
                trans_sla = sla_df[sla_df['transition'] == transition]['sla_days']
                trans_valid = trans_sla.dropna()
                total_trans = len(sla_df[sla_df['transition'] == transition])
                
                stats_data.append({
                    'Transition': transition,
                    'Total Records': total_trans,
                    'SLA Valid': len(trans_valid),
                    'SLA N/A': total_trans - len(trans_valid),
                    'Avg SLA (days)': f"{trans_valid.mean():.1f}" if len(trans_valid) > 0 else 'N/A',
                    'Min': f"{int(trans_valid.min())}" if len(trans_valid) > 0 else 'N/A',
                    'Max': f"{int(trans_valid.max())}" if len(trans_valid) > 0 else 'N/A',
                    'Median': f"{int(trans_valid.median())}" if len(trans_valid) > 0 else 'N/A'
                })
            
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
            
            # Visualization
            st.markdown("---")
            st.subheader("Average SLA per Transition")
            
            chart_data = sla_df[sla_df['sla_days'].notna()].groupby('transition').agg({
                'sla_days': ['mean', 'count']
            }).reset_index()
            chart_data.columns = ['Transition', 'Avg SLA', 'Count']
            
            if len(chart_data) > 0:
                fig = px.bar(
                    chart_data,
                    x='Transition',
                    y='Avg SLA',
                    color='Count',
                    title="Average SLA per Status Transition",
                    labels={'Avg SLA': 'Average SLA (Days)', 'Transition': 'Status Transition', 'Count': 'Valid Records'},
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(xaxis_tickangle=-45, height=500)
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 8: Duplicate Applications
    with tab8:
        st.header("Duplicate Applications Analysis")
        st.markdown(
            "**Historical Data Context**: This dataset contains multiple "
            "records for the same application ID, representing historical "
            "tracking, status updates, and workflow progression through "
            "the CA evaluation process."
        )
        
        if 'apps_id' in df.columns:
            app_counts = df['apps_id'].value_counts()
            duplicates = app_counts[app_counts > 1]
            
            if len(duplicates) > 0:
                st.info(
                    f"Found {len(duplicates)} duplicate application IDs with "
                    f"{duplicates.sum()} total duplicate records"
                )
                
                duplicate_ids = duplicates.index.tolist()
                dup_records = df[df['apps_id'].isin(duplicate_ids)].sort_values(
                    'apps_id'
                )
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Duplicate IDs", len(duplicates))
                
                with col2:
                    st.metric("Max Records per ID", duplicates.max())
                
                with col3:
                    st.metric("Total Duplicate Records", duplicates.sum())
                
                with col4:
                    avg_records = duplicates.mean()
                    st.metric("Avg Records per ID", f"{avg_records:.1f}")
                
                # Duplicate distribution by status
                st.subheader("Duplicate Apps by Status")
                dup_status = dup_records.groupby('apps_status_clean').agg({
                    'apps_id': 'nunique'
                }).reset_index()
                dup_status.columns = ['Status', 'Total Duplicate Apps']
                dup_status['Total Records'] = dup_records.groupby('apps_status_clean').size().values
                st.dataframe(dup_status.sort_values('Total Duplicate Apps', ascending=False), use_container_width=True, hide_index=True)
                
                # Duplicate distribution by scoring
                st.subheader("Duplicate Apps by Scoring")
                dup_scoring = dup_records.groupby('Scoring_Detail').agg({
                    'apps_id': 'nunique'
                }).reset_index()
                dup_scoring.columns = ['Scoring', 'Total Duplicate Apps']
                dup_scoring['Total Records'] = dup_records.groupby('Scoring_Detail').size().values
                st.dataframe(dup_scoring.sort_values('Total Duplicate Apps', ascending=False), use_container_width=True, hide_index=True)
                
                # Detailed records
                st.markdown("---")
                st.subheader("Duplicate Application Records Detail")
                
                display_cols = [
                    'apps_id', 'user_name', 'apps_status', 'Scoring_Detail',
                    'action_on', 'RealisasiDate', 'Outstanding_PH', 'SLA_Days'
                ]
                
                avail_cols = [c for c in display_cols if c in dup_records.columns]
                
                st.dataframe(
                    dup_records[avail_cols].sort_values('apps_id'),
                    use_container_width=True,
                    height=600
                )
                
                # Distribution chart
                st.markdown("---")
                st.subheader("Distribution of Duplicate Counts")
                st.markdown(
                    "**How many applications appear N times**"
                )
                
                dup_dist = duplicates.value_counts().sort_index()
                fig = px.bar(
                    x=dup_dist.index,
                    y=dup_dist.values,
                    labels={
                        'x': 'Number of Records per Application',
                        'y': 'Count of Application IDs'
                    },
                    title="Duplicate Applications Frequency Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("No duplicate application IDs found in the dataset")
    
    # Tab 9: Raw Data
    with tab9:
        st.header("Complete Raw Data Export")
        st.info("Full dataset with all processed fields")
        
        display_cols = [
            'apps_id', 'position_name', 'user_name', 'apps_status',
            'desc_status_apps', 'Produk', 'action_on', 'Initiation',
            'RealisasiDate', 'Outstanding_PH', 'Pekerjaan', 'Jabatan',
            'Pekerjaan_Pasangan', 'Hasil_Scoring', 'JenisKendaraan',
            'branch_name', 'Tujuan_Kredit', 'LastOD', 'max_OD',
            'OSPH_clean', 'OSPH_Category', 'Scoring_Detail',
            'SLA_Days', 'Risk_Score', 'Risk_Category'
        ]
        
        avail_cols = [c for c in display_cols if c in df_filtered.columns]
        
        st.subheader("Filtered Dataset")
        st.dataframe(
            df_filtered[avail_cols],
            use_container_width=True,
            height=500
        )
        
        csv = df_filtered[avail_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Dataset (CSV)",
            data=csv,
            file_name=f"CA_Analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#666'>"
        f"CA Analytics Dashboard | "
        f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
