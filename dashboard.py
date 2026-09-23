"""
GTA Business Directory – Streamlit Dashboard
=============================================
Run with:  streamlit run dashboard.py
"""

import io
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GTA Business Directory",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS – premium dark-mode design with glassmorphism accents
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ── Import Outfit font ───────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

    /* ── Global ────────────────────────────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* Dark background */
    .stApp {
        background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 40%, #0f2340 100%);
        color: #e2e8f0;
        min-height: 100vh;
    }

    /* ── Sidebar ──────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #0a1628 100%);
        border-right: 1px solid rgba(99, 179, 237, 0.15);
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #90cdf4;
    }

    /* ── Main page header ─────────────────────────────────────────────────── */
    .hero-section {
        background: linear-gradient(135deg,
            rgba(16, 40, 90, 0.8) 0%,
            rgba(20, 60, 120, 0.6) 50%,
            rgba(12, 35, 80, 0.8) 100%);
        border: 1px solid rgba(99, 179, 237, 0.25);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(12px);
        position: relative;
        overflow: hidden;
    }
    .hero-section::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -20%;
        width: 60%;
        height: 200%;
        background: radial-gradient(ellipse, rgba(66, 153, 225, 0.08) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #63b3ed 0%, #4299e1 40%, #90cdf4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 0.4rem 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        color: #a0aec0;
        font-size: 1.05rem;
        font-weight: 400;
        margin: 0;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(66, 153, 225, 0.15);
        border: 1px solid rgba(66, 153, 225, 0.3);
        color: #63b3ed;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.2rem 0.7rem;
        border-radius: 50px;
        margin-bottom: 0.8rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* ── KPI metric cards ─────────────────────────────────────────────────── */
    .kpi-card {
        background: linear-gradient(135deg,
            rgba(16, 40, 90, 0.7) 0%,
            rgba(20, 50, 100, 0.5) 100%);
        border: 1px solid rgba(99, 179, 237, 0.2);
        border-radius: 16px;
        padding: 1.5rem 1.6rem;
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        border-color: rgba(99, 179, 237, 0.45);
        box-shadow: 0 12px 40px rgba(66, 153, 225, 0.2);
    }
    .kpi-card::after {
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 60px; height: 60px;
        background: radial-gradient(circle, rgba(99, 179, 237, 0.12) 0%, transparent 70%);
        border-radius: 0 16px 0 0;
    }
    .kpi-icon  { font-size: 1.6rem; margin-bottom: 0.5rem; }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #63b3ed;
        letter-spacing: -0.5px;
        line-height: 1.1;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #718096;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.25rem;
    }

    /* ── Section headers ──────────────────────────────────────────────────── */
    .section-header {
        font-size: 1.2rem;
        font-weight: 700;
        color: #90cdf4;
        margin: 1.8rem 0 0.8rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid rgba(99, 179, 237, 0.15);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ── Chart cards ──────────────────────────────────────────────────────── */
    .chart-card {
        background: rgba(13, 27, 42, 0.6);
        border: 1px solid rgba(99, 179, 237, 0.15);
        border-radius: 16px;
        padding: 1.2rem;
        backdrop-filter: blur(8px);
    }

    /* ── Data table ───────────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    /* ── Streamlit widget overrides ───────────────────────────────────────── */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: rgba(13, 27, 42, 0.7) !important;
        border-color: rgba(99, 179, 237, 0.25) !important;
        color: #e2e8f0 !important;
        border-radius: 10px !important;
    }
    .stTextInput > div > div > input {
        background: rgba(13, 27, 42, 0.7) !important;
        border-color: rgba(99, 179, 237, 0.25) !important;
        color: #e2e8f0 !important;
        border-radius: 10px !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #3182ce 0%, #2b6cb0 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(49, 130, 206, 0.4) !important;
    }
    .stDownloadButton > button {
        background: linear-gradient(135deg, #276749 0%, #22543d 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    /* Divider */
    hr { border-color: rgba(99, 179, 237, 0.12) !important; }

    /* No-data notice */
    .no-data {
        text-align: center;
        color: #718096;
        padding: 3rem;
        font-size: 1rem;
    }

    /* Pill badge */
    .pill {
        display: inline-block;
        background: rgba(49, 130, 206, 0.18);
        border: 1px solid rgba(49, 130, 206, 0.3);
        color: #63b3ed;
        border-radius: 50px;
        padding: 0.15rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Plotly dark theme helper
# ---------------------------------------------------------------------------
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#a0aec0", size=12),
    title_font=dict(family="Outfit, sans-serif", color="#90cdf4", size=14),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(
        bgcolor="rgba(13,27,42,0.6)",
        bordercolor="rgba(99,179,237,0.2)",
        borderwidth=1,
        font=dict(color="#a0aec0"),
    ),
    xaxis=dict(
        gridcolor="rgba(99,179,237,0.08)",
        tickfont=dict(color="#a0aec0"),
        title_font=dict(color="#718096"),
    ),
    yaxis=dict(
        gridcolor="rgba(99,179,237,0.08)",
        tickfont=dict(color="#a0aec0"),
        title_font=dict(color="#718096"),
    ),
    colorway=[
        "#4299e1", "#63b3ed", "#90cdf4", "#48bb78",
        "#68d391", "#f6ad55", "#fc8181", "#b794f4",
        "#f687b3", "#76e4f7",
    ],
)

COLOUR_SEQ = [
    "#4299e1", "#63b3ed", "#90cdf4", "#48bb78",
    "#68d391", "#f6ad55", "#fc8181", "#b794f4",
    "#f687b3", "#76e4f7", "#faf089",
]


def style_fig(fig: go.Figure) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


# ---------------------------------------------------------------------------
# Data loading & cleaning
# ---------------------------------------------------------------------------

CSV_PATH = Path(__file__).parent / "data" / "businesses.csv"


@st.cache_data(show_spinner="Loading & cleaning data…")
def load_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=[
            "business_name", "category", "subcategory", "address",
            "city", "phone", "website", "rating", "num_reviews",
            "description", "source_url",
        ])

    df = pd.read_csv(CSV_PATH, dtype=str)

    # ── Standardise column names ──────────────────────────────────────────
    df.columns = df.columns.str.strip().str.lower()

    # ── Drop fully-empty rows ─────────────────────────────────────────────
    df.dropna(how="all", inplace=True)

    # ── Strip whitespace from all string columns ──────────────────────────
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

    # ── Replace empty strings with NaN ────────────────────────────────────
    df.replace("", pd.NA, inplace=True)

    # ── Standardise city names ────────────────────────────────────────────
    CITY_MAP = {
        "toronto":       "Toronto",
        "mississauga":   "Mississauga",
        "brampton":      "Brampton",
        "vaughan":       "Vaughan",
        "markham":       "Markham",
        "richmond hill": "Richmond Hill",
        "richmond-hill": "Richmond Hill",
        "ajax":          "Ajax",
        "pickering":     "Pickering",
        "whitby":        "Whitby",
        "oshawa":        "Oshawa",
        "scarborough":   "Scarborough",
        "etobicoke":     "Etobicoke",
        "north york":    "North York",
        "north-york":    "North York",
    }
    if "city" in df.columns:
        df["city"] = (
            df["city"]
            .str.strip()
            .str.lower()
            .map(lambda v: CITY_MAP.get(v, v.title()) if pd.notna(v) else pd.NA)
        )

    # ── Standardise category names ────────────────────────────────────────
    CAT_MAP = {
        "restaurants & food": "Restaurants & Food",
        "restaurants":        "Restaurants & Food",
        "health & medical":   "Health & Medical",
        "health":             "Health & Medical",
        "home services":      "Home Services",
        "home-services":      "Home Services",
        "beauty & wellness":  "Beauty & Wellness",
        "beauty":             "Beauty & Wellness",
        "automotive":         "Automotive",
        "professional services": "Professional Services",
        "professional":       "Professional Services",
        "shopping & retail":  "Shopping & Retail",
        "shopping":           "Shopping & Retail",
        "education & childcare": "Education & Childcare",
        "education":          "Education & Childcare",
        "fitness & recreation": "Fitness & Recreation",
        "fitness":            "Fitness & Recreation",
        "pets":               "Pets",
        "places of worship":  "Places of Worship",
        "religion":           "Places of Worship",
    }
    if "category" in df.columns:
        df["category"] = (
            df["category"]
            .str.strip()
            .str.lower()
            .map(lambda v: CAT_MAP.get(v, v.title()) if pd.notna(v) else pd.NA)
        )

    # ── Deduplicate by business_name + city ───────────────────────────────
    df.drop_duplicates(subset=["business_name", "city"], inplace=True)

    # ── Convert numeric fields ────────────────────────────────────────────
    for col in ["rating", "num_reviews"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Reset index ───────────────────────────────────────────────────────
    df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# Helper: number formatting
# ---------------------------------------------------------------------------

def fmt_number(n: int) -> str:
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown(
            "<h2 style='color:#63b3ed;font-size:1.3rem;font-weight:700;"
            "margin-bottom:0.2rem;'>🔎 Filters</h2>"
            "<p style='color:#718096;font-size:0.82rem;margin-top:0;'>"
            "Refine the directory</p>",
            unsafe_allow_html=True,
        )

        st.divider()

        # Clear all filters
        def clear_filters():
            st.session_state.filter_city = []
            st.session_state.filter_cat = []
            st.session_state.filter_name = ""
            st.session_state.filter_phone = False
            st.session_state.filter_website = False

        if st.button("🧹 Clear all filters", use_container_width=True):
            clear_filters()
            st.rerun()

        # City filter
        cities = sorted(df["city"].dropna().unique().tolist())

        selected_cities = st.multiselect(
            "🏢 City",
            options=cities,
            key="filter_city",
        )

        # Category filter
        categories = sorted(df["category"].dropna().unique().tolist())

        selected_cats = st.multiselect(
            "📂 Category",
            options=categories,
            key="filter_cat",
        )

        # Business name search
        name_query = st.text_input(
            "🔤 Search Business Name",
            placeholder="e.g. Tim Hortons",
            key="filter_name",
        )

        # Phone filter
        has_phone = st.checkbox(
            "📞 Has phone number",
            value=False,
            key="filter_phone",
        )

        # Website filter
        has_website = st.checkbox(
            "🌐 Has website",
            value=False,
            key="filter_website",
        )

        st.divider()

    # Apply filters
    filtered = df.copy()

    if selected_cities:
        filtered = filtered[
            filtered["city"].isin(selected_cities)
        ]

    if selected_cats:
        filtered = filtered[
            filtered["category"].isin(selected_cats)
        ]

    if name_query:
        filtered = filtered[
            filtered["business_name"].str.contains(
                name_query,
                case=False,
                na=False,
            )
        ]

    if has_phone:
        filtered = filtered[
            filtered["phone"].notna()
        ]

    if has_website:
        filtered = filtered[
            filtered["website"].notna()
        ]

    return filtered
        )
        fig = px.bar(
            city_counts,
            x="Count", y="City",
            orientation="h",
            color="Count",
            color_continuous_scale=["#1a365d", "#4299e1", "#90cdf4"],
            text="Count",
        )
        fig.update_traces(textposition="outside", textfont_size=11)
        fig.update_coloraxes(showscale=False)
        style_fig(fig)
        fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<p class="section-header">📂 Businesses by Category</p>',
                    unsafe_allow_html=True)
        cat_counts = (
            df["category"].value_counts().reset_index()
            .rename(columns={"category": "Category", "count": "Count"})
        )
        fig2 = px.pie(
            cat_counts,
            values="Count",
            names="Category",
            hole=0.5,
            color_discrete_sequence=COLOUR_SEQ,
        )
        fig2.update_traces(
            textinfo="percent+label",
            textfont_size=11,
            hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>",
        )
        style_fig(fig2)
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # ── Row 2: Top categories bar + Heatmap ──────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<p class="section-header">🏆 Top Categories (bar)</p>',
                    unsafe_allow_html=True)
        top_cats = (
            df["category"].value_counts()
            .head(10).reset_index()
            .rename(columns={"category": "Category", "count": "Count"})
        )
        fig3 = px.bar(
            top_cats,
            x="Category", y="Count",
            color="Count",
            color_continuous_scale=["#1a365d", "#4299e1", "#90cdf4"],
            text="Count",
        )
        fig3.update_traces(textposition="outside", textfont_size=11)
        fig3.update_coloraxes(showscale=False)
        style_fig(fig3)
        fig3.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.markdown('<p class="section-header">🗺️ Business Distribution by City & Category</p>',
                    unsafe_allow_html=True)
        pivot = (
            df.groupby(["city", "category"], observed=True)
            .size()
            .reset_index(name="Count")
        )
        top_cities = df["city"].value_counts().head(8).index.tolist()
        top_catsv  = df["category"].value_counts().head(8).index.tolist()
        pivot_f = pivot[
            pivot["city"].isin(top_cities) & pivot["category"].isin(top_catsv)
        ]
        heat_data = pivot_f.pivot_table(
            index="city", columns="category", values="Count", fill_value=0
        )
        fig4 = px.imshow(
            heat_data,
            color_continuous_scale=["#0a0f1e", "#1a365d", "#2b6cb0", "#63b3ed", "#90cdf4"],
            aspect="auto",
            text_auto=True,
        )
        style_fig(fig4)
        fig4.update_layout(
            xaxis_tickangle=-30,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── Row 3: Treemap ────────────────────────────────────────────────────
    st.markdown('<p class="section-header">📊 Category Breakdown Treemap</p>',
                unsafe_allow_html=True)
    tree_df = (
        df.groupby(["category", "city"], observed=True)
        .size()
        .reset_index(name="Count")
    )
    fig5 = px.treemap(
        tree_df,
        path=["category", "city"],
        values="Count",
        color="Count",
        color_continuous_scale=["#1a365d", "#2b6cb0", "#4299e1", "#90cdf4"],
    )
    style_fig(fig5)
    fig5.update_layout(margin=dict(l=5, r=5, t=30, b=5))
    st.plotly_chart(fig5, use_container_width=True)


# ---------------------------------------------------------------------------
# Business table
# ---------------------------------------------------------------------------

def render_table(df: pd.DataFrame) -> None:
    st.markdown(
        '<p class="section-header">📋 Business Directory<span class="pill">'
        f'{len(df):,} results</span></p>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.markdown('<div class="no-data">No businesses match the current filters.</div>',
                    unsafe_allow_html=True)
        return

    # Build display dataframe
    display_cols = {
        "business_name": "Business Name",
        "category":      "Category",
        "city":          "City",
        "phone":         "Phone",
        "website":       "Website",
        "address":       "Address",
        "description":   "Description",
        "source_url":    "Source URL",
    }
    available = {k: v for k, v in display_cols.items() if k in df.columns}
    disp = df[list(available.keys())].rename(columns=available).fillna("—")

    st.dataframe(
        disp,
        use_container_width=True,
        height=500,
        column_config={
            "Website": st.column_config.LinkColumn(
                "Website", display_text="Open ↗", max_chars=60
            ),
            "Source URL": st.column_config.LinkColumn(
                "Source URL", display_text="View listing ↗", max_chars=60
            ),
            "Business Name": st.column_config.TextColumn(width="medium"),
            "Description": st.column_config.TextColumn(width="large"),
        },
        hide_index=True,
    )

    # ── CSV download ────────────────────────────────────────────────────────
    csv_bytes = disp.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download filtered results as CSV",
        data=csv_bytes,
        file_name="gta_businesses_filtered.csv",
        mime="text/csv",
        use_container_width=False,
    )


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    # Header
    st.markdown(
        """
        <div class="hero-section">
            <div class="hero-badge">📍 Greater Toronto Area</div>
            <h1 class="hero-title">GTA Business Directory</h1>
            <p class="hero-subtitle">
                Explore, filter, and analyse thousands of real local businesses
                across the GTA — sourced from GTASearch.com's public open-data directory.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load data
    df_full = load_data()

    if df_full.empty:
        st.warning(
            "⚠️ No data found. Click the button below to create the business data.",
            icon="⚠️",
        )

        if st.button("🚀 Run Scraper", use_container_width=True):
            with st.spinner(
                "Scraping GTA business data... This may take several minutes."
            ):
                from scraper import scrape, normalise_phone, save_csv

                records = scrape(max_pages=1, enrich=False)

                for r in records:
                    if r["phone"]:
                        r["phone"] = normalise_phone(r["phone"])

                save_csv(records)

            st.success(f"Done! Scraped {len(records):,} businesses.")
            st.cache_data.clear()
            st.rerun()

        st.stop()

    # Apply sidebar filters
    df_filtered = render_sidebar(df_full)

    # KPI cards
    render_kpis(df_full, df_filtered)

    st.divider()

    # Charts
    render_charts(df_filtered)

    st.divider()

    # Directory table
    render_table(df_filtered)

    # Footer
    st.markdown(
        "<br><p style='text-align:center;color:#4a5568;font-size:0.78rem'>"
        "Data sourced from <a href='https://www.gtasearch.com' target='_blank' "
        "style='color:#4299e1'>GTASearch.com</a> public directory listings. "
        "Built for educational data-analysis purposes only.</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
