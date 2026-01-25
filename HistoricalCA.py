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
    "18-08-2025", "05-09-2025", "25-12-2025", "26-12-2025", "31-12-2025"
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
    """Calculate SLA in working days only"""
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
    """Clean and prepare data for analysis"""
    df = df.copy()
    
    for col in ['action_on', 'Initiation', 'RealisasiDate']:
        if col in df.columns:
            df[f'{col}_parsed'] = df[col].apply(parse_date)
    
    if all(c in df.columns for c in ['action_on_parsed', 'RealisasiDate_parsed']):
        df['SLA_Days'] = df.apply(
            lambda r: calculate_sla_days(r['action_on_parsed'], r['RealisasiDate_parsed']), 
            axis=1
        )
    
    if 'Outstanding_PH' in df.columns:
        df['OSPH_clean'] = pd.to_numeric(
            df['Outstanding_PH'].astype(str).str.replace(',', ''), 
            errors='coerce'
        )
        df['OSPH_Category'] = df['OSPH_clean'].apply(get_osph_category)
    
    for col in ['LastOD', 'max_OD']:
        if col in df.columns:
            df[f'{col}_clean'] = pd.to_numeric(df[col], errors='coerce')
    
    if 'apps_status' in df.columns:
        df['apps_status_clean'] = df['apps_status'].fillna('Unknown').astype(str).str.strip()
    
    if 'Hasil_Scoring_1' in df.columns:
        df['Scoring_Detail'] = df['Hasil_Scoring_1'].fillna('(Pilih Semua)').astype(str).str.strip()
    
    if 'action_on_parsed' in df.columns:
        df['Hour'] = df['action_on_parsed'].dt.hour
        df['DayOfWeek'] = df['action_on_parsed'].dt.dayofweek
        df['DayName'] = df['action_on_parsed'].dt.day_name()
        df['Month'] = df['action_on_parsed'].dt.month
        df['YearMonth'] = df['action_on_parsed'].dt.to_period('M').astype(str)
        df['Quarter'] = df['action_on_parsed'].dt.quarter
    
    categorical_fields = [
        'desc_status_apps', 'Produk', 'Pekerjaan', 'Jabatan',
        'Pekerjaan_Pasangan', 'JenisKendaraan', 'branch_name', 
        'Tujuan_Kredit', 'user_name', 'position_name'
    ]
    
    for field in categorical_fields:
        if field in df.columns:
            df[f'{field}_clean'] = df[field].fillna('Unknown').astype(str).str.strip()
    
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
            'Pekerjaan', 'Jabatan', 'Pekerjaan_Pasangan', 'Hasil_Scoring_1',
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
    
    if 'OSPH_Category' in df.columns and 'Scoring_Detail' in df.columns:
        for osph in ['0 - 250 Juta', '250 - 500 Juta', '500 Juta+']:
            df_osph = df[df['OSPH_Category'] == osph]
            if len(df_osph) > 0:
                approve = df_osph['Scoring_Detail'].isin(
                    ['APPROVE', 'Approve 1', 'Approve 2']
                ).sum()
                total = len(df_osph[df_osph['Scoring_Detail'] != '(Pilih Semua)'])
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
    
    # TAB 2: OD Impact Analysis
    with tab2:
        st.header("OD Impact Analysis - LastOD & max_OD")
        st.info("Analysis of how Overdue Days (OD) impact scoring decisions and risk profiles")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("LastOD Analysis")
            st.markdown("**Purpose**: Understand LastOD impact on approval rates")
            
            if 'LastOD_clean' in df_filtered.columns:
                try:
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
                                ['APPROVE', 'Approve 1', 'Approve 2']
                            ).sum()
                            
                            reject = df_od['Scoring_Detail'].isin(
                                ['Reject', 'Reject 1', 'Reject 2']
                            ).sum()
                            
                            total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                            approval_pct = (approve/total*100) if total > 0 else 0
                            avg_risk = df_od['Risk_Score'].mean()
                            
                            lastod_analysis.append({
                                'LastOD Range': cat,
                                'Total Apps': df_od['apps_id'].nunique(),
                                'Approve': approve,
                                'Reject': reject,
                                'Approval %': f"{approval_pct:.1f}%",
                                'Avg Risk': f"{avg_risk:.1f}" if pd.notna(avg_risk) else "-"
                            })
                    
                    if lastod_analysis:
                        lastod_df = pd.DataFrame(lastod_analysis)
                        st.dataframe(lastod_df, use_container_width=True, hide_index=True)
                        
                        fig = px.bar(
                            lastod_df,
                            x='LastOD Range',
                            y=['Approve', 'Reject'],
                            title="LastOD vs Approval/Rejection",
                            barmode='group'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error dalam LastOD analysis: {str(e)}")
            else:
                st.warning("Kolom 'LastOD_clean' tidak ditemukan")
        
        with col2:
            st.subheader("max_OD Analysis")
            st.markdown("**Purpose**: Understand max_OD impact on approval rates")
            
            if 'max_OD_clean' in df_filtered.columns:
                try:
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
                                ['APPROVE', 'Approve 1', 'Approve 2']
                            ).sum()
                            
                            reject = df_od['Scoring_Detail'].isin(
                                ['Reject', 'Reject 1', 'Reject 2']
                            ).sum()
                            
                            total = len(df_od[df_od['Scoring_Detail'] != '(Pilih Semua)'])
                            approval_pct = (approve/total*100) if total > 0 else 0
                            avg_risk = df_od['Risk_Score'].mean()
                            
                            maxod_analysis.append({
                                'max_OD Range': cat,
                                'Total Apps': df_od['apps_id'].nunique(),
                                'Approve': approve,
                                'Reject': reject,
                                'Approval %': f"{approval_pct:.1f}%",
                                'Avg Risk': f"{avg_risk:.1f}" if pd.notna(avg_risk) else "-"
                            })
                    
                    if maxod_analysis:
                        maxod_df = pd.DataFrame(maxod_analysis)
                        st.dataframe(maxod_df, use_container_width=True, hide_index=True)
                        
                        fig = px.bar(
                            maxod_df,
                            x='max_OD Range',
                            y=['Approve', 'Reject'],
                            title="max_OD vs Approval/Rejection",
                            barmode='group'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error dalam max_OD analysis: {str(e)}")
            else:
                st.warning("Kolom 'max_OD_clean' tidak ditemukan")
        
        st.markdown("---")
        st.subheader("OD Trend Analysis: LastOD vs max_OD")
        st.markdown("**Purpose**: Identify if customer OD is improving or worsening")
        
        if 'LastOD_clean' in df_filtered.columns and 'max_OD_clean' in df_filtered.columns:
            try:
                df_temp = df_filtered.copy()
                df_temp['OD_Trend'] = df_temp['LastOD_clean'] - df_temp['max_OD_clean']
                
                df_temp['OD_Trend_Category'] = pd.cut(
                    df_temp['OD_Trend'],
                    bins=[-np.inf, -10, -1, 0, 10, np.inf],
                    labels=[
                        'Significant Improvement',
                        'Slight Improvement',
                        'Stable',
                        'Slight Worsening',
                        'Significant Worsening'
                    ]
                )
                
                trend_analysis = []
                for cat in df_temp['OD_Trend_Category'].unique():
                    if pd.notna(cat):
                        df_trend = df_temp[df_temp['OD_Trend_Category'] == cat]
                        approve = df_trend['Scoring_Detail'].isin(
                            ['APPROVE', 'Approve 1', 'Approve 2']
                        ).sum()
                        total = len(df_trend[df_trend['Scoring_Detail'] != '(Pilih Semua)'])
                        approval_pct = (approve/total*100) if total > 0 else 0
                        avg_risk = df_trend['Risk_Score'].mean()
                        
                        trend_analysis.append({
                            'OD Trend': str(cat),
                            'Total Apps': df_trend['apps_id'].nunique(),
                            'Approval %': f"{approval_pct:.1f}%",
                            'Avg Risk': f"{avg_risk:.1f}" if pd.notna(avg_risk) else "-"
                        })
                
                if trend_analysis:
                    trend_df = pd.DataFrame(trend_analysis)
                    st.dataframe(trend_df, use_container_width=True, hide_index=True)
                    
                    fig = px.bar(
                        trend_df,
                        x='OD Trend',
                        y='Total Apps',
                        title="OD Trend Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error dalam OD Trend analysis: {str(e)}")
    
    # TAB 3: Status & Scoring Matrix
    with tab3:
        st.header("Status & Scoring Matrix")
        st.info("Complete cross-tabulation of application status and scoring results")
        
        st.subheader("Cross-Tabulation Matrix")
        st.markdown("**Purpose**: See relationship between status and scoring outcome")
        
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
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Application Status Summary")
            st.markdown("**Metrics per Status**: Volume, SLA, and Risk")
            
            if 'apps_status_clean' in df_filtered.columns:
                status_detail = df_filtered.groupby('apps_status_clean').agg({
                    'apps_id': 'nunique',
                    'SLA_Days': 'mean',
                    'Risk_Score': 'mean'
                }).reset_index()
                
                status_detail.columns = [
                    'Status',
                    'Total Apps',
                    'Avg SLA',
                    'Avg Risk'
                ]
                
                status_detail = status_detail.sort_values(
                    'Total Apps',
                    ascending=False
                )
                
                st.dataframe(status_detail, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("Scoring Result Summary")
            st.markdown("**Distribution of Scoring Outcomes**")
            
            if 'Scoring_Detail' in df_filtered.columns:
                scoring_detail = df_filtered['Scoring_Detail'].value_counts().reset_index()
                scoring_detail.columns = ['Scoring Result', 'Count']
                scoring_detail['Percentage'] = (
                    scoring_detail['Count'] / len(df_filtered) * 100
                ).round(1)
                
                st.dataframe(
                    scoring_detail,
                    use_container_width=True,
                    hide_index=True
                )
    
    # TAB 4: CA Performance
    with tab4:
        st.header("CA Performance Analytics")
        st.info("Individual CA performance metrics and comparison")
        
        if 'user_name_clean' in df_filtered.columns:
            ca_perf = []
            
            for ca in sorted(df_filtered['user_name_clean'].unique()):
                if ca == 'Unknown':
                    continue
                
                df_ca = df_filtered[df_filtered['user_name_clean'] == ca]
                
                approve = df_ca['Scoring_Detail'].isin(
                    ['APPROVE', 'Approve 1', 'Approve 2']
                ).sum()
                
                reject = df_ca['Scoring_Detail'].isin(
                    ['Reject', 'Reject 1', 'Reject 2']
                ).sum()
                
                total_scored = len(
                    df_ca[df_ca['Scoring_Detail'] != '(Pilih Semua)']
                )
                
                other = total_scored - approve - reject
                
                avg_sla = (
                    f"{df_ca['SLA_Days'].mean():.1f}" 
                    if df_ca['SLA_Days'].notna().any() 
                    else "-"
                )
                
                approval_pct = (
                    f"{approve/total_scored*100:.1f}%" 
                    if total_scored > 0 
                    else "-"
                )
                
                avg_risk = (
                    f"{df_ca['Risk_Score'].mean():.0f}" 
                    if df_ca['Risk_Score'].notna().any() 
                    else "-"
                )
                
                ca_perf.append({
                    'CA Name': ca,
                    'Total Apps': df_ca['apps_id'].nunique(),
                    'Avg SLA (days)': avg_sla,
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
    
    # TAB 5: Product Performance
    with tab5:
        st.header("Product Performance Analytics")
        st.info("Performance metrics by product")
        
        if 'Produk_clean' in df_filtered.columns:
            product_perf = []
            
            for product in sorted(df_filtered['Produk_clean'].unique()):
                if product == 'Unknown':
                    continue
                
                df_prod = df_filtered[df_filtered['Produk_clean'] == product]
                
                approve = df_prod['Scoring_Detail'].isin(
                    ['APPROVE', 'Approve 1', 'Approve 2']
                ).sum()
                
                total_scored = len(
                    df_prod[df_prod['Scoring_Detail'] != '(Pilih Semua)']
                )
                
                approval_pct = (
                    f"{approve/total_scored*100:.1f}%" 
                    if total_scored > 0 
                    else "-"
                )
                
                avg_osph = df_prod['OSPH_clean'].mean()
                avg_risk = df_prod['Risk_Score'].mean()
                avg_sla = df_prod['SLA_Days'].mean()
                
                product_perf.append({
                    'Product': product,
                    'Total Apps': df_prod['apps_id'].nunique(),
                    'Approve': approve,
                    'Approval %': approval_pct,
                    'Avg Outstanding PH': f"Rp {avg_osph/1e6:.0f}M" if pd.notna(avg_osph) else "-",
                    'Avg Risk': f"{avg_risk:.0f}" if pd.notna(avg_risk) else "-",
                    'Avg SLA': f"{avg_sla:.1f}" if pd.notna(avg_sla) else "-"
                })
            
            prod_df = pd.DataFrame(product_perf).sort_values('Total Apps', ascending=False)
            st.subheader("Product Performance Table")
            st.dataframe(prod_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(prod_df, x='Product', y='Total Apps', title="Product Volume Distribution")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                prod_df_p = prod_df.copy()
                prod_df_p['Approval_n'] = prod_df_p['Approval %'].str.replace('%', '').replace('-', '0').astype(float)
                fig = px.scatter(prod_df_p, x='Total Apps', y='Approval_n', size='Total Apps', hover_data=['Product'], title="Product: Volume vs Approval Rate")
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 6: Branch Performance
    with tab6:
        st.header("Branch Performance Analytics")
        st.info("Performance metrics by branch")
        
        if 'branch_name_clean' in df_filtered.columns:
            branch_perf = []
            
            for branch in sorted(df_filtered['branch_name_clean'].unique()):
                if branch == 'Unknown':
                    continue
                
                df_branch = df_filtered[df_filtered['branch_name_clean'] == branch]
                
                approve = df_branch['Scoring_Detail'].isin(
                    ['APPROVE', 'Approve 1', 'Approve 2']
                ).sum()
                
                total_scored = len(
                    df_branch[df_branch['Scoring_Detail'] != '(Pilih Semua)']
                )
                
                approval_pct = (
                    f"{approve/total_scored*100:.1f}%" 
                    if total_scored > 0 
                    else "-"
                )
                
                avg_osph = df_branch['OSPH_clean'].mean()
                avg_risk = df_branch['Risk_Score'].mean()
                avg_sla = df_branch['SLA_Days'].mean()
                
                branch_perf.append({
                    'Branch': branch,
                    'Total Apps': df_branch['apps_id'].nunique(),
                    'Approve': approve,
                    'Approval %': approval_pct,
                    'Avg Outstanding PH': f"Rp {avg_osph/1e6:.0f}M" if pd.notna(avg_osph) else "-",
                    'Avg Risk': f"{avg_risk:.0f}" if pd.notna(avg_risk) else "-",
                    'Avg SLA': f"{avg_sla:.1f}" if pd.notna(avg_sla) else "-"
                })
            
            branch_df = pd.DataFrame(branch_perf).sort_values('Total Apps', ascending=False)
            st.subheader("Branch Performance Table")
            st.dataframe(branch_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(branch_df, x='Branch', y='Total Apps', title="Branch Volume Distribution")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                branch_df_p = branch_df.copy()
                branch_df_p['Approval_n'] = branch_df_p['Approval %'].str.replace('%', '').replace('-', '0').astype(float)
                fig = px.scatter(branch_df_p, x='Total Apps', y='Approval_n', size='Total Apps', hover_data=['Branch'], title="Branch: Volume vs Approval Rate")
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 7: Position/Role Impact
    with tab7:
        st.header("Position/Role Impact Analysis")
        st.info("How position affects approval rate and risk")
        
        if 'position_name_clean' in df_filtered.columns:
            position_perf = []
            
            for position in sorted(df_filtered['position_name_clean'].unique()):
                if position == 'Unknown':
                    continue
                
                df_pos = df_filtered[df_filtered['position_name_clean'] == position]
                
                approve = df_pos['Scoring_Detail'].isin(
                    ['APPROVE', 'Approve 1', 'Approve 2']
                ).sum()
                
                total_scored = len(
                    df_pos[df_pos['Scoring_Detail'] != '(Pilih Semua)']
                )
                
                approval_pct = (
                    f"{approve/total_scored*100:.1f}%" 
                    if total_scored > 0 
                    else "-"
                )
                
                avg_risk = df_pos['Risk_Score'].mean()
                
                position_perf.append({
                    'Position': position,
                    'Total Apps': df_pos['apps_id'].nunique(),
                    'Approve': approve,
                    'Approval %': approval_pct,
                    'Avg Risk': f"{avg_risk:.0f}" if pd.notna(avg_risk) else "-"
                })
            
            pos_df = pd.DataFrame(position_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(pos_df, use_container_width=True, hide_index=True)
            
            fig = px.bar(pos_df, x='Position', y='Total Apps', title="Position/Role Distribution")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 8: Job Type Analysis
    with tab8:
        st.header("Job Type (Pekerjaan) Analysis")
        st.info("Approval rate and risk by occupation")
        
        if 'Pekerjaan_clean' in df_filtered.columns:
            job_perf = []
            
            for job in sorted(df_filtered['Pekerjaan_clean'].unique()):
                if job == 'Unknown':
                    continue
                
                df_job = df_filtered[df_filtered['Pekerjaan_clean'] == job]
                
                approve = df_job['Scoring_Detail'].isin(
                    ['APPROVE', 'Approve 1', 'Approve 2']
                ).sum()
                
                reject = df_job['Scoring_Detail'].isin(
                    ['Reject', 'Reject 1', 'Reject 2']
                ).sum()
                
                total_scored = len(
                    df_job[df_job['Scoring_Detail'] != '(Pilih Semua)']
                )
                
                approval_pct = (
                    f"{approve/total_scored*100:.1f}%" 
                    if total_scored > 0 
                    else "-"
                )
                
                avg_risk = df_job['Risk_Score'].mean()
                avg_osph = df_job['OSPH_clean'].mean()
                
                job_perf.append({
                    'Job Type': job,
                    'Total Apps': df_job['apps_id'].nunique(),
                    'Approve': approve,
                    'Reject': reject,
                    'Approval %': approval_pct,
                    'Avg Risk': f"{avg_risk:.0f}" if pd.notna(avg_risk) else "-",
                    'Avg OSPH': f"Rp {avg_osph/1e6:.0f}M" if pd.notna(avg_osph) else "-"
                })
            
            job_df = pd.DataFrame(job_perf).sort_values('Total Apps', ascending=False)
            st.subheader("Job Type Performance Table")
            st.dataframe(job_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(job_df.head(15), x='Job Type', y='Total Apps', title="Top 15 Job Types by Volume")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                job_df_p = job_df.copy()
                job_df_p['Approval_n'] = job_df_p['Approval %'].str.replace('%', '').replace('-', '0').astype(float)
                fig = px.scatter(job_df_p.head(15), x='Total Apps', y='Approval_n', size='Total Apps', hover_data=['Job Type'], title="Job Type: Volume vs Approval")
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 9: Credit Purpose Analysis
    with tab9:
        st.header("Credit Purpose (Tujuan Kredit) Analysis")
        st.info("Analysis by credit purpose")
        
        if 'Tujuan_Kredit_clean' in df_filtered.columns:
            purpose_perf = []
            
            for purpose in sorted(df_filtered['Tujuan_Kredit_clean'].unique()):
                if purpose == 'Unknown':
                    continue
                
                df_purp = df_filtered[df_filtered['Tujuan_Kredit_clean'] == purpose]
                
                approve = df_purp['Scoring_Detail'].isin(
                    ['APPROVE', 'Approve 1', 'Approve 2']
                ).sum()
                
                total_scored = len(
                    df_purp[df_purp['Scoring_Detail'] != '(Pilih Semua)']
                )
                
                approval_pct = (
                    f"{approve/total_scored*100:.1f}%" 
                    if total_scored > 0 
                    else "-"
                )
                
                avg_risk = df_purp['Risk_Score'].mean()
                
                purpose_perf.append({
                    'Credit Purpose': purpose,
                    'Total Apps': df_purp['apps_id'].nunique(),
                    'Approval %': approval_pct,
                    'Avg Risk': f"{avg_risk:.0f}" if pd.notna(avg_risk) else "-"
                })
            
            purp_df = pd.DataFrame(purpose_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(purp_df, use_container_width=True, hide_index=True)
            
            fig = px.pie(purp_df, values='Total Apps', names='Credit Purpose', title="Distribution by Credit Purpose")
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 10: Spouse Job Impact
    with tab10:
        st.header("Spouse Job (Pekerjaan Pasangan) Impact")
        st.info("Impact of spouse occupation on approval rate")
        
        if 'Pekerjaan_Pasangan_clean' in df_filtered.columns:
            spouse_perf = []
            
            for spouse_job in sorted(df_filtered['Pekerjaan_Pasangan_clean'].unique()):
                if spouse_job == 'Unknown':
                    continue
                
                df_spouse = df_filtered[df_filtered['Pekerjaan_Pasangan_clean'] == spouse_job]
                
                approve = df_spouse['Scoring_Detail'].isin(
                    ['APPROVE', 'Approve 1', 'Approve 2']
                ).sum()
                
                total_scored = len(
                    df_spouse[df_spouse['Scoring_Detail'] != '(Pilih Semua)']
                )
                
                approval_pct = (
                    f"{approve/total_scored*100:.1f}%" 
                    if total_scored > 0 
                    else "-"
                )
                
                avg_risk = df_spouse['Risk_Score'].mean()
                
                spouse_perf.append({
                    'Spouse Job': spouse_job,
                    'Total Apps': df_spouse['apps_id'].nunique(),
                    'Approval %': approval_pct,
                    'Avg Risk': f"{avg_risk:.0f}" if pd.notna(avg_risk) else "-"
                })
            
            spouse_df = pd.DataFrame(spouse_perf).sort_values('Total Apps', ascending=False)
            st.dataframe(spouse_df, use_container_width=True, hide_index=True)
            
            fig = px.bar(spouse_df, x='Spouse Job', y='Total Apps', title="Spouse Job Distribution")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 11: Time Pattern Analysis
    with tab11:
        st.header("Time Pattern Analysis")
        st.info("Approval patterns by time dimension")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("By Day of Week")
            if 'DayName' in df_filtered.columns:
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_data = []
                
                for day in day_order:
                    df_day = df_filtered[df_filtered['DayName'] == day]
                    if len(df_day) > 0:    if total > 0:
                    rate = approve / total * 100
                    if rate < 30:
                        warnings.append(
                            f"Low approval rate {rate:.1f}% in {osph} segment"
                        )
                    elif rate > 60:
                        insights.append(
                            f"Strong approval rate {rate:.1f}% in {osph} segment"
                        )
    
    if 'LastOD_clean' in df.columns and 'Scoring_Detail' in df.columns:
        high_od = df[df['LastOD_clean'] > 30]
        if len(high_od) > 0:
            reject_count = high_od['Scoring_Detail'].isin(
                ['Reject', 'Reject 1', 'Reject 2']
            ).sum()
            reject_rate = (reject_count / len(high_od)) * 100
            
            warnings.append(
                f"High LastOD (>30 days): {reject_rate:.1f}% rejection rate"
            )
    
    if 'SLA_Days' in df.columns and 'apps_status_clean' in df.columns:
        for status in sorted(df['apps_status_clean'].unique())[:5]:
            if status == 'Unknown':
                continue
            
            df_status = df[df['apps_status_clean'] == status]
            sla_avg = df_status['SLA_Days'].mean()
            
            if pd.notna(sla_avg) and sla_avg > 5:
                warnings.append(
                    f"{status}: Average SLA is {sla_avg:.1f} days (above target)"
                )
    
    return insights, warnings

def main():
    """Main application"""
    st.title("CA Analytics Dashboard")
    st.markdown("Advanced Business Intelligence - Performance Analysis & Monitoring")
    st.markdown("---")
    
    df = load_data()
    if df is None or df.empty:
        st.error("Data tidak dapat dimuat")
        st.stop()
    
    total_records = len(df)
    unique_apps = df['apps_id'].nunique()
    total_fields = len(df.columns)
    
    st.success(
        f"{total_records:,} records | "
        f"{unique_apps:,} unique applications | "
        f"{total_fields} fields"
    )
    
    st.sidebar.title("Analytics Control Panel")
    
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
    
    if 'Produk_clean' in df.columns:
        all_products = sorted(df['Produk_clean'].unique().tolist())
        selected_product = st.sidebar.selectbox(
            "Product",
            ['All'] + all_products
        )
    else:
        selected_product = 'All'
    
    if 'branch_name_clean' in df.columns:
        all_branches = sorted(df['branch_name_clean'].unique().tolist())
        selected_branch = st.sidebar.selectbox(
            "Branch",
            ['All'] + all_branches
        )
    else:
        selected_branch = 'All'
    
    if 'user_name_clean' in df.columns:
        all_cas = sorted(df['user_name_clean'].unique().tolist())
        selected_ca = st.sidebar.selectbox(
            "CA Name",
            ['All'] + all_cas
        )
    else:
        selected_ca = 'All'
    
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
    
    st.sidebar.markdown("---")
    st.sidebar.info(
        f"{len(df_filtered):,} records ({len(df_filtered)/len(df)*100:.1f}%)"
    )
    st.sidebar.info(
        f"{df_filtered['apps_id'].nunique():,} unique applications"
    )
    
    st.header("Key Insights & Alerts")
    insights, warnings = generate_analytical_insights(df_filtered)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            '<div class="success-card"><h3>Strategic Insights</h3>',
            unsafe_allow_html=True
        )
        if insights:
            for insight in insights:
                st.markdown(f"**{insight}**")
        else:
            st.markdown("No significant patterns detected")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
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
    
    st.header("Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        total_apps = df_filtered['apps_id'].nunique()
        st.metric("Total Applications", f"{total_apps:,}")
    
    with kpi2:
        avg_sla = df_filtered['SLA_Days'].mean()
        sla_display = f"{avg_sla:.1f}" if not pd.isna(avg_sla) else "N/A"
        st.metric("Average SLA (days)", sla_display)
    
    with kpi3:
        if 'Scoring_Detail' in df_filtered.columns:
            approve_count = df_filtered['Scoring_Detail'].isin(
                ['APPROVE', 'Approve 1', 'Approve 2']
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
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14, tab15, tab16, tab17, tab18 = st.tabs([
        "Outstanding PH Analysis",
        "OD Impact Analysis",
        "Status & Scoring Matrix",
        "CA Performance",
        "Product Performance",
        "Branch Performance",
        "Position/Role Impact",
        "Job Type Analysis",
        "Credit Purpose",
        "Spouse Job Impact",
        "Time Pattern Analysis",
        "SLA vs Quality",
        "Vehicle Type Performance",
        "Status + Job Type",
        "Branch + Product",
        "Predictive Patterns",
        "Trends & Forecasting",
        "Complete Analysis"
    ])
    
    # TAB 1: Outstanding PH Analysis
    with tab1:
        st.header("Outstanding PH Analysis - 4 Dimensions")
        st.info("Comprehensive analysis of Outstanding PH with 4 analytical dimensions")
        
        st.subheader("Dimension 1: Outstanding PH vs Scoring Result")
        st.markdown("**Purpose**: Understand scoring decision patterns across Outstanding PH ranges")
        
        if 'OSPH_Category' in df_filtered.columns and 'Scoring_Detail' in df_filtered.columns:
            dim1_data = []
            
            osph_ranges = sorted([
                x for x in df_filtered['OSPH_Category'].unique() 
                if x != 'Unknown'
            ])
            
            for osph in osph_ranges:
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                harga_min = df_osph['OSPH_clean'].min() if 'OSPH_clean' in df_osph.columns else 0
                harga_max = df_osph['OSPH_clean'].max() if 'OSPH_clean' in df_osph.columns else 0
                
                row = {
                    'Range': osph,
                    'Min Value': f"Rp {harga_min:,.0f}",
                    'Max Value': f"Rp {harga_max:,.0f}",
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                scoring_values = [
                    '(Pilih Semua)', '-', 'APPROVE', 'Approve 1', 'Approve 2',
                    'Reguler', 'Reguler 1', 'Reguler 2',
                    'Reject', 'Reject 1', 'Reject 2', 'Scoring in Progress'
                ]
                
                for scoring in scoring_values:
                    count = len(df_osph[df_osph['Scoring_Detail'] == scoring])
                    if count > 0:
                        row[scoring] = count
                
                dim1_data.append(row)
            
            dim1_df = pd.DataFrame(dim1_data)
            st.dataframe(dim1_df, use_container_width=True, hide_index=True)
            
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
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Dimension 2: Outstanding PH vs Application Status")
        st.markdown("**Purpose**: Distribution of application status across Outstanding PH ranges")
        
        if 'OSPH_Category' in df_filtered.columns and 'apps_status_clean' in df_filtered.columns:
            status_data = []
            
            for osph in sorted([
                x for x in df_filtered['OSPH_Category'].unique() 
                if x != 'Unknown'
            ]):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                row = {'Range': osph, 'Total Apps': df_osph['apps_id'].nunique()}
                
                for status in df_filtered['apps_status_clean'].unique():
                    if status != 'Unknown':
                        count = len(df_osph[df_osph['apps_status_clean'] == status])
                        if count > 0:
                            row[status] = count
                
                status_data.append(row)
            
            status_df = pd.DataFrame(status_data)
            st.dataframe(status_df, use_container_width=True, hide_index=True)
            
            status_cols = [
                c for c in status_df.columns 
                if c not in ['Range', 'Total Apps']
            ]
            
            if status_cols:
                heatmap_status = status_df[['Range'] + status_cols].set_index('Range')
                fig = px.imshow(
                    heatmap_status.T,
                    text_auto=True,
                    title="Outstanding PH vs Application Status",
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Dimension 3: Outstanding PH vs Job Type (Pekerjaan)")
        st.markdown("**Purpose**: Occupation profile across Outstanding PH ranges")
        
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
                
                harga_min = df_osph['OSPH_clean'].min() if 'OSPH_clean' in df_osph.columns else 0
                harga_max = df_osph['OSPH_clean'].max() if 'OSPH_clean' in df_osph.columns else 0
                
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
        
        st.markdown("---")
        st.subheader("Dimension 4: Outstanding PH vs Vehicle Type")
        st.markdown("**Purpose**: Vehicle preference and risk profile by Outstanding PH range")
        
        if 'OSPH_Category' in df_filtered.columns and 'JenisKendaraan_clean' in df_filtered.columns:
            dim4_data = []
            
            for osph in sorted([
                x for x in df_filtered['OSPH_Category'].unique() 
                if x != 'Unknown'
            ]):
                df_osph = df_filtered[df_filtered['OSPH_Category'] == osph]
                
                harga_min = df_osph['OSPH_clean'].min() if 'OSPH_clean' in df_osph.columns else 0
                harga_max = df_osph['OSPH_clean'].max() if 'OSPH_clean' in df_osph.columns else 0
                
                row = {
                    'Range': osph,
                    'Min Value': f"Rp {harga_min:,.0f}",
                    'Max Value': f"Rp {harga_max:,.0f}",
                    'Total Apps': df_osph['apps_id'].nunique(),
                    'Total Records': len(df_osph)
                }
                
                for vehicle_type in df_filtered['JenisKendaraan_clean'].unique():
                    if vehicle_type != 'Unknown':
                        count = len(df_osph[df_osph['JenisKendaraan_clean'] == vehicle_type])
                        if count > 0:
                            row[vehicle_type] = count
                
                dim4_data.append(row)
