import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

# ========== KONFIGURASI ==========
st.set_page_config(page_title="CA Analytics Dashboard",
                   layout="wide",
                   page_icon="📊")

FILE_NAME = "HistoricalCA.xlsx"

# Custom CSS
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# ========= TANGGAL MERAH (LIBUR NASIONAL + CUTI BERSAMA) =========
TANGGAL_MERAH = [
    "01-01-2025", "27-01-2025", "28-01-2025", "29-01-2025", "28-03-2025", "31-03-2025",
    "01-04-2025", "02-04-2025", "03-04-2025", "04-04-2025", "07-04-2025", "18-04-2025",
    "01-05-2025", "12-05-2025", "29-05-2025", "06-06-2025", "09-06-2025", "27-06-2025",
    "18-08-2025", "05-09-2025", "25-12-2025", "26-12-2025", "31-12-2025",
    "01-01-2026", "02-01-2026", "16-01-2026", "16-02-2026", "17-02-2026",
    "18-03-2026", "19-03-2026", "20-03-2026", "23-03-2026", "24-03-2026",
    "03-04-2026", "01-05-2026", "14-05-2026", "27-05-2026", "28-05-2026",
    "01-06-2026", "16-06-2026", "17-08-2026", "25-08-2026", "25-12-2026",
    "31-12-2026",
]
TANGGAL_MERAH_DT = [datetime.strptime(d, "%d-%m-%Y").date() for d in TANGGAL_MERAH]


# ========== FUNGSI HELPER ==========
def parse_date(date_str):
    if pd.isna(date_str) or date_str == "-" or date_str == "":
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        formats = ["%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S",
                   "%Y-%m-%d", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).split(".")[0], fmt)
            except Exception:
                continue
        result = pd.to_datetime(date_str, errors="coerce")
        if pd.isna(result):
            return None
        return result.to_pydatetime()
    except Exception:
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
    except Exception:
        return False


def calculate_sla_days(start_dt, end_dt):
    # None jika salah satu tanggal kosong/invalid
    if not start_dt or not end_dt or pd.isna(start_dt) or pd.isna(end_dt):
        return None
    try:
        if not isinstance(start_dt, datetime):
            start_dt = pd.to_datetime(start_dt)
        if not isinstance(end_dt, datetime):
            end_dt = pd.to_datetime(end_dt)
        if pd.isna(start_dt) or pd.isna(end_dt):
            return None

        # Jika action_on > 15:30 → hitung mulai besok 08:30 (JQM)
        start_adjusted = start_dt
        cutoff = datetime.strptime("15:30", "%H:%M").time()
        if start_dt.time() >= cutoff:
            start_adjusted = start_dt + timedelta(days=1)
            start_adjusted = start_adjusted.replace(
                hour=8, minute=30, second=0
            )
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
    except Exception:
        return None


def get_osph_category(osph_value):
    try:
        if pd.isna(osph_value) or osph_value is None:
            return "Unknown"
        osph_value = float(osph_value)
        if osph_value <= 250_000_000:
            return "0 - 250 Juta"
        elif osph_value <= 500_000_000:
            return "250 - 500 Juta"
        else:
            return "500 Juta+"
    except Exception:
        return "Unknown"


def map_scoring_group(x):
    """Mapping scoring detail ke group besar untuk analitik, tanpa mengubah raw-nya."""
    if pd.isna(x):
        return "OTHER"
    s = str(x).strip().upper()
    if "APPROVE" in s and "REJECT" not in s:
        return "APPROVE"
    if "REGULER" in s or "REGULAR" in s:
        return "REGULER"
    if "REJECT" in s or "NOT RECOMMENDED" in s:
        return "REJECT"
    if "IN PROGRESS" in s:
        return "IN PROGRESS"
    return "OTHER"


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Parse dates
    for col in ["action_on", "Initiation", "RealisasiDate"]:
        if col in df.columns:
            try:
                df[f"{col}_parsed"] = df[col].apply(parse_date)
            except Exception as e:
                st.warning(f"⚠️ Error parsing {col}: {str(e)}")
                df[f"{col}_parsed"] = None

    # SLA
    if "action_on_parsed" in df.columns and "RealisasiDate_parsed" in df.columns:
        try:
            df["SLA_Days"] = df.apply(
                lambda r: calculate_sla_days(
                    r["action_on_parsed"], r["RealisasiDate_parsed"]
                ),
                axis=1,
            )
        except Exception as e:
            st.warning(f"⚠️ Error calculating SLA: {str(e)}")
            df["SLA_Days"] = None

    # OSPH
    if "Outstanding_PH" in df.columns:
        try:
            df["OSPH_clean"] = pd.to_numeric(
                df["Outstanding_PH"].astype(str).str.replace(",", ""),
                errors="coerce",
            )
            df["OSPH_Category"] = df["OSPH_clean"].apply(get_osph_category)
        except Exception as e:
            st.warning(f"⚠️ Error processing OSPH: {str(e)}")

    # Scoring detail + group analitik
    if "Hasil_Scoring_1" in df.columns:
        try:
            df["Scoring_Clean"] = df["Hasil_Scoring_1"].fillna("-")
            df["Scoring_Group"] = df["Hasil_Scoring_1"].apply(map_scoring_group)
        except Exception as e:
            st.warning(f"⚠️ Error processing scoring: {str(e)}")

    # Time features
    if "action_on_parsed" in df.columns:
        try:
            df["Hour"] = df["action_on_parsed"].dt.hour
            df["DayOfWeek"] = df["action_on_parsed"].dt.dayofweek
            df["Month"] = df["action_on_parsed"].dt.month
            df["Week"] = df["action_on_parsed"].dt.isocalendar().week
            df["YearMonth"] = df["action_on_parsed"].dt.to_period("M").astype(str)
        except Exception as e:
            st.warning(f"⚠️ Error creating time features: {str(e)}")

    # Risk score sederhana
    if "OSPH_clean" in df.columns and "SLA_Days" in df.columns:
        try:
            osph_norm = (df["OSPH_clean"] - df["OSPH_clean"].min()) / (
                df["OSPH_clean"].max() - df["OSPH_clean"].min() + 1
            )
            sla_norm = (df["SLA_Days"] - df["SLA_Days"].min()) / (
                df["SLA_Days"].max() - df["SLA_Days"].min() + 1
            )
            df["Risk_Score"] = (osph_norm * 0.6 + sla_norm * 0.4) * 100
        except Exception as e:
            st.warning(f"⚠️ Error calculating risk score: {str(e)}")

    return df


