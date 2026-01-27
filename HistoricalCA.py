import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(page_title="CA Analytics", layout="wide")

# ============================================================================
# STYLING
# ============================================================================

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

# ============================================================================
# CONSTANTS
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

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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
    """Format timedelta to 'X hari Y jam Z menit W detik' format"""
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
    Exclude weekends and holidays
    """
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        
        start_adjusted = start_dt
        if start_dt.time() >= datetime.strptime("15:30", "%H:%M").time():
            start_adjusted = start_dt + timedelta(days=1)
            start_adjusted = start_adjusted.replace(hour=8, minute=30, second=0, microsecond=0)
            while not is_working_day(start_adjusted):
                start_adjusted += timedelta(days=1)
        
        total_working_seconds = 0
        current_time = start_adjusted
        working_start = datetime.strptime("08:30", "%H:%M").time()
        working_end = datetime.strptime("15:30", "%H:%M").time()
        
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
    except:
        return None

def calculate_historical_sla(df):
    """
    Calculate SLA per row dengan flow proses CA yang benar
    
    Flow:
    1. PENDING CA → count sampai Recommendation ada
    2. PENDING CA COMPLETED → count dari waktu sebelumnya
    3. RECOMMENDED/NOT RECOMMENDED → historical count
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
    """Calculate risk score based on Outstanding PH"""
    score = 0
    if pd.notna(row.get('Outstanding_PH')):
        osph_val = float(row['Outstanding_PH']) if isinstance(row['Outstanding_PH'], (int, float)) else 0
        if osph_val > 500000000:
            score += 30
        elif osph_val > 250000000:
            score += 20
        else:
            score += 10
    return score

def categorize_risk(score):
    """Categorize risk based on score"""
    if score >= 25:
        return "High Risk"
    elif score >= 15:
        return "Medium Risk"
    else:
        return "Low Risk"

