import copy
import math
from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="AI Enabled Workforce & Capacity Planning",
    page_icon="🚀",
    layout="wide",
)

APP_SCHEMA_VERSION = "v17_headcount_based_forecast_hcfix2"

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

PRODUCT_REVERSE_DISPLAY = {
    value: key
    for key, value in PRODUCT_DISPLAY.items()
}

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

DEFAULT_ATTRITION = {
    product: 8.0
    for product in PRODUCTS
}

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


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


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
        st.session_state.uploaded_file_id = None
        st.session_state.last_filter_signature = None
        st.session_state.needs_recalc = False


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
        row = {
            "Product": PRODUCT_DISPLAY[product],
        }

        for year in FORECAST_YEARS:
            row[f"{year} BAU"] = float(
                growth_parameters[year][region][product]["BAU"]
            )
            row[f"{year} DC"] = float(
                growth_parameters[year][region][product]["DC"]
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
                for year in FORECAST_YEARS:
                    growth_parameters[year][region][product] = {
                        "BAU": float(row[f"{year} BAU"]),
                        "DC": float(row[f"{year} DC"]),
                    }

    return growth_parameters


def attrition_dict_to_df(attrition_parameters):
    return pd.DataFrame(
        [
            {
                "Product": PRODUCT_DISPLAY[product],
                "Attr %": float(attrition_parameters.get(product, 8.0)),
            }
            for product in PRODUCTS
        ]
    )


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

    productive_hours = float(row["Hrs/Day"])
    working_days = int(row["Days/M"])
    target_utilization = float(row["Util %"])

    return productive_hours, working_days, target_utilization


def get_growth_value(growth_parameters, year, region, product, kind):
    try:
        return float(growth_parameters[int(year)][region][product][kind])
    except Exception:
        return 0.0


def calculate_workforce_headcount(df, growth_parameters, attrition_parameters):
    rows = []

    for _, row in df.iterrows():
        region = str(row["Region"]).strip()
        product = str(row["Product"]).strip()
        baseline_engineers = safe_float(row["Current_SE"], 0.0)

        for forecast_year in FORECAST_YEARS:
            bau_growth_pct = get_growth_value(
                growth_parameters,
                forecast_year,
                region,
                product,
                "BAU",
            )

            dc_growth_pct = get_growth_value(
                growth_parameters,
                forecast_year,
                region,
                product,
                "DC",
            )

            attrition_pct = safe_float(
                attrition_parameters.get(product, 0.0),
                0.0,
            )

            total_growth_pct = bau_growth_pct + dc_growth_pct
            multiplication_factor = 1 + (total_growth_pct / 100.0)

            opening_engineers = baseline_engineers
            available_engineers = opening_engineers * (1 - attrition_pct / 100.0)

            bau_required_engineers = opening_engineers * (
                1 + bau_growth_pct / 100.0
            )

            dc_incremental_engineers = opening_engineers * (
                dc_growth_pct / 100.0
            )

            combined_required_engineers = opening_engineers * multiplication_factor

            additional_required = max(
                math.ceil(combined_required_engineers - available_engineers),
                0,
            )

            final_engineers = available_engineers + additional_required

            if int(forecast_year) == 2027:
                calculation_basis = "Headcount baseline from uploaded Current_SE"
            else:
                calculation_basis = "Headcount baseline from previous year Final Engineers"

            rows.append(
                {
                    "Forecast Year": int(forecast_year),
                    "Region": region,
                    "Product": product,
                    "Calculation Basis": calculation_basis,
                    "Baseline Engineers": round(opening_engineers, 2),
                    "Opening Engineers": round(opening_engineers, 2),
                    "Attrition %": round(attrition_pct, 2),
                    "Available Engineers": round(available_engineers, 2),
                    "BAU Growth %": round(bau_growth_pct, 2),
                    "DC Growth %": round(dc_growth_pct, 2),
                    "Total Growth %": round(total_growth_pct, 2),
                    "Multiplication Factor": round(multiplication_factor, 4),
                    "BAU Required Engineers": round(bau_required_engineers, 2),
                    "DC Incremental Engineers": round(dc_incremental_engineers, 2),
                    "Combined Required Engineers": round(combined_required_engineers, 2),
                    "Combined Additional Required": int(additional_required),
                    "Closing Engineers": round(final_engineers, 2),
                    "Final Engineers": round(final_engineers, 2),
                }
            )

            baseline_engineers = final_engineers

    return pd.DataFrame(rows)


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

    required = (
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
        existing_resource
        .merge(required, on="Product", how="outer")
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

    df = pd.read_csv(
        StringIO(cleaned_text),
        engine="python",
    )

    df.columns = df.columns.str.strip()

    unnamed_cols = [
        col
        for col in df.columns
        if str(col).startswith("Unnamed")
    ]

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

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

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
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

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

    fig.update_xaxes(
        fixedrange=True,
        tickangle=-20,
    )

    fig.update_yaxes(
        fixedrange=True,
        rangemode="tozero",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "scrollZoom": False,
        },
    )


init_state()

st.sidebar.header("Planning Assumptions")
st.sidebar.caption(
    "Headcount-based forecast. "
    "2028 baseline uses 2027 final engineers. "
    "2029 baseline uses 2028 final engineers."
)

with st.sidebar.form("planning_assumptions_form"):
    st.subheader("Region and Product Growth by Forecast Year")

    edited_growth_dfs = {}

    for region in REGIONS:
        show_region_header(region)

        edited_growth_dfs[region] = st.data_editor(
            growth_region_to_df(
                st.session_state.growth_parameters,
                region,
            ),
            hide_index=True,
            use_container_width=True,
            disabled=["Product"],
            height=245,
            column_config={
                "Product": st.column_config.TextColumn(
                    "Product",
                    width=115,
                ),
                "2027 BAU": st.column_config.NumberColumn(
                    "2027 BAU %",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    width=70,
                ),
                "2027 DC": st.column_config.NumberColumn(
                    "2027 DC %",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    width=70,
                ),
                "2028 BAU": st.column_config.NumberColumn(
                    "2028 BAU %",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    width=70,
                ),
                "2028 DC": st.column_config.NumberColumn(
                    "2028 DC %",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    width=70,
                ),
                "2029 BAU": st.column_config.NumberColumn(
                    "2029 BAU %",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    width=70,
                ),
                "2029 DC": st.column_config.NumberColumn(
                    "2029 DC %",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    width=70,
                ),
            },
            key=f"growth_data_editor_{region.lower()}",
        )

    st.subheader("BU Wise Attrition")

    edited_attrition_df = st.data_editor(
        attrition_dict_to_df(st.session_state.attrition_parameters),
        hide_index=True,
        use_container_width=True,
        disabled=["Product"],
        height=210,
        column_config={
            "Product": st.column_config.TextColumn(
                "Product",
                width=118,
            ),
            "Attr %": st.column_config.NumberColumn(
                "Attr %",
                min_value=0.0,
                max_value=30.0,
                step=0.5,
                width=58,
            ),
        },
        key="attrition_data_editor",
    )

    st.subheader("Workforce Productivity")

    edited_productivity_df = st.data_editor(
        productivity_to_df(),
        hide_index=True,
        use_container_width=True,
        height=85,
        column_config={
            "Hrs/Day": st.column_config.NumberColumn(
                "Hrs/Day",
                min_value=1.0,
                max_value=24.0,
                step=0.5,
                width=64,
            ),
            "Days/M": st.column_config.NumberColumn(
                "Days/M",
                min_value=1,
                max_value=31,
                step=1,
                width=58,
            ),
            "Util %": st.column_config.NumberColumn(
                "Util %",
                min_value=1.0,
                max_value=100.0,
                step=1.0,
                width=58,
            ),
        },
        key="productivity_data_editor",
    )

    apply_assumptions = st.form_submit_button("Apply Assumptions")

    if apply_assumptions:
        st.session_state.growth_parameters = growth_region_dfs_to_dict(
            edited_growth_dfs
        )

        st.session_state.attrition_parameters = attrition_df_to_dict(
            edited_attrition_df
        )

        productive_hours, working_days, target_utilization = productivity_df_to_values(
            edited_productivity_df
        )

        st.session_state.productive_hours = productive_hours
        st.session_state.working_days = working_days
        st.session_state.target_utilization = target_utilization
        st.session_state.result_df = None
        st.session_state.needs_recalc = True

        st.sidebar.success("Assumptions applied. Dashboard will refresh.")


st.title("AI Enabled Workforce & Capacity Planning")

st.info(
    "Upload workforce_input.csv, update assumptions, click Apply Assumptions, "
    "and review the rolling 2027, 2028 and 2029 headcount forecast."
)

uploaded_file = st.file_uploader(
    "Upload workforce_input.csv",
    type=["csv"],
)

if uploaded_file is not None:
    current_file_id = f"{uploaded_file.name}_{len(uploaded_file.getvalue())}"

    if current_file_id != st.session_state.uploaded_file_id:
        try:
            raw_df = safe_read_csv(uploaded_file)
            st.session_state.input_df = validate_input_data(raw_df)
            st.session_state.uploaded_file_id = current_file_id
            st.session_state.result_df = None
            st.session_state.needs_recalc = True
            st.success("CSV uploaded successfully.")

        except Exception as error:
            st.error("CSV upload failed. Please check file format.")
            st.exception(error)
            st.stop()

if st.session_state.input_df is None:
    st.warning("Please upload workforce_input.csv to start workforce planning.")
    st.stop()

original_df = st.session_state.input_df

st.markdown("### Dashboard Filters")

filter_col1, filter_col2, filter_col3 = st.columns(3)

filtered_df = original_df.copy()

with filter_col1:
    if "Year" in filtered_df.columns:
        available_input_years = (
            filtered_df["Year"]
            .dropna()
            .astype(int)
            .sort_values()
            .unique()
            .tolist()
        )

        selected_input_years = st.multiselect(
            "Select Input Year",
            options=available_input_years,
            default=available_input_years,
        )

        filtered_df = filtered_df[
            filtered_df["Year"].astype(int).isin(selected_input_years)
        ]

    else:
        selected_input_years = ["All"]

with filter_col2:
    available_regions = [
        region
        for region in REGIONS
        if region in filtered_df["Region"].unique()
    ]

    selected_regions = st.multiselect(
        "Select Region",
        options=available_regions,
        default=available_regions,
    )

    filtered_df = filtered_df[
        filtered_df["Region"].isin(selected_regions)
    ]

if filtered_df.empty:
    st.warning("No data available for selected Input Year / Region filter.")
    st.stop()

df = filtered_df

filter_signature = (
    tuple(selected_input_years),
    tuple(selected_regions),
    int(len(df)),
)

if st.session_state.last_filter_signature != filter_signature:
    st.session_state.result_df = None
    st.session_state.needs_recalc = True
    st.session_state.last_filter_signature = filter_signature

if st.session_state.needs_recalc or st.session_state.result_df is None:
    result_all_years = calculate_workforce_headcount(
        df=df,
        growth_parameters=st.session_state.growth_parameters,
        attrition_parameters=st.session_state.attrition_parameters,
    )

    st.session_state.result_df = result_all_years
    st.session_state.needs_recalc = False

else:
    result_all_years = st.session_state.result_df

with filter_col3:
    available_forecast_years = (
        result_all_years["Forecast Year"]
        .dropna()
        .astype(int)
        .sort_values()
        .unique()
        .tolist()
    )

    selected_forecast_years = st.multiselect(
        "Select Forecast Year",
        options=available_forecast_years,
        default=[2027] if 2027 in available_forecast_years else available_forecast_years[:1],
    )

    if not selected_forecast_years:
        selected_forecast_years = [available_forecast_years[0]]

result = result_all_years[
    result_all_years["Forecast Year"].astype(int).isin(selected_forecast_years)
].copy()

summary_year = max(
    [
        int(year)
        for year in selected_forecast_years
    ]
)

summary_result = result_all_years[
    result_all_years["Forecast Year"].astype(int) == summary_year
].copy()

st.subheader("Dashboard Summary")

total_current = df["Current_SE"].sum()
total_available = round(summary_result["Available Engineers"].sum(), 1)
total_bau_required = round(summary_result["BAU Required Engineers"].sum(), 1)
total_dc_required = round(summary_result["DC Incremental Engineers"].sum(), 1)
total_combined_required = round(summary_result["Combined Required Engineers"].sum(), 1)
total_combined_hiring = int(summary_result["Combined Additional Required"].sum())

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

kpi1.metric("Existing 2026 SE", total_current)
kpi2.metric(f"After Attrition {summary_year}", total_available)
kpi3.metric(f"BAU Required SE {summary_year}", total_bau_required)
kpi4.metric(f"DC Addl. SE {summary_year}", total_dc_required)
kpi5.metric(f"Forecast Required SE {summary_year}", total_combined_required)
kpi6.metric(f"Additional Required {summary_year}", total_combined_hiring)

st.markdown("---")
st.subheader("Visual Dashboard")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    product_required = (
        summary_result.groupby("Product")["Combined Required Engineers"]
        .sum()
        .reset_index()
    )

    show_bar_chart_with_values(
        product_required,
        "Product",
        "Combined Required Engineers",
        f"Forecast Required SE by Product - {summary_year}",
        "Product",
    )

with chart_col2:
    region_required = (
        summary_result.groupby("Region")["Combined Required Engineers"]
        .sum()
        .reset_index()
    )

    show_bar_chart_with_values(
        region_required,
        "Region",
        "Combined Required Engineers",
        f"Forecast Required SE by Region - {summary_year}",
        "Region",
    )

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    product_hiring = (
        summary_result.groupby("Product")["Combined Additional Required"]
        .sum()
        .reset_index()
    )

    show_bar_chart_with_values(
        product_hiring,
        "Product",
        "Combined Additional Required",
        f"Additional Requirement by Product - {summary_year}",
        "Product",
    )

with chart_col4:
    region_hiring = (
        summary_result.groupby("Region")["Combined Additional Required"]
        .sum()
        .reset_index()
    )

    show_bar_chart_with_values(
        region_hiring,
        "Region",
        "Combined Additional Required",
        f"Additional Requirement by Region - {summary_year}",
        "Region",
    )

tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Executive Summary",
        "Input Data",
        "Full Results",
        "BU Requirement Comparison",
        "DC and Combined",
        "Yearly Forecast",
        "Download",
    ]
)

