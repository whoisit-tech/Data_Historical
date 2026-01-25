import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

st.set_page_config(page_title="CA Analytics Ultimate", layout="wide", page_icon="📊")

FILE_NAME = "HistoricalCA.xlsx"

st.markdown("""
<style>
    .insight-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; margin: 10px 0; }
    .warning-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 15px; color: white; margin: 10px 0; }
    .success-card { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 20px; border-radius: 15px; color: white; margin: 10px 0; }
    .info-card { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 20px; border-radius: 15px; color: white; margin: 10px 0; }
    h1 { color: #667eea; text-align: center; }
    h2 { color: #764ba2; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
    .metric-card { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

TANGGAL_MERAH = ["01-01-2025", "27-01-2025", "28-01-2025", "29-01-2025", "28-03-2025", "31-03-2025",
    "01-04-2025", "02-04-2025", "03-04-2025", "04-04-2025", "07-04-2025", "18-04-2025",
    "01-05-2025", "12-05-2025", "29-05-2025", "06-06-2025", "09-06-2025", "27-06-2025",
    "18-08-2025", "05-09-2025", "25-12-2025", "26-12-2025", "31-12-2025"]
TANGGAL_MERAH_DT = [datetime.strptime(d, "%d-%m-%Y").date() for d in TANGGAL_MERAH]

def parse_date(date_str):
    if pd.isna(date_str) or date_str == '-':
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        for fmt in ["%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                return datetime.strptime(str(date_str).split('.')[0], fmt)
            except:
                continue
        return pd.to_datetime(date_str, errors='coerce').to_pydatetime()
    except:
        return None

def is_working_day(date):
    if pd.isna(date):
        return False
    if not isinstance(date, datetime):
        date = pd.to_datetime(date)
    return date.weekday() < 5 and date.date() not in TANGGAL_MERAH_DT

def calculate_sla_days(start_dt, end_dt):
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
        return "500 Juta+"
    except:
        return "Unknown"

def calculate_risk_score(row):
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
    if pd.notna(row.get('SLA_Days')):
        if row['SLA_Days'] > 5:
            score += 20
        elif row['SLA_Days'] > 3:
            score += 10
    return min(score, 100)

def preprocess_data(df):
    df = df.copy()
    
    # Parse dates
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    # Calculate SLA
    if all(c in df.columns for c in ['action_on_parsed', 'RealisasiDate_parsed']):
        df['SLA_Days'] = df.apply(lambda r: calculate_sla_days(r['action_on_parsed'], r['RealisasiDate_parsed']), axis=1)
    
    # OSPH
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(df['Outstanding_PH'].astype(str).str.replace(',', ''), errors='coerce')
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    # OD
    for col in ['LastOD', 'max_OD']:
        if col in df.columns:
            df[f'{col}_clean'] = pd.to_numeric(df[col], errors='coerce')
    
    # apps_status - JANGAN GROUPING, ambil semua nilai unik
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
    # Hasil_Scoring_1 - JANGAN GROUPING, simpan semua detail
    if 'Hasil_Scoring_1' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring_1'].fillna('-').astype(str).str.strip()
        df['Is_Scored'] = ~df['Scoring_Detail'].isin(['-', 'Scoring in Progress'])
    
    # Time features
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Quarter'] = df['action_on_parsed'].dt.quarter
    
    # Clean other fields
    for field in ['desc_status_apps', 'Produk', 'Pekerjaan', 'Jabatan',
                  'Pekerjaan_Pasangan', 'JenisKendaraan', 'branch_name', 'Tujuan_Kredit',
                  'user_name', 'position_name']:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
    # Risk scoring
    df['Risk_Score'] = df.apply(calculate_risk_score, axis=1)
    df['Risk_Category'] = pd.cut(df['Risk_Score'], bins=[0, 30, 60, 100], labels=['Low Risk', 'Medium Risk', 'High Risk'])
    
    return df

@st.cache_data
def load_data():
    try:
        if not Path(FILE_NAME).exists():
            st.error(f"❌ File tidak ditemukan: {FILE_NAME}")
            return None
        df = pd.read_excel(FILE_NAME)
        
        # Validasi kolom wajib
        required_cols = ['apps_id', 'position_name', 'user_name', 'apps_status', 'desc_status_apps', 
                        'Produk', 'action_on', 'Initiation', 'RealisasiDate', 'Outstanding_PH', 
                        'Pekerjaan', 'Jabatan', 'Pekerjaan_Pasangan', 'Hasil_Scoring_1', 
                        'JenisKendaraan', 'branch_name', 'Tujuan_Kredit', 'LastOD', 'max_OD']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"❌ Kolom tidak ditemukan: {', '.join(missing)}")
            return None
        
        return preprocess_data(df)
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return None

def generate_analytical_insights(df):
    insights = []
    warnings = []
    recommendations = []
    
    # 1. Analisis Korelasi OSPH vs Approval Rate
    if 'OSPH_Category' in df.columns and 'Scoring_Detail' in df.columns:
        for osph in ['0 - 250 Juta', '250 - 500 Juta', '500 Juta+']:
            df_osph = df[df['OSPH_Category'] == osph]
            if len(df_osph) > 0:
                approve_count = df_osph['Scoring_Detail'].str.contains('Approve', case=False, na=False).sum()
                total = len(df_osph[df_osph['Scoring_Detail'] != '-'])
                if total > 0:
                    rate = approve_count / total * 100
                    if rate < 30:
                        warnings.append(f"⚠️ {osph}: Approval rate rendah ({rate:.1f}%)")
                        recommendations.append(f"📋 Review kriteria scoring untuk segmen {osph}")
    
    # 2. Analisis Bottleneck SLA
    if 'SLA_Days' in df.columns and 'apps_status_clean' in df.columns:
        for status in df['apps_status_clean'].unique():
            if status == 'Unknown':
                continue
            df_status = df[df['apps_status_clean'] == status]
            sla_avg = df_status['SLA_Days'].mean()
            if pd.notna(sla_avg) and sla_avg > 5:
                warnings.append(f"⚠️ Bottleneck: {status} (SLA {sla_avg:.1f} hari)")
                recommendations.append(f"📋 Prioritas review untuk status {status}")
    
    # 3. Analisis Ketimpangan Beban Kerja CA
    if 'user_name_clean' in df.columns:
        ca_load = df.groupby('user_name_clean')['apps_id'].nunique()
        if len(ca_load) > 0:
            max_load = ca_load.max()
            min_load = ca_load.min()
            avg_load = ca_load.mean()
            if max_load > avg_load * 1.5:
                warnings.append(f"⚠️ Ketimpangan beban: Max {max_load:.0f} vs Min {min_load:.0f}")
                recommendations.append("📋 Redistribusi beban kerja CA")
    
    # 4. Analisis Pola Reject
    if 'Scoring_Detail' in df.columns:
        reject_types = df[df['Scoring_Detail'].str.contains('Reject', case=False, na=False)]
        if len(reject_types) > 0:
            reject_rate = len(reject_types) / len(df[df['Scoring_Detail'] != '-']) * 100
            if reject_rate > 40:
                warnings.append(f"⚠️ Reject rate tinggi: {reject_rate:.1f}%")
                recommendations.append("📋 Analisis root cause reject")
    
    # 5. Insight Positif
    if 'SLA_Days' in df.columns:
        sla_avg = df['SLA_Days'].mean()
        if pd.notna(sla_avg) and sla_avg <= 3:
            insights.append(f"✅ SLA Excellence: {sla_avg:.1f} hari (Target: ≤3)")
    
    return insights, warnings, recommendations

def main():
    st.title("🎯 CA ANALYTICS ULTIMATE DASHBOARD")
    st.markdown("### Dashboard Business Intelligence - Analytical & Strategic Insights")
    st.markdown("---")
    
    df = load_data()
    if df is None or df.empty:
        st.error("❌ Data tidak dapat dimuat atau kosong")
        st.stop()
    
    st.success(f"✅ **{len(df):,} records** | **{df['apps_id'].nunique():,} unique applications** | **{len(df.columns)} columns loaded**")
    
    # SIDEBAR - Filter tanpa grouping
    st.sidebar.title("🎛️ Panel Kontrol Analytics")
    
    # Filter apps_status - SEMUA nilai unik, tidak digrouping
    if 'apps_status_clean' in df.columns:
        all_status = sorted([x for x in df['apps_status_clean'].unique() if x != 'Unknown'])
        selected_status = st.sidebar.multiselect(
            "📋 Status Aplikasi (Detail)", 
            all_status,
            default=all_status,
            help="NOT RECOMMENDED CA, PENDING CA, Pending CA Completed, RECOMMENDED CA, RECOMMENDED CA WITH COND"
        )
    else:
        selected_status = []
    
    # Filter Hasil_Scoring_1 - SEMUA nilai unik, tidak digrouping
    if 'Scoring_Detail' in df.columns:
        all_scoring = sorted([x for x in df['Scoring_Detail'].unique() if x not in ['', 'nan']])
        selected_scoring = st.sidebar.multiselect(
            "🎯 Hasil Scoring (Detail)",
            all_scoring,
            default=all_scoring,
            help="-, APPROVE, Approve 1, Approve 2, REGULER, Reguler 1, Reguler 2, REJECT, Reject 1, Reject 2, Scoring in Progress"
        )
    else:
        selected_scoring = []
    
    selected_product = st.sidebar.selectbox("🚗 Produk", ['Semua'] + sorted(df['Produk_clean'].unique().tolist()) if 'Produk_clean' in df.columns else ['Semua'])
    selected_branch = st.sidebar.selectbox("🏢 Cabang", ['Semua'] + sorted(df['branch_name_clean'].unique().tolist()) if 'branch_name_clean' in df.columns else ['Semua'])
    selected_ca = st.sidebar.selectbox("👤 CA", ['Semua'] + sorted(df['user_name_clean'].unique().tolist()) if 'user_name_clean' in df.columns else ['Semua'])
    selected_osph = st.sidebar.selectbox("💰 OSPH Range", ['Semua'] + sorted([x for x in df['OSPH_Category'].unique() if x != 'Unknown']) if 'OSPH_Category' in df.columns else ['Semua'])
    
    # Apply filters
    df_filtered = df.copy()
    if selected_status:
        df_filtered = df_filtered[df_filtered['apps_status_clean'].isin(selected_status)]
    if selected_scoring:
        df_filtered = df_filtered[df_filtered['Scoring_Detail'].isin(selected_scoring)]
    if selected_product != 'Semua':
        df_filtered = df_filtered[df_filtered['Produk_clean'] == selected_product]
    if selected_branch != 'Semua':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    if selected_ca != 'Semua':
        df_filtered = df_filtered[df_filtered['user_name_clean'] == selected_ca]
    if selected_osph != 'Semua':
        df_filtered = df_filtered[df_filtered['OSPH_Category'] == selected_osph]
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 **{len(df_filtered):,} records** ({len(df_filtered)/len(df)*100:.1f}% dari total)")
    st.sidebar.info(f"🎯 **{df_filtered['apps_id'].nunique():,} unique apps**")
    
    # ANALYTICAL INSIGHTS
    st.header("💡 Analytical Insights & Strategic Recommendations")
    insights, warnings, recommendations = generate_analytical_insights(df_filtered)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="success-card"><h3>✅ Key Insights</h3>', unsafe_allow_html=True)
        if insights:
            for i in insights:
                st.markdown(f"**{i}**")
        else:
            st.markdown("_Analyze data untuk mendapat insight_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="warning-card"><h3>⚠️ Critical Alerts</h3>', unsafe_allow_html=True)
        if warnings:
            for w in warnings:
                st.markdown(f"**{w}**")
        else:
            st.markdown("✅ _No critical issues detected_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="info-card"><h3>📋 Action Items</h3>', unsafe_allow_html=True)
        if recommendations:
            for r in recommendations:
                st.markdown(f"**{r}**")
        else:
            st.markdown("_No immediate actions required_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # KPIs
    st.header("📈 Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        total_apps = df_filtered['apps_id'].nunique()
        st.metric("📝 Total Aplikasi", f"{total_apps:,}")
    
    with kpi2:
        avg_sla = df_filtered['SLA_Days'].mean()
        emoji = "🟢" if avg_sla <= 3 else "🟡" if avg_sla <= 5 else "🔴"
        st.metric("⏱️ Avg SLA", f"{avg_sla:.1f}d {emoji}" if not pd.isna(avg_sla) else "N/A")
    
    with kpi3:
        if 'Scoring_Detail' in df_filtered.columns:
            approve_count = df_filtered['Scoring_Detail'].str.contains('Approve', case=False, na=False).sum()
            total_scored = len(df_filtered[df_filtered['Scoring_Detail'] != '-'])
            rate = approve_count / total_scored * 100 if total_scored > 0 else 0
            st.metric("✅ Approval Rate", f"{rate:.1f}%")
    
    with kpi4:
        avg_osph = df_filtered['OSPH_clean'].mean()
        st.metric("💰 Avg OSPH", f"Rp {avg_osph/1e6:.0f}M" if not pd.isna(avg_osph) else "N/A")
    
    with kpi5:
        total_ca = df_filtered['user_name_clean'].nunique()
        st.metric("👥 Active CA", f"{total_ca:,}")
    
    with kpi6:
        avg_risk = df_filtered['Risk_Score'].mean()
        risk_emoji = "🟢" if avg_risk < 30 else "🟡" if avg_risk < 60 else "🔴"
        st.metric("⚠️ Risk Score", f"{avg_risk:.0f} {risk_emoji}" if not pd.isna(avg_risk) else "N/A")
    
    st.markdown("---")
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "💰 OSPH Analysis (Excel Format)",
        "📋 Status & Scoring Detail",
        "👥 CA Performance",
        "🔍 Deep Dive Analysis",
        "📊 Correlation Matrix",
        "📈 Trends & Patterns",
        "🎯 Strategic Segments",
        "📋 Raw Data"
    ])
    
    with tab1:
        st.header("💰 Analisis OSPH - Format Excel")
        st.info("Analisis lengkap sesuai struktur Excel: CS NEW dan CS USED dengan breakdown detail")
        
        # Tabs untuk CS NEW vs CS USED
        subtab1, subtab2, subtab3 = st.tabs(["📊 Overview", "🆕 CS NEW - Skema Harga", "♻️ CS USED - Skema Harga"])
        
        with subtab1:
            st.subheader("Overview per Range OSPH")
            if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
                overview_data = []
                for osph in sorted([x for x in df_filtered['OSPH_Category'].unique() if x != 'Unknown']):
                    df_o = df_filtered[df_filtered['OSPH_Category'] == osph]
                    
                    # Count by scoring detail
                    approve2 = len(df_o[df_o['Scoring_Detail'] == 'Approve 2'])
                    reguler1 = len(df_o[df_o['Scoring_Detail'] == 'Reguler 1'])
                    reguler2 = len(df_o[df_o['Scoring_Detail'] == 'Reguler 2'])
                    reject1 = len(df_o[df_o['Scoring_Detail'] == 'Reject 1'])
                    scoring_progress = len(df_o[df_o['Scoring_Detail'] == 'Scoring in Progress'])
                    
                    overview_data.append({
                        'Range OSPH': osph,
                        'Total Apps ID': df_o['apps_id'].nunique(),
                        '% dari Total': f"{df_o['apps_id'].nunique()/df_filtered['apps_id'].nunique()*100:.1f}%",
                        'Total Records': len(df_o),
                        'Approve 2': approve2,
                        'Reguler 1': reguler1,
                        'Reguler 2': reguler2,
                        'Reject 1': reject1,
                        'Scoring in Progress': scoring_progress,
                        'Avg SLA': f"{df_o['SLA_Days'].mean():.1f}" if df_o['SLA_Days'].notna().any() else "-"
                    })
                
                overview_df = pd.DataFrame(overview_data)
                st.dataframe(overview_df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.pie(overview_df, values='Total Apps ID', names='Range OSPH',
                               title="Distribusi Apps ID per OSPH", hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.bar(overview_df, x='Range OSPH',
                               y=['Approve 2', 'Reguler 1', 'Reguler 2', 'Reject 1', 'Scoring in Progress'],
                               title="Detail Scoring per OSPH Range", barmode='stack')
                    st.plotly_chart(fig, use_container_width=True)
        
        with subtab2:
            st.subheader("🆕 CS NEW - Breakdown Skema Harga")
            st.markdown("**Sesuai format Excel: Range Harga, Breakdown Pekerjaan, Jenis Kendaraan**")
            
            if 'Produk_clean' in df_filtered.columns:
                # Filter CS NEW
                cs_new = df_filtered[df_filtered['Produk_clean'].str.contains('NEW|BARU|Baru', case=False, na=False)]
                
                if len(cs_new) > 0:
                    st.info(f"📊 {cs_new['apps_id'].nunique()} aplikasi CS NEW dari {len(cs_new)} records")
                    
                    # Tabel 1: Range Harga Overview
                    st.markdown("#### 📊 Tabel 1: Overview per Range Harga")
                    new_overview = []
                    for osph in sorted([x for x in cs_new['OSPH_Category'].unique() if x != 'Unknown']):
                        df_o = cs_new[cs_new['OSPH_Category'] == osph]
                        new_overview.append({
                            'Range Harga': osph,
                            'Harga Min': f"Rp {df_o['OSPH_clean'].min():,.0f}",
                            'Harga Max': f"Rp {df_o['OSPH_clean'].max():,.0f}",
                            'Total Apps ID': df_o['apps_id'].nunique(),
                            '% dari Total': f"{df_o['apps_id'].nunique()/cs_new['apps_id'].nunique()*100:.1f}%",
                            'Total Records': len(df_o),
                            'Approve 2': len(df_o[df_o['Scoring_Detail'] == 'Approve 2']),
                            'Reguler 1': len(df_o[df_o['Scoring_Detail'] == 'Reguler 1']),
                            'Reguler 2': len(df_o[df_o['Scoring_Detail'] == 'Reguler 2']),
                            'Reject 1': len(df_o[df_o['Scoring_Detail'] == 'Reject 1']),
                            'Scoring in Progress': len(df_o[df_o['Scoring_Detail'] == 'Scoring in Progress'])
                        })
                    new_df = pd.DataFrame(new_overview)
                    st.dataframe(new_df, use_container_width=True, hide_index=True)
                    
                    # Tabel 2: Breakdown Pekerjaan
                    st.markdown("#### 💼 Tabel 2: Breakdown per Kategori Pekerjaan")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'Pekerjaan_clean' in cs_new.columns:
                            job_breakdown = []
                            for osph in sorted([x for x in cs_new['OSPH_Category'].unique() if x != 'Unknown']):
                                df_o = cs_new[cs_new['OSPH_Category'] == osph]
                                karyawan = len(df_o[df_o['Pekerjaan_clean'].str.contains('KARYAWAN|PEGAWAI', case=False, na=False)])
                                wiraswasta = len(df_o[df_o['Pekerjaan_clean'].str.contains('WIRASWASTA|WIRAUSAHA', case=False, na=False)])
                                irt = len(df_o[df_o['Pekerjaan_clean'].str.contains('IBU|RUMAH|TANGGA', case=False, na=False)])
                                lainnya = len(df_o) - karyawan - wiraswasta - irt
                                
                                job_breakdown.append({
                                    'Range Harga': osph,
                                    'Karyawan': karyawan,
                                    'Wiraswasta': wiraswasta,
                                    'Ibu Rumah Tangga': irt,
                                    'Lainnya': lainnya
                                })
                            job_df = pd.DataFrame(job_breakdown)
                            st.dataframe(job_df, use_container_width=True, hide_index=True)
                    
                    with col2:
                        # Chart pekerjaan
                        fig = px.bar(job_df, x='Range Harga', 
                                   y=['Karyawan', 'Wiraswasta', 'Ibu Rumah Tangga', 'Lainnya'],
                                   title="Distribusi Pekerjaan per OSPH", barmode='stack')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabel 3: Jenis Kendaraan
                    st.markdown("#### 🚗 Tabel 3: Breakdown Jenis Kendaraan")
                    if 'JenisKendaraan_clean' in cs_new.columns:
                        vehicle_breakdown = []
                        for osph in sorted([x for x in cs_new['OSPH_Category'].unique() if x != 'Unknown']):
                            df_o = cs_new[cs_new['OSPH_Category'] == osph]
                            beban = len(df_o[df_o['JenisKendaraan_clean'].str.contains('BEBAN|PICK', case=False, na=False)])
                            penumpang = len(df_o[df_o['JenisKendaraan_clean'].str.contains('PENUMPANG|SEDAN|MPV|SUV', case=False, na=False)])
                            lainnya = len(df_o) - beban - penumpang
                            
                            vehicle_breakdown.append({
                                'Range Harga': osph,
                                'Mb. Beban': beban,
                                'Mb. Penumpang': penumpang,
                                'Lainnya': lainnya
                            })
                        vehicle_df = pd.DataFrame(vehicle_breakdown)
                        st.dataframe(vehicle_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Tidak ada data CS NEW dalam filter yang dipilih")
        
        with subtab3:
            st.subheader("♻️ CS USED - Breakdown Skema Harga")
            st.markdown("**Sesuai format Excel: Range Harga, Breakdown Pekerjaan, Jenis Kendaraan**")
            
            if 'Produk_clean' in df_filtered.columns:
                # Filter CS USED
                cs_used = df_filtered[df_filtered['Produk_clean'].str.contains('USED|BEKAS', case=False, na=False)]
                
                if len(cs_used) > 0:
                    st.info(f"📊 {cs_used['apps_id'].nunique()} aplikasi CS USED dari {len(cs_used)} records")
                    
                    # Tabel 1: Range Harga Overview
                    st.markdown("#### 📊 Tabel 1: Overview per Range Harga")
                    used_overview = []
                    for osph in sorted([x for x in cs_used['OSPH_Category'].unique() if x != 'Unknown']):
                        df_o = cs_used[cs_used['OSPH_Category'] == osph]
                        used_overview.append({
                            'Range Harga': osph,
                            'Harga Min': f"Rp {df_o['OSPH_clean'].min():,.0f}",
                            'Harga Max': f"Rp {df_o['OSPH_clean'].max():,.0f}",
                            'Total Apps ID': df_o['apps_id'].nunique(),
                            '% dari Total': f"{df_o['apps_id'].nunique()/cs_used['apps_id'].nunique()*100:.1f}%",
                            'Total Records': len(df_o)
                        })
                    used_df = pd.DataFrame(used_overview)
                    st.dataframe(used_df, use_container_width=True, hide_index=True)
                    
                    # Tabel 2: Breakdown Pekerjaan (seperti Excel)
                    st.markdown("#### 💼 Tabel 2: Breakdown per Kategori Pekerjaan")
                    if 'Pekerjaan_clean' in cs_used.columns:
                        job_breakdown = []
                        for osph in sorted([x for x in cs_used['OSPH_Category'].unique() if x != 'Unknown']):
                            df_o = cs_used[cs_used['OSPH_Category'] == osph]
                            karyawan = len(df_o[df_o['Pekerjaan_clean'].str.contains('KARYAWAN|PEGAWAI', case=False, na=False)])
                            wiraswasta = len(df_o[df_o['Pekerjaan_clean'].str.contains('WIRASWASTA|WIRAUSAHA', case=False, na=False)])
                            irt = len(df_o[df_o['Pekerjaan_clean'].str.contains('IBU|RUMAH|TANGGA', case=False, na=False)])
                            lainnya = len(df_o) - karyawan - wiraswasta - irt
                            
                            job_breakdown.append({
                                'Range Harga': osph,
                                'Karyawan': karyawan,
                                'Wiraswasta': wiraswasta,
                                'Ibu Rumah Tangga': irt,
                                'Lainnya': lainnya
                            })
                        job_df = pd.DataFrame(job_breakdown)
                        st.dataframe(job_df, use_container_width=True, hide_index=True)
                    
                    # Tabel 3: Jenis Kendaraan
                    st.markdown("#### 🚗 Tabel 3: Breakdown Jenis Kendaraan")
                    if 'JenisKendaraan_clean' in cs_used.columns:
                        vehicle_breakdown = []
                        for osph in sorted([x for x in cs_used['OSPH_Category'].unique() if x != 'Unknown']):
                            df_o = cs_used[cs_used['OSPH_Category'] == osph]
                            beban = len(df_o[df_o['JenisKendaraan_clean'].str.contains('BEBAN|PICK', case=False, na=False)])
                            penumpang = len(df_o[df_o['JenisKendaraan_clean'].str.contains('PENUMPANG|SEDAN|MPV|SUV', case=False, na=False)])
                            lainnya = len(df_o) - beban - penumpang
                            
                            vehicle_breakdown.append({
                                'Range Harga': osph,
                                'Mb. Beban': beban,
                                'Mb. Penumpang': penumpang,
                                'Lainnya': lainnya
                            })
                        vehicle_df = pd.DataFrame(vehicle_breakdown)
                        st.dataframe(vehicle_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Tidak ada data CS USED dalam filter yang dipilih")
    
    with tab2:
        st.header("📋 Status Aplikasi & Detail Scoring")
        st.info("Semua nilai ditampilkan tanpa grouping sesuai data asli")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 apps_status (Detail)")
            if 'apps_status_clean' in df_filtered.columns:
                status_count = df_filtered['apps_status_clean'].value_counts().reset_index()
                status_count.columns = ['Status', 'Jumlah']
                status_count['%'] = (status_count['Jumlah'] / len(df_filtered) * 100).round(1)
                st.dataframe(status_count, hide_index=True, use_container_width=True)
                
                fig = px.pie(status_count, values='Jumlah', names='Status',
                           title="Distribusi apps_status", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🎯 Hasil_Scoring_1 (Detail)")
            if 'Scoring_Detail' in df_filtered.columns:
                scoring_count = df_filtered['Scoring_Detail'].value_counts().reset_index()
                scoring_count.columns = ['Hasil Scoring', 'Jumlah']
                scoring_count['%'] = (scoring_count['Jumlah'] / len(df_filtered) * 100).round(1)
                st.dataframe(scoring_count, hide_index=True, use_container_width=True)
                
                fig = px.bar(scoring_count, x='Hasil Scoring', y='Jumlah',
                           title="Distribusi Hasil Scoring", text='Jumlah')
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
        
        # Cross-tabulation
        st.subheader("🔗 Cross Analysis: Status vs Scoring")
        if 'apps_status_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            cross_tab = pd.crosstab(df_filtered['apps_status_clean'], 
                                   df_filtered['Scoring_Detail'], 
                                   margins=True, margins_name='TOTAL')
            st.dataframe(cross_tab, use_container_width=True)
    
    with tab3:
        st.header("👥 Performance CA Individual")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = []
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                # Hitung detail scoring
                approve = df_ca['Scoring_Detail'].str.contains('Approve', case=False, na=False).sum()
                reguler = df_ca['Scoring_Detail'].str.contains('Reguler', case=False, na=False).sum()
                reject = df_ca['Scoring_Detail'].str.contains('Reject', case=False, na=False).sum()
                total_scored = approve + reguler + reject
                
                ca_perf.append({
                    'CA Name': ca,
                    'Total Apps': df_ca['apps_id'].nunique(),
                    'Total Records': len(df_ca),
                    'Avg SLA': f"{df_ca['SLA_Days'].mean():.1f}" if df_ca['SLA_Days'].notna().any() else "-",
                    'Approve': approve,
                    'Reguler': reguler,
                    'Reject': reject,
                    'Approval Rate': f"{approve/total_scored*100:.1f}%" if total_scored > 0 else "-",
                    'Avg Risk Score': f"{df_ca['Risk_Score'].mean():.0f}" if df_ca['Risk_Score'].notna().any() else "-"
                })
            
            ca_df = pd.DataFrame(ca_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(ca_df.head(10), x='CA Name', y='Total Apps',
                           title="Top 10 CA by Volume")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                ca_df['Approval_num'] = ca_df['Approval Rate'].str.replace('%', '').replace('-', '0').astype(float)
                fig = px.scatter(ca_df, x='Total Apps', y='Approval_num',
                               size='Total Records', hover_data=['CA Name'],
                               title="Volume vs Approval Rate",
                               labels={'Approval_num': 'Approval %'})
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("🔍 Deep Dive: Multi-Dimensional Analysis")
        
        # Analisis Produk → OSPH → Pekerjaan → Kendaraan
        st.subheader("🔗 Hierarki: Produk → OSPH → Pekerjaan → Kendaraan")
        
        if all(c in df_filtered.columns for c in ['Produk_clean', 'OSPH_Category', 'Pekerjaan_clean', 'JenisKendaraan_clean']):
            deep_analysis = df_filtered.groupby(['Produk_clean', 'OSPH_Category', 'Pekerjaan_clean', 'JenisKendaraan_clean']).agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean',
                'Risk_Score': 'mean'
            }).reset_index()
            deep_analysis.columns = ['Produk', 'OSPH', 'Pekerjaan', 'Kendaraan', 'Total Apps', 'Avg SLA', 'Avg Risk']
            deep_analysis = deep_analysis.sort_values('Total Apps', ascending=False).head(20)
            
            st.dataframe(deep_analysis, use_container_width=True, hide_index=True)
            
            # Sunburst chart
            fig = px.sunburst(deep_analysis, path=['Produk', 'OSPH', 'Pekerjaan', 'Kendaraan'],
                            values='Total Apps', color='Avg Risk',
                            title="Interactive Hierarchy: Produk → OSPH → Pekerjaan → Kendaraan")
            st.plotly_chart(fig, use_container_width=True)
            
            # Insight otomatis
            st.markdown("#### 🎯 Automated Insights:")
            top_combo = deep_analysis.iloc[0]
            st.markdown(f'<div class="insight-card">**Top Combination:** {top_combo["Produk"]} + {top_combo["OSPH"]} + {top_combo["Pekerjaan"]} + {top_combo["Kendaraan"]} ({top_combo["Total Apps"]:.0f} apps, SLA: {top_combo["Avg SLA"]:.1f}d)</div>', unsafe_allow_html=True)
    
    with tab5:
        st.header("📊 Correlation Matrix & Heatmaps")
        
        # Correlation: OSPH vs Scoring
        st.subheader("💰 OSPH Range vs Hasil Scoring")
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            corr_data = pd.crosstab(df_filtered['OSPH_Category'], df_filtered['Scoring_Detail'])
            
            fig = px.imshow(corr_data, text_auto=True, aspect="auto",
                          title="Heatmap: OSPH vs Scoring",
                          labels=dict(x="Hasil Scoring", y="OSPH Range", color="Count"))
            st.plotly_chart(fig, use_container_width=True)
        
        # Correlation: Status vs Scoring
        st.subheader("📋 apps_status vs Hasil Scoring")
        if 'apps_status_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            corr_status = pd.crosstab(df_filtered['apps_status_clean'], df_filtered['Scoring_Detail'])
            
            fig = px.imshow(corr_status, text_auto=True, aspect="auto",
                          title="Heatmap: Status vs Scoring",
                          labels=dict(x="Hasil Scoring", y="apps_status", color="Count"))
            st.plotly_chart(fig, use_container_width=True)
    
    with tab6:
        st.header("📈 Trends & Time-Series Analysis")
        
        if 'YearMonth' in df_filtered.columns:
            # Monthly trend
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean',
                'Risk_Score': 'mean'
            }).reset_index()
            monthly.columns = ['Month', 'Volume', 'Avg SLA', 'Avg Risk']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=monthly['Month'], y=monthly['Volume'], name="Volume"), secondary_y=False)
            fig.add_trace(go.Scatter(x=monthly['Month'], y=monthly['Avg SLA'], name="Avg SLA", mode='lines+markers'), secondary_y=True)
            fig.update_layout(title="Monthly Trend: Volume & SLA")
            fig.update_yaxes(title_text="Volume", secondary_y=False)
            fig.update_yaxes(title_text="SLA (days)", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        
        # Hourly pattern
        if 'Hour' in df_filtered.columns:
            hourly = df_filtered.groupby('Hour').size().reset_index(name='Count')
            fig = px.line(hourly, x='Hour', y='Count', markers=True,
                        title="Hourly Pattern: Application Submissions")
            fig.add_vrect(x0=8.5, x1=15.5, fillcolor="green", opacity=0.1, 
                        annotation_text="Working Hours (08:30-15:30)")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab7:
        st.header("🎯 Strategic Segmentation")
        
        # Segmentasi Risk
        st.subheader("⚠️ Risk Segmentation")
        if 'Risk_Category' in df_filtered.columns:
            risk_seg = df_filtered.groupby('Risk_Category').agg({
                'apps_id': 'nunique',
                'OSPH_clean': 'mean',
                'SLA_Days': 'mean'
            }).reset_index()
            risk_seg.columns = ['Risk Category', 'Total Apps', 'Avg OSPH', 'Avg SLA']
            st.dataframe(risk_seg, use_container_width=True, hide_index=True)
            
            fig = px.bar(risk_seg, x='Risk Category', y='Total Apps',
                       color='Risk Category', title="Distribution by Risk Category")
            st.plotly_chart(fig, use_container_width=True)
        
        # Segmentasi Produk
        st.subheader("🚗 Product Performance")
        if 'Produk_clean' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            prod_perf = []
            for prod in df_filtered['Produk_clean'].unique():
                df_p = df_filtered[df_filtered['Produk_clean'] == prod]
                approve = df_p['Scoring_Detail'].str.contains('Approve', case=False, na=False).sum()
                total = len(df_p[df_p['Scoring_Detail'] != '-'])
                
                prod_perf.append({
                    'Produk': prod,
                    'Total Apps': df_p['apps_id'].nunique(),
                    'Approval Rate': f"{approve/total*100:.1f}%" if total > 0 else "-",
                    'Avg SLA': f"{df_p['SLA_Days'].mean():.1f}" if df_p['SLA_Days'].notna().any() else "-",
                    'Avg OSPH': f"Rp {df_p['OSPH_clean'].mean()/1e6:.0f}M" if df_p['OSPH_clean'].notna().any() else "-"
                })
            
            prod_df = pd.DataFrame(prod_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(prod_df, use_container_width=True, hide_index=True)
    
    with tab8:
        st.header("📋 Complete Raw Data")
        st.info("Semua field wajib ditampilkan sesuai requirement")
        
        # Pilih kolom yang tersedia
        display_cols = ['apps_id', 'user_name', 'position_name', 'apps_status', 'desc_status_apps',
                       'Produk', 'action_on_parsed', 'Initiation_parsed', 'RealisasiDate_parsed',
                       'Outstanding_PH', 'OSPH_clean', 'OSPH_Category', 'Pekerjaan', 'Jabatan',
                       'Pekerjaan_Pasangan', 'Hasil_Scoring_1', 'Scoring_Detail', 'JenisKendaraan',
                       'branch_name', 'Tujuan_Kredit', 'LastOD', 'max_OD', 'SLA_Days', 'Risk_Score']
        
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        
        st.dataframe(df_filtered[available_cols], use_container_width=True, height=500)
        
        # Download button
        csv = df_filtered[available_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Data (CSV)",
            data=csv,
            file_name=f"CA_Analytics_Full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    st.markdown(f"<div style='text-align:center;color:#666'>Dashboard Analytics | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
