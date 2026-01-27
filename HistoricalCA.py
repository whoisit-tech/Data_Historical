"""
CA (Credit Analysis) Historical Performance Dashboard
Professional Analytical Dashboard - 9 Tabs
Improved SLA Calculation: Format "X hari Y jam Z menit W detik"

Author: Claude AI
Version: 1.0 (Production Ready)
Date: January 27, 2026

Features:
- 9 Professional Tabs with 20+ Visualizations
- Improved SLA Calculation (working hours: 8:30 AM - 3:30 PM)
- Outstanding PH Analysis
- Risk Management & Scoring
- Multi-Dimensional Analysis
- Duplicate Detection
- Data Export

Requirements:
- streamlit >= 1.28.0
- pandas >= 2.0.0
- plotly >= 5.0.0
- openpyxl >= 3.0.0

Data File Required:
- HistoricalCA.xlsx (dalam directory yang sama dengan app.py)

Usage:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================

st.set_page_config(
    page_title="CA Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1 {
        color: #667eea;
        text-align: center;
        font-size: 2.5em;
        margin-bottom: 10px;
    }
    h2 {
        color: #764ba2;
        border-bottom: 3px solid #667eea;
        padding-bottom: 10px;
        font-size: 1.8em;
    }
    h3 {
        color: #667eea;
        font-size: 1.3em;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

FILE_NAME = "HistoricalCA.xlsx"

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

WORKING_START = "08:30"
WORKING_END = "15:30"

RISK_HIGH = 25
RISK_MEDIUM = 15

OSPH_RANGES = [
    (0, 250000000, "0 - 250 Juta"),
    (250000000, 500000000, "250 - 500 Juta"),
    (500000000, float('inf'), "500 Juta+")
]

# ============================================================================
# UTILITY FUNCTIONS - Date & Time
# ============================================================================

@st.cache_data
def is_working_day(date):
    """Check if date is a working day (exclude weekends and holidays)"""
    if pd.isna(date):
        return False
    if not isinstance(date, datetime):
        date = pd.to_datetime(date)

    is_weekday = date.weekday() < 5
    is_not_holiday = date.date() not in TANGGAL_MERAH_DT

    return is_weekday and is_not_holiday

def format_timedelta(total_seconds):
    """Format timedelta to Indonesian format: X hari Y jam Z menit W detik"""
    if total_seconds is None or pd.isna(total_seconds):
        return "N/A"

    total_seconds = int(total_seconds)

    days = total_seconds // 86400
    remaining = total_seconds % 86400
    hours = remaining // 3600
    remaining = remaining % 3600
    minutes = remaining // 60
    seconds = remaining % 60

    parts = []
    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0:
        parts.append(f"{hours} jam")
    if minutes > 0:
        parts.append(f"{minutes} menit")
    if seconds > 0:
        parts.append(f"{seconds} detik")

    return " ".join(parts) if parts else "0 detik"

def calculate_sla_seconds(start_dt, end_dt):
    """
    Calculate SLA in working seconds (8:30 AM - 3:30 PM only)
    Only count working hours, exclude weekends and holidays
    """
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None

    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)

        start_adjusted = start_dt
        working_end_time = datetime.strptime(WORKING_END, "%H:%M").time()

        if start_dt.time() >= working_end_time:
            start_adjusted = start_dt + timedelta(days=1)
            start_adjusted = start_adjusted.replace(hour=8, minute=30, second=0, microsecond=0)
            while not is_working_day(start_adjusted):
                start_adjusted += timedelta(days=1)

        total_working_seconds = 0
        current_time = start_adjusted
        working_start = datetime.strptime(WORKING_START, "%H:%M").time()
        working_end = datetime.strptime(WORKING_END, "%H:%M").time()

        while current_time < end_dt:
            current_date = current_time.date()

            if is_working_day(datetime.combine(current_date, datetime.min.time())):
                day_start = current_time
                day_end = end_dt if end_dt.date() == current_date else datetime.combine(current_date, working_end)

                if day_start.time() < working_start:
                    day_start = day_start.replace(hour=8, minute=30, second=0, microsecond=0)
                if day_end.time() > working_end:
                    day_end = day_end.replace(hour=15, minute=30, second=0, microsecond=0)

                if day_start.time() < working_end and day_end.time() > working_start:
                    total_working_seconds += (day_end - day_start).total_seconds()

            current_time = datetime.combine(current_date + timedelta(days=1), working_start)

        return total_working_seconds
    except Exception as e:
        st.warning(f"Error calculating SLA: {str(e)}")
        return None

# ============================================================================
# UTILITY FUNCTIONS - SLA Calculation
# ============================================================================

def calculate_historical_sla(df):
    """
    Calculate SLA per row berdasarkan flow proses CA
    
    Flow:
    1. PENDING CA: count dari action_on sampai Recommendation field terisi
    2. PENDING CA COMPLETED: count dari waktu sebelumnya ke waktu ini  
    3. RECOMMENDED/NOT RECOMMENDED: historical (current - previous)
    """
    df_sorted = df.sort_values(['apps_id', 'action_on']).reset_index(drop=True)
    sla_list = []

    for idx, row in df_sorted.iterrows():
        app_id = row['apps_id']
        current_status = row.get('apps_status', 'Unknown')
        current_time = row.get('action_on')
        recommendation = row.get('Recommendation')

        status_clean = current_status.strip() if isinstance(current_status, str) else current_status
        prev_rows = df_sorted[(df_sorted['apps_id'] == app_id) & (df_sorted.index < idx)]

        sla_seconds = None
        sla_category = None
        from_status = None

        if len(prev_rows) > 0:
            prev_row = prev_rows.iloc[-1]
            prev_status = prev_row.get('apps_status', 'Unknown')
            prev_time = prev_row.get('action_on')
            from_status = prev_status.strip() if isinstance(prev_status, str) else prev_status

            if 'PENDING CA' in status_clean.upper():
                if pd.isna(recommendation) or recommendation == '' or recommendation == '-':
                    sla_seconds = None
                    sla_category = "PENDING"
                else:
                    sla_seconds = calculate_sla_seconds(prev_time, current_time)
                    sla_category = "COMPLETED"
            else:
                sla_seconds = calculate_sla_seconds(prev_time, current_time)
                sla_category = "COMPLETED"

            transition = f"{from_status} → {status_clean}"
        else:
            transition = f"START → {status_clean}"
            sla_category = "START"
            from_status = 'START'

        sla_list.append({
            'idx': idx,
            'apps_id': app_id,
            'transition': transition,
            'from_status': from_status if from_status else 'START',
            'to_status': status_clean,
            'sla_seconds': sla_seconds,
            'sla_formatted': format_timedelta(sla_seconds),
            'sla_category': sla_category,
            'action_on': current_time,
            'recommendation': recommendation
        })

    return pd.DataFrame(sla_list)

# ============================================================================
# UTILITY FUNCTIONS - Data Processing
# ============================================================================

def get_osph_category(osph_value):
    """Categorize Outstanding PH into predefined ranges"""
    try:
        if pd.isna(osph_value):
            return "Unknown"
        osph_value = float(osph_value)
        for min_val, max_val, category in OSPH_RANGES:
            if min_val <= osph_value < max_val:
                return category
        return "Unknown"
    except:
        return "Unknown"

def calculate_risk_score(row):
    """Calculate risk score based on Outstanding PH value"""
    score = 0
    if pd.notna(row.get('Outstanding_PH')):
        try:
            osph_val = float(row['Outstanding_PH'])
            if osph_val > 500000000:
                score += 30
            elif osph_val > 250000000:
                score += 20
            else:
                score += 10
        except:
            pass
    return score

def categorize_risk(score):
    """Categorize risk based on score"""
    if score >= RISK_HIGH:
        return "High Risk"
    elif score >= RISK_MEDIUM:
        return "Medium Risk"
    else:
        return "Low Risk"

def load_and_process_data():
    """Load data from Excel file and perform data processing"""
    try:
        df = pd.read_excel(FILE_NAME)

        df['action_on'] = pd.to_datetime(df['action_on'], errors='coerce')
        df['apps_status_clean'] = df['apps_status'].str.strip() if 'apps_status' in df.columns else df['apps_status']
        df['OSPH_clean'] = pd.to_numeric(df['Outstanding_PH'], errors='coerce')
        df['OSPH_Category'] = df['Outstanding_PH'].apply(get_osph_category)
        df['Risk_Score'] = df.apply(calculate_risk_score, axis=1)
        df['Risk_Category'] = df['Risk_Score'].apply(categorize_risk)
        df['Rekomendasi'] = df.get('Recommendation', '')
        df['Pekerjaan_clean'] = df.get('Pekerjaan', '').astype(str).str.strip()
        df['JenisKendaraan_clean'] = df.get('JenisKendaraan', '').astype(str).str.strip()

        return df
    except FileNotFoundError:
        st.error(f"Error: File '{FILE_NAME}' tidak ditemukan!")
        st.info("Pastikan file HistoricalCA.xlsx ada dalam directory yang sama dengan app.py")
        return None
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_sla_summary_metrics(sla_df):
    """Create SLA summary metrics"""
    completed_sla = sla_df[sla_df['sla_seconds'].notna()]['sla_seconds'].dropna()

    metrics = {
        'average': completed_sla.mean() if len(completed_sla) > 0 else 0,
        'minimum': completed_sla.min() if len(completed_sla) > 0 else 0,
        'maximum': completed_sla.max() if len(completed_sla) > 0 else 0,
        'median': completed_sla.median() if len(completed_sla) > 0 else 0,
        'count': len(completed_sla),
        'pending': len(sla_df[sla_df['sla_category'] == 'PENDING'])
    }

    return metrics

def create_transition_statistics(sla_df):
    """Create detailed transition statistics"""
    stats_data = []

    for transition in sorted(sla_df['transition'].unique()):
        trans_data = sla_df[sla_df['transition'] == transition]
        trans_sla = trans_data[trans_data['sla_seconds'].notna()]['sla_seconds']

        stats_data.append({
            'Transition': transition,
            'Total': len(trans_data),
            'Valid SLA': len(trans_sla),
            'Pending': len(trans_data) - len(trans_sla),
            'Average': format_timedelta(trans_sla.mean()) if len(trans_sla) > 0 else 'N/A',
            'Min': format_timedelta(trans_sla.min()) if len(trans_sla) > 0 else 'N/A',
            'Max': format_timedelta(trans_sla.max()) if len(trans_sla) > 0 else 'N/A',
            'Median': format_timedelta(trans_sla.median()) if len(trans_sla) > 0 else 'N/A'
        })

    return pd.DataFrame(stats_data)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application function with 9 tabs"""

    st.title("CA (Credit Analysis) Historical Performance Dashboard")
    st.markdown("<p style='text-align: center; color: #666;'><b>Professional Analytical Dashboard - 9 Tabs</b></p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #999;'>SLA Format: <code>2 hari 1 jam 4 menit 50 detik</code> | Working Hours: <b>8:30 AM - 3:30 PM</b></p>", unsafe_allow_html=True)

    df = load_and_process_data()

    if df is None or len(df) == 0:
        st.error("Data loading failed!")
        st.stop()
        return

    sla_df = calculate_historical_sla(df)
    df_filtered = df.copy()

    st.markdown("---")

    # 9 TABS
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "Overview",
        "SLA Analysis",
        "Status Flow",
        "Risk Analysis",
        "Outstanding PH",
        "Scoring",
        "Multi-Dimensional",
        "Duplicates",
        "Raw Data"
    ])

    # TAB 1: OVERVIEW
    with tab1:
        st.header("Overview")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", f"{len(df):,}")
        with col2:
            st.metric("Unique Applications", f"{df['apps_id'].nunique():,}")
        with col3:
            users = df['user_name'].nunique() if 'user_name' in df.columns else 0
            st.metric("Unique Users", f"{users:,}")
        with col4:
            branches = df['branch_name'].nunique() if 'branch_name' in df.columns else 0
            st.metric("Unique Branches", f"{branches:,}")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Application Status Distribution")
            status_counts = df['apps_status_clean'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Status Distribution",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Risk Category Distribution")
            risk_counts = df['Risk_Category'].value_counts()
            fig = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title="Risk Distribution",
                color_discrete_sequence=['#FF6B6B', '#FFC107', '#51CF66']
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Key Metrics Summary")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            high_risk = len(df[df['Risk_Category'] == 'High Risk'])
            st.metric("High Risk Count", high_risk)
        with col2:
            med_risk = len(df[df['Risk_Category'] == 'Medium Risk'])
            st.metric("Medium Risk Count", med_risk)
        with col3:
            low_risk = len(df[df['Risk_Category'] == 'Low Risk'])
            st.metric("Low Risk Count", low_risk)
        with col4:
            avg_osph = df['OSPH_clean'].mean()
            st.metric("Average Outstanding PH", f"Rp {avg_osph/1e9:.1f}B")

    # TAB 2: SLA ANALYSIS
    with tab2:
        st.header("SLA Analysis (Working Hours: 8:30 AM - 3:30 PM)")

        st.markdown("""
        ### Flow Proses CA & SLA Calculation:

        1. **PENDING CA** - Menunggu dokumen/info dari RM/BM
           - SLA dihitung dari action_on sampai Recommendation field terisi
           - Jika Recommendation kosong: SLA = N/A (Status: PENDING)

        2. **PENDING CA COMPLETED** - Dokumen lengkap, siap dianalisis
           - SLA dihitung dari waktu sebelumnya ke waktu ini

        3. **RECOMMENDED/NOT RECOMMENDED** - Keputusan final
           - SLA adalah historical (current minus previous untuk same app_id)
        """)

        st.markdown("---")

        metrics = create_sla_summary_metrics(sla_df)

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Average SLA", format_timedelta(metrics['average']))
        with col2:
            st.metric("Min SLA", format_timedelta(metrics['minimum']))
        with col3:
            st.metric("Max SLA", format_timedelta(metrics['maximum']))
        with col4:
            st.metric("Median SLA", format_timedelta(metrics['median']))
        with col5:
            st.metric("Pending Count", metrics['pending'])

        st.markdown("---")

        st.subheader("SLA Statistics per Transition")
        stats_df = create_transition_statistics(sla_df)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        st.subheader("Sample Records with SLA Details")
        sample_cols = ['apps_id', 'from_status', 'to_status', 'action_on', 'sla_formatted', 'sla_category', 'recommendation']
        display_sla = sla_df[sample_cols].head(30).copy()
        st.dataframe(display_sla, use_container_width=True, hide_index=True, height=400)

    # TAB 3: STATUS FLOW
    with tab3:
        st.header("Status Flow Analysis")

        transition_counts = sla_df['transition'].value_counts()

        col1, col2 = st.columns([3, 1])

        with col1:
            fig = px.bar(
                x=transition_counts.values,
                y=transition_counts.index,
                orientation='h',
                title="Status Transition Frequency",
                labels={'x': 'Count', 'y': 'Transition'},
                color=transition_counts.values,
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col1:
            st.markdown("---")
            st.subheader("Transition Summary")

            transition_summary = []
            for trans in sorted(sla_df['transition'].unique()):
                count = len(sla_df[sla_df['transition'] == trans])
                transition_summary.append({'Transition': trans, 'Count': count})

            summary_df = pd.DataFrame(transition_summary).sort_values('Count', ascending=False)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # TAB 4: RISK ANALYSIS
    with tab4:
        st.header("Risk Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("High Risk", len(df[df['Risk_Category'] == 'High Risk']))
        with col2:
            st.metric("Medium Risk", len(df[df['Risk_Category'] == 'Medium Risk']))
        with col3:
            st.metric("Low Risk", len(df[df['Risk_Category'] == 'Low Risk']))

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Risk Distribution")
            risk_counts = df['Risk_Category'].value_counts()
            fig = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title="Risk Category Distribution",
                color_discrete_map={'High Risk': '#FF6B6B', 'Medium Risk': '#FFC107', 'Low Risk': '#51CF66'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Risk Score Distribution")
            fig = px.histogram(
                df,
                x='Risk_Score',
                nbins=20,
                title="Risk Score Histogram",
                labels={'Risk_Score': 'Risk Score'},
                color_discrete_sequence=['#667eea']
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        st.subheader("Risk by Application Status")
        risk_status = pd.crosstab(df['apps_status_clean'], df['Risk_Category'])
        fig = px.bar(
            risk_status,
            title="Risk Category by Application Status",
            barmode='stack',
            color_discrete_map={'High Risk': '#FF6B6B', 'Medium Risk': '#FFC107', 'Low Risk': '#51CF66'}
        )
        st.plotly_chart(fig, use_container_width=True)

    # TAB 5: OUTSTANDING PH
    with tab5:
        st.header("Outstanding PH Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Outstanding PH", f"Rp {df['OSPH_clean'].sum()/1e9:.1f}B")
        with col2:
            st.metric("Average Outstanding PH", f"Rp {df['OSPH_clean'].mean()/1e9:.1f}B")
        with col3:
            st.metric("Max Outstanding PH", f"Rp {df['OSPH_clean'].max()/1e9:.1f}B")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Outstanding PH Distribution")
            osph_counts = df['OSPH_Category'].value_counts()
            fig = px.pie(
                values=osph_counts.values,
                names=osph_counts.index,
                title="Outstanding PH Range Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Outstanding PH Histogram")
            fig = px.histogram(
                df,
                x='OSPH_clean',
                nbins=30,
                title="Outstanding PH Distribution",
                labels={'OSPH_clean': 'Outstanding PH (Rp)'}
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        st.subheader("Outstanding PH by Application Status")
        osph_status = pd.crosstab(df['apps_status_clean'], df['OSPH_Category'])
        fig = px.bar(
            osph_status,
            title="Outstanding PH Range by Application Status",
            barmode='stack'
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        st.subheader("Outstanding PH Statistics")
        osph_stats = df.groupby('OSPH_Category')['OSPH_clean'].agg([
            ('Count', 'count'),
            ('Mean', 'mean'),
            ('Min', 'min'),
            ('Max', 'max'),
            ('Std Dev', 'std')
        ]).round(0)
        st.dataframe(osph_stats, use_container_width=True)

    # TAB 6: SCORING DETAIL
    with tab6:
        st.header("Scoring Detail Analysis")

        if 'Hasil_Scoring' in df.columns:
            st.metric("Total Scoring Records", len(df[df['Hasil_Scoring'].notna()]))

            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Scoring Distribution")
                scoring_counts = df['Hasil_Scoring'].value_counts()
                fig = px.bar(
                    x=scoring_counts.index,
                    y=scoring_counts.values,
                    title="Scoring Result Distribution",
                    labels={'x': 'Scoring', 'y': 'Count'},
                    color=scoring_counts.values,
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Scoring by Status")
                scoring_status = pd.crosstab(df['Hasil_Scoring'], df['apps_status_clean'])
                fig = px.bar(
                    scoring_status,
                    title="Scoring by Application Status",
                    barmode='group'
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            st.subheader("Detailed Scoring Statistics")
            scoring_detail = df.groupby('Hasil_Scoring').agg({
                'apps_id': 'count',
                'Risk_Score': ['mean', 'min', 'max'],
                'OSPH_clean': ['mean', 'min', 'max']
            }).round(0)
            st.dataframe(scoring_detail, use_container_width=True)

        else:
            st.info("Scoring data not available in dataset")

    # TAB 7: MULTI-DIMENSIONAL
    with tab7:
        st.header("Multi-Dimensional Analysis")

        st.subheader("Dimension 1: Outstanding PH vs Application Status")
        dim1_data = pd.crosstab(df['OSPH_Category'], df['apps_status_clean'])
        fig = px.bar(
            dim1_data,
            title="Outstanding PH Range vs Application Status",
            barmode='stack'
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        st.subheader("Dimension 2: Risk Category vs Outstanding PH")
        dim2_data = pd.crosstab(df['OSPH_Category'], df['Risk_Category'])
        fig = px.bar(
            dim2_data,
            title="Risk Category by Outstanding PH Range",
            barmode='stack',
            color_discrete_map={'High Risk': '#FF6B6B', 'Medium Risk': '#FFC107', 'Low Risk': '#51CF66'}
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        st.subheader("Dimension 3: Job Type Analysis")
        if 'Pekerjaan_clean' in df.columns:
            pekerjaan_counts = df[df['Pekerjaan_clean'] != ''].groupby('Pekerjaan_clean').size().nlargest(10)
            fig = px.bar(
                x=pekerjaan_counts.index,
                y=pekerjaan_counts.values,
                title="Top 10 Job Types",
                labels={'x': 'Job Type', 'y': 'Count'},
                color=pekerjaan_counts.values,
                color_continuous_scale='Plasma'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        st.subheader("Dimension 4: Vehicle Type Analysis")
        if 'JenisKendaraan_clean' in df.columns:
            kendaraan_counts = df[df['JenisKendaraan_clean'] != ''].groupby('JenisKendaraan_clean').size()
            fig = px.pie(
                values=kendaraan_counts.values,
                names=kendaraan_counts.index,
                title="Vehicle Type Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)

    # TAB 8: DUPLICATES
    with tab8:
        st.header("Duplicate Applications Analysis")

        app_counts = df['apps_id'].value_counts()
        duplicates = app_counts[app_counts > 1]

        if len(duplicates) > 0:
            st.warning(f"Found {len(duplicates)} duplicate application IDs with {duplicates.sum()} total records")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Duplicate IDs", len(duplicates))
            with col2:
                st.metric("Max Records per ID", duplicates.max())
            with col3:
                st.metric("Total Duplicates", duplicates.sum())
            with col4:
                st.metric("Average per ID", f"{duplicates.mean():.1f}")

            st.markdown("---")

            st.subheader("Duplicate Frequency Distribution")
            dup_dist = duplicates.value_counts().sort_index()
            fig = px.bar(
                x=dup_dist.index,
                y=dup_dist.values,
                labels={'x': 'Records per Application', 'y': 'Count of Apps'},
                title="Duplicate Frequency",
                color=dup_dist.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.success("No duplicate application IDs found")

    # TAB 9: RAW DATA
    with tab9:
        st.header("Raw Data Export")

        display_cols = [
            'apps_id', 'user_name', 'apps_status_clean', 'action_on',
            'Outstanding_PH', 'Risk_Category', 'OSPH_Category', 'Rekomendasi'
        ]
        avail_cols = [c for c in display_cols if c in df.columns]

        st.subheader("Complete Dataset View")
        st.dataframe(
            df[avail_cols],
            use_container_width=True,
            height=600
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            csv = df[avail_cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"CA_Analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        with col2:
            st.info(f"Total records available: {len(df):,}")

    # FOOTER
    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#999;font-size:0.9em;'>"
        f"<p><b>CA Analytics Dashboard</b> | Version 1.0 | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        f"<p>SLA Format: X hari Y jam Z menit W detik | Working Hours: 8:30 AM - 3:30 PM</p>"
        f"</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
