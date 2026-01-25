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
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    if all(c in df.columns for c in ['action_on_parsed', 'RealisasiDate_parsed']):
        df['SLA_Days'] = df.apply(lambda r: calculate_sla_days(r['action_on_parsed'], r['RealisasiDate_parsed']), axis=1)
    
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(df['Outstanding_PH'].astype(str).str.replace(',', ''), errors='coerce')
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    for col in ['LastOD', 'max_OD']:
        if col in df.columns:
            df[f'{col}_clean'] = pd.to_numeric(df[col], errors='coerce')
    
    # Standardisasi apps_status - JANGAN DIGROUPING
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
    # Standardisasi Hasil_Scoring_1
    if 'Hasil_Scoring_1' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring_1'].fillna('-').astype(str).str.strip()
        
        # Mapping detail scoring
        scoring_mapping = {
            '-': '-',
            'APPROVE': 'APPROVE',
            'Approve 1': 'Approve 1',
            'Approve 2': 'Approve 2',
            'REGULER': 'REGULER',
            'Reguler': 'REGULER',
            'Reguler 1': 'Reguler 1',
            'Reguler 2': 'Reguler 2',
            'REJECT': 'REJECT',
            'Reject': 'REJECT',
            'Reject 1': 'Reject 1',
            'Reject 2': 'Reject 2',
            'Scoring in Progress': 'Scoring in Progress',
            'data historical': 'data historical'
        }
        df['Scoring_Detail'] = df['Scoring_Detail'].replace(scoring_mapping)
        df['Is_Scored'] = ~df['Scoring_Detail'].isin(['-', 'data historical', 'Scoring in Progress'])
        
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
            elif x == 'DATA HISTORICAL':
                return 'DATA HISTORICAL'
            elif x == '-':
                return 'BELUM SCORING'
            return 'OTHER'
        df['Scoring_Group'] = df['Scoring_Detail'].apply(get_group)
    
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Quarter'] = df['action_on_parsed'].dt.quarter
    
    for field in ['desc_status_apps', 'Produk', 'Pekerjaan', 'Jabatan',
                  'Pekerjaan_Pasangan', 'JenisKendaraan', 'branch_name', 'Tujuan_Kredit',
                  'user_name', 'position_name']:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
    df['Risk_Score'] = df.apply(calculate_risk_score, axis=1)
    df['Risk_Category'] = pd.cut(df['Risk_Score'], bins=[0, 30, 60, 100], labels=['Low Risk', 'Medium Risk', 'High Risk'])
    
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

def generate_insights(df):
    insights, warnings, successes, recommendations = [], [], [], []
    
    if 'OSPH_Category' in df.columns and 'Scoring_Group' in df.columns:
        osph_approval = df.groupby('OSPH_Category').apply(
            lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
        ).to_dict()
        if osph_approval:
            best_osph = max(osph_approval, key=osph_approval.get)
            successes.append(f"🎯 Segmen Terbaik: {best_osph} ({osph_approval[best_osph]:.1f}% approval)")
    
    if 'SLA_Days' in df.columns:
        sla_data = df['SLA_Days'].dropna()
        if len(sla_data) > 0:
            avg_sla = sla_data.mean()
            within_3 = (sla_data <= 3).sum() / len(sla_data) * 100
            if avg_sla <= 3:
                successes.append(f"✅ SLA Sangat Baik: {avg_sla:.1f} hari rata-rata")
            elif avg_sla > 5:
                warnings.append(f"⚠️ Alert SLA: {avg_sla:.1f} hari (target: 3)")
                recommendations.append("📋 Tambah bandwidth CA")
            insights.append(f"📊 {within_3:.1f}% selesai ≤3 hari")
    
    if 'user_name' in df.columns and 'apps_id' in df.columns:
        ca_workload = df.groupby('user_name')['apps_id'].nunique()
        if len(ca_workload) > 0:
            max_w = ca_workload.max()
            avg_w = ca_workload.mean()
            if max_w > avg_w * 1.5:
                warnings.append(f"⚠️ Ketimpangan Beban Kerja: Max {max_w:.0f} vs Avg {avg_w:.0f}")
                recommendations.append("📋 Redistribusi beban kerja")
    
    return insights, warnings, successes, recommendations

