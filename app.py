import copy
from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st

from workforce_model import calculate_workforce

st.set_page_config(
    page_title="AI Enabled Workforce & Capacity Planning",
    page_icon="🚀",
    layout="wide",
)

UP_ARROW = chr(8593)
BAU_UP_LABEL = "BAU " + UP_ARROW + "%"
DC_UP_LABEL = "DC " + UP_ARROW + "%"
APP_SCHEMA_VERSION = "v17_headcount_based_forecast"

REGIONS = ["North", "West", "South", "East"]
PRODUCTS = [
    "UPS",
    "Cooling",
    "Power Products",
    "Power System",
    "Industrial Automation",
]
FORECAST_YEARS = [2027, 2028, 2029]

PRODUCT_ALIASES = {
    "Power Product": "Power Products",
    "Power Products": "Power Products",
    "Power System": "Power System",
    "Industrial Automation": "Industrial Automation",
    "Industiral Automation": "Industrial Automation",
    "UPS": "UPS",
    "Cooling": "Cooling",
}

PRODUCT_DISPLAY = {
    "UPS": "UPS",
    "Cooling": "Cooling",
    "Power Products": "Power Prod",
    "Power System": "Power Sys",
    "Industrial Automation": "Ind Auto",
}
PRODUCT_REVERSE_DISPLAY = {value: key for key, value in PRODUCT_DISPLAY.items()}

REGION_STYLES = {
    "North": {"bg": "#EAF4FF", "border": "#1F77B4", "text": "#174A7C"},
    "West": {"bg": "#FFF4E5", "border": "#FF7F0E", "text": "#8A4A00"},
    "South": {"bg": "#EAF8EF", "border": "#2CA02C", "text": "#1B6B28"},
    "East": {"bg": "#F3EAFB", "border": "#9467BD", "text": "#573B78"},
}

BASE_GROWTH_BY_REGION = {
    "North": {
        "UPS": {"BAU": 20.0, "DC": 10.0},
        "Cooling": {"BAU": 20.0, "DC": 10.0},
        "Power Products": {"BAU": 15.0, "DC": 5.0},
        "Power System": {"BAU": 15.0, "DC": 5.0},
        "Industrial Automation": {"BAU": 15.0, "DC": 5.0},
    },
    "West": {
        "UPS": {"BAU": 30.0, "DC": 20.0},
        "Cooling": {"BAU": 30.0, "DC": 20.0},
        "Power Products": {"BAU": 20.0, "DC": 10.0},
        "Power System": {"BAU": 20.0, "DC": 10.0},
        "Industrial Automation": {"BAU": 20.0, "DC": 10.0},
    },
    "South": {
        "UPS": {"BAU": 22.0, "DC": 10.0},
        "Cooling": {"BAU": 22.0, "DC": 10.0},
        "Power Products": {"BAU": 20.0, "DC": 5.0},
        "Power System": {"BAU": 20.0, "DC": 5.0},
        "Industrial Automation": {"BAU": 20.0, "DC": 5.0},
    },
    "East": {
        "UPS": {"BAU": 15.0, "DC": 5.0},
        "Cooling": {"BAU": 15.0, "DC": 5.0},
        "Power Products": {"BAU": 15.0, "DC": 5.0},
        "Power System": {"BAU": 15.0, "DC": 5.0},
        "Industrial Automation": {"BAU": 15.0, "DC": 5.0},
    },
}

