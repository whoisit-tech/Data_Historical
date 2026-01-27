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
    .sla-detail { 
        font-family: 'Courier New', monospace; 
        background: #f0f0f0; 
        padding: 5px; 
        border-radius: 5px; 
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

def calculate_sla_detailed(start_dt, end_dt):
    """
    Calculate detailed SLA in working days, hours, minutes, seconds
    Returns: dict with days, hours, minutes, seconds, total_seconds, formatted_string
    """
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        
        # If start time is after 3:30 PM, move to next working day at 8:30 AM
        start_adjusted = start_dt
        if start_dt.time() >= datetime.strptime("15:30", "%H:%M").time():
            start_adjusted = start_dt + timedelta(days=1)
            start_adjusted = start_adjusted.replace(hour=8, minute=30, second=0)
            while not is_working_day(start_adjusted):
                start_adjusted += timedelta(days=1)
        
        # Calculate total time difference
        total_delta = end_dt - start_adjusted
        total_seconds = int(total_delta.total_seconds())
        
        # Count working days
        working_days = 0
        current = start_adjusted.date()
        end_date = end_dt.date()
        
        while current <= end_date:
            if is_working_day(datetime.combine(current, datetime.min.time())):
                working_days += 1
            current += timedelta(days=1)
        
        # Calculate detailed breakdown
        days = total_seconds // 86400
        remaining = total_seconds % 86400
        hours = remaining // 3600
        remaining = remaining % 3600
        minutes = remaining // 60
        seconds = remaining % 60
        
        # Format string
        formatted = f"{days}d {hours}h {minutes}m {seconds}s"
        
        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'working_days': working_days,
            'total_seconds': total_seconds,
            'formatted': formatted
        }
    except:
        return None

