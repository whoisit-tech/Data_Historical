import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

# ========== KONFIGURASI ==========
st.set_page_config(page_title="CA Analytics Dashboard", layout="wide", page_icon="📊")

FILE_NAME = "HistoricalCA.xlsx"

# Custom CSS
st.markdown("""
<style>
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
    h1 { color: #667eea; text-align: center; }
    h2 { color: #764ba2; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
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

def preprocess_data(df):
    df = df.copy()
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    if 'action_on_parsed' in df.columns and 'RealisasiDate_parsed' in df.columns:
        df['SLA_Days'] = df.apply(lambda row: calculate_sla_days(row['action_on_parsed'], row['RealisasiDate_parsed']), axis=1)
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(df['Outstanding_PH'].astype(str).str.replace(',', ''), errors='coerce')
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    if 'LastOD' in df.columns:
        df['LastOD_clean'] = pd.to_numeric(df['LastOD'], errors='coerce')
    if 'max_OD' in df.columns:
        df['max_OD_clean'] = pd.to_numeric(df['max_OD'], errors='coerce')
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
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
    string_fields = ['apps_status', 'Produk', 'Pekerjaan', 'Jabatan', 'Pekerjaan_Pasangan', 
                    'JenisKendaraan', 'branch_name', 'Tujuan_Kredit', 'user_name', 'position_name']
    for field in string_fields:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
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

# ========== MAIN APP ==========
def main():
    st.title("🎯 CA Analytics Dashboard")
    st.markdown("### Executive Performance Analytics for Board Presentation")
    st.markdown("---")
    
    df = load_data()
    if df is None or df.empty:
        st.error("❌ Failed to load data")
        st.stop()
    
    st.success(f"✅ **{len(df):,}** records | **{df['apps_id'].nunique() if 'apps_id' in df.columns else 0:,}** unique apps")
    
    # Sidebar Filters
    st.sidebar.title("🔍 Filters")
    selected_product = st.sidebar.selectbox("🚗 Produk", ['All'] + sorted(df['Produk_clean'].unique().tolist()) if 'Produk_clean' in df.columns else ['All'])
    selected_branch = st.sidebar.selectbox("🏢 Branch", ['All'] + sorted(df['branch_name_clean'].unique().tolist()) if 'branch_name_clean' in df.columns else ['All'])
    selected_ca = st.sidebar.selectbox("👤 CA", ['All'] + sorted(df['user_name_clean'].unique().tolist()) if 'user_name_clean' in df.columns else ['All'])
    
    df_filtered = df.copy()
    if selected_product != 'All':
        df_filtered = df_filtered[df_filtered['Produk_clean'] == selected_product]
    if selected_branch != 'All':
        df_filtered = df_filtered[df_filtered['branch_name_clean'] == selected_branch]
    if selected_ca != 'All':
        df_filtered = df_filtered[df_filtered['user_name_clean'] == selected_ca]
    
    st.sidebar.info(f"📊 {len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)")
    
    # KPIs
    st.header("📊 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📝 Total Apps", f"{df_filtered['apps_id'].nunique():,}")
    with col2:
        avg_sla = df_filtered['SLA_Days'].mean()
        st.metric("⏱️ Avg SLA", f"{avg_sla:.1f}d" if not pd.isna(avg_sla) else "N/A")
    with col3:
        if 'Scoring_Group' in df_filtered.columns:
            approved = (df_filtered['Scoring_Group'] == 'APPROVE').sum()
            total = len(df_filtered[df_filtered['Scoring_Group'] != 'OTHER'])
            rate = approved / total * 100 if total > 0 else 0
            st.metric("✅ Approval Rate", f"{rate:.1f}%")
    with col4:
        avg_osph = df_filtered['OSPH_clean'].mean()
        st.metric("💰 Avg OSPH", f"Rp {avg_osph/1e6:.1f}M" if not pd.isna(avg_osph) else "N/A")
    with col5:
        st.metric("👥 Active CA", f"{df_filtered['user_name'].nunique():,}")
    
    st.markdown("---")
    
    # Main Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 OSPH Analysis", "👥 CA Performance", "📊 Scoring Detail", "📈 Trends", "📋 Data"])
    
    # TAB 1: OSPH
    with tab1:
        st.header("💰 OSPH Range Analysis")
        
        if 'OSPH_Category' in df_filtered.columns:
            osph_data = []
            for osph in sorted(df_filtered['OSPH_Category'].unique()):
                if osph == 'Unknown':
                    continue
                df_o = df_filtered[df_filtered['OSPH_Category'] == osph]
                approve = len(df_o[df_o['Scoring_Group'] == 'APPROVE'])
                reguler = len(df_o[df_o['Scoring_Group'] == 'REGULER'])
                reject = len(df_o[df_o['Scoring_Group'] == 'REJECT'])
                total = approve + reguler + reject
                osph_data.append({
                    'Range': osph,
                    'Apps': df_o['apps_id'].nunique(),
                    'APPROVE': approve,
                    'REGULER': reguler,
                    'REJECT': reject,
                    'Approval %': f"{approve/total*100:.1f}%" if total > 0 else "0%",
                    'Avg SLA': f"{df_o['SLA_Days'].mean():.1f}d" if df_o['SLA_Days'].notna().any() else "-"
                })
            
            osph_df = pd.DataFrame(osph_data)
            st.dataframe(osph_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(osph_df, values='Apps', names='Range', title="Volume by OSPH", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(osph_df, x='Range', y=['APPROVE', 'REGULER', 'REJECT'],
                           title="Scoring by OSPH", barmode='stack')
                st.plotly_chart(fig, use_container_width=True)
            
            # Kecenderungan
            st.subheader("📈 Detected Patterns (Kecenderungan)")
            patterns = []
            
            # Pattern: Best segment
            best_osph = osph_df.loc[osph_df['Apps'].idxmax(), 'Range']
            patterns.append(f"📊 **Highest Volume**: {best_osph} dengan {osph_df.loc[osph_df['Apps'].idxmax(), 'Apps']} apps")
            
            # Pattern: Approval rate
            osph_df['Approval_num'] = osph_df['Approval %'].str.replace('%', '').astype(float)
            best_approval = osph_df.loc[osph_df['Approval_num'].idxmax(), 'Range']
            best_rate = osph_df.loc[osph_df['Approval_num'].idxmax(), 'Approval_num']
            patterns.append(f"✅ **Best Approval Rate**: {best_approval} ({best_rate:.1f}%)")
            
            # Low vs High
            if len(osph_df) >= 3:
                low_apps = osph_df[osph_df['Range'] == '0 - 250 Juta']['Apps'].values[0] if '0 - 250 Juta' in osph_df['Range'].values else 0
                high_apps = osph_df[osph_df['Range'] == '500 Juta+']['Apps'].values[0] if '500 Juta+' in osph_df['Range'].values else 0
                if low_apps > high_apps * 2:
                    patterns.append(f"💡 **Market Insight**: Low-value segment dominates ({low_apps} vs {high_apps}) → Focus on volume strategy")
                elif high_apps > low_apps:
                    patterns.append(f"💰 **Market Insight**: Premium segment strong ({high_apps} apps) → Opportunity for upselling")
            
            for p in patterns:
                st.markdown(f'<div class="insight-card">{p}</div>', unsafe_allow_html=True)
            
            # Hierarchy
            st.subheader("🔍 Breakdown: Product → OSPH → Vehicle → Occupation")
            if all(col in df_filtered.columns for col in ['Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean']):
                hier = df_filtered.groupby(['Produk_clean', 'OSPH_Category', 'JenisKendaraan_clean', 'Pekerjaan_clean']).size().reset_index(name='Count')
                st.dataframe(hier.sort_values('Count', ascending=False).head(20), hide_index=True)
    
    # TAB 2: CA Performance
    with tab2:
        st.header("👥 CA Performance Ranking")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_data = []
            for ca in df_filtered['user_name_clean'].unique():
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                apps = df_ca['apps_id'].nunique()
                sla = df_ca['SLA_Days'].mean()
                approve = len(df_ca[df_ca['Scoring_Group'] == 'APPROVE'])
                total = len(df_ca[df_ca['Scoring_Group'] != 'OTHER'])
                rate = approve / total * 100 if total > 0 else 0
                
                ca_data.append({
                    'CA': ca,
                    'Apps': apps,
                    'Avg SLA': f"{sla:.1f}" if not pd.isna(sla) else "-",
                    'Approval Rate': f"{rate:.1f}%",
                    'APPROVE': approve,
                    'REGULER': len(df_ca[df_ca['Scoring_Group'] == 'REGULER']),
                    'REJECT': len(df_ca[df_ca['Scoring_Group'] == 'REJECT']),
                    '⭐ Rating': '🌟🌟🌟' if rate > 60 else '🌟🌟' if rate > 40 else '🌟'
                })
            
            ca_df = pd.DataFrame(ca_data).sort_values('Apps', ascending=False)
            st.dataframe(ca_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(ca_df.head(10), x='CA', y='Apps', title="Top 10 CA by Volume", color='Apps')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                ca_df['Approval_num'] = ca_df['Approval Rate'].str.replace('%', '').astype(float)
                fig = px.scatter(ca_df, x='Avg SLA', y='Approval_num', size='Apps',
                               hover_data=['CA'], title="SLA vs Approval Rate")
                st.plotly_chart(fig, use_container_width=True)
            
            # CA Insights
            st.subheader("💡 CA Performance Insights")
            insights = []
            best_ca = ca_df.iloc[0]['CA']
            insights.append(f"🏆 **Top Performer**: {best_ca} dengan {ca_df.iloc[0]['Apps']} apps")
            
            best_approval_ca = ca_df.loc[ca_df['Approval_num'].idxmax(), 'CA']
            insights.append(f"✅ **Best Approval Rate**: {best_approval_ca} ({ca_df.loc[ca_df['Approval_num'].idxmax(), 'Approval Rate']})")
            
            # Workload balance
            max_apps = ca_df['Apps'].max()
            min_apps = ca_df['Apps'].min()
            if max_apps > min_apps * 2:
                insights.append(f"⚠️ **Workload Imbalance**: Range {min_apps}-{max_apps} apps per CA → Consider redistribution")
            
            for i in insights:
                st.markdown(f'<div class="success-card">{i}</div>', unsafe_allow_html=True)
    
    # TAB 3: Scoring Detail
    with tab3:
        st.header("📊 Scoring Breakdown (No Grouping)")
        
        if 'Scoring_Detail' in df_filtered.columns:
            scoring = df_filtered['Scoring_Detail'].value_counts().reset_index()
            scoring.columns = ['Scoring', 'Count']
            scoring['%'] = (scoring['Count'] / len(df_filtered) * 100).round(2)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(scoring, x='Scoring', y='Count', text='Count',
                           title="All Scoring Results", color='Count')
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(scoring, hide_index=True)
    
    # TAB 4: Trends
    with tab4:
        st.header("📈 Time Analysis")
        
        if 'YearMonth' in df_filtered.columns:
            monthly = df_filtered.groupby('YearMonth').agg({
                'apps_id': 'nunique',
                'SLA_Days': 'mean'
            }).reset_index()
            monthly.columns = ['Month', 'Volume', 'Avg SLA']
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=monthly['Month'], y=monthly['Volume'], name="Volume"), secondary_y=False)
            fig.add_trace(go.Scatter(x=monthly['Month'], y=monthly['Avg SLA'], name="Avg SLA", mode='lines+markers'), secondary_y=True)
            fig.update_layout(title="Monthly Trend")
            st.plotly_chart(fig, use_container_width=True)
        
        if 'Hour' in df_filtered.columns:
            hourly = df_filtered.groupby('Hour').size().reset_index(name='Count')
            fig = px.line(hourly, x='Hour', y='Count', title="Hourly Pattern", markers=True)
            fig.add_vrect(x0=8.5, x1=15.5, fillcolor="green", opacity=0.1, annotation_text="Work Hours")
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 5: Data
    with tab5:
        st.header("📋 Raw Data")
        cols = ['apps_id', 'user_name_clean', 'Produk_clean', 'OSPH_Category', 'Scoring_Detail', 
                'apps_status_clean', 'SLA_Days', 'branch_name_clean']
        available = [c for c in cols if c in df_filtered.columns]
        st.dataframe(df_filtered[available], use_container_width=True, height=400)
        
        csv = df_filtered[available].to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, f"CA_Data_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
    
    st.markdown("---")
    st.markdown(f"<div style='text-align:center;color:#666'>Dashboard Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
