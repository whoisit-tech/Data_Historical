import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ========== KONFIGURASI ==========
st.set_page_config(page_title="CA Analytics Ultimate", layout="wide", page_icon="📊")

FILE_NAME = "HistoricalCA.xlsx"

# Custom CSS
st.markdown("""
<style>
    .big-title { font-size: 48px; font-weight: bold; color: #667eea; text-align: center; }
    .insight-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px; border-radius: 15px; color: white;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1); margin: 10px 0;
    }
    .warning-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px; border-radius: 15px; color: white;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1); margin: 10px 0;
    }
    .success-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 20px; border-radius: 15px; color: white;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1); margin: 10px 0;
    }
    .info-card {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 20px; border-radius: 15px; color: white;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1); margin: 10px 0;
    }
    .metric-big { font-size: 32px; font-weight: bold; color: #1f77b4; }
    .metric-delta-up { color: #28a745; font-size: 18px; }
    .metric-delta-down { color: #dc3545; font-size: 18px; }
    h1 { color: #667eea; text-align: center; }
    h2 { color: #764ba2; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
    h3 { color: #8b5cf6; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f0f2f6; padding: 10px 20px; 
        border-radius: 8px; font-weight: bold;
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

# ========== HELPER FUNCTIONS ==========
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
        return result.to_pydatetime() if not pd.isna(result) else None
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
    
    # OSPH factor
    if pd.notna(row.get('OSPH_clean')):
        if row['OSPH_clean'] > 500000000:
            score += 30
        elif row['OSPH_clean'] > 250000000:
            score += 20
        else:
            score += 10
    
    # OD factor
    if pd.notna(row.get('LastOD_clean')):
        if row['LastOD_clean'] > 30:
            score += 40
        elif row['LastOD_clean'] > 10:
            score += 25
        elif row['LastOD_clean'] > 0:
            score += 15
    
    # SLA factor
    if pd.notna(row.get('SLA_Days')):
        if row['SLA_Days'] > 5:
            score += 20
        elif row['SLA_Days'] > 3:
            score += 10
    
    # Status factor
    if pd.notna(row.get('apps_status_clean')):
        if 'NOT RECOMMENDED' in str(row['apps_status_clean']):
            score += 10
    
    return min(score, 100)

def preprocess_data(df):
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Calculate SLA
    if 'action_on_parsed' in df.columns and 'RealisasiDate_parsed' in df.columns:
        df['SLA_Days'] = df.apply(lambda row: calculate_sla_days(row['action_on_parsed'], row['RealisasiDate_parsed']), axis=1)
    
    # Process OSPH
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(df['Outstanding_PH'].astype(str).str.replace(',', ''), errors='coerce')
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    # Process OD
    if 'LastOD' in df.columns:
        df['LastOD_clean'] = pd.to_numeric(df['LastOD'], errors='coerce')
    if 'max_OD' in df.columns:
        df['max_OD_clean'] = pd.to_numeric(df['max_OD'], errors='coerce')
    
    # Process Scoring
    if 'Hasil_Scoring_1' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring_1'].fillna('BELUM SCORING').astype(str).str.strip()
        df['Scoring_Detail'] = df['Scoring_Detail'].replace(['-', '', 'data historical'], 'BELUM SCORING')
        df['Is_Scored'] = ~df['Scoring_Detail'].isin(['BELUM SCORING', 'nan'])
        
        def get_group(x):
            x = str(x).upper()
            if 'APPROVE' in x:
                return 'APPROVE'
            elif 'REGULER' in x:
                return 'REGULER'
            elif 'REJECT' in x:
                return 'REJECT'
            elif 'PROGRESS' in x:
                return 'IN PROGRESS'
            else:
                return 'OTHER'
        df['Scoring_Group'] = df['Scoring_Detail'].apply(get_group)
    
    # Time features
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['MonthName'] = df['action_on_parsed'].dt.month_name()
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Date'] = df['action_on_parsed'].dt.date
        df['Year'] = df['action_on_parsed'].dt.year
        df['Quarter'] = df['action_on_parsed'].dt.quarter
        df['WeekOfYear'] = df['action_on_parsed'].dt.isocalendar().week
    
    # Clean string fields
    string_fields = ['apps_status', 'desc_status_apps', 'Produk', 'Pekerjaan', 'Jabatan',
                    'Pekerjaan_Pasangan', 'JenisKendaraan', 'branch_name', 'Tujuan_Kredit',
                    'position_name', 'user_name']
    for field in string_fields:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
    # Calculate Risk Score
    df['Risk_Score'] = df.apply(calculate_risk_score, axis=1)
    
    # Risk Category
    df['Risk_Category'] = pd.cut(df['Risk_Score'], 
                                  bins=[0, 30, 60, 100], 
                                  labels=['Low Risk', 'Medium Risk', 'High Risk'])
    
    return df

@st.cache_data
def load_data():
    try:
        if not Path(FILE_NAME).exists():
            st.error(f"❌ File tidak ditemukan!")
            return None
        df = pd.read_excel(FILE_NAME)
        return preprocess_data(df)
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def generate_advanced_insights(df):
    """Generate comprehensive insights"""
    insights = []
    warnings = []
    successes = []
    recommendations = []
    
    # 1. OSPH Analysis
    if 'OSPH_Category' in df.columns and 'Scoring_Group' in df.columns:
        osph_approval = df.groupby('OSPH_Category').apply(
            lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        ).to_dict()
        if osph_approval:
            best_osph = max(osph_approval, key=osph_approval.get)
            worst_osph = min(osph_approval, key=osph_approval.get)
            successes.append(f"🎯 **Best Segment**: {best_osph} - Approval rate {osph_approval[best_osph]:.1f}%")
            if osph_approval[worst_osph] < 30:
                warnings.append(f"⚠️ {worst_osph} approval rate rendah ({osph_approval[worst_osph]:.1f}%) - Review criteria")
                recommendations.append(f"📋 Tighten screening untuk {worst_osph} atau adjust pricing")
    
    # 2. SLA Performance
    if 'SLA_Days' in df.columns:
        sla_data = df['SLA_Days'].dropna()
        if len(sla_data) > 0:
            avg_sla = sla_data.mean()
            median_sla = sla_data.median()
            within_3days = (sla_data <= 3).sum() / len(sla_data) * 100
            
            if avg_sla <= 3:
                successes.append(f"✅ **SLA Excellent**: Avg {avg_sla:.1f} hari kerja")
            elif avg_sla > 5:
                warnings.append(f"⚠️ **SLA Alert**: Avg {avg_sla:.1f} hari (target: 3 hari)")
                recommendations.append("📋 Increase CA bandwidth atau streamline approval process")
            
            insights.append(f"📊 {within_3days:.1f}% aplikasi selesai ≤3 hari kerja")
            
            if median_sla < avg_sla - 1:
                insights.append(f"⚡ Ada outliers: Median {median_sla:.1f}d vs Mean {avg_sla:.1f}d")
    
    # 3. CA Workload Balance
    if 'user_name' in df.columns and 'apps_id' in df.columns:
        ca_workload = df.groupby('user_name')['apps_id'].nunique()
        if len(ca_workload) > 1:
            avg_workload = ca_workload.mean()
            max_workload = ca_workload.max()
            min_workload = ca_workload.min()
            std_workload = ca_workload.std()
            
            if max_workload > avg_workload * 1.5:
                warnings.append(f"⚠️ **Workload Imbalance**: Max {max_workload:.0f} vs Avg {avg_workload:.0f} apps")
                recommendations.append("📋 Redistribute workload - transfer dari CA overloaded ke yang underutilized")
            
            if std_workload / avg_workload > 0.3:
                insights.append(f"📊 High variance in CA workload (CV: {std_workload/avg_workload:.2f})")
    
    # 4. Product Performance
    if 'Produk_clean' in df.columns and 'Scoring_Group' in df.columns:
        prod_approval = df.groupby('Produk_clean').apply(
            lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        ).to_dict()
        if prod_approval:
            best_prod = max(prod_approval, key=prod_approval.get)
            worst_prod = min(prod_approval, key=prod_approval.get)
            successes.append(f"🚗 **Best Product**: {best_prod} ({prod_approval[best_prod]:.1f}% approval)")
            
            if prod_approval[worst_prod] < 40:
                warnings.append(f"⚠️ {worst_prod} underperforming ({prod_approval[worst_prod]:.1f}%)")
                recommendations.append(f"📋 Review {worst_prod} product criteria atau target market")
    
    # 5. Branch Performance
    if 'branch_name_clean' in df.columns and 'Scoring_Group' in df.columns:
        branch_approval = df.groupby('branch_name_clean').apply(
            lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        ).to_dict()
        if branch_approval:
            best_branch = max(branch_approval, key=branch_approval.get)
            worst_branch = min(branch_approval, key=branch_approval.get)
            
            if branch_approval[best_branch] - branch_approval[worst_branch] > 20:
                insights.append(f"🏢 Large branch variance: {best_branch} ({branch_approval[best_branch]:.1f}%) vs {worst_branch} ({branch_approval[worst_branch]:.1f}%)")
                recommendations.append(f"📋 Share best practices dari {best_branch} ke {worst_branch}")
    
    # 6. Peak Hours Analysis
    if 'Hour' in df.columns:
        hourly = df.groupby('Hour').size()
        if len(hourly) > 0:
            peak_hour = hourly.idxmax()
            peak_count = hourly.max()
            off_peak = hourly.min()
            
            insights.append(f"🕐 Peak Hour: {peak_hour}:00 ({peak_count} apps)")
            
            if peak_count / off_peak > 3:
                warnings.append(f"⚠️ High peak variance - {peak_count} apps at peak vs {off_peak} off-peak")
                recommendations.append("📋 Consider staggered work hours atau workload distribution")
    
    # 7. Risk Analysis
    if 'Risk_Category' in df.columns:
        high_risk = len(df[df['Risk_Category'] == 'High Risk'])
        high_risk_pct = high_risk / len(df) * 100
        
        if high_risk_pct > 20:
            warnings.append(f"⚠️ {high_risk_pct:.1f}% applications are High Risk ({high_risk} apps)")
            recommendations.append("📋 Implement stricter screening for high-risk segments")
        elif high_risk_pct < 10:
            successes.append(f"✅ Low risk portfolio: Only {high_risk_pct:.1f}% high risk")
    
    # 8. Occupation Analysis
    if 'Pekerjaan_clean' in df.columns and 'Scoring_Group' in df.columns:
        pek_approval = df.groupby('Pekerjaan_clean').apply(
            lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        ).to_dict()
        if pek_approval:
            pek_sorted = sorted(pek_approval.items(), key=lambda x: x[1], reverse=True)
            if len(pek_sorted) > 0:
                insights.append(f"💼 Best Occupation: {pek_sorted[0][0]} ({pek_sorted[0][1]:.1f}% approval)")
    
    # 9. Trend Analysis
    if 'YearMonth' in df.columns and 'Scoring_Group' in df.columns:
        monthly_approval = df.groupby('YearMonth').apply(
            lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        )
        if len(monthly_approval) >= 2:
            trend = monthly_approval.iloc[-1] - monthly_approval.iloc[-2]
            if abs(trend) > 5:
                if trend > 0:
                    successes.append(f"📈 Approval rate trending UP: +{trend:.1f}% MoM")
                else:
                    warnings.append(f"📉 Approval rate trending DOWN: {trend:.1f}% MoM")
                    recommendations.append("📋 Investigate причин decline dan implement corrective actions")
    
    return insights, warnings, successes, recommendations

# ========== MAIN APP ==========
def main():
    st.markdown('<h1 class="big-title">🎯 CA ANALYTICS ULTIMATE DASHBOARD</h1>', unsafe_allow_html=True)
    st.markdown("### Complete Business Intelligence for Credit Analyst Operations")
    st.markdown("---")
    
    # Load data
    with st.spinner("⏳ Loading and processing data..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("❌ Failed to load data")
        st.stop()
    
    st.success(f"✅ **{len(df):,}** records loaded | **{df['apps_id'].nunique() if 'apps_id' in df.columns else 0:,}** unique applications | **{len(df.columns)}** fields analyzed")
    
    # ========== SIDEBAR ==========
    st.sidebar.title("🎛️ Control Panel")
    st.sidebar.markdown("---")
    
    # Filters
    st.sidebar.subheader("🔍 Filters")
    
    selected_product = st.sidebar.selectbox(
        "🚗 Product",
        ['All'] + sorted(df['Produk_clean'].unique().tolist()) if 'Produk_clean' in df.columns else ['All']
    )
    
    selected_branch = st.sidebar.selectbox(
        "🏢 Branch",
        ['All'] + sorted(df['branch_name_clean'].unique().tolist()) if 'branch_name_clean' in df.columns else ['All']
    )
    
    selected_ca = st.sidebar.selectbox(
        "👤 CA",
        ['All'] + sorted(df['user_name_clean'].unique().tolist()) if 'user_name_clean' in df.columns else ['All']
    )
    
    selected_osph = st.sidebar.selectbox(
        "💰 OSPH Range",
        ['All'] + sorted([x for x in df['OSPH_Category'].unique() if x != 'Unknown']) if 'OSPH_Category' in df.columns else ['All']
    )
    
    selected_risk = st.sidebar.selectbox(
        "⚠️ Risk Category",
        ['All'] + list(df['Risk_Category'].unique()) if 'Risk_Category' in df.columns else ['All']
    )
    
    # Date range
    date_range = None
    if 'action_on_parsed' in df.columns:
        df_dates = df[df['action_on_parsed'].notna()]
        if len(df_dates) > 0:
            min_date = df_dates['action_on_parsed'].min().date()
            max_date = df_dates['action_on_parsed'].max().date()
            date_range = st.sidebar.date_input("📅 Date Range", value=(min_date, max_date))
    
    # Apply filters
    df_filtered = df.copy()
    
    if selected_product != 'All':
        df_filtered = df_filtered[df_filtered['Produk_clean'] == selected_product]
    if selected_branch != 'All':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    if selected_ca != 'All':
        df_filtered = df_filtered[df_filtered['user_name_clean'] == selected_ca]
    if selected_osph != 'All':
        df_filtered = df_filtered[df_filtered['OSPH_Category'] == selected_osph]
    if selected_risk != 'All':
        df_filtered = df_filtered[df_filtered['Risk_Category'] == selected_risk]
    
    if date_range and len(date_range) == 2 and 'action_on_parsed' in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered['action_on_parsed'].notna()) &
            (df_filtered['action_on_parsed'].dt.date >= date_range[0]) &
            (df_filtered['action_on_parsed'].dt.date <= date_range[1])
        ]
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 Showing: **{len(df_filtered):,}** records\n\n({len(df_filtered)/len(df)*100:.1f}% of total)")
    
    if st.sidebar.button("🔄 Reset All Filters"):
        st.rerun()
    
    # ========== EXECUTIVE SUMMARY ==========
    st.header("📊 Executive Summary & Intelligence")
    
    # Generate insights
    insights, warnings, successes, recommendations = generate_advanced_insights(df_filtered)
    
    # Display in 4 columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="success-card">', unsafe_allow_html=True)
        st.markdown("### ✅ Wins")
        for s in successes[:3]:
            st.markdown(f"**{s}**")
        if not successes:
            st.markdown("_No major wins_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="insight-card">', unsafe_allow_html=True)
        st.markdown("### 💡 Insights")
        for i in insights[:3]:
            st.markdown(f"**{i}**")
        if not insights:
            st.markdown("_No insights_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="warning-card">', unsafe_allow_html=True)
        st.markdown("### ⚠️ Alerts")
        for w in warnings[:3]:
            st.markdown(f"**{w}**")
        if not warnings:
            st.markdown("✅ _All healthy_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### 📋 Actions")
        for r in recommendations[:3]:
            st.markdown(f"**{r}**")
        if not recommendations:
            st.markdown("_No actions needed_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========== KPI DASHBOARD ==========
    st.header("📈 Key Performance Indicators")
    
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        total_apps = df_filtered['apps_id'].nunique() if 'apps_id' in df_filtered.columns else 0
        st.metric("📝 Total Apps", f"{total_apps:,}")
    
    with kpi2:
        avg_sla = df_filtered['SLA_Days'].mean() if 'SLA_Days' in df_filtered.columns else 0
        sla_emoji = "🟢" if avg_sla <= 3 else "🟡" if avg_sla <= 5 else "🔴"
        st.metric("⏱️ Avg SLA", f"{avg_sla:.1f}d {sla_emoji}")
    
    with kpi3:
        if 'Scoring_Group' in df_filtered.columns:
            approved = (df_filtered['Scoring_Group'] == 'APPROVE').sum()
            total_scored = len(df_filtered[df_filtered['Scoring_Group'] != 'OTHER'])
            rate = approved / total_scored * 100 if total_scored > 0 else 0
            st.metric("✅ Approval", f"{rate:.1f}%")
    
    with kpi4:
        avg_osph = df_filtered['OSPH_clean'].mean() if 'OSPH_clean' in df_filtered.columns else 0
        st.metric("💰 Avg OSPH", f"{avg_osph/1e6:.1f}M")
    
    with kpi5:
        total_ca = df_filtered['user_name'].nunique() if 'user_name' in df_filtered.columns else 0
        st.metric("👥 Active CA", f"{total_ca:,}")
    
    with kpi6:
        avg_risk = df_filtered['Risk_Score'].mean() if 'Risk_Score' in df_filtered.columns else 0
        risk_emoji = "🟢" if avg_risk < 30 else "🟡" if avg_risk < 60 else "🔴"
        st.metric("⚠️ Risk Score", f"{avg_risk:.0f} {risk_emoji}")
    
    # Additional KPIs Row 2
    kpi7, kpi8, kpi9, kpi10, kpi11, kpi12 = st.columns(6)
    
    with kpi7:
        recommended = len(df_filtered[df_filtered['apps_status_clean'].str.contains('RECOMMENDED CA', na=False)])
        st.metric("👍 Recommended", f"{recommended:,}")
    
    with kpi8:
        not_recommended = len(df_filtered[df_filtered['apps_status_clean'].str.contains('NOT RECOMMENDED', na=False)])
        st.metric("❌ Not Rec", f"{not_recommended:,}")
    
    with kpi9:
        pending = len(df_filtered[df_filtered['apps_status_clean'].str.contains('PENDING', na=False)])
        st.metric("⏳ Pending", f"{pending:,}")
    
    with kpi10:
        if 'LastOD_clean' in df_filtered.columns:
            avg_od = df_filtered['LastOD_clean'].mean()
            st.metric("📊 Avg LastOD", f"{avg_od:.0f}" if not pd.isna(avg_od) else "N/A")
    
    with kpi11:
        work_hours_compliance = 0
        if 'Hour' in df_filtered.columns:
            total = len(df_filtered[df_filtered['Hour'].notna()])
            within = len(df_filtered[(df_filtered['Hour'] >= 8) & (df_filtered['Hour'] <= 15)])
            work_hours_compliance = within / total * 100 if total > 0 else 0
        st.metric("🕐 Work Hours", f"{work_hours_compliance:.0f}%")
    
    with kpi12:
        high_risk_count = len(df_filtered[df_filtered['Risk_Category'] == 'High Risk']) if 'Risk_Category' in df_filtered.columns else 0
        st.metric("🔴 High Risk", f"{high_risk_count:,}")
    
    st.markdown("---")
    
    # ========== MAIN TABS ==========
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "🎯 OSPH Strategy",
        "👥 CA Performance",
        "📊 Scoring Analysis",
        "🚗 Product & Branch",
        "💼 Occupation & Vehicle",
        "⚠️ Risk Analysis",
        "📈 Trends & Forecasting",
        "🔍 Advanced Analytics",
        "📋 Complete Data"
    ])
    
    # ========== TAB 1: OSPH STRATEGY ==========
    with tab1:
        st.header("💰 OSPH Range Strategy & Optimization")
        
        if 'OSPH_Category' in df_filtered.columns:
            # Summary Table
            st.subheader("📊 Performance by OSPH Range")
            
            osph_data = []
            for osph in sorted(df_filtered['OSPH_Category'].unique()):
                if osph == 'Unknown':
                    continue
                df_o = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                apps = df_o['apps_id'].nunique()
                approve = len(df_o[df_o['Scoring_Group'] == 'APPROVE'])
                reguler = len(df_o[df_o['Scoring_Group'] == 'REGULER'])
                reject = len(df_o[df_o['Scoring_Group'] == 'REJECT'])
                total_scored = approve + reguler + reject
                
                approval_rate = approve / total_scored * 100 if total_scored > 0 else 0
                reject_rate = reject / total_scored * 100 if total_scored > 0 else 0
                
                avg_sla = df_o['SLA_Days'].mean() if 'SLA_Days' in df_o.columns else 0
                avg_osph_val = df_o['OSPH_clean'].mean() if 'OSPH_clean' in df_o.columns else 0
                
                # Risk
                high_risk = len(df_o[df_o['Risk_Category'] == 'High Risk']) if 'Risk_Category' in df_o.columns else 0
                risk_pct = high_risk / len(df_o) * 100 if len(df_o) > 0 else 0
                
                # Strategy recommendation
                if approval_rate > 60 and reject_rate < 20:
                    strategy = "✅ Priority Segment"
                elif approval_rate > 40:
                    strategy = "⚠️ Monitor Closely"
                else:
                    strategy = "🔴 Review Criteria"
                
                osph_data.append({
                    'Range': osph,
                    'Apps': apps,
                    '% Volume': f"{apps/total_apps*100:.1f}%",
                    'APPROVE': approve,
                    'REGULER': reguler,
                    'REJECT': reject,
                    'Approval %': f"{approval_rate:.1f}%",
                    'Reject %': f"{reject_rate:.1f}%",
                    'Avg SLA': f"{avg_sla:.1f}d",
                    'Avg Value': f"Rp{avg_osph_val/1e6:.0f}M",
                    'High Risk %': f"{risk_pct:.1f}%",
                    '🎯 Strategy': strategy
                })
            
            osph_df = pd.DataFrame(osph_data)
            st.dataframe(osph_df, use_container_width=True, hide_index=True)
            
            # Visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(osph_df, values='Apps', names='Range',
                           title="📊 Volume Distribution by OSPH", hole=0.4,
                           color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                osph_df['Approval_num'] = osph_df['Approval %'].str.replace('%', '').astype(float)
                fig = px.bar(osph_df, x='Range', y='Approval_num',
                           title="✅ Approval Rate Comparison",
                           color='Approval_num',
                           color_continuous_scale='RdYlGn',
                           text='Approval %')
                fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Target: 50%")
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            
            # Scoring breakdown
            st.subheader("📋 Detailed Scoring by OSPH")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(osph_df, x='Range', y=['APPROVE', 'REGULER', 'REJECT'],
                           title="Scoring Distribution by OSPH", barmode='stack',
                           color_discrete_map={'APPROVE': '#28a745', 'REGULER': '#ffc107', 'REJECT': '#dc3545'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                osph_df['Reject_num'] = osph_df['Reject %'].str.replace('%', '').astype(float)
                fig = px.scatter(osph_df, x='Approval_num', y='Reject_num', size='Apps',
                               hover_data=['Range'], title="Approval vs Reject Rate",
                               labels={'Approval_num': 'Approval %', 'Reject_num': 'Reject %'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Hierarchy Analysis
            st.subheader("🔍 Complete Hierarchy: Product → OSPH → Vehicle → Occupation")
            
            if all(col in df_filtered.columns for col in ['Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean']):
                hier = df_filtered.groupby(['Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean']).agg({
                    'apps_id': 'nunique',
                    'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                }).reset_index()
                hier.columns = ['Product', 'OSPH', 'Vehicle', 'Occupation', 'Apps', 'Approval %']
                hier = hier.sort_values('Apps', ascending=False)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig = px.sunburst(hier.head(50),
                                    path=['Product', 'OSPH', 'Vehicle', 'Occupation'],
                                    values='Apps',
                                    color='Approval %',
                                    color_continuous_scale='RdYlGn',
                                    title="Hierarchy Sunburst (Top 50)")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Top 15 Combinations:**")
                    hier['Approval %'] = hier['Approval %'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(hier.head(15), hide_index=True, height=400)
            
            # Pattern Detection
            st.subheader("📈 Detected Patterns (Kecenderungan)")
            
            patterns = []
            
            # Pattern 1: Volume concentration
            top_range = osph_df.iloc[0]
            if float(top_range['% Volume'].replace('%', '')) > 60:
                patterns.append(f"📊 **High Concentration**: {top_range['Range']} dominates with {top_range['% Volume']} of volume")
            
            # Pattern 2: Approval trend by value
            if len(osph_df) >= 3:
                low_approval = osph_df[osph_df['Range'] == '0 - 250 Juta']['Approval_num'].values[0] if '0 - 250 Juta' in osph_df['Range'].values else 0
                high_approval = osph_df[osph_df['Range'] == '500 Juta+']['Approval_num'].values[0] if '500 Juta+' in osph_df['Range'].values else 0
                
                if low_approval > high_approval + 10:
                    patterns.append(f"✅ **Low-value strength**: Lower OSPH has {low_approval:.1f}% approval vs {high_approval:.1f}% for high OSPH → Mass market strategy works")
                elif high_approval > low_approval + 10:
                    patterns.append(f"💰 **Premium potential**: High OSPH shows {high_approval:.1f}% approval → Focus on premium segment")
            
            # Pattern 3: Risk correlation
            osph_df['Risk_num'] = osph_df['High Risk %'].str.replace('%', '').astype(float)
            high_risk_range = osph_df.loc[osph_df['Risk_num'].idxmax()]
            if high_risk_range['Risk_num'] > 30:
                patterns.append(f"⚠️ **Risk concentration**: {high_risk_range['Range']} has {high_risk_range['High Risk %']} high-risk apps → Tighten criteria")
            
            # Pattern 4: SLA by OSPH
            osph_df['SLA_num'] = osph_df['Avg SLA'].str.replace('d', '').astype(float)
            if osph_df['SLA_num'].max() - osph_df['SLA_num'].min() > 2:
                slow_range = osph_df.loc[osph_df['SLA_num'].idxmax()]
                patterns.append(f"⏱️ **SLA variance**: {slow_range['Range']} takes {slow_range['Avg SLA']} (slowest) → Needs process optimization")
            
            for p in patterns:
                st.markdown(f'<div class="insight-card">{p}</div>', unsafe_allow_html=True)
    
    # ========== TAB 2: CA PERFORMANCE ==========
    with tab2:
        st.header("👥 CA Performance Ranking & Analysis")
        
        if 'user_name_clean' in df_filtered.columns:
            # CA Performance Table
            st.subheader("📊 Complete CA Performance Metrics")
            
            ca_data = []
            for ca in df_filtered['user_name_clean'].unique():
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                position = df_ca['position_name_clean'].mode()[0] if 'position_name_clean' in df_ca.columns and len(df_ca) > 0 else 'Unknown'
                
                apps = df_ca['apps_id'].nunique()
                records = len(df_ca)
                
                sla = df_ca['SLA_Days'].mean() if 'SLA_Days' in df_ca.columns else 0
                
                approve = len(df_ca[df_ca['Scoring_Group'] == 'APPROVE'])
                reguler = len(df_ca[df_ca['Scoring_Group'] == 'REGULER'])
                reject = len(df_ca[df_ca['Scoring_Group'] == 'REJECT'])
                total_scored = approve + reguler + reject
                
                approval_rate = approve / total_scored * 100 if total_scored > 0 else 0
                
                avg_osph = df_ca['OSPH_clean'].mean() if 'OSPH_clean' in df_ca.columns else 0
                
                # Productivity score
                productivity = apps / sla if sla > 0 else 0
                
                # Quality score (weighted: 60% approval, 20% reguler, -20% reject)
                quality = (approval_rate * 0.6 + (reguler/total_scored*100 if total_scored > 0 else 0) * 0.2 - (reject/total_scored*100 if total_scored > 0 else 0) * 0.2) if total_scored > 0 else 0
                
                # Overall rating
                if approval_rate > 60 and sla <= 3:
                    rating = "⭐⭐⭐"
                elif approval_rate > 40 and sla <= 5:
                    rating = "⭐⭐"
                else:
                    rating = "⭐"
                
                ca_data.append({
                    'CA': ca,
                    'Position': position,
                    'Apps': apps,
                    'Records': records,
                    'Avg SLA': f"{sla:.1f}d",
                    'APPROVE': approve,
                    'REGULER': reguler,
                    'REJECT': reject,
                    'Approval %': f"{approval_rate:.1f}%",
                    'Avg OSPH': f"Rp{avg_osph/1e6:.0f}M",
                    'Productivity': f"{productivity:.1f}",
                    'Quality Score': f"{quality:.1f}",
                    '⭐ Rating': rating
                })
            
            ca_df = pd.DataFrame(ca_data).sort_values('Apps', ascending=False)
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            # Visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(ca_df.head(10), x='CA', y='Apps',
                           title="🏆 Top 10 CA by Volume",
                           color='Apps',
                           color_continuous_scale='Blues',
                           text='Apps')
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                ca_df['Approval_num'] = ca_df['Approval %'].str.replace('%', '').astype(float)
                ca_df['SLA_num'] = ca_df['Avg SLA'].str.replace('d', '').astype(float)
                
                fig = px.scatter(ca_df, x='SLA_num', y='Approval_num',
                               size='Apps', hover_data=['CA'],
                               title="⚖️ SLA vs Approval Rate",
                               labels={'SLA_num': 'Avg SLA (days)', 'Approval_num': 'Approval %'},
                               color='Approval_num',
                               color_continuous_scale='RdYlGn')
                fig.add_vline(x=3, line_dash="dash", line_color="green", annotation_text="Target SLA")
                fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Target Approval")
                st.plotly_chart(fig, use_container_width=True)
            
            # CA Comparison
            st.subheader("📊 CA Comparison Matrix")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(ca_df.head(10), x='CA', y=['APPROVE', 'REGULER', 'REJECT'],
                           title="Scoring Distribution - Top 10 CA", barmode='stack',
                           color_discrete_map={'APPROVE': '#28a745', 'REGULER': '#ffc107', 'REJECT': '#dc3545'})
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                ca_df['Quality_num'] = ca_df['Quality Score'].str.replace('%', '').astype(float)
                ca_df['Productivity_num'] = ca_df['Productivity'].astype(float)
                
                fig = px.scatter(ca_df, x='Productivity_num', y='Quality_num',
                               size='Apps', hover_data=['CA'],
                               title="📈 Productivity vs Quality",
                               labels={'Productivity_num': 'Productivity', 'Quality_num': 'Quality Score'},
                               color='Apps',
                               color_continuous_scale='Viridis')
                st.plotly_chart(fig, use_container_width=True)
            
            # CA Insights
            st.subheader("💡 CA Performance Insights")
            
            insights_ca = []
            
            # Top performer
            top_ca = ca_df.iloc[0]
            insights_ca.append(f"🏆 **Top Volume**: {top_ca['CA']} handled {top_ca['Apps']} apps")
            
            # Best approval
            best_approval_ca = ca_df.loc[ca_df['Approval_num'].idxmax()]
            insights_ca.append(f"✅ **Best Approval**: {best_approval_ca['CA']} with {best_approval_ca['Approval %']} approval rate")
            
            # Fastest processing
            fastest_ca = ca_df.loc[ca_df['SLA_num'].idxmin()]
            insights_ca.append(f"⚡ **Fastest**: {fastest_ca['CA']} avg SLA {fastest_ca['Avg SLA']}")
            
            # Workload distribution
            max_apps = ca_df['Apps'].max()
            min_apps = ca_df['Apps'].min()
            if max_apps > min_apps * 2:
                insights_ca.append(f"⚠️ **Workload Gap**: {min_apps}-{max_apps} apps range → Redistribution needed")
            
            # Quality leaders
            top_quality = ca_df.nlargest(3, 'Quality_num')
            insights_ca.append(f"🌟 **Quality Leaders**: {', '.join(top_quality['CA'].tolist())}")
            
            for i in insights_ca:
                st.markdown(f'<div class="success-card">{i}</div>', unsafe_allow_html=True)
    
    # ========== TAB 3: SCORING ANALYSIS ==========
    with tab3:
        st.header("📊 Complete Scoring Analysis (No Grouping)")
        
        if 'Scoring_Detail' in df_filtered.columns:
            # Scoring breakdown
            scoring = df_filtered['Scoring_Detail'].value_counts().reset_index()
            scoring.columns = ['Scoring', 'Count']
            scoring['%'] = (scoring['Count'] / len(df_filtered) * 100).round(2)
            scoring['Cumulative %'] = scoring['%'].cumsum().round(2)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.bar(scoring, x='Scoring', y='Count',
                           title="📋 All Scoring Results Distribution",
                           color='Count',
                           color_continuous_scale='Viridis',
                           text='Count')
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45, height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Scoring Breakdown:**")
                st.dataframe(scoring, hide_index=True, height=500)
            
            # Scoring by Product
            if 'Produk_clean' in df_filtered.columns:
                st.subheader("🚗 Scoring by Product")
                
                scoring_prod = df_filtered.groupby(['Produk_clean', 'Scoring_Detail']).size().reset_index(name='Count')
                
                fig = px.bar(scoring_prod, x='Produk_clean', y='Count',
                           color='Scoring_Detail', title="Scoring Distribution by Product",
                           barmode='stack', height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Scoring by OSPH
            if 'OSPH_Category' in df_filtered.columns:
                st.subheader("💰 Scoring by OSPH Range")
                
                scoring_osph = df_filtered.groupby(['OSPH_Category', 'Scoring_Detail']).size().reset_index(name='Count')
                
                fig = px.bar(scoring_osph, x='OSPH_Category', y='Count',
                           color='Scoring_Detail', title="Scoring Distribution by OSPH",
                           barmode='stack', height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Scoring by Branch
            if 'branch_name_clean' in df_filtered.columns:
                st.subheader("🏢 Scoring by Branch")
                
                scoring_branch = df_filtered.groupby(['branch_name_clean', 'Scoring_Detail']).size().reset_index(name='Count')
                top_branches = scoring_branch.groupby('branch_name_clean')['Count'].sum().nlargest(10).index
                scoring_branch_top = scoring_branch[scoring_branch['branch_name_clean'].isin(top_branches)]
                
                fig = px.bar(scoring_branch_top, x='branch_name_clean', y='Count',
                           color='Scoring_Detail', title="Scoring Distribution - Top 10 Branches",
                           barmode='stack', height=400)
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    # ========== TAB 4: PRODUCT & BRANCH ==========
    with tab4:
        st.header("🚗 Product & Branch Performance")
        
        col1, col2 = st.columns(2)
        
        # Product Analysis
        with col1:
            st.subheader("🚗 Product Performance")
            
            if 'Produk_clean' in df_filtered.columns:
                prod_data = []
                for prod in df_filtered['Produk_clean'].unique():
                    df_prod = df_filtered[df_filtered['Produk_clean'] == prod]
                    
                    apps = df_prod['apps_id'].nunique()
                    approve = len(df_prod[df_prod['Scoring_Group'] == 'APPROVE'])
                    total = len(df_prod[df_prod['Scoring_Group'] != 'OTHER'])
                    rate = approve / total * 100 if total > 0 else 0
                    
                    avg_sla = df_prod['SLA_Days'].mean()
                    avg_osph = df_prod['OSPH_clean'].mean()
                    
                    prod_data.append({
                        'Product': prod,
                        'Apps': apps,
                        'Approval %': f"{rate:.1f}%",
                        'Avg SLA': f"{avg_sla:.1f}d" if not pd.isna(avg_sla) else "-",
                        'Avg OSPH': f"Rp{avg_osph/1e6:.0f}M" if not pd.isna(avg_osph) else "-"
                    })
                
                prod_df = pd.DataFrame(prod_data).sort_values('Apps', ascending=False)
                st.dataframe(prod_df, hide_index=True)
                
                fig = px.pie(prod_df, values='Apps', names='Product',
                           title="Product Volume Distribution", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        
        # Branch Analysis
        with col2:
            st.subheader("🏢 Branch Performance")
            
            if 'branch_name_clean' in df_filtered.columns:
                branch_data = []
                for branch in df_filtered['branch_name_clean'].unique():
                    df_branch = df_filtered[df_filtered['branch_name_clean'] == branch]
                    
                    apps = df_branch['apps_id'].nunique()
                    approve = len(df_branch[df_branch['Scoring_Group'] == 'APPROVE'])
                    total = len(df_branch[df_branch['Scoring_Group'] != 'OTHER'])
                    rate = approve / total * 100 if total > 0 else 0
                    
                    avg_sla = df_branch['SLA_Days'].mean()
                    
                    branch_data.append({
                        'Branch': branch,
                        'Apps': apps,
                        'Approval %': f"{rate:.1f}%",
                        'Avg SLA': f"{avg_sla:.1f}d" if not pd.isna(avg_sla) else "-"
                    })
                
                branch_df = pd.DataFrame(branch_data).sort_values('Apps', ascending=False)
                st.dataframe(branch_df.head(15), hide_index=True)
                
                fig = px.bar(branch_df.head(10), x='Branch', y='Apps',
                           title="Top 10 Branches", color='Apps')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    # ========== TAB 5: OCCUPATION & VEHICLE ==========
    with tab5:
        st.header("💼 Occupation & Vehicle Analysis")
        
        col1, col2 = st.columns(2)
        
        # Occupation
        with col1:
            st.subheader("💼 Top Occupations")
            
            if 'Pekerjaan_clean' in df_filtered.columns:
                pek = df_filtered['Pekerjaan_clean'].value_counts().head(15).reset_index()
                pek.columns = ['Occupation', 'Count']
                
                st.dataframe(pek, hide_index=True)
                
                fig = px.bar(pek, x='Occupation', y='Count',
                           title="Top 15 Occupations", color='Count')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
        
        # Vehicle
        with col2:
            st.subheader("🚙 Vehicle Types")
            
            if 'JenisKendaraan_clean' in df_filtered.columns:
                veh = df_filtered['JenisKendaraan_clean'].value_counts().reset_index()
                veh.columns = ['Vehicle', 'Count']
                
                st.dataframe(veh, hide_index=True)
                
                fig = px.pie(veh, values='Count', names='Vehicle',
                           title="Vehicle Distribution", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
    
    # ========== TAB 6: RISK ANALYSIS ==========
    with tab6:
        st.header("⚠️ Risk Analysis & Management")
        
        if 'Risk_Category' in df_filtered.columns:
            # Risk distribution
            risk_dist = df_filtered['Risk_Category'].value_counts().reset_index()
            risk_dist.columns = ['Risk Category', 'Count']
            risk_dist['%'] = (risk_dist['Count'] / len(df_filtered) * 100).round(1)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.dataframe(risk_dist, hide_index=True)
            
            with col2:
                fig = px.pie(risk_dist, values='Count', names='Risk Category',
                           title="Risk Portfolio Distribution",
                           color='Risk Category',
                           color_discrete_map={'Low Risk': '#28a745', 'Medium Risk': '#ffc107', 'High Risk': '#dc3545'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Risk by OSPH
            if 'OSPH_Category' in df_filtered.columns:
                st.subheader("Risk by OSPH Range")
                
                risk_osph = df_filtered.groupby(['OSPH_Category', 'Risk_Category']).size().reset_index(name='Count')
                
                fig = px.bar(risk_osph, x='OSPH_Category', y='Count',
                           color='Risk_Category', barmode='group',
                           title="Risk Distribution by OSPH",
                           color_discrete_map={'Low Risk': '#28a745', 'Medium Risk': '#ffc107', 'High Risk': '#dc3545'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Risk factors
            st.subheader("📊 Risk Factor Analysis")