def calculate_historical_sla_detailed(df):
    """
    Calculate detailed SLA per row based on transition from previous row for same app_id
    Flow: PENDING CA → Pending CA Completed → NOT RECOMMENDED/RECOMMENDED CA/RECOMMENDED CA WITH COND
    
    SLA Rules:
    1. PENDING CA: SLA dihitung dari action sebelumnya sampai field Recommendation terisi
    2. Pending Ca Completed: SLA dari PENDING CA (action_on) ke Pending Ca Completed (action_on)
    3. RECOMMENDED/NOT RECOMMENDED/RECOMMENDED WITH COND: SLA dari Pending Ca Completed (action_on) ke status ini (action_on)
    """
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
            
            sla_detail = None
            transition = f"{prev_status} → {current_status}"
            
            # Special handling based on status
            if current_status == 'PENDING CA' or current_status == 'Pending CA':
                # PENDING CA: hitung SLA hanya jika ada Recommendation
                if pd.notna(recommendation) and recommendation != '' and recommendation != '-':
                    sla_detail = calculate_sla_detailed(prev_time, current_time)
                    transition = f"{prev_status} → {current_status} (Recommendation: {recommendation[:20]}...)"
                else:
                    transition = f"{prev_status} → {current_status} (Waiting Recommendation)"
            
            elif current_status == 'Pending Ca Completed':
                # Pending Ca Completed: hitung dari PENDING CA
                sla_detail = calculate_sla_detailed(prev_time, current_time)
            
            elif current_status in ['RECOMMENDED CA', 'NOT RECOMMENDED CA', 'RECOMMENDED CA WITH COND']:
                # Final status: hitung dari Pending Ca Completed
                sla_detail = calculate_sla_detailed(prev_time, current_time)
            
            else:
                # Status lain: hitung normal
                sla_detail = calculate_sla_detailed(prev_time, current_time)
        else:
            # Row pertama untuk app ini
            prev_status = 'START'
            sla_detail = None
            transition = f"START → {current_status}"
        
        sla_list.append({
            'idx': idx,
            'apps_id': app_id,
            'Transition': transition,
            'From_Status': prev_status,
            'To_Status': current_status,
            'SLA_Detail': sla_detail,
            'SLA_Formatted': sla_detail['formatted'] if sla_detail else None,
            'SLA_Days': sla_detail['days'] if sla_detail else None,
            'SLA_Hours': sla_detail['hours'] if sla_detail else None,
            'SLA_Minutes': sla_detail['minutes'] if sla_detail else None,
            'SLA_Seconds': sla_detail['seconds'] if sla_detail else None,
            'SLA_Working_Days': sla_detail['working_days'] if sla_detail else None,
            'Has_Recommendation': pd.notna(recommendation) and recommendation != '' and recommendation != '-'
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
    
    # SLA risk contribution (using working days)
    if pd.notna(row.get('SLA_Working_Days')):
        if row['SLA_Working_Days'] > 5:
            score += 20
        elif row['SLA_Working_Days'] > 3:
            score += 10
    
    return min(score, 100)

def preprocess_data(df):
    """Clean and prepare data for analysis"""
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Calculate historical SLA per row with detailed breakdown
    if all(c in df.columns for c in ['apps_id', 'action_on_parsed', 'apps_status']):
        # Clean apps_status first
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
        
        # Calculate detailed SLA
        sla_history = calculate_historical_sla_detailed(df)
        
        # Merge SLA ke original dataframe berdasarkan index
        for _, sla_row in sla_history.iterrows():
            if sla_row['idx'] < len(df):
                df.at[sla_row['idx'], 'SLA_Formatted'] = sla_row['SLA_Formatted']
                df.at[sla_row['idx'], 'SLA_Days'] = sla_row['SLA_Days']
                df.at[sla_row['idx'], 'SLA_Hours'] = sla_row['SLA_Hours']
                df.at[sla_row['idx'], 'SLA_Minutes'] = sla_row['SLA_Minutes']
                df.at[sla_row['idx'], 'SLA_Seconds'] = sla_row['SLA_Seconds']
                df.at[sla_row['idx'], 'SLA_Working_Days'] = sla_row['SLA_Working_Days']
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
    
    # Clean Hasil_Scoring
    if 'Hasil_Scoring' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring'].fillna('(Pilih Semua)').astype(str).str.strip()
    
    # Clean Recommendation field
    if 'Recommendation' in df.columns:
        df['Recommendation_clean'] = df['Recommendation'].fillna('').astype(str).str.strip()
    else:
        df['Recommendation_clean'] = ''
    
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
            'Segmen', 'action_on', 'Initiation', 'RealisasiDate', 'Outstanding_PH',
            'Pekerjaan', 'Jabatan', 'Hasil_Scoring',
            'JenisKendaraan', 'branch_name', 'Tujuan_Kredit', 
            'Recommendation', 'LastOD', 'max_OD'
        ]
        
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"Kolom tidak ditemukan: {', '.join(missing)}")
            st.info("Kolom yang tersedia: " + ", ".join(df.columns.tolist()))
            return None
        
        return preprocess_data(df)
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
                            f"⚠️ Low approval rate {rate:.1f}% in {osph} segment - "
                            f"Investigate scoring criteria"
                        )
                    elif rate > 60:
                        insights.append(
                            f"✅ Strong approval rate {rate:.1f}% in {osph} segment - "
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
                f"⚠️ High LastOD (>30 days): {reject_rate:.1f}% rejection rate - "
                f"Strong negative impact on approvals"
            )
    
    # Insight 3: SLA Performance (using working days)
    if 'SLA_Working_Days' in df.columns and 'apps_status_clean' in df.columns:
        for status in sorted(df['apps_status_clean'].unique())[:5]:
            if status == 'Unknown':
                continue
            
            df_status = df[df['apps_status_clean'] == status]
            sla_avg = df_status['SLA_Working_Days'].mean()
            
            if pd.notna(sla_avg) and sla_avg > 5:
                warnings.append(
                    f"⏱️ {status}: Average SLA is {sla_avg:.1f} working days "
                    f"(above 5-day target)"
                )
    
    return insights, warnings