DEFAULT_GROWTH_PARAMETERS = {
    year: copy.deepcopy(BASE_GROWTH_BY_REGION)
    for year in FORECAST_YEARS
}
DEFAULT_ATTRITION = {product: 8.0 for product in PRODUCTS}

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f2f6ff 0%, #eefaf3 55%, #fff8ec 100%);
        border-right: 1px solid #d8e1ef;
    }
    .region-card {
        border-radius: 12px;
        padding: 10px 12px;
        margin: 12px 0 8px 0;
        font-weight: 800;
    }
    .leadership-box {
        background: linear-gradient(135deg, #eef4ff 0%, #f8f0ff 45%, #fff8ec 100%);
        border-left: 8px solid #4f7cff;
        border-radius: 16px;
        padding: 18px 22px;
        margin: 12px 0 22px 0;
        box-shadow: 0 5px 18px rgba(41, 65, 120, 0.10);
    }
    .highlight {
        font-weight: 800;
        color: #1f5eff;
    }
    .warning {
        font-weight: 800;
        color: #d97706;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state():
    if st.session_state.get("schema_version") != APP_SCHEMA_VERSION:
        st.session_state.schema_version = APP_SCHEMA_VERSION
        st.session_state.growth_parameters = copy.deepcopy(DEFAULT_GROWTH_PARAMETERS)
        st.session_state.attrition_parameters = copy.deepcopy(DEFAULT_ATTRITION)
        st.session_state.productive_hours = 7.0
        st.session_state.working_days = 20
        st.session_state.target_utilization = 90.0
        st.session_state.input_df = None
        st.session_state.result_df = None
        st.session_state.needs_recalc = False
        st.session_state.uploaded_file_id = None
        st.session_state.last_filter_signature = None


def show_region_header(region):
    style = REGION_STYLES[region]
    st.markdown(
        f"""
        <div class="region-card"
             style="background:{style['bg']};
                    border-left:7px solid {style['border']};
                    color:{style['text']};">
            {region} Growth
        </div>
        """,
        unsafe_allow_html=True,
    )


def growth_region_to_df(growth_parameters, region):
    rows = []
    for product in PRODUCTS:
        row = {"Product": PRODUCT_DISPLAY[product]}
        for forecast_year in FORECAST_YEARS:
            row[f"{forecast_year} BAU"] = float(
                growth_parameters[int(forecast_year)][region][product]["BAU"]
            )
            row[f"{forecast_year} DC"] = float(
                growth_parameters[int(forecast_year)][region][product]["DC"]
            )
        rows.append(row)
    return pd.DataFrame(rows)


def growth_region_dfs_to_dict(edited_growth_dfs):
    growth_parameters = copy.deepcopy(DEFAULT_GROWTH_PARAMETERS)
    for region, growth_df in edited_growth_dfs.items():
        for _, row in growth_df.iterrows():
            product_label = str(row["Product"]).strip()
            product = PRODUCT_REVERSE_DISPLAY.get(product_label)
            if product in PRODUCTS:
                for forecast_year in FORECAST_YEARS:
                    growth_parameters[int(forecast_year)][region][product] = {
                        "BAU": float(row[f"{forecast_year} BAU"]),
                        "DC": float(row[f"{forecast_year} DC"]),
                    }
    return growth_parameters


def attrition_dict_to_df(attrition_parameters):
    rows = []
    for product in PRODUCTS:
        rows.append(
            {
                "Product": PRODUCT_DISPLAY[product],
                "Attr %": float(attrition_parameters.get(product, 8.0)),
            }
        )
    return pd.DataFrame(rows)


def attrition_df_to_dict(attrition_df):
    attrition_parameters = copy.deepcopy(DEFAULT_ATTRITION)
    for _, row in attrition_df.iterrows():
        product_label = str(row["Product"]).strip()
        product = PRODUCT_REVERSE_DISPLAY.get(product_label)
        if product in PRODUCTS:
            attrition_parameters[product] = float(row["Attr %"])
    return attrition_parameters


def productivity_to_df():
    return pd.DataFrame(
        [
            {
                "Hrs/Day": float(st.session_state.productive_hours),
                "Days/M": int(st.session_state.working_days),
                "Util %": float(st.session_state.target_utilization),
            }
        ]
    )


def productivity_df_to_values(productivity_df):
    row = productivity_df.iloc[0]
    return float(row["Hrs/Day"]), int(row["Days/M"]), float(row["Util %"])


def add_total_row_and_column(matrix):
    matrix = matrix.copy()
    matrix["Total"] = matrix.sum(axis=1)
    total_row = pd.DataFrame(matrix.sum(axis=0)).T
    total_row.index = ["Total"]
    return pd.concat([matrix, total_row])


def build_bu_requirement_comparison(df, result):
    existing_resource = (
        df.groupby("Product")["Current_SE"]
        .sum()
        .reset_index()
        .rename(columns={"Current_SE": "Existing 2026 SE"})
    )
    requirement = (
        result.groupby("Product")["Combined Required Engineers"]
        .sum()
        .reset_index()
        .rename(columns={"Combined Required Engineers": "Forecast Required SE"})
    )
    hiring = (
        result.groupby("Product")["Combined Additional Required"]
        .sum()
        .reset_index()
        .rename(columns={"Combined Additional Required": "Additional Required"})
    )
    comparison = (
        existing_resource.merge(requirement, on="Product", how="outer")
        .merge(hiring, on="Product", how="outer")
        .fillna(0)
    )
    comparison["Gap / Surplus"] = (
        comparison["Forecast Required SE"] - comparison["Existing 2026 SE"]
    )
    comparison["Existing 2026 SE"] = comparison["Existing 2026 SE"].round(1)
    comparison["Forecast Required SE"] = comparison["Forecast Required SE"].round(1)
    comparison["Gap / Surplus"] = comparison["Gap / Surplus"].round(1)
    comparison["Additional Required"] = comparison["Additional Required"].astype(int)
    total_row = pd.DataFrame(
        {
            "Product": ["Total"],
            "Existing 2026 SE": [comparison["Existing 2026 SE"].sum()],
            "Forecast Required SE": [comparison["Forecast Required SE"].sum()],
            "Additional Required": [comparison["Additional Required"].sum()],
            "Gap / Surplus": [comparison["Gap / Surplus"].sum()],
        }
    )
    return pd.concat([comparison, total_row], ignore_index=True)


def safe_read_csv(uploaded_file):
    raw_bytes = uploaded_file.getvalue()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin1")

    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        while line.endswith(","):
            line = line[:-1]
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)
    df = pd.read_csv(StringIO(cleaned_text), engine="python")
    df.columns = df.columns.str.strip()
    unnamed_cols = [col for col in df.columns if str(col).startswith("Unnamed")]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    return df


def validate_input_data(df):
    required_columns = [
        "Region",
        "Product",
        "Current_SE",
        "Breakdown_WO",
        "Breakdown_Hrs",
        "PM_WO",
        "PM_Hrs",
        "Startup_WO",
        "Startup_Hrs",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}")
        st.stop()

    df = df.copy()
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Product"] = df["Product"].astype(str).str.strip()
    df["Product"] = df["Product"].replace(PRODUCT_ALIASES)

    invalid_regions = sorted(set(df["Region"].unique()) - set(REGIONS))
    invalid_products = sorted(set(df["Product"].unique()) - set(PRODUCTS))
    if invalid_regions:
        st.error(f"Invalid regions found in uploaded file: {invalid_regions}")
        st.stop()
    if invalid_products:
        st.error(f"Invalid products found in uploaded file: {invalid_products}")
        st.stop()

    numeric_columns = [
        "Current_SE",
        "Breakdown_WO",
        "Breakdown_Hrs",
        "PM_WO",
        "PM_Hrs",
        "Startup_WO",
        "Startup_Hrs",
    ]
    if "Year" in df.columns:
        numeric_columns.append("Year")

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[numeric_columns].isnull().any().any():
        st.error("Some numeric columns contain blank or invalid numeric values.")
        st.stop()
    return df


def show_bar_chart_with_values(data, x_col, y_col, title, color_col=None):
    if color_col is None:
        color_col = x_col
    fig = px.bar(
        data,
        x=x_col,
        y=y_col,
        color=color_col,
        text=y_col,
        title=title,
    )
    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        cliponaxis=False,
    )
    fig.update_layout(
        height=430,
        title_x=0.05,
        showlegend=False,
        margin=dict(l=40, r=30, t=70, b=90),
        xaxis_title="",
        yaxis_title="Engineers",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(fixedrange=True, tickangle=-20)
    fig.update_yaxes(fixedrange=True, rangemode="tozero")
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False},
    )


init_state()

st.sidebar.header("Planning Assumptions")
st.sidebar.caption(
    "Edit one region table with 2027, 2028, and 2029 BAU/DC growth columns. "
    "2028 baseline uses 2027 final engineers. 2029 baseline uses 2028 final engineers."
)

with st.sidebar.form("planning_assumptions_form"):
    st.subheader("Region and Product Growth by Forecast Year")
    edited_growth_dfs = {}

    for region in REGIONS:
        show_region_header(region)
        edited_growth_dfs[region] = st.data_editor(
            growth_region_to_df(st.session_state.growth_parameters, region),
            hide_index=True,
            use_container_width=True,
            disabled=["Product"],
            height=245,
            column_config={
                "Product": st.column_config.TextColumn("Product", width=115),
           