def main():
    st.title("🎯 CA ANALYTICS ULTIMATE DASHBOARD")
    st.markdown("### Dashboard Business Intelligence Lengkap untuk Presentasi Direksi")
    st.markdown("---")
    
    df = load_data()
    if df is None or df.empty:
        st.error("❌ Gagal memuat data")
        st.stop()
    
    st.success(f"✅ {len(df):,} records | {df['apps_id'].nunique():,} aplikasi | {len(df.columns)} kolom")
    
    # Sidebar
    st.sidebar.title("🎛️ Panel Kontrol")
    selected_product = st.sidebar.selectbox("🚗 Produk", ['Semua'] + sorted(df['Produk_clean'].unique().tolist()) if 'Produk_clean' in df.columns else ['Semua'])
    selected_branch = st.sidebar.selectbox("🏢 Cabang", ['Semua'] + sorted(df['branch_name_clean'].unique().tolist()) if 'branch_name_clean' in df.columns else ['Semua'])
    selected_ca = st.sidebar.selectbox("👤 CA", ['Semua'] + sorted(df['user_name_clean'].unique().tolist()) if 'user_name_clean' in df.columns else ['Semua'])
    selected_osph = st.sidebar.selectbox("💰 OSPH", ['Semua'] + sorted([x for x in df['OSPH_Category'].unique() if x != 'Unknown']) if 'OSPH_Category' in df.columns else ['Semua'])
    
    # Filter apps_status - ambil semua unique values
    if 'apps_status_clean' in df.columns:
        all_status = sorted([x for x in df['apps_status_clean'].unique() if x != 'Unknown'])
        selected_status = st.sidebar.multiselect("📋 Status Aplikasi", 
            all_status,
            default=all_status)
    
    # Filter scoring - ambil semua unique values
    if 'Scoring_Detail' in df.columns:
        all_scoring = sorted([x for x in df['Scoring_Detail'].unique() if x not in ['', 'nan']])
        selected_scoring = st.sidebar.multiselect("🎯 Hasil Scoring",
            all_scoring,
            default=[x for x in all_scoring if x not in ['-', 'data historical', 'Scoring in Progress']])
    
    df_filtered = df.copy()
    if selected_product != 'Semua':
        df_filtered = df_filtered[df_filtered['Produk_clean'] == selected_product]
    if selected_branch != 'Semua':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    if selected_ca != 'Semua':
        df_filtered = df_filtered[df_filtered['user_name_clean'] == selected_ca]
    if selected_osph != 'Semua':
        df_filtered = df_filtered[df_filtered['OSPH_Category'] == selected_osph]
    if 'apps_status_clean' in df.columns and selected_status:
        df_filtered = df_filtered[df_filtered['apps_status_clean'].isin(selected_status)]
    if 'Scoring_Detail' in df.columns and selected_scoring:
        df_filtered = df_filtered[df_filtered['Scoring_Detail'].isin(selected_scoring)]
    
    st.sidebar.info(f"📊 {len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    
    # Executive Summary
    st.header("📊 Ringkasan Eksekutif")
    insights, warnings, successes, recommendations = generate_insights(df_filtered)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="success-card"><h3>✅ Pencapaian</h3>', unsafe_allow_html=True)
        for s in successes[:3]:
            st.markdown(f"**{s}**")
        if not successes:
            st.markdown("_Tidak ada pencapaian_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="insight-card"><h3>💡 Insight</h3>', unsafe_allow_html=True)
        for i in insights[:3]:
            st.markdown(f"**{i}**")
        if not insights:
            st.markdown("_Tidak ada insight_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="warning-card"><h3>⚠️ Alert</h3>', unsafe_allow_html=True)
        for w in warnings[:3]:
            st.markdown(f"**{w}**")
        if not warnings:
            st.markdown("✅ _Semua sehat_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="info-card"><h3>📋 Tindakan</h3>', unsafe_allow_html=True)
        for r in recommendations[:3]:
            st.markdown(f"**{r}**")
        if not recommendations:
            st.markdown("_Tidak ada tindakan_")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # KPIs
    st.header("📈 Metrik Utama")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        st.metric("📝 Jumlah Aplikasi", f"{df_filtered['apps_id'].nunique():,}")
    with kpi2:
        avg_sla = df_filtered['SLA_Days'].mean()
        emoji = "🟢" if avg_sla <= 3 else "🟡" if avg_sla <= 5 else "🔴"
        st.metric("⏱️ SLA Rata-rata", f"{avg_sla:.1f}h {emoji}" if not pd.isna(avg_sla) else "N/A")
    with kpi3:
        if 'Scoring_Group' in df_filtered.columns:
            approved = (df_filtered['Scoring_Group'] == 'APPROVE').sum()
            total = len(df_filtered[df_filtered['Scoring_Group'] != 'OTHER'])
            rate = approved / total * 100 if total > 0 else 0
            st.metric("✅ Tingkat Approval", f"{rate:.1f}%")
    with kpi4:
        avg_osph = df_filtered['OSPH_clean'].mean()
        st.metric("💰 OSPH Rata-rata", f"{avg_osph/1e6:.0f}M" if not pd.isna(avg_osph) else "N/A")
    with kpi5:
        st.metric("👥 Jumlah CA", f"{df_filtered['user_name'].nunique():,}")
    with kpi6:
        avg_risk = df_filtered['Risk_Score'].mean()
        risk_emoji = "🟢" if avg_risk < 30 else "🟡" if avg_risk < 60 else "🔴"
        st.metric("⚠️ Skor Risiko", f"{avg_risk:.0f} {risk_emoji}" if not pd.isna(avg_risk) else "N/A")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🎯 Strategi OSPH",
        "👥 Kinerja CA",
        "📊 Detail Scoring",
        "📋 Status Aplikasi",
        "🚗 Produk/Cabang",
        "🔍 Analisis Mendalam",
        "📈 Tren",
        "📋 Data Lengkap"
    ])
    
    with tab1:
        st.header("💰 Strategi OSPH - Analisis Lengkap")
        
        # Tab untuk CS NEW vs CS USED
        subtab1, subtab2, subtab3 = st.tabs(["📊 Ringkasan", "🆕 CS NEW - Skema Harga", "♻️ CS USED - Skema Harga"])
        
        with subtab1:
            st.subheader("Ringkasan Umum per Range OSPH")
            if 'OSPH_Category' in df_filtered.columns:
                osph_data = []
                for osph in sorted(df_filtered['OSPH_Category'].unique()):
                    if osph == 'Unknown':
                        continue
                    df_o = df_filtered[df_filtered['OSPH_Category'] == osph]
                    apps = df_o['apps_id'].nunique()
                    records = len(df_o)
                    
                    # Hitung semua scoring detail
                    approve2 = len(df_o[df_o['Scoring_Detail'] == 'Approve 2'])
                    reguler1 = len(df_o[df_o['Scoring_Detail'] == 'Reguler 1'])
                    reguler2 = len(df_o[df_o['Scoring_Detail'] == 'Reguler 2'])
                    reject1 = len(df_o[df_o['Scoring_Detail'] == 'Reject 1'])
                    scoring_progress = len(df_o[df_o['Scoring_Detail'] == 'Scoring in Progress'])
                    
                    osph_data.append({
                        'Range OSPH': osph,
                        'Total Apps ID': apps,
                        '% dari Total': f"{apps/df_filtered['apps_id'].nunique()*100:.1f}%",
                        'Total Records': records,
                        'Approve 2': approve2,
                        'Reguler 1': reguler1,
                        'Reguler 2': reguler2,
                        'Reject 1': reject1,
                        'Scoring in Progress': scoring_progress,
                        'SLA Avg': f"{df_o['SLA_Days'].mean():.1f}h" if df_o['SLA_Days'].notna().any() else "-"
                    })
                
                osph_df = pd.DataFrame(osph_data)
                st.dataframe(osph_df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.pie(osph_df, values='Total Apps ID', names='Range OSPH', 
                               title="Distribusi Apps ID per OSPH", hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    fig = px.bar(osph_df, x='Range OSPH', 
                               y=['Approve 2', 'Reguler 1', 'Reguler 2', 'Reject 1', 'Scoring in Progress'], 
                               title="Detail Scoring per OSPH", barmode='stack')
                    st.plotly_chart(fig, use_container_width=True)
        
        with subtab2:
            st.subheader("🆕 CS NEW - Breakdown Skema Harga")
            st.info("Analisis detail untuk mobil baru berdasarkan range harga dan kategori")
            
            # Simulasi data CS NEW - disesuaikan dengan struktur Excel
            if 'OSPH_Category' in df_filtered.columns and 'Produk_clean' in df_filtered.columns:
                # Filter untuk CS NEW (asumsi ada indikator produk baru)
                cs_new = df_filtered[df_filtered['Produk_clean'].str.contains('NEW|BARU|Baru', case=False, na=False)]
                
                if len(cs_new) > 0:
                    new_analysis = []
                    for osph in sorted(cs_new['OSPH_Category'].unique()):
                        if osph == 'Unknown':
                            continue
                        df_o = cs_new[cs_new['OSPH_Category'] == osph]
                        
                        # Ambil min max dari OSPH_clean
                        harga_min = df_o['OSPH_clean'].min() if 'OSPH_clean' in df_o.columns else 0
                        harga_max = df_o['OSPH_clean'].max() if 'OSPH_clean' in df_o.columns else 0
                        
                        new_analysis.append({
                            'Range Harga': osph,
                            'Harga Min': f"Rp {harga_min:,.0f}",
                            'Harga Max': f"Rp {harga_max:,.0f}",
                            'Total Apps ID': df_o['apps_id'].nunique(),
                            '% dari Total': f"{df_o['apps_id'].nunique()/cs_new['apps_id'].nunique()*100:.1f}%",
                            'Total Records': len(df_o),
                            'Approve 2': len(df_o[df_o['Scoring_Detail'] == 'Approve 2']),
                            'Reguler 1': len(df_o[df_o['Scoring_Detail'] == 'Reguler 1']),
                            'Reguler 2': len(df_o[df_o['Scoring_Detail'] == 'Reguler 2']),
                            'Reject 1': len(df_o[df_o['Scoring_Detail'] == 'Reject 1']),
                            'Scoring in Progress': len(df_o[df_o['Scoring_Detail'] == 'Scoring in Progress'])
                        })
                    
                    new_df = pd.DataFrame(new_analysis)
                    st.dataframe(new_df, use_container_width=True, hide_index=True)
                    
                    # Breakdown tambahan seperti Excel
                    st.markdown("#### Breakdown per Kategori")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Karyawan vs Wiraswasta
                        if 'Pekerjaan_clean' in cs_new.columns:
                            job_breakdown = cs_new.groupby(['OSPH_Category', 'Pekerjaan_clean']).agg({
                                'apps_id': 'nunique'
                            }).reset_index()
                            job_pivot = job_breakdown.pivot(index='OSPH_Category', columns='Pekerjaan_clean', values='apps_id').fillna(0)
                            st.markdown("**Breakdown: Pekerjaan**")
                            st.dataframe(job_pivot, use_container_width=True)
                    
                    with col2:
                        # Ibu Rumah Tangga
                        if 'Pekerjaan_clean' in cs_new.columns:
                            irt = cs_new[cs_new['Pekerjaan_clean'].str.contains('IBU|RUMAH|TANGGA', case=False, na=False)]
                            if len(irt) > 0:
                                irt_breakdown = irt.groupby('OSPH_Category')['apps_id'].nunique().reset_index()
                                st.markdown("**Ibu Rumah Tangga**")
                                st.dataframe(irt_breakdown, use_container_width=True, hide_index=True)
                    
                    # Mb. Beban vs Mb. Penumpang
                    st.markdown("#### Jenis Kendaraan")
                    if 'JenisKendaraan_clean' in cs_new.columns:
                        vehicle_breakdown = cs_new.groupby(['OSPH_Category', 'JenisKendaraan_clean']).agg({
                            'apps_id': 'nunique'
                        }).reset_index()
                        vehicle_pivot = vehicle_breakdown.pivot(index='OSPH_Category', columns='JenisKendaraan_clean', values='apps_id').fillna(0)
                        st.dataframe(vehicle_pivot, use_container_width=True)
                else:
                    st.warning("Tidak ada data CS NEW dalam filter ini")
        
        with subtab3:
            st.subheader("♻️ CS USED - Breakdown Skema Harga")
            st.info("Analisis detail untuk mobil bekas berdasarkan range harga dan kategori")
            
            if 'OSPH_Category' in df_filtered.columns and 'Produk_clean' in df_filtered.columns:
                # Filter untuk CS USED
                cs_used = df_filtered[df_filtered['Produk_clean'].str.contains('USED|BEKAS', case=False, na=False)]
                
                if len(cs_used) > 0:
                    used_analysis = []
                    for osph in sorted(cs_used['OSPH_Category'].unique()):
                        if osph == 'Unknown':
                            continue
                        df_o = cs_used[cs_used['OSPH_Category'] == osph]
                        
                        harga_min = df_o['OSPH_clean'].min() if 'OSPH_clean' in df_o.columns else 0
                        harga_max = df_o['OSPH_clean'].max() if 'OSPH_clean' in df_o.columns else 0
                        
                        used_analysis.append({
                            'Range Harga': osph,
                            'Harga Min': f"Rp {harga_min:,.0f}",
                            'Harga Max': f"Rp {harga_max:,.0f}",
                            'Total Apps ID': df_o['apps_id'].nunique(),
                            '% dari Total': f"{df_o['apps_id'].nunique()/cs_used['apps_id'].nunique()*100:.1f}%",
                            'Total Records': len(df_o),
                            'Karyawan': len(df_o[df_o['Pekerjaan_clean'].str.contains('KARYAWAN|PEGAWAI', case=False, na=False)]) if 'Pekerjaan_clean' in df_o.columns else 0,
                            'Wiraswasta': len(df_o[df_o['Pekerjaan_clean'].str.contains('WIRASWASTA|WIRAUSAHA', case=False, na=False)]) if 'Pekerjaan_clean' in df_o.columns else 0,
                            'Ibu Rumah Tangga': len(df_o[df_o['Pekerjaan_clean'].str.contains('IBU|RUMAH|TANGGA', case=False, na=False)]) if 'Pekerjaan_clean' in df_o.columns else 0,
                            'Lainnya': len(df_o) - (
                                len(df_o[df_o['Pekerjaan_clean'].str.contains('KARYAWAN|PEGAWAI|WIRASWASTA|WIRAUSAHA|IBU|RUMAH|TANGGA', case=False, na=False)]) if 'Pekerjaan_clean' in df_o.columns else 0
                            )
                        })
                    
                    used_df = pd.DataFrame(used_analysis)
                    st.dataframe(used_df, use_container_width=True, hide_index=True)
                    
                    # Breakdown Mb. Beban vs Penumpang
                    st.markdown("#### Jenis Kendaraan")
                    if 'JenisKendaraan_clean' in cs_used.columns:
                        vehicle_breakdown = cs_used.groupby(['OSPH_Category', 'JenisKendaraan_clean']).agg({
                            'apps_id': 'nunique'
                        }).reset_index()
                        vehicle_pivot = vehicle_breakdown.pivot(index='OSPH_Category', columns='JenisKendaraan_clean', values='apps_id').fillna(0)
                        st.dataframe(vehicle_pivot, use_container_width=True)
                else:
                    st.warning("Tidak ada data CS USED dalam filter ini")
    
    with tab2:
        st.header("👥 Kinerja CA")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_data = []
            for ca in df_filtered['user_name_clean'].unique():
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                apps = df_ca['apps_id'].nunique()
                sla = df_ca['SLA_Days'].mean()
                approve = len(df_ca[df_ca['Scoring_Group'] == 'APPROVE'])
                reguler = len(df_ca[df_ca['Scoring_Group'] == 'REGULER'])
                reject = len(df_ca[df_ca['Scoring_Group'] == 'REJECT'])
                total = approve + reguler + reject
                rate = approve / total * 100 if total > 0 else 0
                
                ca_data.append({
                    'CA': ca,
                    'Jumlah Apps': apps,
                    'SLA': f"{sla:.1f}h" if not pd.isna(sla) else "-",
                    'APPROVE': approve,
                    'REGULER': reguler,
                    'REJECT': reject,
                    '% Approval': f"{rate:.1f}%",
                    'Rating': '⭐⭐⭐' if rate > 60 else '⭐⭐' if rate > 40 else '⭐'
                })
            
            ca_df = pd.DataFrame(ca_data).sort_values('Jumlah Apps', ascending=False)
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(ca_df.head(10), x='CA', y='Jumlah Apps', title="Top 10 CA berdasarkan Volume")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                ca_df['Approval_num'] = ca_df['% Approval'].str.replace('%', '').astype(float)
                ca_df['SLA_num'] = ca_df['SLA'].str.replace('h', '').replace('-', '0').astype(float)
                fig = px.scatter(ca_df, x='SLA_num', y='Approval_num', size='Jumlah Apps', 
                               hover_data=['CA'], title="SLA vs Approval Rate",
                               labels={'SLA_num': 'SLA (hari)', 'Approval_num': 'Approval %'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Tambahan: History per CA
            st.subheader("📜 History Hasil Scoring per CA")
            if 'position_name_clean' in df_filtered.columns:
                ca_history = df_filtered.groupby(['user_name_clean', 'Scoring_Group']).size().reset_index(name='Jumlah')
                ca_pivot = ca_history.pivot(index='user_name_clean', columns='Scoring_Group', values='Jumlah').fillna(0)
                st.dataframe(ca_pivot, use_container_width=True)
    
    with tab3:
        st.header("📊 Detail Scoring")
        
        if 'Scoring_Detail' in df_filtered.columns:
            scoring = df_filtered['Scoring_Detail'].value_counts().reset_index()
            scoring.columns = ['Hasil Scoring', 'Jumlah']
            scoring['%'] = (scoring['Jumlah'] / len(df_filtered) * 100).round(2)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(scoring, x='Hasil Scoring', y='Jumlah', text='Jumlah', 
                           title="Distribusi Hasil Scoring")
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(scoring, hide_index=True, use_container_width=True)
            
            # Filter posisi CA untuk Reject/Reguler
            st.subheader("🔍 Filter Posisi CA: Reject & Reguler")
            if 'position_name_clean' in df_filtered.columns:
                reject_reguler = df_filtered[df_filtered['Scoring_Group'].isin(['REJECT', 'REGULER'])]
                if len(reject_reguler) > 0:
                    position_analysis = reject_reguler.groupby(['position_name_clean', 'Scoring_Group']).agg({
                        'apps_id': 'nunique'
                    }).reset_index()
                    position_pivot = position_analysis.pivot(index='position_name_clean', 
                                                            columns='Scoring_Group', 
                                                            values='apps_id').fillna(0)
                    st.dataframe(position_pivot, use_container_width=True)
                    
                    # Note: Satu app_id bisa punya banyak posisi CA
                    multi_ca = df_filtered.groupby('apps_id')['user_name_clean'].nunique()
                    multi_ca_apps = multi_ca[multi_ca > 1].count()
                    st.info(f"ℹ️ {multi_ca_apps} aplikasi ditangani oleh lebih dari 1 CA")
                else:
                    st.warning("Tidak ada data Reject/Reguler")
    
    with tab4:
        st.header("📋 Status Aplikasi")
        
        if 'apps_status_clean' in df_filtered.columns:
            status_data = df_filtered.groupby('apps_status_clean').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean'
            }).reset_index()
            status_data.columns = ['Status', 'Jumlah Apps', 'SLA Rata-rata']
            status_data['SLA Rata-rata'] = status_data['SLA Rata-rata'].round(1)
            
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(status_data, hide_index=True, use_container_width=True)
            with col2:
                fig = px.pie(status_data, values='Jumlah Apps', names='Status', 
                           title="Distribusi Status Aplikasi", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            
            # Status vs Scoring
            st.subheader("📊 Status Aplikasi vs Hasil Scoring")
            if 'Scoring_Group' in df_filtered.columns:
                status_scoring = df_filtered.groupby(['apps_status_clean', 'Scoring_Group']).size().reset_index(name='Jumlah')
                status_pivot = status_scoring.pivot(index='apps_status_clean', columns='Scoring_Group', values='Jumlah').fillna(0)
                st.dataframe(status_pivot, use_container_width=True)
                
                fig = px.bar(status_scoring, x='apps_status_clean', y='Jumlah', color='Scoring_Group',
                           title="Status Aplikasi vs Scoring", barmode='stack')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.header("🚗 Produk & Cabang")
        
        col1, col2 = st.columns(2)
        with col1:
            if 'Produk_clean' in df_filtered.columns:
                prod = df_filtered['Produk_clean'].value_counts().reset_index()
                prod.columns = ['Produk', 'Jumlah']
                st.dataframe(prod, hide_index=True, use_container_width=True)
                fig = px.pie(prod, values='Jumlah', names='Produk', title="Distribusi Produk", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'branch_name_clean' in df_filtered.columns:
                branch = df_filtered['branch_name_clean'].value_counts().head(10).reset_index()
                branch.columns = ['Cabang', 'Jumlah']
                st.dataframe(branch, hide_index=True, use_container_width=True)
                fig = px.bar(branch, x='Cabang', y='Jumlah', title="Top 10 Cabang")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab6:
        st.header("🔍 Analisis Mendalam: Produk → OSPH → Kendaraan → Pekerjaan")
        
        # Pilih produk untuk analisis
        if 'Produk_clean' in df_filtered.columns:
            selected_prod_analysis = st.selectbox("Pilih Produk untuk Analisis", 
                ['Semua'] + sorted(df_filtered['Produk_clean'].unique().tolist()))
            
            df_analysis = df_filtered if selected_prod_analysis == 'Semua' else df_filtered[df_filtered['Produk_clean'] == selected_prod_analysis]
            
            # Breakdown: Produk → OSPH
            st.subheader(f"📊 Breakdown: {selected_prod_analysis} → OSPH")
            if 'OSPH_Category' in df_analysis.columns:
                prod_osph = df_analysis.groupby(['Produk_clean', 'OSPH_Category']).agg({
                    'apps_id': 'nunique',
                    'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                }).reset_index()
                prod_osph.columns = ['Produk', 'OSPH', 'Jumlah Apps', '% Approval']
                prod_osph['% Approval'] = prod_osph['% Approval'].round(1)
                st.dataframe(prod_osph, hide_index=True, use_container_width=True)
                
                fig = px.sunburst(prod_osph, path=['Produk', 'OSPH'], values='Jumlah Apps',
                                title="Hierarki: Produk → OSPH")
                st.plotly_chart(fig, use_container_width=True)
            
            # Breakdown: OSPH → Jenis Kendaraan
            st.subheader("🚗 Breakdown: OSPH → Jenis Kendaraan")
            if 'JenisKendaraan_clean' in df_analysis.columns and 'OSPH_Category' in df_analysis.columns:
                osph_vehicle = df_analysis.groupby(['OSPH_Category', 'JenisKendaraan_clean']).agg({
                    'apps_id': 'nunique',
                    'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                }).reset_index()
                osph_vehicle.columns = ['OSPH', 'Jenis Kendaraan', 'Jumlah Apps', '% Approval']
                osph_vehicle['% Approval'] = osph_vehicle['% Approval'].round(1)
                st.dataframe(osph_vehicle, hide_index=True, use_container_width=True)
                
                fig = px.bar(osph_vehicle, x='OSPH', y='Jumlah Apps', color='Jenis Kendaraan',
                           title="OSPH vs Jenis Kendaraan", barmode='group')
                st.plotly_chart(fig, use_container_width=True)
            
            # Breakdown: Jenis Kendaraan → Pekerjaan
            st.subheader("💼 Breakdown: Jenis Kendaraan → Pekerjaan")
            if 'Pekerjaan_clean' in df_analysis.columns and 'JenisKendaraan_clean' in df_analysis.columns:
                vehicle_job = df_analysis.groupby(['JenisKendaraan_clean', 'Pekerjaan_clean']).agg({
                    'apps_id': 'nunique',
                    'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                }).reset_index()
                vehicle_job.columns = ['Jenis Kendaraan', 'Pekerjaan', 'Jumlah Apps', '% Approval']
                vehicle_job['% Approval'] = vehicle_job['% Approval'].round(1)
                vehicle_job = vehicle_job.sort_values('Jumlah Apps', ascending=False).head(20)
                st.dataframe(vehicle_job, hide_index=True, use_container_width=True)
                
                fig = px.treemap(vehicle_job, path=['Jenis Kendaraan', 'Pekerjaan'], 
                               values='Jumlah Apps', color='% Approval',
                               title="Treemap: Kendaraan → Pekerjaan (colored by Approval %)")
                st.plotly_chart(fig, use_container_width=True)
            
            # Kecenderungan untuk masuk CA
            st.subheader("📈 Kecenderungan Masuk ke CA")
            st.markdown("""
            Analisis kombinasi yang paling sering masuk ke proses CA:
            """)
            
            if all(col in df_analysis.columns for col in ['Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean']):
                tendency = df_analysis.groupby(['Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean']).agg({
                    'apps_id': 'nunique',
                    'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0,
                    'SLA_Days': 'mean'
                }).reset_index()
                tendency.columns = ['Produk', 'OSPH', 'Kendaraan', 'Pekerjaan', 'Jumlah Apps', '% Approval', 'SLA Avg']
                tendency['% Approval'] = tendency['% Approval'].round(1)
                tendency['SLA Avg'] = tendency['SLA Avg'].round(1)
                tendency = tendency.sort_values('Jumlah Apps', ascending=False).head(15)
                
                st.dataframe(tendency, hide_index=True, use_container_width=True)
                
                # Insight otomatis
                st.markdown("#### 🎯 Insight Otomatis:")
                top_combo = tendency.iloc[0]
                st.markdown(f'<div class="insight-card">Kombinasi paling sering: <b>{top_combo["Produk"]}</b> + <b>{top_combo["OSPH"]}</b> + <b>{top_combo["Kendaraan"]}</b> + <b>{top_combo["Pekerjaan"]}</b> ({top_combo["Jumlah Apps"]} apps, {top_combo["% Approval"]:.1f}% approval)</div>', unsafe_allow_html=True)
                
                best_approval = tendency.loc[tendency['% Approval'].idxmax()]
                st.markdown(f'<div class="success-card">Approval tertinggi: <b>{best_approval["Produk"]}</b> + <b>{best_approval["OSPH"]}</b> + <b>{best_approval["Kendaraan"]}</b> + <b>{best_approval["Pekerjaan"]}</b> ({best_approval["% Approval"]:.1f}% approval)</div>', unsafe_allow_html=True)
    
    with tab7:
        st.header("📈 Tren")
        
        if 'YearMonth' in df_filtered.columns:
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean'
            }).reset_index()
            monthly.columns = ['Bulan', 'Volume', 'SLA']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=monthly['Bulan'], y=monthly['Volume'], name="Volume"), secondary_y=False)
            fig.add_trace(go.Scatter(x=monthly['Bulan'], y=monthly['SLA'], name="SLA", mode='lines+markers'), secondary_y=True)
            fig.update_layout(title="Tren Bulanan: Volume & SLA")
            fig.update_yaxes(title_text="Volume Aplikasi", secondary_y=False)
            fig.update_yaxes(title_text="SLA (hari)", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        
        if 'Hour' in df_filtered.columns:
            hourly = df_filtered.groupby('Hour').size().reset_index(name='Jumlah')
            fig = px.line(hourly, x='Hour', y='Jumlah', title="Pola Per Jam", markers=True)
            fig.add_vrect(x0=8.5, x1=15.5, fillcolor="green", opacity=0.1, annotation_text="Jam Kerja (08:30-15:30)")
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("ℹ️ Aplikasi yang masuk setelah jam 15:30 akan dikerjakan keesokan harinya")
        
        # Tren approval per bulan
        if 'YearMonth' in df_filtered.columns and 'Scoring_Group' in df_filtered.columns:
            st.subheader("📊 Tren Approval Rate per Bulan")
            monthly_scoring = df_filtered.groupby(['YearMonth', 'Scoring_Group']).size().reset_index(name='Jumlah')
            monthly_approval = df_filtered.groupby('YearMonth').apply(
                lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x[x['Scoring_Group'] != 'OTHER']) * 100 if len(x[x['Scoring_Group'] != 'OTHER']) > 0 else 0
            ).reset_index(name='% Approval')
            
            fig = px.line(monthly_approval, x='YearMonth', y='% Approval', 
                        title="Tren Approval Rate", markers=True)
            fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Target 50%")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab8:
        st.header("📋 Data Lengkap")
        
        cols = ['apps_id', 'user_name_clean', 'position_name_clean', 'Produk_clean', 
                'OSPH_Category', 'OSPH_clean', 'Scoring_Detail', 'Scoring_Group',
                'apps_status_clean', 'SLA_Days', 'branch_name_clean', 'Pekerjaan_clean',
                'JenisKendaraan_clean', 'Tujuan_Kredit_clean', 'LastOD_clean', 'max_OD_clean',
                'Risk_Score', 'Risk_Category', 'action_on_parsed', 'RealisasiDate_parsed']
        available = [c for c in cols if c in df_filtered.columns]
        
        st.dataframe(df_filtered[available], use_container_width=True, height=500)
        
        csv = df_filtered[available].to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, 
                          f"CA_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")
    
    st.markdown("---")
    st.markdown(f"<div style='text-align:center;color:#666'>Terakhir diupdate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