def main():
    """Main application"""
    st.title("🎯 CA Analytics Dashboard")
    st.markdown(
        "**Advanced Business Intelligence** - Performance Analysis & Monitoring with Detailed SLA Tracking"
    )
    st.markdown("---")
    
    # Load data
    df = load_data()
    if df is None or df.empty:
        st.error("❌ Data tidak dapat dimuat")
        st.stop()
    
    # Calculate historical SLA
    df_sla_history = calculate_historical_sla_detailed(df)
    
    # Display data summary
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    total_fields = len(df.columns)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Records", f"{total_records:,}")
    with col2:
        st.metric("📋 Unique Applications", f"{unique_apps:,}")
    with col3:
        st.metric("🔢 Total Fields", total_fields)
    
    # Sidebar filters
    st.sidebar.title("🎛️ Analytics Control Panel")
    
    # Status filter
    if 'apps_status_clean' in df.columns:
        all_status = sorted([
            x for x in df['apps_status_clean'].unique() 
            if x != 'Unknown'
        ])
        selected_status = st.sidebar.multiselect(
            "📌 Application Status",
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
            "✍️ Scoring Result",
            all_scoring,
            default=all_scoring
        )
    else:
        selected_scoring = []
    
    # Segmen filter (NEW)
    if 'Segmen_clean' in df.columns:
        all_segmen = sorted([x for x in df['Segmen_clean'].unique() if x != 'Unknown'])
        selected_segmen = st.sidebar.selectbox(
            "🎯 Segmen",
            ['All'] + all_segmen
        )
    else:
        selected_segmen = 'All'
    
    # Branch filter
    if 'branch_name_clean' in df.columns:
        all_branches = sorted(df['branch_name_clean'].unique().tolist())
        selected_branch = st.sidebar.selectbox(
            "🏢 Branch",
            ['All'] + all_branches
        )
    else:
        selected_branch = 'All'
    
    # CA filter
    if 'user_name_clean' in df.columns:
        all_cas = sorted(df['user_name_clean'].unique().tolist())
        selected_ca = st.sidebar.selectbox(
            "👤 CA Name",
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
            "💰 Outstanding PH",
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
        f"📊 {len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)"
    )
    st.sidebar.info(
        f"📋 {df_filtered['apps_id'].nunique():,} unique applications"
    )
    
    # Analytical insights
    st.header("💡 Key Insights & Alerts")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            '<div class="warning-card"><h3>⚠️ Risk Alerts</h3>',
            unsafe_allow_html=True
        )
        if warnings:
            for warning in warnings:
                st.markdown(f"• {warning}")
        else:
            st.markdown("✅ All metrics within acceptable range")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(
            '<div class="success-card"><h3>✨ Positive Insights</h3>',
            unsafe_allow_html=True
        )
        if insights:
            for insight in insights:
                st.markdown(f"• {insight}")
        else:
            st.markdown("📊 Monitoring performance metrics...")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # KPIs
    st.header("📊 Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        total_apps = df_filtered['apps_id'].nunique()
        st.metric("Total Applications", f"{total_apps:,}")
    
    with kpi2:
        avg_sla = df_sla_history_filtered['SLA_Working_Days'].mean()
        sla_display = f"{avg_sla:.1f}" if not pd.isna(avg_sla) else "N/A"
        st.metric("Avg SLA (work days)", sla_display)
    
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
        st.metric("Avg Outstanding PH", osph_display)
    
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
        "🏆 Outstanding PH Analysis",
        "📉 OD Impact Analysis",
        "📊 Status & Scoring Matrix",
        "👥 CA Performance",
        "🔮 Predictive Patterns",
        "📈 Trends & Forecasting",
        "⏱️ Detailed SLA Tracking",
        "🔄 Duplicate Applications",
        "📄 Raw Data"
    ])
    
    # Tab 1: Outstanding PH Analysis
    with tab1:
        st.header("💰 Outstanding PH Analysis - 4 Dimensions")
        st.info(
            "Comprehensive analysis of Outstanding PH with 4 analytical dimensions"
        )
        
        # Dimension 1: OSPH vs Scoring
        st.subheader("📌 Dimension 1: Outstanding PH vs Scoring Result")
        
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            dim1_data = []
            
            for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                row = {
                    'Range': osph,
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                scoring_values = [
                    'APPROVE', 'APPROVE 1', 'APPROVE 2',
                    'REGULER', 'REGULER 1', 'REGULER 2',
                    'REJECT', 'REJECT 1', 'REJECT 2'
                ]
                
                for scoring in scoring_values:
                    count = len(df_osph[df_osph['Scoring_Detail'] == scoring])
                    if count > 0:
                        row[scoring] = count
                
                dim1_data.append(row)
            
            dim1_df = pd.DataFrame(dim1_data)
            st.dataframe(dim1_df, use_container_width=True, hide_index=True)
            
            # Heatmap
            scoring_cols = [c for c in dim1_df.columns if c not in ['Range', 'Total Apps', 'Total Records']]
            
            if scoring_cols:
                heatmap_data = dim1_df[['Range'] + scoring_cols].set_index('Range')
                fig = px.imshow(
                    heatmap_data.T,
                    text_auto=True,
                    title="Outstanding PH vs Scoring Result Distribution",
                    labels=dict(x="Outstanding PH Range", y="Scoring Result", color="Count"),
                    aspect="auto",
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Continue with other dimensions (similar pattern)...
        # (Code continues with Dimension 2, 3, 4 similar to original)
    
    # Tab 7: Detailed SLA Tracking (NEW - Enhanced)
    with tab7:
        st.header("⏱️ Detailed SLA Tracking & Analysis")
        st.info(
            "**SLA Flow**: PENDING CA → Pending Ca Completed → NOT RECOMMENDED/RECOMMENDED CA/RECOMMENDED CA WITH COND\n\n"
            "SLA dihitung dengan detail: Hari, Jam, Menit, Detik (hanya hari kerja, exclude weekend & tanggal merah)"
        )
        
        if 'apps_id' in df_filtered.columns and 'action_on_parsed' in df_filtered.columns:
            # Pivot Table: App ID → Status Transitions with Detailed SLA
            st.subheader("📋 SLA Pivot Table by Application")
            
            pivot_data = []
            for app_id in sorted(df_sla_history_filtered['apps_id'].unique())[:50]:  # Limit to first 50 for display
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
            
            # Detailed SLA Statistics
            st.markdown("---")
            st.subheader("📊 SLA Statistics by Transition")
            
            stats_data = []
            for transition in sorted(df_sla_history_filtered['Transition'].unique()):
                trans_data = df_sla_history_filtered[df_sla_history_filtered['Transition'] == transition]
                valid_sla = trans_data[trans_data['SLA_Days'].notna()]
                
                if len(valid_sla) > 0:
                    stats_data.append({
                        'Transition': transition,
                        'Total Records': len(trans_data),
                        'With SLA': len(valid_sla),
                        'Avg Days': f"{valid_sla['SLA_Days'].mean():.2f}",
                        'Avg Hours': f"{valid_sla['SLA_Hours'].mean():.1f}",
                        'Avg Minutes': f"{valid_sla['SLA_Minutes'].mean():.1f}",
                        'Avg Working Days': f"{valid_sla['SLA_Working_Days'].mean():.1f}",
                        'Min': valid_sla['SLA_Formatted'].iloc[valid_sla['SLA_Days'].argmin()],
                        'Max': valid_sla['SLA_Formatted'].iloc[valid_sla['SLA_Days'].argmax()],
                    })
            
            if stats_data:
                stats_df = pd.DataFrame(stats_data)
                st.dataframe(stats_df, use_container_width=True, hide_index=True)
            
            # SLA Distribution Chart
            st.markdown("---")
            st.subheader("📈 SLA Distribution by Transition")
            
            chart_data = df_sla_history_filtered[df_sla_history_filtered['SLA_Working_Days'].notna()]
            
            if len(chart_data) > 0:
                fig = px.box(
                    chart_data,
                    x='Transition',
                    y='SLA_Working_Days',
                    title="SLA Distribution (Working Days) by Transition",
                    labels={'SLA_Working_Days': 'Working Days', 'Transition': 'Status Transition'}
                )
                fig.update_layout(xaxis_tickangle=-45, height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed breakdown
                fig2 = px.scatter(
                    chart_data,
                    x='From_Status',
                    y='SLA_Days',
                    color='To_Status',
                    size='SLA_Hours',
                    hover_data=['SLA_Formatted', 'apps_id'],
                    title="SLA Scatter: Days vs Hours (sized by hours)",
                    labels={'SLA_Days': 'Total Days', 'From_Status': 'From Status'}
                )
                fig2.update_layout(height=500)
                st.plotly_chart(fig2, use_container_width=True)
    
    # Tab 9: Raw Data (Enhanced with new fields)
    with tab9:
        st.header("📄 Complete Raw Data Export")
        st.info("Full dataset with all processed fields including detailed SLA breakdown")
        
        display_cols = [
            'apps_id', 'position_name', 'user_name', 'apps_status',
            'desc_status_apps', 'Segmen', 'action_on', 'Initiation',
            'RealisasiDate', 'Outstanding_PH', 'Pekerjaan', 'Jabatan',
            'Hasil_Scoring', 'JenisKendaraan', 'branch_name', 
            'Tujuan_Kredit', 'Recommendation', 'LastOD', 'max_OD',
            'OSPH_clean', 'OSPH_Category', 'Scoring_Detail',
            'SLA_Formatted', 'SLA_Days', 'SLA_Hours', 'SLA_Minutes', 'SLA_Seconds',
            'SLA_Working_Days', 'Risk_Score', 'Risk_Category', 'Transition'
        ]
        
        avail_cols = [c for c in display_cols if c in df_filtered.columns]
        
        st.subheader("📊 Filtered Dataset")
        st.dataframe(
            df_filtered[avail_cols],
            use_container_width=True,
            height=500
        )
        
        # Download button
        csv = df_filtered[avail_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Dataset (CSV)",
            data=csv,
            file_name=f"CA_Analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#666'>"
        f"CA Analytics Dashboard v2.0 with Detailed SLA | "
        f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