def load_and_process_data():
    """Load and process data from Excel file"""
    try:
        df = pd.read_excel(FILE_NAME)
        df['action_on'] = pd.to_datetime(df['action_on'], errors='coerce')
        df['apps_status_clean'] = df['apps_status'].str.strip() if 'apps_status' in df.columns else df['apps_status']
        df['OSPH_clean'] = pd.to_numeric(df['Outstanding_PH'], errors='coerce')
        df['OSPH_Category'] = df['Outstanding_PH'].apply(get_osph_category)
        df['Risk_Score'] = df.apply(calculate_risk_score, axis=1)
        df['Risk_Category'] = df['Risk_Score'].apply(categorize_risk)
        df['Rekomendasi'] = df.get('Recommendation', '')
        df['Pekerjaan_clean'] = df.get('Pekerjaan', '').str.strip()
        df['JenisKendaraan_clean'] = df.get('JenisKendaraan', '').str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    st.title("CA (Credit Analysis) Historical Performance Dashboard")
    st.markdown("**Professional Analytical Dashboard dengan 9 Tabs**")
    st.markdown("SLA Format: `2 hari 1 jam 4 menit 50 detik` | Working Hours: 8:30 AM - 3:30 PM")
    
    # Load data
    df = load_and_process_data()
    
    if df is None or len(df) == 0:
        st.error("Could not load Historical_CA (1).xlsx file. Make sure it exists in the same directory.")
        return
    
    sla_df = calculate_historical_sla(df)
    df_filtered = df.copy()
    
    st.markdown("---")
    
    # ========== 9 TABS ==========
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "Overview", "SLA Analysis", "Status Flow", "Risk Analysis",
        "Outstanding PH", "Scoring Detail", "Multi-Dimensional", "Duplicates", "Raw Data"
    ])
    
    # ===== TAB 1: OVERVIEW =====
    with tab1:
        st.header("Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            st.metric("Unique Apps", df['apps_id'].nunique())
        with col3:
            st.metric("Unique Users", df['user_name'].nunique() if 'user_name' in df.columns else 0)
        with col4:
            st.metric("Unique Branches", df['branch_name'].nunique() if 'branch_name' in df.columns else 0)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Status Distribution")
            status_counts = df['apps_status_clean'].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index, title="Application Status")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Risk Distribution")
            risk_counts = df['Risk_Category'].value_counts()
            fig = px.pie(values=risk_counts.values, names=risk_counts.index, title="Risk Categories")
            st.plotly_chart(fig, use_container_width=True)
    
    # ===== TAB 2: SLA ANALYSIS =====
    with tab2:
        st.header("SLA Analysis (Working Hours: 8:30 AM - 3:30 PM)")
        
        st.markdown("""
        **Flow Proses CA & SLA:**
        - PENDING CA → Menunggu dokumen (hitung sampai Recommendation ada)
        - PENDING CA COMPLETED → Dokumen lengkap (hitung dari waktu sebelumnya)
        - RECOMMENDED/NOT RECOMMENDED → Keputusan final (historical count)
        """)
        
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        completed_sla = sla_df[sla_df['sla_seconds'].notna()]['sla_seconds'].dropna()
        
        with col1:
            avg_seconds = completed_sla.mean() if len(completed_sla) > 0 else 0
            st.metric("Average SLA", format_timedelta(avg_seconds))
        with col2:
            min_seconds = completed_sla.min() if len(completed_sla) > 0 else 0
            st.metric("Min SLA", format_timedelta(min_seconds))
        with col3:
            max_seconds = completed_sla.max() if len(completed_sla) > 0 else 0
            st.metric("Max SLA", format_timedelta(max_seconds))
        with col4:
            median_seconds = completed_sla.median() if len(completed_sla) > 0 else 0
            st.metric("Median SLA", format_timedelta(median_seconds))
        
        st.markdown("---")
        st.subheader("SLA Statistics per Transition")
        
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
                'Max': format_timedelta(trans_sla.max()) if len(trans_sla) > 0 else 'N/A'
            })
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Sample Records")
        sample_cols = ['apps_id', 'from_status', 'to_status', 'action_on', 'sla_formatted', 'sla_category']
        st.dataframe(sla_df[sample_cols].head(20), use_container_width=True, hide_index=True)
    
    # ===== TAB 3: STATUS FLOW =====
    with tab3:
        st.header("Status Flow Analysis")
        
        transition_counts = sla_df['transition'].value_counts()
        fig = px.bar(x=transition_counts.values, y=transition_counts.index, orientation='h',
                    title="Status Transition Frequency", labels={'x': 'Count', 'y': 'Transition'})
        st.plotly_chart(fig, use_container_width=True)
    
    # ===== TAB 4: RISK ANALYSIS =====
    with tab4:
        st.header("Risk Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            risk_counts = df['Risk_Category'].value_counts()
            fig = px.pie(values=risk_counts.values, names=risk_counts.index, title="Risk Distribution")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.histogram(df, x='Risk_Score', nbins=20, title="Risk Score Distribution")
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        risk_status = pd.crosstab(df['apps_status_clean'], df['Risk_Category'])
        fig = px.bar(risk_status, title="Risk Category by Status", barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
    
    # ===== TAB 5: OUTSTANDING PH =====
    with tab5:
        st.header("Outstanding PH Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            osph_counts = df['OSPH_Category'].value_counts()
            fig = px.pie(values=osph_counts.values, names=osph_counts.index, title="Outstanding PH Distribution")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.histogram(df, x='OSPH_clean', nbins=30, title="Outstanding PH Histogram")
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        osph_status = pd.crosstab(df['apps_status_clean'], df['OSPH_Category'])
        fig = px.bar(osph_status, title="Outstanding PH by Status", barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
    
    # ===== TAB 6: SCORING DETAIL =====
    with tab6:
        st.header("Scoring Detail Analysis")
        
        if 'Hasil_Scoring' in df.columns:
            scoring_counts = df['Hasil_Scoring'].value_counts()
            fig = px.bar(x=scoring_counts.index, y=scoring_counts.values, title="Scoring Distribution",
                        labels={'x': 'Scoring', 'y': 'Count'})
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            scoring_status = pd.crosstab(df['Hasil_Scoring'], df['apps_status_clean'])
            fig = px.bar(scoring_status, title="Scoring by Status", barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Scoring data not available")
    
    # ===== TAB 7: MULTI-DIMENSIONAL =====
    with tab7:
        st.header("Multi-Dimensional Analysis")
        
        st.subheader("Dimension 1: Outstanding PH vs Status")
        dim1_data = pd.crosstab(df['OSPH_Category'], df['apps_status_clean'])
        fig = px.bar(dim1_data, title="Outstanding PH vs Status", barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Dimension 2: Risk vs Outstanding PH")
        dim2_data = pd.crosstab(df['OSPH_Category'], df['Risk_Category'])
        fig = px.bar(dim2_data, title="Risk by Outstanding PH", barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Dimension 3: Job Type (Pekerjaan)")
        if 'Pekerjaan_clean' in df.columns:
            pekerjaan_counts = df['Pekerjaan_clean'].value_counts().head(10)
            fig = px.bar(x=pekerjaan_counts.index, y=pekerjaan_counts.values, title="Top 10 Job Types")
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Dimension 4: Vehicle Type (Jenis Kendaraan)")
        if 'JenisKendaraan_clean' in df.columns:
            kendaraan_counts = df['JenisKendaraan_clean'].value_counts()
            fig = px.pie(values=kendaraan_counts.values, names=kendaraan_counts.index, title="Vehicle Type")
            st.plotly_chart(fig, use_container_width=True)
    
    # ===== TAB 8: DUPLICATES =====
    with tab8:
        st.header("Duplicate Applications Analysis")
        
        app_counts = df['apps_id'].value_counts()
        duplicates = app_counts[app_counts > 1]
        
        if len(duplicates) > 0:
            st.info(f"Found {len(duplicates)} duplicate IDs with {duplicates.sum()} total records")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Duplicate IDs", len(duplicates))
            with col2:
                st.metric("Max Records per ID", duplicates.max())
            with col3:
                st.metric("Total Duplicate Records", duplicates.sum())
            with col4:
                st.metric("Avg Records per ID", f"{duplicates.mean():.1f}")
            
            st.markdown("---")
            dup_dist = duplicates.value_counts().sort_index()
            fig = px.bar(x=dup_dist.index, y=dup_dist.values, labels={'x': 'Records per App', 'y': 'Count'},
                        title="Duplicate Frequency")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No duplicate application IDs found")
    
    # ===== TAB 9: RAW DATA =====
    with tab9:
        st.header("Complete Raw Data Export")
        
        display_cols = ['apps_id', 'user_name', 'apps_status_clean', 'action_on',
                       'Outstanding_PH', 'Risk_Category', 'OSPH_Category', 'Rekomendasi']
        avail_cols = [c for c in display_cols if c in df.columns]
        
        st.subheader("Dataset")
        st.dataframe(df[avail_cols], use_container_width=True, height=500)
        
        csv = df[avail_cols].to_csv(index=False).encode('utf-8')
        st.download_button(label="Download CSV", data=csv,
                          file_name=f"CA_Analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                          mime="text/csv")
    
    # ========== FOOTER ==========
    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#666'>"
        f"CA Analytics Dashboard | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    main()