with tab0:
    st.subheader("Executive Summary - Leadership View")

    selected_input_year_text = (
        ", ".join([str(year) for year in selected_input_years])
        if selected_input_years
        else "All"
    )

    selected_region_text = (
        ", ".join(selected_regions)
        if selected_regions
        else "All"
    )

    selected_forecast_year_text = (
        ", ".join([str(year) for year in selected_forecast_years])
        if selected_forecast_years
        else "All"
    )

    s1, s2, s3 = st.columns(3)

    s1.metric("Existing 2026 SE", round(total_current, 1))
    s2.metric(f"Forecast Required SE {summary_year}", total_combined_required)
    s3.metric(f"Additional Required {summary_year}", total_combined_hiring)

    st.markdown(
        f"""
        <div class="leadership-box">
            <b>Leadership Readout</b>
            <ul>
                <li>Input filter: <span class="highlight">Year {selected_input_year_text}</span>, Region <span class="highlight">{selected_region_text}</span>.</li>
                <li>Forecast years selected: <span class="highlight">{selected_forecast_year_text}</span>.</li>
                <li>Dashboard summary shown for: <span class="highlight">{summary_year}</span>.</li>
                <li>Current installed base: <span class="highlight">{round(total_current, 1)} SE</span>.</li>
                <li>Available engineers after attrition: <span class="highlight">{total_available} SE</span>.</li>
                <li>BAU required engineers: <span class="highlight">{total_bau_required} SE</span>.</li>
                <li>DC incremental engineers: <span class="highlight">{total_dc_required} SE</span>.</li>
                <li>Total forecast requirement: <span class="warning">{total_combined_required} SE</span>.</li>
                <li>Total additional hiring requirement: <span class="warning">{total_combined_hiring} SE</span>.</li>
                <li>2027 baseline uses uploaded Current_SE. 2028 baseline uses 2027 final engineers. 2029 baseline uses 2028 final engineers.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    exec_col1, exec_col2 = st.columns(2)

    with exec_col1:
        st.markdown("### Product Level Requirement")

        product_summary = (
            summary_result.groupby("Product")[
                [
                    "Combined Required Engineers",
                    "Combined Additional Required",
                ]
            ]
            .sum()
            .round(1)
            .reset_index()
        )

        st.dataframe(
            product_summary,
            use_container_width=True,
        )

    with exec_col2:
        st.markdown("### Region Level Requirement")

        region_summary = (
            summary_result.groupby("Region")[
                [
                    "Combined Required Engineers",
                    "Combined Additional Required",
                ]
            ]
            .sum()
            .round(1)
            .reset_index()
        )

        st.dataframe(
            region_summary,
            use_container_width=True,
        )

with tab1:
    st.subheader("Uploaded Input Data")

    st.dataframe(
        df,
        use_container_width=True,
    )

with tab2:
    st.subheader("Workforce Planning Results")

    st.dataframe(
        result,
        use_container_width=True,
    )

with tab3:
    st.subheader("BU Requirement Comparison")

    st.info(
        f"This table compares existing 2026 resources with selected forecast requirement for {summary_year}."
    )

    st.dataframe(
        build_bu_requirement_comparison(
            df=df,
            result=summary_result,
        ),
        use_container_width=True,
    )

with tab4:
    st.subheader("DC Addition Requirement Table")

    dc_table = summary_result.pivot_table(
        values="DC Incremental Engineers",
        index="Product",
        columns="Region",
        fill_value=0,
        aggfunc="sum",
    )

    st.dataframe(
        add_total_row_and_column(dc_table).round(1),
        use_container_width=True,
    )

    st.subheader("Combined BAU + DC Requirement Table")

    combined_table = summary_result.pivot_table(
        values="Combined Required Engineers",
        index="Product",
        columns="Region",
        fill_value=0,
        aggfunc="sum",
    )

    st.dataframe(
        add_total_row_and_column(combined_table).round(1),
        use_container_width=True,
    )

    st.subheader("Combined Hiring Requirement Table")

    hiring_table = summary_result.pivot_table(
        values="Combined Additional Required",
        index="Product",
        columns="Region",
        fill_value=0,
        aggfunc="sum",
    )

    st.dataframe(
        add_total_row_and_column(hiring_table).round(1),
        use_container_width=True,
    )

with tab5:
    st.subheader("Yearly Forecast Summary")

    yearly_summary = (
        result_all_years.groupby("Forecast Year", as_index=False)
        .agg(
            {
                "Baseline Engineers": "sum",
                "Available Engineers": "sum",
                "BAU Required Engineers": "sum",
                "DC Incremental Engineers": "sum",
                "Combined Required Engineers": "sum",
                "Combined Additional Required": "sum",
                "Final Engineers": "sum",
            }
        )
    )

    round_cols = [
        "Baseline Engineers",
        "Available Engineers",
        "BAU Required Engineers",
        "DC Incremental Engineers",
        "Combined Required Engineers",
        "Final Engineers",
    ]

    yearly_summary[round_cols] = yearly_summary[round_cols].round(1)
    yearly_summary["Combined Additional Required"] = yearly_summary[
        "Combined Additional Required"
    ].astype(int)

    st.dataframe(
        yearly_summary,
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("2027 and 2028 Multiplication Factor Table")

    factor_table = result_all_years[
        result_all_years["Forecast Year"].astype(int).isin([2027, 2028])
    ][
        [
            "Forecast Year",
            "Region",
            "Product",
            "Calculation Basis",
            "Baseline Engineers",
            "BAU Growth %",
            "DC Growth %",
            "Total Growth %",
            "Multiplication Factor",
            "Combined Required Engineers",
            "Attrition %",
            "Available Engineers",
            "Combined Additional Required",
            "Final Engineers",
        ]
    ].copy()

    factor_table = factor_table.sort_values(
        [
            "Forecast Year",
            "Region",
            "Product",
        ]
    )

    st.dataframe(
        factor_table,
        use_container_width=True,
    )

    st.caption(
        "Multiplication Factor = 1 + ((BAU Growth % + DC Growth %) / 100)."
    )

    st.markdown("---")

    for forecast_year in selected_forecast_years:
        st.markdown(f"### {forecast_year} Detailed Forecast")

        year_result = result_all_years[
            result_all_years["Forecast Year"].astype(int) == int(forecast_year)
        ].copy()

        st.dataframe(
            year_result,
            use_container_width=True,
        )

with tab6:
    st.subheader("Download Output")

    csv_output = result.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Workforce Planning Output",
        data=csv_output,
        file_name="workforce_planning_output_v17.csv",
        mime="text/csv",
    )
