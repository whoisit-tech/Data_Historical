import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
from pathlib import Path

# ========== KONFIGURASI ==========
st.set_page_config(page_title="CA Analytics Dashboard", layout="wide", page_icon="📊")

# File Excel
FILE_NAME = "HistoricalCA.xlsx"

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .insight-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Tanggal merah
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

# ========== FUNGSI HELPER ==========

def parse_date(date_str):
    if pd.isna(date_str) or date_str == '-' or date_str == '':
        return None
    
    try:
        if isinstance(date_str, datetime):
            return date_str
        
        formats = ["%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).split('.')[0], fmt)
            except:
                continue
        
        result = pd.to_datetime(date_str, errors='coerce')
        if pd.isna(result):
            return None
        return result.to_pydatetime()
    except:
        return None

def is_working_day(date):
    try:
        if pd.isna(date):
            return False
        if not isinstance(date, datetime):
            date = pd.to_datetime(date)
        if date.weekday() >= 5 or date.date() in TANGGAL_MERAH_DT:
            return False
        return True
    except:
        return False

def calculate_sla_days(start_dt, end_dt):
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        
        if pd.isna(start_dt) or pd.isna(end_dt):
            return None
        
        start_adjusted = start_dt
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

def get_osph_category(osph_value):
    try:
        if pd.isna(osph_value) or osph_value is None:
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

def preprocess_data(df):
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            try:
                df[f'{col}_parsed'] = df[col].apply(parse_date)
            except Exception as e:
                st.warning(f"⚠️ Error parsing {col}: {str(e)}")
                df[f'{col}_parsed'] = None
    
    # SLA
    if 'action_on_parsed' in df.columns and 'RealisasiDate_parsed' in df.columns:
        try:
            df['SLA_Days'] = df.apply(
                lambda row: calculate_sla_days(row['action_on_parsed'], row['RealisasiDate_parsed']), axis=1
            )
        except Exception as e:
            st.warning(f"⚠️ Error calculating SLA: {str(e)}")
            df['SLA_Days'] = None
    
    # OSPH
    if 'Outstanding_PH' in df.columns:
        try:
            df['OSPH_clean'] = pd.to_numeric(
                df['Outstanding_PH'].astype(str).str.replace(',', ''), errors='coerce'
            )
            df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
        except Exception as e:
            st.warning(f"⚠️ Error processing OSPH: {str(e)}")
    
    # SCORING – definisi jelas
    if 'Hasil_Scoring_1' in df.columns:
        try:
            df['Scoring_Raw'] = df['Hasil_Scoring_1']

            df['Is_Scored'] = df['Hasil_Scoring_1'].astype(str).str.strip().isin(['', '-']) == False

            def map_main_decision(x):
                x_str = str(x).upper().strip()
                if x_str.startswith('APPROVE'):
                    return 'APPROVE'
                if x_str.startswith('REGULER'):
                    return 'REGULER'
                if x_str.startswith('REJECT'):
                    return 'REJECT'
                if x_str in ['', '-']:
                    return 'NOT SCORED'
                return 'OTHER'

            df['Scoring_Main'] = df['Hasil_Scoring_1'].apply(map_main_decision)
        except Exception as e:
            st.warning(f"⚠️ Error processing scoring: {str(e)}")
    
    # Time features
    if 'action_on_parsed' in df.columns:
        try:
            df['Hour'] = df['action_on_parsed'].dt.hour
            df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
            df['Month'] = df['action_on_parsed'].dt.month
            df['Week'] = df['action_on_parsed'].dt.isocalendar().week
            df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        except Exception as e:
            st.warning(f"⚠️ Error creating time features: {str(e)}")
    
    # Risk score
    if 'OSPH_clean' in df.columns and 'SLA_Days' in df.columns:
        try:
            osph_norm = (df['OSPH_clean'] - df['OSPH_clean'].min()) / (df['OSPH_clean'].max() - df['OSPH_clean'].min() + 1)
            sla_norm = (df['SLA_Days'] - df['SLA_Days'].min()) / (df['SLA_Days'].max() - df['SLA_Days'].min() + 1)
            df['Risk_Score'] = (osph_norm * 0.6 + sla_norm * 0.4) * 100
        except Exception as e:
            st.warning(f"⚠️ Error calculating risk score: {str(e)}")
    
    return df

# ========== LOAD DATA ==========

@st.cache_data
def load_data():
    if not Path(FILE_NAME).exists():
        st.error(f"❌ File '{FILE_NAME}' tidak ditemukan di folder yang sama dengan script")
        st.stop()
    
    try:
        df = pd.read_excel(FILE_NAME)
        st.info(f"📊 Raw data loaded: {len(df)} rows")
        
        df_processed = preprocess_data(df)
        st.info("✅ Data preprocessing completed")
        
        return df_processed
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

# ========== MAIN APP ==========

def main():
    st.title("Credit Analyst Analytics Dashboard")
    st.markdown("Comprehensive Analytics for Historical CA Performance")
    st.markdown("---")

    with st.spinner("⏳ Loading data from HistoricalCA.xlsx..."):
        df = load_data()
    if df is None or df.empty:
        st.error("❌ Failed to load data.")
        st.stop()
    st.success(f"✅ Data loaded successfully! Total records: {len(df)}")

    # Sidebar filters
    st.sidebar.header("🔍 Filters")

    df_filtered = df.copy()

    # Posisi CA / user_name
    if 'user_name' in df_filtered.columns:
        ca_positions = ["All"] + sorted(df_filtered['user_name'].dropna().unique().tolist())
        selected_ca = st.sidebar.selectbox("Posisi / CA", ca_positions)
        if selected_ca != "All":
            df_filtered = df_filtered[df_filtered['user_name'] == selected_ca]

    # Produk
    if 'Produk' in df_filtered.columns:
        products = ["All"] + sorted(df_filtered['Produk'].dropna().unique().tolist())
        selected_product = st.sidebar.selectbox("Produk", products)
        if selected_product != "All":
            df_filtered = df_filtered[df_filtered['Produk'] == selected_product]

    # Cabang
    if 'branch_name' in df_filtered.columns:
        branches = ["All"] + sorted(df_filtered['branch_name'].dropna().unique().tolist())
        selected_branch = st.sidebar.selectbox("Branch", branches)
        if selected_branch != "All":
            df_filtered = df_filtered[df_filtered['branch_name'] == selected_branch]

    # Date range
    date_range = None
    if 'action_on_parsed' in df_filtered.columns:
        df_with_dates = df_filtered[df_filtered['action_on_parsed'].notna()].copy()
        if len(df_with_dates) > 0:
            try:
                min_date = pd.to_datetime(df_with_dates['action_on_parsed'].min())
                max_date = pd.to_datetime(df_with_dates['action_on_parsed'].max())
                if pd.notna(min_date) and pd.notna(max_date):
                    date_range = st.sidebar.date_input(
                        "Periode",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date()
                    )
            except Exception:
                date_range = None
    if date_range is not None and len(date_range) == 2 and 'action_on_parsed' in df_filtered.columns:
        try:
            df_filtered = df_filtered[
                (df_filtered['action_on_parsed'].dt.date >= date_range[0]) &
                (df_filtered['action_on_parsed'].dt.date <= date_range[1])
            ]
        except Exception:
            pass

    # ========== KPI SECTION ==========

    st.header("📈 Key Performance Indicators")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

    with kpi_col1:
        if 'apps_id' in df_filtered.columns:
            total_apps = df_filtered['apps_id'].nunique()
        else:
            total_apps = len(df_filtered)
        st.metric("📦 Total Apps (Distinct)", f"{total_apps:,}")

    with kpi_col2:
        if 'SLA_Days' in df_filtered.columns:
            avg_sla = df_filtered['SLA_Days'].mean()
            st.metric("⏱ Avg SLA (Hari Kerja)", f"{avg_sla:.1f}" if not pd.isna(avg_sla) else "N/A")
        else:
            st.metric("⏱ Avg SLA", "N/A")

    with kpi_col3:
        if 'Is_Scored' in df_filtered.columns:
            if 'apps_id' in df_filtered.columns:
                total_scored = df_filtered[df_filtered['Is_Scored'] == True]['apps_id'].nunique()
            else:
                total_scored = len(df_filtered[df_filtered['Is_Scored'] == True])
            st.metric("📝 Total Scored (sudah ada hasil scoring CA)", f"{total_scored:,}")
        else:
            st.metric("📝 Total Scored", "N/A")

    with kpi_col4:
        if 'Scoring_Main' in df_filtered.columns:
            if 'apps_id' in df_filtered.columns:
                approved = df_filtered[df_filtered['Scoring_Main'] == 'APPROVE']['apps_id'].nunique()
            else:
                approved = len(df_filtered[df_filtered['Scoring_Main'] == 'APPROVE'])
            st.metric("✅ Approved (semua jenis Approve)", f"{approved:,}")
        else:
            st.metric("✅ Approved", "N/A")

    with kpi_col5:
        if 'Scoring_Main' in df_filtered.columns:
            if 'apps_id' in df_filtered.columns:
                rejected = df_filtered[df_filtered['Scoring_Main'] == 'REJECT']['apps_id'].nunique()
            else:
                rejected = len(df_filtered[df_filtered['Scoring_Main'] == 'REJECT'])
            st.metric("❌ Rejected (semua jenis Reject)", f"{rejected:,}")
        else:
            st.metric("❌ Rejected", "N/A")

    st.markdown("---")

    # ========== CONVERSION FUNNEL ==========

    st.header("🎯 Conversion Funnel Rate Analysis")

    if 'Scoring_Main' in df_filtered.columns and 'Is_Scored' in df_filtered.columns:
        total_apps_f = len(df_filtered)
        scored_f = len(df_filtered[df_filtered['Is_Scored'] == True])
        approved_f = len(df_filtered[df_filtered['Scoring_Main'] == 'APPROVE'])

        funnel_data = {
            "Stage": [
                "Total Applications",
                "Scored (sudah di-review CA)",
                "Approved"
            ],
            "Count": [total_apps_f, scored_f, approved_f]
        }
        funnel_df = pd.DataFrame(funnel_data)

        fig = go.Figure(go.Funnel(
            y=funnel_df["Stage"],
            x=funnel_df["Count"],
            textinfo="value+percent total"
        ))
        fig.update_layout(title="Conversion Funnel")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Scoring data belum lengkap untuk funnel.")

    st.markdown("---")

    # ========== RAW DATA EXPLORER (VERSI RINGKAS) ==========

    st.header("📋 Raw Data Explorer")
    all_columns = df_filtered.columns.tolist()
    default_cols = ['apps_id', 'Produk', 'OSPH_Category', 'Pekerjaan',
                    'JenisKendaraan', 'Scoring_Main', 'SLA_Days', 'branch_name']
    display_cols = [col for col in default_cols if col in all_columns]

    selected_cols = st.multiselect("Select columns to display", all_columns, default=display_cols)

    if selected_cols:
        search_term = st.text_input("🔍 Search in data")

        display_df = df_filtered[selected_cols].copy()

        if search_term:
            mask = display_df.astype(str).apply(
                lambda x: x.str.contains(search_term, case=False, na=False)
            ).any(axis=1)
            display_df = display_df[mask]

        st.dataframe(display_df, use_container_width=True, height=400)

        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name=f"CA_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        st.subheader("📊 Data Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", len(display_df))
        with col2:
            st.metric("Total Columns", len(selected_cols))
        with col3:
            st.metric("Unique Apps", display_df['apps_id'].nunique() if 'apps_id' in selected_cols else "N/A")

    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: #666;'>"
        f"<p>Credit Analyst Analytics Dashboard - Built with Streamlit & Plotly</p>"
        f"<p>Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        f"</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