@st.cache_data
def load_data():
    if not Path(FILE_NAME).exists():
        st.error(f"❌ File '{FILE_NAME}' tidak ditemukan di folder script.")
        st.stop()
    try:
        df = pd.read_excel(FILE_NAME)
        st.info(f"📊 Raw data loaded: {len(df):,} rows")
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
    st.title("🎯 Credit Analyst Analytics Dashboard")
    st.markdown("**Performance & Risk Insight untuk Portfolio Historical CA**")
    st.markdown("---")

    with st.spinner("Loading data from HistoricalCA.xlsx..."):
        df = load_data()
    if df is None or df.empty:
        st.error("❌ Failed to load data.")
        st.stop()
    st.success(f"✅ Data loaded successfully! Total records: {len(df):,}")

    # ------------ SIDEBAR FILTER ------------
    st.sidebar.header("🔍 Filters")

    # Filter CA (untuk analisa per analis)
    if "user_name" in df.columns:
        ca_list = ["All"] + sorted(df["user_name"].dropna().unique().tolist())
        selected_ca = st.sidebar.selectbox("Credit Analyst (user_name)", ca_list)
    else:
        selected_ca = "All"

    # Filter status aplikasi (hasil CA)
    if "apps_status" in df.columns:
        status_list = ["All"] + sorted(df["apps_status"].dropna().unique().tolist())
        selected_status = st.sidebar.selectbox("Status CA (apps_status)", status_list)
    else:
        selected_status = "All"

    products = (
        ["All"] + sorted(df["Produk"].dropna().unique().tolist())
        if "Produk" in df.columns
        else ["All"]
    )
    selected_product = st.sidebar.selectbox("Produk", products)

    branches = (
        ["All"] + sorted(df["branch_name"].dropna().unique().tolist())
        if "branch_name" in df.columns
        else ["All"]
    )
    selected_branch = st.sidebar.selectbox("Branch", branches)

    # Date filter
    date_range = None
    if "action_on_parsed" in df.columns:
        df_with_dates = df[df["action_on_parsed"].notna()].copy()
        if len(df_with_dates) > 0:
            try:
                min_date = pd.to_datetime(df_with_dates["action_on_parsed"].min())
                max_date = pd.to_datetime(df_with_dates["action_on_parsed"].max())
                if pd.notna(min_date) and pd.notna(max_date):
                    date_range = st.sidebar.date_input(
                        "Periode Action_on",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date(),
                    )
            except Exception:
                st.sidebar.warning("⚠️ Date filter tidak tersedia")
                date_range = None

    # Terapkan filter
    df_filtered = df.copy()
    if selected_ca != "All" and "user_name" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["user_name"] == selected_ca]
    if selected_status != "All" and "apps_status" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["apps_status"] == selected_status]
    if selected_product != "All" and "Produk" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Produk"] == selected_product]
    if selected_branch != "All" and "branch_name" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["branch_name"] == selected_branch]
    if (
        date_range is not None
        and len(date_range) == 2
        and "action_on_parsed" in df_filtered.columns
    ):
        try:
            df_filtered = df_filtered[
                (df_filtered["action_on_parsed"].notna())
                & (df_filtered["action_on_parsed"].dt.date >= date_range[0])
                & (df_filtered["action_on_parsed"].dt.date <= date_range[1])
            ]
        except Exception as e:
            st.warning(f"⚠️ Date filter error: {str(e)}")

    # ========== KPI SECTION ==========
    st.header("📊 Key Performance Indicators")

    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

    with kpi_col1:
        total_apps = (
            df_filtered["apps_id"].nunique()
            if "apps_id" in df_filtered.columns
            else len(df_filtered)
        )
        st.metric("📝 Total Apps (Distinct)", f"{total_apps:,}")

    with kpi_col2:
        if "SLA_Days" in df_filtered.columns:
            avg_sla = df_filtered["SLA_Days"].mean()
            st.metric(
                "⏱️ Avg SLA (hari kerja)",
                f"{avg_sla:.1f} d" if not pd.isna(avg_sla) else "N/A",
            )
        else:
            st.metric("⏱️ Avg SLA", "N/A")

    with kpi_col3:
        if "Hasil_Scoring_1" in df_filtered.columns:
            total_scored = len(df_filtered[df_filtered["Hasil_Scoring_1"] != "-"])
            st.metric("✅ Total Scored", f"{total_scored:,}")
        else:
            st.metric("✅ Total Scored", "N/A")

    with kpi_col4:
        if "apps_status" in df_filtered.columns:
            recommended = len(
                df_filtered[
                    df_filtered["apps_status"].str.contains(
                        "RECOMMENDED CA", case=False, na=False
                    )
                ]
            )
            st.metric("👍 Recommended CA", f"{recommended:,}")
        else:
            st.metric("👍 Recommended CA", "N/A")

    with kpi_col5:
        if "apps_status" in df_filtered.columns:
            not_recommended = len(
                df_filtered[
                    df_filtered["apps_status"].str.contains(
                        "NOT RECOMMENDED", case=False, na=False
                    )
                ]
            )
            st.metric("❌ Not Recommended CA", f"{not_recommended:,}")
        else:
            st.metric("❌ Not Recommended CA", "N/A")

    # Additional KPIs
    st.markdown("### 📌 Additional Metrics")
    kpi_col6, kpi_col7, kpi_col8, kpi_col9 = st.columns(4)

    with kpi_col6:
        if "user_name" in df_filtered.columns and "apps_id" in df_filtered.columns:
            apps_per_ca = (
                df_filtered.groupby("apps_id")["user_name"].nunique().mean()
            )
            st.metric("👥 Avg CA per AppID", f"{apps_per_ca:.2f}")
        else:
            st.metric("👥 Avg CA per AppID", "N/A")

    with kpi_col7:
        if "user_name" in df_filtered.columns:
            total_ca = df_filtered["user_name"].nunique()
            st.metric("🎯 Total CA Active", f"{total_ca:,}")
        else:
            st.metric("🎯 Total CA Active", "N/A")

    with kpi_col8:
        if "Produk" in df_filtered.columns:
            cs_new = len(df_filtered[df_filtered["Produk"] == "CS NEW"])
            cs_used = len(df_filtered[df_filtered["Produk"] == "CS USED"])
            st.metric("🚗 CS NEW / USED", f"{cs_new:,} / {cs_used:,}")
        else:
            st.metric("🚗 Products", "N/A")

    with kpi_col9:
        if "Hour" in df_filtered.columns and len(df_filtered) > 0:
            working_hours = df_filtered[
                (df_filtered["Hour"] >= 8) & (df_filtered["Hour"] <= 15)
            ]
            compliance = len(working_hours) / len(df_filtered) * 100
            st.metric("⏰ Work Hours Compliance", f"{compliance:.1f}%")
        else:
            st.metric("⏰ Work Hours", "N/A")

    st.markdown("---")

    # ========== HIGHLIGHT: OSPH BREAKDOWN ==========
    st.header("📌 Highlight Analysis - OSPH Breakdown")
    highlight_tabs = st.tabs(
        ["📊 By Range Harga", "👔 By Pekerjaan", "🚗 By Jenis Kendaraan"]
    )

    # TAB 1: Range Harga
    with highlight_tabs[0]:
        st.subheader("Analysis by OSPH Range")
        if "OSPH_Category" in df_filtered.columns and "Scoring_Group" in df_filtered.columns:
            range_analysis = (
                df_filtered.groupby("OSPH_Category")
                .agg({"apps_id": "nunique", "OSPH_clean": ["min", "max"]})
                .reset_index()
            )
            range_analysis.columns = [
                "Range Harga",
                "Total Apps ID",
                "Harga Min",
                "Harga Max",
            ]

            scoring_counts = (
                df_filtered.groupby(["OSPH_Category", "Scoring_Group"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )

            range_analysis = range_analysis.merge(
                scoring_counts,
                left_on="Range Harga",
                right_on="OSPH_Category",
                how="left",
            )
            if "OSPH_Category" in range_analysis.columns:
                range_analysis = range_analysis.drop("OSPH_Category", axis=1)

            for col in ["APPROVE", "REGULER", "REJECT", "IN PROGRESS", "OTHER"]:
                if col not in range_analysis.columns:
                    range_analysis[col] = 0

            # Label yang lebih jelas untuk Division Head
            range_analysis = range_analysis.rename(
                columns={
                    "APPROVE": "Approve",
                    "REGULER": "Reguler",
                    "REJECT": "Reject",
                    "IN PROGRESS": "Scoring in Progress",
                }
            )

            range_analysis["% dari Total"] = (
                range_analysis["Total Apps ID"] / total_apps * 100
            ).round(1)

            range_analysis["Harga Min"] = range_analysis["Harga Min"].apply(
                lambda x: f"Rp {x/1e6:,.1f}M" if pd.notna(x) else "-"
            )
            range_analysis["Harga Max"] = range_analysis["Harga Max"].apply(
                lambda x: f"Rp {x/1e6:,.1f}M" if pd.notna(x) else "-"
            )

            st.dataframe(range_analysis, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(
                    range_analysis,
                    values="Total Apps ID",
                    names="Range Harga",
                    title="Share Volume per OSPH Range",
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                bar_data = (
                    df_filtered.groupby(["OSPH_Category", "Scoring_Group"])
                    .size()
                    .reset_index(name="Count")
                )
                bar_data = bar_data[
                    bar_data["Scoring_Group"].isin(["APPROVE", "REGULER", "REJECT"])
                ]
                fig = px.bar(
                    bar_data,
                    x="OSPH_Category",
                    y="Count",
                    color="Scoring_Group",
                    title="Hasil Scoring per Range OSPH",
                    barmode="group",
                    labels={"OSPH_Category": "Range Harga", "Count": "Jumlah"},
                )
                st.plotly_chart(fig, use_container_width=True)

    # TAB 2: Pekerjaan
    with highlight_tabs[1]:
        st.subheader("Analysis by Pekerjaan & OSPH Range")
        if all(
            c in df_filtered.columns
            for c in ["OSPH_Category", "Pekerjaan", "Scoring_Group"]
        ):
            job_pivot = df_filtered.pivot_table(
                index="OSPH_Category",
                columns="Pekerjaan",
                values="apps_id",
                aggfunc="nunique",
                fill_value=0,
            )
            st.dataframe(job_pivot, use_container_width=True)

            fig = px.imshow(
                job_pivot,
                text_auto=True,
                aspect="auto",
                title="Heatmap: OSPH Range vs Pekerjaan",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig, use_container_width=True)

            job_dist = (
                df_filtered.groupby(["OSPH_Category", "Pekerjaan"])
                .size()
                .reset_index(name="Count")
            )
            fig = px.bar(
                job_dist,
                x="OSPH_Category",
                y="Count",
                color="Pekerjaan",
                title="Distribusi OSPH Range per Pekerjaan",
                barmode="stack",
            )
            st.plotly_chart(fig, use_container_width=True)

    # TAB 3: Jenis Kendaraan
    with highlight_tabs[2]:
        st.subheader("Analysis by Jenis Kendaraan & OSPH Range")
        if all(c in df_filtered.columns for c in ["OSPH_Category", "JenisKendaraan"]):
            vehicle_pivot = df_filtered.pivot_table(
                index="OSPH_Category",
                columns="JenisKendaraan",
                values="apps_id",
                aggfunc="nunique",
                fill_value=0,
            )
            st.dataframe(vehicle_pivot, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.imshow(
                    vehicle_pivot,
                    text_auto=True,
                    aspect="auto",
                    title="Heatmap: OSPH Range vs Jenis Kendaraan",
                    color_continuous_scale="Greens",
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                vehicle_dist = (
                    df_filtered.groupby(["OSPH_Category", "JenisKendaraan"])
                    .size()
                    .reset_index(name="Count")
                )
                fig = px.bar(
                    vehicle_dist,
                    x="OSPH_Category",
                    y="Count",
                    color="JenisKendaraan",
                    title="Distribusi Volume per Jenis Kendaraan",
                    barmode="group",
                )
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ========== DETAIL TABS ==========
    tabs = st.tabs(
        [
            "📈 Trend & Pattern",
            "🎯 Conversion Analysis",
            "⏱️ SLA Deep Dive",
            "🔍 Segmentation",
            "💡 Insights",
            "📋 Raw Data",
        ]
    )

    # TAB 1: Trend & Pattern
    with tabs[0]:
        st.header("📈 Trend Analysis & Patterns")
        c1, c2 = st.columns(2)

        with c1:
            if "YearMonth" in df_filtered.columns and "Scoring_Group" in df_filtered.columns:
                try:
                    monthly_data = []
                    for m in sorted(df_filtered["YearMonth"].unique()):
                        m_df = df_filtered[df_filtered["YearMonth"] == m]
                        volume = (
                            m_df["apps_id"].nunique()
                            if "apps_id" in m_df.columns
                            else len(m_df)
                        )
                        total = len(m_df)
                        approval_rate = (
                            (m_df["Scoring_Group"] == "APPROVE").sum()
                            / total
                            * 100
                            if total > 0
                            else 0
                        )
                        monthly_data.append(
                            {"Month": m, "Volume": volume, "Approval_Rate": approval_rate}
                        )
                    if monthly_data:
                        monthly_trend = pd.DataFrame(monthly_data)
                        fig = make_subplots(specs=[[{"secondary_y": True}]])
                        fig.add_trace(
                            go.Bar(
                                x=monthly_trend["Month"],
                                y=monthly_trend["Volume"],
                                name="Volume Apps",
                            ),
                            secondary_y=False,
                        )
                        fig.add_trace(
                            go.Scatter(
                                x=monthly_trend["Month"],
                                y=monthly_trend["Approval_Rate"],
                                name="Approval %",
                                mode="lines+markers",
                            ),
                            secondary_y=True,
                        )
                        fig.update_layout(
                            title="Trend Bulanan: Volume & Approval Rate"
                        )
                        fig.update_yaxes(title_text="Volume Apps", secondary_y=False)
                        fig.update_yaxes(
                            title_text="Approval Rate (%)", secondary_y=True
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("⚠️ No monthly trend data available")
                except Exception as e:
                    st.error(f"Error creating monthly trend: {str(e)}")

        with c2:
            if "DayOfWeek" in df_filtered.columns:
                dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                dow_data = (
                    df_filtered.groupby("DayOfWeek")
                    .size()
                    .reset_index(name="Count")
                )
                dow_data["Day"] = dow_data["DayOfWeek"].apply(lambda x: dow_names[x])
                fig = px.bar(
                    dow_data,
                    x="Day",
                    y="Count",
                    title="Pola Harian (Senin–Minggu)",
                    color="Count",
                    color_continuous_scale="Blues",
                )
                st.plotly_chart(fig, use_container_width=True)

        # Correlation
        if all(c in df_filtered.columns for c in ["OSPH_clean", "SLA_Days", "LastOD", "max_OD"]):
            st.subheader("🔗 Korelasi OSPH, SLA & OD")
            corr_cols = ["OSPH_clean", "SLA_Days", "LastOD", "max_OD"]
            df_corr = df_filtered[corr_cols].copy()
            for c in corr_cols:
                df_corr[c] = pd.to_numeric(df_corr[c], errors="coerce")
            df_corr = df_corr.dropna()
            if len(df_corr) > 0:
                corr_df = df_corr.corr()
                fig = px.imshow(
                    corr_df,
                    text_auto=True,
                    aspect="auto",
                    title="Correlation Heatmap",
                    color_continuous_scale="RdBu_r",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Not enough valid data for correlation analysis")

    # TAB 2: Conversion Analysis
    with tabs[1]:
        st.header("🎯 Conversion Funnel & Rate Analysis")
        if "Scoring_Group" in df_filtered.columns:
            funnel_data = [
                ("Total Applications", len(df_filtered)),
                ("Scored", len(df_filtered[df_filtered["Scoring_Group"] != "OTHER"])),
                ("Approved", len(df_filtered[df_filtered["Scoring_Group"] == "APPROVE"])),
            ]
            funnel_df = pd.DataFrame(funnel_data, columns=["Stage", "Count"])
            fig = go.Figure(
                go.Funnel(
                    y=funnel_df["Stage"],
                    x=funnel_df["Count"],
                    textinfo="value+percent total",
                )
            )
            fig.update_layout(title="Conversion Funnel CA")
            st.plotly_chart(fig, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if "OSPH_Category" in df_filtered.columns:
                    osph_conv = (
                        df_filtered.groupby("OSPH_Category")["Scoring_Group"]
                        .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                        .reset_index(name="Approval_Rate")
                    )
                    fig = px.bar(
                        osph_conv,
                        x="OSPH_Category",
                        y="Approval_Rate",
                        title="Approval Rate per Range OSPH",
                        color="Approval_Rate",
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with c2:
                if "Pekerjaan" in df_filtered.columns:
                    job_conv = (
                        df_filtered.groupby("Pekerjaan")["Scoring_Group"]
                        .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                        .reset_index(name="Approval_Rate")
                    )
                    fig = px.bar(
                        job_conv,
                        x="Pekerjaan",
                        y="Approval_Rate",
                        title="Approval Rate per Pekerjaan",
                        color="Approval_Rate",
                    )
                    fig.update_xaxes(tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

            with c3:
                if "JenisKendaraan" in df_filtered.columns:
                    vehicle_conv = (
                        df_filtered.groupby("JenisKendaraan")["Scoring_Group"]
                        .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                        .reset_index(name="Approval_Rate")
                    )
                    fig = px.bar(
                        vehicle_conv,
                        x="JenisKendaraan",
                        y="Approval_Rate",
                        title="Approval Rate per Jenis Kendaraan",
                        color="Approval_Rate",
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # TAB 3: SLA Deep Dive
    with tabs[2]:
        st.header("⏱️ SLA Performance Deep Dive")
        if "SLA_Days" in df_filtered.columns:
            df_sla = df_filtered[df_filtered["SLA_Days"].notna()].copy()
            df_sla["SLA_Days"] = pd.to_numeric(df_sla["SLA_Days"], errors="coerce")
            df_sla = df_sla[df_sla["SLA_Days"].notna()]
            if len(df_sla) > 0:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Min SLA", f"{df_sla['SLA_Days'].min():.1f} d")
                with c2:
                    st.metric("Median SLA", f"{df_sla['SLA_Days'].median():.1f} d")
                with c3:
                    st.metric("Mean SLA", f"{df_sla['SLA_Days'].mean():.1f} d")
                with c4:
                    st.metric("Max SLA", f"{df_sla['SLA_Days'].max():.1f} d")

                c1, c2 = st.columns(2)
                with c1:
                    fig = px.histogram(
                        df_sla, x="SLA_Days", nbins=30, title="Distribusi SLA (hari kerja)"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    if "OSPH_Category" in df_sla.columns:
                        fig = px.box(
                            df_sla,
                            x="OSPH_Category",
                            y="SLA_Days",
                            title="SLA per Range OSPH",
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ No valid SLA data available")

    # TAB 4: Segmentation
    with tabs[3]:
        st.header("🔍 Customer Segmentation Analysis")
        if all(
            c in df_filtered.columns
            for c in ["OSPH_Category", "Pekerjaan", "JenisKendaraan"]
        ):
            segment_data = (
                df_filtered.groupby(["OSPH_Category", "Pekerjaan", "JenisKendaraan"])
                .size()
                .reset_index(name="Count")
            )
            fig = px.sunburst(
                segment_data,
                path=["OSPH_Category", "Pekerjaan", "JenisKendaraan"],
                values="Count",
                title="Segmentasi 3 Level: OSPH – Pekerjaan – Kendaraan",
            )
            st.plotly_chart(fig, use_container_width=True)
            top_segments = segment_data.nlargest(10, "Count")
            st.dataframe(top_segments, use_container_width=True)

    # TAB 5: Insights (bahasa bisnis)
    with tabs[4]:
        st.header("💡 Key Insights & Recommendations")

        insights = []

        # 1. Segment OSPH terbaik
        if "OSPH_Category" in df_filtered.columns and "Scoring_Group" in df_filtered.columns:
            osph_approval = (
                df_filtered.groupby("OSPH_Category")["Scoring_Group"]
                .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                .to_dict()
            )
            if osph_approval:
                best_osph = max(osph_approval, key=osph_approval.get)
                worst_osph = min(osph_approval, key=osph_approval.get)
                insights.append(
                    f"🎯 **Range OSPH dengan kualitas terbaik**: {best_osph} "
                    f"dengan approval rate sekitar {osph_approval[best_osph]:.1f}%. "
                    f"Range {worst_osph} memiliki approval rate paling rendah, sehingga perlu risk appetite dan mitigasi tambahan."
                )

        # 2. SLA
        if "SLA_Days" in df_filtered.columns:
            target_sla = 3
            valid_sla = df_filtered[df_filtered["SLA_Days"].notna()]
            if len(valid_sla) > 0:
                within_sla = (valid_sla["SLA_Days"] <= target_sla).sum()
                within_sla_pct = within_sla / len(valid_sla) * 100
                insights.append(
                    f"⏱️ **Kecepatan proses CA**: sekitar {within_sla_pct:.1f}% aplikasi "
                    f"selesai dalam ≤ {target_sla} hari kerja. Outlier di atas target dapat "
                    f"difokuskan pada cabang/segmen tertentu untuk perbaikan proses."
                )

        # 3. Pekerjaan
        if "Pekerjaan" in df_filtered.columns and "Scoring_Group" in df_filtered.columns:
            job_approval = (
                df_filtered.groupby("Pekerjaan")["Scoring_Group"]
                .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                .to_dict()
            )
            if job_approval:
                best_job = max(job_approval, key=job_approval.get)
                insights.append(
                    f"👔 **Profil pekerjaan relatif aman**: segmen {best_job} menunjukkan approval rate tertinggi, "
                    f"sehingga dapat dipertimbangkan sebagai core target untuk akuisisi berkualitas."
                )

        # 4. Jenis kendaraan
        if "JenisKendaraan" in df_filtered.columns and "Scoring_Group" in df_filtered.columns:
            vehicle_approval = (
                df_filtered.groupby("JenisKendaraan")["Scoring_Group"]
                .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                .to_dict()
            )
            if vehicle_approval:
                best_vehicle = max(vehicle_approval, key=vehicle_approval.get)
                insights.append(
                    f"🚗 **Jenis kendaraan dengan risiko lebih rendah**: {best_vehicle} "
                    f"memiliki approval rate tertinggi dibanding jenis lain, sehingga dapat "
                    f"dioptimalkan untuk volume tanpa banyak menambah risiko."
                )

        # 5. Branch performance
        if "branch_name" in df_filtered.columns and "Scoring_Group" in df_filtered.columns:
            branch_approval = (
                df_filtered.groupby("branch_name")["Scoring_Group"]
                .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                .to_dict()
            )
            if branch_approval:
                best_branch = max(branch_approval, key=branch_approval.get)
                worst_branch = min(branch_approval, key=branch_approval.get)
                insights.append(
                    f"🏢 **Performa cabang**: cabang dengan kualitas terbaik saat ini adalah {best_branch} "
                    f"(approval rate tertinggi), sedangkan cabang {worst_branch} berada di level terendah "
                    f"dan menjadi kandidat prioritas untuk coaching dan review proses."
                )

        # 6. Peak working hour
        if "Hour" in df_filtered.columns and len(df_filtered) > 0:
            peak_hour = df_filtered["Hour"].mode()[0]
            peak_count = len(df_filtered[df_filtered["Hour"] == peak_hour])
            insights.append(
                f"🕐 **Pola beban kerja**: volume permohonan tertinggi terjadi sekitar jam {peak_hour}:00 "
                f"(~{peak_count/len(df_filtered)*100:.1f}% dari total). Penjadwalan CA dan support di jam ini "
                f"akan membantu menurunkan SLA dan backlog."
            )

        for txt in insights:
            st.markdown(
                f'<div class="insight-box">{txt}</div>',
                unsafe_allow_html=True,
            )

        st.subheader("📋 Actionable Recommendations")
        recs = [
            "1. Fokuskan ekspansi ke range OSPH dan segmen pekerjaan dengan approval tinggi sebagai **low-risk growth**.",
            "2. Untuk range OSPH tinggi dengan approval rendah, terapkan mitigasi (DP lebih besar, dokumen cashflow lebih ketat).",
            "3. Lakukan coaching dan sharing best practice dari cabang top-performer ke cabang dengan approval paling rendah.",
            "4. Review kapasitas tim pada peak hour untuk menjaga SLA tetap dalam target dan mencegah penumpukan PENDING CA.",
            "5. Manfaatkan Risk_Score untuk diferensiasi pricing/limit sehingga return sejalan dengan risiko.",
        ]
        for r in recs:
            st.markdown(r)

        st.subheader("📊 Statistical Summary")
        if all(c in df_filtered.columns for c in ["OSPH_clean", "SLA_Days"]):
            stats_data = {
                "Metric": ["OSPH (Rp)", "SLA (Days)"],
                "Mean": [
                    f"{df_filtered['OSPH_clean'].mean()/1e6:.1f}M"
                    if df_filtered["OSPH_clean"].notna().any()
                    else "N/A",
                    f"{df_filtered['SLA_Days'].mean():.2f}"
                    if df_filtered["SLA_Days"].notna().any()
                    else "N/A",
                ],
                "Median": [
                    f"{df_filtered['OSPH_clean'].median()/1e6:.1f}M"
                    if df_filtered["OSPH_clean"].notna().any()
                    else "N/A",
                    f"{df_filtered['SLA_Days'].median():.2f}"
                    if df_filtered["SLA_Days"].notna().any()
                    else "N/A",
                ],
                "Std Dev": [
                    f"{df_filtered['OSPH_clean'].std()/1e6:.1f}M"
                    if df_filtered["OSPH_clean"].notna().any()
                    else "N/A",
                    f"{df_filtered['SLA_Days'].std():.2f}"
                    if df_filtered["SLA_Days"].notna().any()
                    else "N/A",
                ],
                "Min": [
                    f"{df_filtered['OSPH_clean'].min()/1e6:.1f}M"
                    if df_filtered["OSPH_clean"].notna().any()
                    else "N/A",
                    f"{df_filtered['SLA_Days'].min():.2f}"
                    if df_filtered["SLA_Days"].notna().any()
                    else "N/A",
                ],
                "Max": [
                    f"{df_filtered['OSPH_clean'].max()/1e6:.1f}M"
                    if df_filtered["OSPH_clean"].notna().any()
                    else "N/A",
                    f"{df_filtered['SLA_Days'].max():.2f}"
                    if df_filtered["SLA_Days"].notna().any()
                    else "N/A",
                ],
            }
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True)

    # TAB 6: Raw Data
    with tabs[5]:
        st.header("📋 Raw Data Explorer")
        all_columns = df_filtered.columns.tolist()
        default_cols = [
            "apps_id",
            "apps_status",
            "Produk",
            "OSPH_Category",
            "Outstanding_PH",
            "Pekerjaan",
            "JenisKendaraan",
            "Hasil_Scoring_1",
            "SLA_Days",
            "branch_name",
            "user_name",
        ]
        display_cols = [c for c in default_cols if c in all_columns]
        selected_cols = st.multiselect(
            "Select columns to display", all_columns, default=display_cols
        )
        if selected_cols:
            search_term = st.text_input("🔍 Search in data")
            display_df = df_filtered[selected_cols].copy()
            if search_term:
                mask = display_df.astype(str).apply(
                    lambda x: x.str.contains(search_term, case=False, na=False)
                ).any(axis=1)
                display_df = display_df[mask]
            st.dataframe(display_df, use_container_width=True, height=400)
            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Filtered Data (CSV)",
                data=csv,
                file_name=f"CA_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Rows", len(display_df))
            with c2:
                st.metric("Total Columns", len(selected_cols))
            with c3:
                st.metric(
                    "Unique Apps",
                    display_df["apps_id"].nunique()
                    if "apps_id" in selected_cols
                    else "N/A",
                )

    # ========== ADVANCED & COMPARATIVE ==========
    st.markdown("---")
    st.header("🔬 Advanced & Comparative Analytics")

    adv_col1, adv_col2 = st.columns(2)

    with adv_col1:
        st.subheader("📈 Approval Rate Trends")
        if all(c in df_filtered.columns for c in ["YearMonth", "Scoring_Group"]):
            try:
                monthly_data = []
                for m in df_filtered["YearMonth"].unique():
                    m_df = df_filtered[df_filtered["YearMonth"] == m]
                    total = len(m_df)
                    if total > 0:
                        approval = (m_df["Scoring_Group"] == "APPROVE").sum() / total * 100
                        reguler = (m_df["Scoring_Group"] == "REGULER").sum() / total * 100
                        reject = (m_df["Scoring_Group"] == "REJECT").sum() / total * 100
                        monthly_data.append(
                            {
                                "YearMonth": m,
                                "Approval_Rate": approval,
                                "Reguler_Rate": reguler,
                                "Reject_Rate": reject,
                            }
                        )
                if monthly_data:
                    monthly_approval = pd.DataFrame(monthly_data).sort_values("YearMonth")
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=monthly_approval["YearMonth"],
                            y=monthly_approval["Approval_Rate"],
                            mode="lines+markers",
                            name="Approval",
                            line=dict(color="#10b981", width=3),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=monthly_approval["YearMonth"],
                            y=monthly_approval["Reguler_Rate"],
                            mode="lines+markers",
                            name="Reguler",
                            line=dict(color="#f59e0b", width=3),
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=monthly_approval["YearMonth"],
                            y=monthly_approval["Reject_Rate"],
                            mode="lines+markers",
                            name="Reject",
                            line=dict(color="#ef4444", width=3),
                        )
                    )
                    fig.update_layout(
                        title="Trend Approval / Reguler / Reject per Bulan",
                        xaxis_title="Month",
                        yaxis_title="Rate (%)",
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ No data available for trend analysis")
            except Exception as e:
                st.error(f"Error creating trend chart: {str(e)}")

    with adv_col2:
        st.subheader("🎯 User (CA) Performance")
        if all(c in df_filtered.columns for c in ["user_name", "Scoring_Group"]):
            try:
                user_perf = (
                    df_filtered.groupby("user_name")
                    .agg({"apps_id": "count"})
                    .reset_index()
                )
                approval_rates = (
                    df_filtered.groupby("user_name")["Scoring_Group"]
                    .apply(
                        lambda x: (x == "APPROVE").sum() / len(x) * 100
                        if len(x) > 0
                        else 0
                    )
                    .reset_index()
                )
                approval_rates.columns = ["user_name", "Approval_Rate"]
                user_perf = user_perf.merge(approval_rates, on="user_name")
                if "SLA_Days" in df_filtered.columns:
                    avg_sla = (
                        df_filtered.groupby("user_name")["SLA_Days"]
                        .mean()
                        .reset_index()
                    )
                    avg_sla.columns = ["user_name", "Avg_SLA"]
                    user_perf = user_perf.merge(avg_sla, on="user_name", how="left")
                else:
                    user_perf["Avg_SLA"] = 0
                user_perf.columns = ["User", "Total_Apps", "Approval_Rate", "Avg_SLA"]
                user_perf = user_perf.sort_values("Total_Apps", ascending=False)
                if len(user_perf) > 0:
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(
                        go.Bar(
                            x=user_perf["User"],
                            y=user_perf["Total_Apps"],
                            name="Total Apps",
                            marker_color="#667eea",
                        ),
                        secondary_y=False,
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=user_perf["User"],
                            y=user_perf["Approval_Rate"],
                            name="Approval %",
                            mode="lines+markers",
                            line=dict(color="#10b981", width=3),
                        ),
                        secondary_y=True,
                    )
                    fig.update_layout(
                        title="Performa CA: Volume vs Approval Rate"
                    )
                    fig.update_xaxes(tickangle=-45)
                    fig.update_yaxes(
                        title_text="Total Applications", secondary_y=False
                    )
                    fig.update_yaxes(
                        title_text="Approval Rate (%)", secondary_y=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ No user performance data available")
            except Exception as e:
                st.error(f"Error creating user performance chart: {str(e)}")

    st.markdown("---")
    st.header("⚖️ Comparative Analysis")

    comp_tabs = st.tabs(
        [
            "OSPH vs Pekerjaan",
            "OSPH vs Vehicle",
            "Product vs Branch",
            "Time Series Comparison",
        ]
    )

    with comp_tabs[0]:
        if all(
            c in df_filtered.columns
            for c in ["OSPH_Category", "Pekerjaan", "Scoring_Group"]
        ):
            comparison_df = (
                df_filtered.groupby(["OSPH_Category", "Pekerjaan"])
                .apply(
                    lambda x: pd.Series(
                        {
                            "Count": len(x),
                            "Approval_Rate": (x["Scoring_Group"] == "APPROVE").sum()
                            / len(x)
                            * 100,
                        }
                    )
                )
                .reset_index()
            )
            fig = px.scatter(
                comparison_df,
                x="OSPH_Category",
                y="Approval_Rate",
                size="Count",
                color="Pekerjaan",
                title="OSPH vs Pekerjaan: Approval Rate & Volume",
                hover_data=["Count"],
            )
            st.plotly_chart(fig, use_container_width=True)

    with comp_tabs[1]:
        if all(
            c in df_filtered.columns
            for c in ["OSPH_Category", "JenisKendaraan", "Scoring_Group"]
        ):
            vehicle_comp = (
                df_filtered.groupby(["OSPH_Category", "JenisKendaraan"])
                .apply(
                    lambda x: pd.Series(
                        {
                            "Count": len(x),
                            "Approval_Rate": (x["Scoring_Group"] == "APPROVE").sum()
                            / len(x)
                            * 100,
                        }
                    )
                )
                .reset_index()
            )
            fig = px.bar(
                vehicle_comp,
                x="OSPH_Category",
                y="Approval_Rate",
                color="JenisKendaraan",
                barmode="group",
                title="Approval Rate: OSPH Category by Vehicle Type",
            )
            st.plotly_chart(fig, use_container_width=True)

    with comp_tabs[2]:
        if all(
            c in df_filtered.columns
            for c in ["Produk", "branch_name", "Scoring_Group"]
        ):
            prod_branch = (
                df_filtered.groupby(["Produk", "branch_name"])["Scoring_Group"]
                .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                .reset_index(name="Approval_Rate")
            )
            fig = px.bar(
                prod_branch,
                x="branch_name",
                y="Approval_Rate",
                color="Produk",
                barmode="group",
                title="Approval Rate per Produk & Branch",
            )
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    with comp_tabs[3]:
        if all(
            c in df_filtered.columns
            for c in ["YearMonth", "Produk", "Scoring_Group"]
        ):
            time_comp = (
                df_filtered.groupby(["YearMonth", "Produk"])["Scoring_Group"]
                .apply(lambda x: (x == "APPROVE").sum() / len(x) * 100)
                .reset_index(name="Approval_Rate")
            )
            fig = px.line(
                time_comp,
                x="YearMonth",
                y="Approval_Rate",
                color="Produk",
                markers=True,
                title="Time Series: Approval Rate per Produk",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown(
        f"""
<div style='text-align: center; color: #666;'>
    <p>📊 Credit Analyst Analytics Dashboard | Built with Streamlit & Plotly</p>
    <p>Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
</div>
""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
