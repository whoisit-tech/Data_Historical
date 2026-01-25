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
    
    # Standardisasi apps_status
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
        status_mapping = {
            'NOT RECOMMENDED CA': 'NOT RECOMMENDED CA',
            'PENDING CA': 'PENDING CA',
            'Pending CA Completed': 'Pending CA Completed',
            'RECOMMENDED CA': 'RECOMMENDED CA',
            'RECOMMENDED CA WITH COND': 'RECOMMENDED CA WITH COND'
        }
        df['apps_status_clean'] = df['apps_status_clean'].replace(status_mapping)
    
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
    
    # Filter apps_status
    if 'apps_status_clean' in df.columns:
        selected_status = st.sidebar.multiselect("📋 Status Aplikasi", 
            ['NOT RECOMMENDED CA', 'PENDING CA', 'Pending CA Completed', 'RECOMMENDED CA', 'RECOMMENDED CA WITH COND'],
            default=['NOT RECOMMENDED CA', 'PENDING CA', 'Pending CA Completed', 'RECOMMENDED CA', 'RECOMMENDED CA WITH COND'])
    
    # Filter scoring
    if 'Scoring_Detail' in df.columns:
        selected_scoring = st.sidebar.multiselect("🎯 Hasil Scoring",
            ['-', 'APPROVE', 'Approve 1', 'Approve 2', 'REGULER', 'Reguler 1', 'Reguler 2', 'REJECT', 'Reject 1', 'Reject 2', 'Scoring in Progress', 'data historical'],
            default=['APPROVE', 'Approve 1', 'Approve 2', 'REGULER', 'Reguler 1', 'Reguler 2', 'REJECT', 'Reject 1', 'Reject 2'])
    
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
        st.header("💰 Strategi OSPH")
        
        if 'OSPH_Category' in df_filtered.columns:
            osph_data = []
            for osph in sorted(df_filtered['OSPH_Category'].unique()):
                if osph == 'Unknown':
                    continue
                df_o = df_filtered[df_filtered['OSPH_Category'] == osph]
                apps = df_o['apps_id'].nunique()
                approve = len(df_o[df_o['Scoring_Group'] == 'APPROVE'])
                reguler = len(df_o[df_o['Scoring_Group'] == 'REGULER'])
                reject = len(df_o[df_o['Scoring_Group'] == 'REJECT'])
                total = approve + reguler + reject
                
                osph_data.append({
                    'Range OSPH': osph,
                    'Jumlah Apps': apps,
                    'APPROVE': approve,
                    'REGULER': reguler,
                    'REJECT': reject,
                    '% Approval': f"{approve/total*100:.1f}%" if total > 0 else "0%",
                    'SLA Rata-rata': f"{df_o['SLA_Days'].mean():.1f}h" if df_o['SLA_Days'].notna().any() else "-"
                })
            
            osph_df = pd.DataFrame(osph_data)
            st.dataframe(osph_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(osph_df, values='Jumlah Apps', names='Range OSPH', title="Volume berdasarkan OSPH", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(osph_df, x='Range OSPH', y=['APPROVE', 'REGULER', 'REJECT'], 
                           title="Scoring berdasarkan OSPH", barmode='stack')
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📈 Kecenderungan")
            patterns = []
            if len(osph_df) > 0:
                best = osph_df.loc[osph_df['Jumlah Apps'].idxmax(), 'Range OSPH']
                patterns.append(f"📊 Volume Tertinggi: {best}")
                
                osph_df['Approval_num'] = osph_df['% Approval'].str.replace('%', '').astype(float)
                best_approval = osph_df.loc[osph_df['Approval_num'].idxmax(), 'Range OSPH']
                patterns.append(f"✅ Approval Terbaik: {best_approval}")
                
                for p in patterns:
                    st.markdown(f'<div class="insight-card">{p}</div>', unsafe_allow_html=True)
    
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
            status_data = df_filtered.groupby(['apps_status_clean', 'Scoring_Group']).size().reset_index(name='Jumlah')
            
            col1, col2 = st.columns(2)
            with col1:
                status_summary = df_filtered['apps_status_clean'].value_counts().reset_index()
                status_summary.columns = ['Status', 'Jumlah']
                fig = px.pie(status_summary, values='Jumlah', names='Status', 
                           title="Distribusi Status Aplikasi", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                status_pivot = status_data.pivot(index='apps_status_clean', 
                                                columns='Scoring_Group', 
                                                values='Jumlah').fillna(0)
                st.dataframe(status_pivot, use_container_width=True)
            
            # Detail breakdown per status
            st.subheader("📊 Detail per Status")
            for status in ['NOT RECOMMENDED CA', 'PENDING CA', 'Pending CA Completed', 
                          'RECOMMENDED CA', 'RECOMMENDED CA WITH COND']:
                if status in df_filtered['apps_status_clean'].values:
                    with st.expander(f"📋 {status}"):
                        df_status = df_filtered[df_filtered['apps_status_clean'] == status]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Apps", df_status['apps_id'].nunique())
                        with col2:
                            avg_sla = df_status['SLA_Days'].mean()
                            st.metric("SLA Rata-rata", f"{avg_sla:.1f}h" if not pd.isna(avg_sla) else "N/A")
                        with col3:
                            if 'Scoring_Group' in df_status.columns:
                                approve_rate = (df_status['Scoring_Group'] == 'APPROVE').sum() / len(df_status) * 100
                                st.metric("Approval Rate", f"{approve_rate:.1f}%")
                        
                        scoring_dist = df_status['Scoring_Detail'].value_counts().head(5)
                        st.bar_chart(scoring_dist)
    
    with tab5:
        st.header("🚗 Analisis Produk & Cabang")
        
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
        
        # Pilih produk untuk drill down
        if 'Produk_clean' in df_filtered.columns:
            products = sorted(df_filtered['Produk_clean'].unique().tolist())
            selected_product_detail = st.selectbox("Pilih Produk untuk Analisis", products)
            
            df_product = df_filtered[df_filtered['Produk_clean'] == selected_product_detail]
            
            st.subheader(f"📊 Breakdown: {selected_product_detail}")
            
            # Level 1: OSPH
            st.markdown("#### 1️⃣ Berdasarkan Range OSPH")
            if 'OSPH_Category' in df_product.columns:
                osph_breakdown = df_product.groupby('OSPH_Category').agg({
                    'apps_id': 'nunique',
                    'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                }).reset_index()
                osph_breakdown.columns = ['Range OSPH', 'Jumlah Apps', '% Approval']
                osph_breakdown['% Approval'] = osph_breakdown['% Approval'].round(2)
                st.dataframe(osph_breakdown, hide_index=True, use_container_width=True)
                
                selected_osph_detail = st.selectbox("Pilih Range OSPH", 
                                                   sorted([x for x in df_product['OSPH_Category'].unique() if x != 'Unknown']))
                
                df_osph = df_product[df_product['OSPH_Category'] == selected_osph_detail]
                
                # Level 2: Jenis Kendaraan
                st.markdown(f"#### 2️⃣ {selected_osph_detail} → Jenis Kendaraan")
                if 'JenisKendaraan_clean' in df_osph.columns:
                    vehicle_breakdown = df_osph.groupby('JenisKendaraan_clean').agg({
                        'apps_id': 'nunique',
                        'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                    }).reset_index()
                    vehicle_breakdown.columns = ['Jenis Kendaraan', 'Jumlah Apps', '% Approval']
                    vehicle_breakdown['% Approval'] = vehicle_breakdown['% Approval'].round(2)
                    vehicle_breakdown = vehicle_breakdown.sort_values('Jumlah Apps', ascending=False)
                    st.dataframe(vehicle_breakdown, hide_index=True, use_container_width=True)
                    
                    if len(vehicle_breakdown) > 0:
                        selected_vehicle = st.selectbox("Pilih Jenis Kendaraan", 
                                                       vehicle_breakdown['Jenis Kendaraan'].tolist())
                        
                        df_vehicle = df_osph[df_osph['JenisKendaraan_clean'] == selected_vehicle]
                        
                        # Level 3: Pekerjaan
                        st.markdown(f"#### 3️⃣ {selected_vehicle} → Pekerjaan")
                        if 'Pekerjaan_clean' in df_vehicle.columns:
                            job_breakdown = df_vehicle.groupby('Pekerjaan_clean').agg({
                                'apps_id': 'nunique',
                                'Scoring_Group': lambda x: (x == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                            }).reset_index()
                            job_breakdown.columns = ['Pekerjaan', 'Jumlah Apps', '% Approval']
                            job_breakdown['% Approval'] = job_breakdown['% Approval'].round(2)
                            job_breakdown = job_breakdown.sort_values('Jumlah Apps', ascending=False)
                            st.dataframe(job_breakdown, hide_index=True, use_container_width=True)
                            
                            # Visualisasi
                            fig = px.bar(job_breakdown.head(10), x='Pekerjaan', y='Jumlah Apps',
                                       color='% Approval', title="Top 10 Pekerjaan",
                                       color_continuous_scale='RdYlGn')
                            fig.update_layout(xaxis_tickangle=-45)
                            st.plotly_chart(fig, use_container_width=True)
            
            # Kecenderungan
            st.markdown("#### 🎯 Kecenderungan Masuk ke CA")
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            
            if 'apps_status_clean' in df_product.columns:
                ca_tendency = df_product['apps_status_clean'].value_counts()
                recommended_pct = (ca_tendency.get('RECOMMENDED CA', 0) + 
                                 ca_tendency.get('RECOMMENDED CA WITH COND', 0)) / len(df_product) * 100
                not_recommended_pct = ca_tendency.get('NOT RECOMMENDED CA', 0) / len(df_product) * 100
                
                st.markdown(f"""
                **Analisis untuk {selected_product_detail}:**
                - ✅ Direkomendasikan ke CA: **{recommended_pct:.1f}%**
                - ❌ Tidak Direkomendasikan: **{not_recommended_pct:.1f}%**
                - 🔄 Pending: **{100 - recommended_pct - not_recommended_pct:.1f}%**
                """)
                
                # Insight berdasarkan OSPH dan approval rate
                if 'OSPH_Category' in df_product.columns and 'Scoring_Group' in df_product.columns:
                    best_osph = df_product.groupby('OSPH_Category').apply(
                        lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                    ).idxmax()
                    best_osph_rate = df_product.groupby('OSPH_Category').apply(
                        lambda x: (x['Scoring_Group'] == 'APPROVE').sum() / len(x) * 100 if len(x) > 0 else 0
                    ).max()
                    
                    st.markdown(f"""
                    **Rekomendasi:**
                    - 🎯 Range OSPH terbaik: **{best_osph}** dengan approval rate **{best_osph_rate:.1f}%**
                    - 💡 Fokuskan effort pada segmen ini untuk hasil optimal
                    """)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab7:
        st.header("📈 Analisis Tren")
        
        if 'YearMonth' in df_filtered.columns:
            st.subheader("📅 Tren Bulanan")
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean'
            }).reset_index()
            monthly.columns = ['Bulan', 'Volume', 'SLA']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=monthly['Bulan'], y=monthly['Volume'], name="Volume"), secondary_y=False)
            fig.add_trace(go.Scatter(x=monthly['Bulan'], y=monthly['SLA'], name="SLA", mode='lines+markers'), secondary_y=True)
            fig.update_layout(title="Tren Bulanan: Volume & SLA")
            fig.update_yaxes(title_text="Volume", secondary_y=False)
            fig.update_yaxes(title_text="SLA (hari)", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        
        if 'Hour' in df_filtered.columns:
            st.subheader("🕐 Pola Jam Kerja")
            hourly = df_filtered.groupby('Hour').size().reset_index(name='Jumlah')
            fig = px.line(hourly, x='Hour', y='Jumlah', title="Distribusi per Jam", markers=True)
            fig.add_vrect(x0=8.5, x1=15.5, fillcolor="green", opacity=0.1, 
                         annotation_text="Jam Kerja (08:30-15:30)")
            st.plotly_chart(fig, use_container_width=True)
            
            work_hours = df_filtered[(df_filtered['Hour'] >= 8) & (df_filtered['Hour'] <= 15)]
            work_hours_pct = len(work_hours) / len(df_filtered) * 100
            st.info(f"📊 {work_hours_pct:.1f}% aplikasi diproses dalam jam kerja (08:30-15:30)")
        
        if 'DayName' in df_filtered.columns:
            st.subheader("📅 Distribusi Hari Kerja")
            daily = df_filtered.groupby('DayName').size().reset_index(name='Jumlah')
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            daily['DayName'] = pd.Categorical(daily['DayName'], categories=day_order, ordered=True)
            daily = daily.sort_values('DayName')
            
            fig = px.bar(daily, x='DayName', y='Jumlah', title="Volume per Hari")
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
        
        # Statistik tambahan
        st.subheader("📊 Statistik Data")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", f"{len(df_filtered):,}")
        with col2:
            st.metric("Unique Apps", f"{df_filtered['apps_id'].nunique():,}")
        with col3:
            if 'user_name_clean' in df_filtered.columns:
                st.metric("Unique CA", f"{df_filtered['user_name_clean'].nunique():,}")
        with col4:
            if 'branch_name_clean' in df_filtered.columns:
                st.metric("Unique Cabang", f"{df_filtered['branch_name_clean'].nunique():,}")
    
    st.markdown("---")
    st.markdown(f"<div style='text-align:center;color:#666'>Terakhir diperbarui: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;color:#999;font-size:12px'>Dashboard CA Analytics Ultimate | Business Intelligence Platform</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
