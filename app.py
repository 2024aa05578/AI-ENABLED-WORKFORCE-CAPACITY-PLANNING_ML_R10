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

APP_SCHEMA_VERSION = "v20_headcount_based_forecast"
REGIONS = ["North", "West", "South", "East"]
PRODUCTS = ["UPS", "Cooling", "Power Products", "Power System", "Industrial Automation"]
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
        "UPS": {"BAU": 20, "DC": 10},
        "Cooling": {"BAU": 20, "DC": 10},
        "Power Products": {"BAU": 15, "DC": 5},
        "Power System": {"BAU": 15, "DC": 5},
        "Industrial Automation": {"BAU": 15, "DC": 5},
    },
    "West": {
        "UPS": {"BAU": 30, "DC": 20},
        "Cooling": {"BAU": 30, "DC": 20},
        "Power Products": {"BAU": 20, "DC": 10},
        "Power System": {"BAU": 20, "DC": 10},
        "Industrial Automation": {"BAU": 20, "DC": 10},
    },
    "South": {
        "UPS": {"BAU": 22, "DC": 10},
        "Cooling": {"BAU": 22, "DC": 10},
        "Power Products": {"BAU": 20, "DC": 5},
        "Power System": {"BAU": 20, "DC": 5},
        "Industrial Automation": {"BAU": 20, "DC": 5},
    },
    "East": {
        "UPS": {"BAU": 15, "DC": 5},
        "Cooling": {"BAU": 15, "DC": 5},
        "Power Products": {"BAU": 15, "DC": 5},
        "Power System": {"BAU": 15, "DC": 5},
        "Industrial Automation": {"BAU": 15, "DC": 5},
    },
}

DEFAULT_GROWTH_PARAMETERS = {year: copy.deepcopy(BASE_GROWTH_BY_REGION) for year in FORECAST_YEARS}
DEFAULT_ATTRITION = {year: {product: 8 for product in PRODUCTS} for year in FORECAST_YEARS}

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
    .highlight {font-weight: 800; color: #1f5eff;}
    .warning {font-weight: 800; color: #d97706;}
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


def to_int(value):
    return int(round(safe_float(value, 0)))


def build_yearwise_dimension_table(result_source, dimension_column):
    grouped = result_source.groupby([dimension_column, "Forecast Year"], as_index=False).agg({
        "Combined Required Engineers": "sum",
        "Combined Additional Required": "sum",
    })
    table_rows = []
    for dimension_value in sorted(grouped[dimension_column].dropna().unique().tolist()):
        row_data = {dimension_column: dimension_value}
        for forecast_year in FORECAST_YEARS:
            year_data = grouped[
                (grouped[dimension_column] == dimension_value)
                & (grouped["Forecast Year"].astype(int) == forecast_year)
            ]
            row_data[f"Required {forecast_year}"] = int(year_data["Combined Required Engineers"].sum()) if not year_data.empty else 0
            row_data[f"Hiring {forecast_year}"] = int(year_data["Combined Additional Required"].sum()) if not year_data.empty else 0
        table_rows.append(row_data)

    output_table = pd.DataFrame(table_rows)
    total_row = {dimension_column: "Total"}
    for forecast_year in FORECAST_YEARS:
        total_row[f"Required {forecast_year}"] = int(output_table[f"Required {forecast_year}"].sum())
        total_row[f"Hiring {forecast_year}"] = int(output_table[f"Hiring {forecast_year}"].sum())
    return pd.concat([output_table, pd.DataFrame([total_row])], ignore_index=True)


def style_vp_table(table, label_column):
    numeric_columns = [column for column in table.columns if column != label_column]
    required_columns = [column for column in numeric_columns if column.startswith("Required")]
    hiring_columns = [column for column in numeric_columns if column.startswith("Hiring")]

    def apply_table_colors(data):
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        for column in required_columns:
            styles[column] = "background-color:#eaf2ff;color:#174a7c;font-weight:700;"
        for column in hiring_columns:
            styles[column] = "background-color:#fff1df;color:#8a4a00;font-weight:700;"
        total_mask = data[label_column].astype(str).eq("Total")
        styles.loc[total_mask, :] = "background-color:#fff3cd;color:#252a34;font-weight:800;border-top:2px solid #d6a700;"
        return styles

    return (
        table.style
        .format({column: "{:,.0f}" for column in numeric_columns})
        .apply(apply_table_colors, axis=None)
        .set_table_styles([
            {"selector": "th", "props": [("background-color", "#dfeaff"), ("color", "#243447"), ("font-weight", "800"), ("border", "1px solid #cbd8ee"), ("text-align", "center")]},
            {"selector": "td", "props": [("border", "1px solid #e6eaf2"), ("font-size", "13px")]},
        ])
    )


def style_year_summary_table(table):
    label_column = "Forecast Year"
    blue_columns = [
        column for column in table.columns
        if column in [
            "Existing 2026 SE",
            "Baseline SE",
            "After Attrition SE",
            "BAU Required SE",
            "DC Addl. SE",
            "Forecast Required SE",
            "Final SE",
        ]
    ]
    orange_columns = [
        column for column in table.columns
        if column == "Additional Required SE"
    ]
    numeric_columns = [column for column in table.columns if column != label_column]

    def apply_summary_colors(data):
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        styles[label_column] = "background-color:#dfeaff;color:#243447;font-weight:800;text-align:center;"
        for column in blue_columns:
            styles[column] = "background-color:#eaf2ff;color:#174a7c;font-weight:700;"
        for column in orange_columns:
            styles[column] = "background-color:#fff1df;color:#8a4a00;font-weight:800;"
        return styles

    return (
        table.style
        .format({column: "{:,.0f}" for column in numeric_columns})
        .apply(apply_summary_colors, axis=None)
        .set_table_styles([
            {"selector": "th", "props": [("background-color", "#dfeaff"), ("color", "#243447"), ("font-weight", "800"), ("border", "1px solid #cbd8ee"), ("text-align", "center")]},
            {"selector": "td", "props": [("border", "1px solid #e6eaf2"), ("font-size", "13px"), ("text-align", "center")]},
        ])
    )


def show_year_grouped_chart(data, x_col, y_col, title):
    chart_data = data.copy()
    chart_data["Forecast Year"] = chart_data["Forecast Year"].astype(str)
    fig = px.bar(
        chart_data,
        x=x_col,
        y=y_col,
        color="Forecast Year",
        barmode="group",
        text=y_col,
        title=title,
        color_discrete_map={"2027": "#4F81BD", "2028": "#F5A623", "2029": "#70AD47"},
    )
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=450,
        title_x=0.05,
        margin=dict(l=40, r=30, t=70, b=90),
        xaxis_title="",
        yaxis_title="Engineers",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend_title_text="Forecast Year",
    )
    fig.update_xaxes(fixedrange=True, tickangle=-20)
    fig.update_yaxes(fixedrange=True, rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})


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
        <div class="region-card" style="background:{style['bg']}; border-left:7px solid {style['border']}; color:{style['text']};">
            {region} Growth
        </div>
        """,
        unsafe_allow_html=True,
    )


def growth_region_to_df(growth_parameters, region):
    rows = []
    for product in PRODUCTS:
        row = {"Product": PRODUCT_DISPLAY[product]}
        for year in FORECAST_YEARS:
            row[f"{year} BAU"] = int(growth_parameters[year][region][product]["BAU"])
            row[f"{year} DC"] = int(growth_parameters[year][region][product]["DC"])
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
                        "BAU": int(round(safe_float(row[f"{year} BAU"], 0))),
                        "DC": int(round(safe_float(row[f"{year} DC"], 0))),
                    }
    return growth_parameters


def attrition_to_df(attrition_parameters):
    rows = []
    for product in PRODUCTS:
        row = {"Product": PRODUCT_DISPLAY[product]}
        for year in FORECAST_YEARS:
            row[f"{year} Attr"] = int(round(safe_float(attrition_parameters[year].get(product, 8), 8)))
        rows.append(row)
    return pd.DataFrame(rows)


def attrition_df_to_dict(attrition_df):
    attrition_parameters = copy.deepcopy(DEFAULT_ATTRITION)
    for _, row in attrition_df.iterrows():
        product_label = str(row["Product"]).strip()
        product = PRODUCT_REVERSE_DISPLAY.get(product_label)
        if product in PRODUCTS:
            for year in FORECAST_YEARS:
                attrition_parameters[year][product] = int(round(safe_float(row[f"{year} Attr"], 0)))
    return attrition_parameters


def productivity_to_df():
    return pd.DataFrame(
        [{
            "Hrs/Day": int(round(safe_float(st.session_state.productive_hours, 7))),
            "Days/M": int(st.session_state.working_days),
            "Util %": int(round(safe_float(st.session_state.target_utilization, 90))),
        }]
    )


def productivity_df_to_values(productivity_df):
    row = productivity_df.iloc[0]
    return float(row["Hrs/Day"]), int(row["Days/M"]), float(row["Util %"])


def get_growth_value(growth_parameters, year, region, product, kind):
    try:
        return int(round(safe_float(growth_parameters[int(year)][region][product][kind], 0)))
    except Exception:
        return 0


def get_attrition_value(attrition_parameters, year, product):
    try:
        return int(round(safe_float(attrition_parameters[int(year)][product], 0)))
    except Exception:
        return 0


def calculate_workforce_headcount(df, growth_parameters, attrition_parameters):
    rows = []
    for _, row in df.iterrows():
        region = str(row["Region"]).strip()
        product = str(row["Product"]).strip()
        baseline_engineers = int(round(safe_float(row["Current_SE"], 0)))

        for forecast_year in FORECAST_YEARS:
            bau_growth_pct = get_growth_value(growth_parameters, forecast_year, region, product, "BAU")
            dc_growth_pct = get_growth_value(growth_parameters, forecast_year, region, product, "DC")
            attrition_pct = get_attrition_value(attrition_parameters, forecast_year, product)

            total_growth_pct = bau_growth_pct + dc_growth_pct
            multiplication_factor = 1 + (total_growth_pct / 100.0)

            opening_engineers = int(round(baseline_engineers))
            available_engineers = int(round(opening_engineers * (1 - attrition_pct / 100.0)))
            bau_required_engineers = int(round(opening_engineers * (1 + bau_growth_pct / 100.0)))
            dc_incremental_engineers = int(round(opening_engineers * (dc_growth_pct / 100.0)))
            combined_required_engineers = bau_required_engineers + dc_incremental_engineers
            additional_required = max(combined_required_engineers - available_engineers, 0)
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
                    "Baseline Engineers": int(opening_engineers),
                    "Opening Engineers": int(opening_engineers),
                    "Attrition %": int(attrition_pct),
                    "Available Engineers": int(available_engineers),
                    "BAU Growth %": int(bau_growth_pct),
                    "DC Growth %": int(dc_growth_pct),
                    "Total Growth %": int(total_growth_pct),
                    "Multiplication Factor": round(multiplication_factor, 2),
                    "BAU Required Engineers": int(bau_required_engineers),
                    "DC Incremental Engineers": int(dc_incremental_engineers),
                    "Combined Required Engineers": int(combined_required_engineers),
                    "Combined Additional Required": int(additional_required),
                    "Closing Engineers": int(final_engineers),
                    "Final Engineers": int(final_engineers),
                }
            )
            baseline_engineers = int(final_engineers)
    return pd.DataFrame(rows)


def add_total_row_and_column(matrix):
    matrix = matrix.copy()
    matrix["Total"] = matrix.sum(axis=1)
    total_row = pd.DataFrame(matrix.sum(axis=0)).T
    total_row.index = ["Total"]
    return pd.concat([matrix, total_row]).astype(int)


def build_bu_requirement_comparison(df, result):
    existing_resource = df.groupby("Product")["Current_SE"].sum().reset_index().rename(columns={"Current_SE": "Existing 2026 SE"})
    required = result.groupby("Product")["Combined Required Engineers"].sum().reset_index().rename(columns={"Combined Required Engineers": "Forecast Required SE"})
    hiring = result.groupby("Product")["Combined Additional Required"].sum().reset_index().rename(columns={"Combined Additional Required": "Additional Required"})
    comparison = existing_resource.merge(required, on="Product", how="outer").merge(hiring, on="Product", how="outer").fillna(0)
    comparison["Gap / Surplus"] = comparison["Forecast Required SE"] - comparison["Existing 2026 SE"]
    for col in ["Existing 2026 SE", "Forecast Required SE", "Additional Required", "Gap / Surplus"]:
        comparison[col] = comparison[col].round(0).astype(int)
    total_row = pd.DataFrame({
        "Product": ["Total"],
        "Existing 2026 SE": [int(comparison["Existing 2026 SE"].sum())],
        "Forecast Required SE": [int(comparison["Forecast Required SE"].sum())],
        "Additional Required": [int(comparison["Additional Required"].sum())],
        "Gap / Surplus": [int(comparison["Gap / Surplus"].sum())],
    })
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
    required_columns = ["Region", "Product", "Current_SE", "Breakdown_WO", "Breakdown_Hrs", "PM_WO", "PM_Hrs", "Startup_WO", "Startup_Hrs"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}")
        st.stop()

    df = df.copy()
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Product"] = df["Product"].astype(str).str.strip().replace(PRODUCT_ALIASES)

    invalid_regions = sorted(set(df["Region"].unique()) - set(REGIONS))
    invalid_products = sorted(set(df["Product"].unique()) - set(PRODUCTS))
    if invalid_regions:
        st.error(f"Invalid regions found in uploaded file: {invalid_regions}")
        st.stop()
    if invalid_products:
        st.error(f"Invalid products found in uploaded file: {invalid_products}")
        st.stop()

    numeric_columns = ["Current_SE", "Breakdown_WO", "Breakdown_Hrs", "PM_WO", "PM_Hrs", "Startup_WO", "Startup_Hrs"]
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
    fig = px.bar(data, x=x_col, y=y_col, color=color_col, text=y_col, title=title)
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
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
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})


def build_year_wise_snapshot(df, result_all_years):
    yearly = result_all_years.groupby("Forecast Year", as_index=False).agg({
        "Baseline Engineers": "sum",
        "Available Engineers": "sum",
        "BAU Required Engineers": "sum",
        "DC Incremental Engineers": "sum",
        "Combined Required Engineers": "sum",
        "Combined Additional Required": "sum",
        "Final Engineers": "sum",
    })
    yearly = yearly.rename(columns={
        "Baseline Engineers": "Baseline SE",
        "Available Engineers": "After Attrition SE",
        "BAU Required Engineers": "BAU Required SE",
        "DC Incremental Engineers": "DC Addl. SE",
        "Combined Required Engineers": "Forecast Required SE",
        "Combined Additional Required": "Additional Required SE",
        "Final Engineers": "Final SE",
    })
    yearly.insert(1, "Existing 2026 SE", int(round(df["Current_SE"].sum())))
    value_cols = [col for col in yearly.columns if col != "Forecast Year"]
    yearly[value_cols] = yearly[value_cols].round(0).astype(int)
    return yearly


def build_actionable_insights(result_all_years):
    yearly = build_year_wise_snapshot(pd.DataFrame({"Current_SE": [0]}), result_all_years).drop(columns=["Existing 2026 SE"])
    data = {int(row["Forecast Year"]): row for _, row in yearly.iterrows()}
    lines = []

    if 2027 in data and 2028 in data:
        req_delta_28 = int(data[2028]["Forecast Required SE"] - data[2027]["Forecast Required SE"])
        hire_delta_28 = int(data[2028]["Additional Required SE"] - data[2027]["Additional Required SE"])
        direction_28 = "increase" if hire_delta_28 > 0 else "reduction" if hire_delta_28 < 0 else "no change"
        lines.append(f"2028 action: plan for {abs(hire_delta_28)} SE {direction_28} in hiring demand versus 2027; forecast requirement changes by {req_delta_28:+d} SE.")

    if 2028 in data and 2029 in data:
        req_delta_29 = int(data[2029]["Forecast Required SE"] - data[2028]["Forecast Required SE"])
        hire_delta_29 = int(data[2029]["Additional Required SE"] - data[2028]["Additional Required SE"])
        direction_29 = "increase" if hire_delta_29 > 0 else "reduction" if hire_delta_29 < 0 else "no change"
        lines.append(f"2029 action: plan for {abs(hire_delta_29)} SE {direction_29} in hiring demand versus 2028; forecast requirement changes by {req_delta_29:+d} SE.")

    year_region = result_all_years.groupby(["Forecast Year", "Region"], as_index=False)["Combined Additional Required"].sum()
    if not year_region.empty:
        top_region = year_region.sort_values("Combined Additional Required", ascending=False).iloc[0]
        lines.append(f"Deployment focus: highest hiring load is {int(top_region['Combined Additional Required'])} SE in {top_region['Region']} during {int(top_region['Forecast Year'])}; prepare onboarding and deployment capacity for that region first.")

    year_product = result_all_years.groupby(["Forecast Year", "Product"], as_index=False)["Combined Additional Required"].sum()
    if not year_product.empty:
        top_product = year_product.sort_values("Combined Additional Required", ascending=False).iloc[0]
        lines.append(f"BU focus: highest hiring load is {int(top_product['Combined Additional Required'])} SE for {top_product['Product']} during {int(top_product['Forecast Year'])}; prioritize sourcing and training for that BU.")

    lines.append("Governance action: review the year-wise growth and attrition assumptions monthly, because 2028 and 2029 depend on the prior year final engineer base.")
    return lines


init_state()

st.sidebar.header("Planning Assumptions")
st.sidebar.caption("Headcount-based forecast. Attrition and BAU/DC growth are year-wise. 2028 baseline uses 2027 final engineers. 2029 baseline uses 2028 final engineers.")

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
                "2027 BAU": st.column_config.NumberColumn("2027 BAU %", min_value=0, max_value=100, step=1, format="%d", width=70),
                "2027 DC": st.column_config.NumberColumn("2027 DC %", min_value=0, max_value=100, step=1, format="%d", width=70),
                "2028 BAU": st.column_config.NumberColumn("2028 BAU %", min_value=0, max_value=100, step=1, format="%d", width=70),
                "2028 DC": st.column_config.NumberColumn("2028 DC %", min_value=0, max_value=100, step=1, format="%d", width=70),
                "2029 BAU": st.column_config.NumberColumn("2029 BAU %", min_value=0, max_value=100, step=1, format="%d", width=70),
                "2029 DC": st.column_config.NumberColumn("2029 DC %", min_value=0, max_value=100, step=1, format="%d", width=70),
            },
            key=f"growth_data_editor_{region.lower()}",
        )

    st.subheader("BU Wise Attrition by Forecast Year")
    edited_attrition_df = st.data_editor(
        attrition_to_df(st.session_state.attrition_parameters),
        hide_index=True,
        use_container_width=True,
        disabled=["Product"],
        height=210,
        column_config={
            "Product": st.column_config.TextColumn("Product", width=118),
            "2027 Attr": st.column_config.NumberColumn("2027 Attr %", min_value=0, max_value=30, step=1, format="%d", width=70),
            "2028 Attr": st.column_config.NumberColumn("2028 Attr %", min_value=0, max_value=30, step=1, format="%d", width=70),
            "2029 Attr": st.column_config.NumberColumn("2029 Attr %", min_value=0, max_value=30, step=1, format="%d", width=70),
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
            "Hrs/Day": st.column_config.NumberColumn("Hrs/Day", min_value=1, max_value=24, step=1, format="%d", width=64),
            "Days/M": st.column_config.NumberColumn("Days/M", min_value=1, max_value=31, step=1, format="%d", width=58),
            "Util %": st.column_config.NumberColumn("Util %", min_value=1, max_value=100, step=1, format="%d", width=58),
        },
        key="productivity_data_editor",
    )

    apply_assumptions = st.form_submit_button("Apply Assumptions")
    if apply_assumptions:
        st.session_state.growth_parameters = growth_region_dfs_to_dict(edited_growth_dfs)
        st.session_state.attrition_parameters = attrition_df_to_dict(edited_attrition_df)
        productive_hours, working_days, target_utilization = productivity_df_to_values(edited_productivity_df)
        st.session_state.productive_hours = productive_hours
        st.session_state.working_days = working_days
        st.session_state.target_utilization = target_utilization
        st.session_state.result_df = None
        st.session_state.needs_recalc = True
        st.sidebar.success("Assumptions applied. Dashboard will refresh.")

st.title("AI Enabled Workforce & Capacity Planning")
st.info("Upload workforce_input.csv, update year-wise assumptions, click Apply Assumptions, and review the rolling 2027, 2028 and 2029 headcount forecast.")

uploaded_file = st.file_uploader("Upload workforce_input.csv", type=["csv"])

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
        available_input_years = filtered_df["Year"].dropna().astype(int).sort_values().unique().tolist()
        selected_input_years = st.multiselect("Select Input Year", options=available_input_years, default=available_input_years)
        filtered_df = filtered_df[filtered_df["Year"].astype(int).isin(selected_input_years)]
    else:
        selected_input_years = ["All"]

with filter_col2:
    available_regions = [region for region in REGIONS if region in filtered_df["Region"].unique()]
    selected_regions = st.multiselect("Select Region", options=available_regions, default=available_regions)
    filtered_df = filtered_df[filtered_df["Region"].isin(selected_regions)]

if filtered_df.empty:
    st.warning("No data available for selected Input Year / Region filter.")
    st.stop()

df = filtered_df
filter_signature = (tuple(selected_input_years), tuple(selected_regions), int(len(df)))
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
    available_forecast_years = result_all_years["Forecast Year"].dropna().astype(int).sort_values().unique().tolist()
    selected_forecast_years = st.multiselect(
        "Select Forecast Year",
        options=available_forecast_years,
        default=[2027] if 2027 in available_forecast_years else available_forecast_years[:1],
    )
    if not selected_forecast_years:
        selected_forecast_years = [available_forecast_years[0]]

result = result_all_years[result_all_years["Forecast Year"].astype(int).isin(selected_forecast_years)].copy()
summary_year = max([int(year) for year in selected_forecast_years])
summary_result = result_all_years[result_all_years["Forecast Year"].astype(int) == summary_year].copy()

total_current = int(round(df["Current_SE"].sum()))
total_available = int(summary_result["Available Engineers"].sum())
total_bau_required = int(summary_result["BAU Required Engineers"].sum())
total_dc_required = int(summary_result["DC Incremental Engineers"].sum())
total_combined_required = int(summary_result["Combined Required Engineers"].sum())
total_combined_hiring = int(summary_result["Combined Additional Required"].sum())

st.markdown("### Year-wise Additional Hiring Requirement")
addl_by_year = result_all_years.groupby("Forecast Year")["Combined Additional Required"].sum().to_dict()
h1, h2, h3 = st.columns(3)
h1.metric("Additional Hiring 2027", int(addl_by_year.get(2027, 0)))
h2.metric("Additional Hiring 2028", int(addl_by_year.get(2028, 0)))
h3.metric("Additional Hiring 2029", int(addl_by_year.get(2029, 0)))

st.markdown("### Year-wise Forecast Clarity")
year_wise_snapshot = build_year_wise_snapshot(df, result_all_years)
st.dataframe(style_year_summary_table(year_wise_snapshot), use_container_width=True, hide_index=True, height=245)

st.markdown("### Product and Region Requirement by Year")
product_year_table = build_yearwise_dimension_table(result_all_years, "Product")
region_year_table = build_yearwise_dimension_table(result_all_years, "Region")
product_col, region_col = st.columns(2)
with product_col:
    st.markdown("#### Product Level Requirement")
    st.dataframe(style_vp_table(product_year_table, "Product"), use_container_width=True, hide_index=True, height=300)
with region_col:
    st.markdown("#### Region Level Requirement")
    st.dataframe(style_vp_table(region_year_table, "Region"), use_container_width=True, hide_index=True, height=300)

st.markdown("---")
st.subheader("Visual Dashboard - 2027, 2028 and 2029")

product_required_all = result_all_years.groupby(["Product", "Forecast Year"], as_index=False)["Combined Required Engineers"].sum()
region_required_all = result_all_years.groupby(["Region", "Forecast Year"], as_index=False)["Combined Required Engineers"].sum()
product_hiring_all = result_all_years.groupby(["Product", "Forecast Year"], as_index=False)["Combined Additional Required"].sum()
region_hiring_all = result_all_years.groupby(["Region", "Forecast Year"], as_index=False)["Combined Additional Required"].sum()

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    show_year_grouped_chart(product_required_all, "Product", "Combined Required Engineers", "Forecast Required SE by Product")
with chart_col2:
    show_year_grouped_chart(region_required_all, "Region", "Combined Required Engineers", "Forecast Required SE by Region")

chart_col3, chart_col4 = st.columns(2)
with chart_col3:
    show_year_grouped_chart(product_hiring_all, "Product", "Combined Additional Required", "Additional Hiring by Product")
with chart_col4:
    show_year_grouped_chart(region_hiring_all, "Region", "Combined Additional Required", "Additional Hiring by Region")

tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Executive Summary",
    "Input Data",
    "Full Results",
    "BU Requirement Comparison",
    "DC and Combined",
    "Yearly Forecast",
    "Download",
])

with tab0:
    st.subheader("Executive Summary")

    selected_input_year_text = ", ".join([str(year) for year in selected_input_years]) if selected_input_years else "All"
    selected_region_text = ", ".join(selected_regions) if selected_regions else "All"
    selected_forecast_year_text = ", ".join([str(year) for year in selected_forecast_years]) if selected_forecast_years else "All"

    executive_summary_table = build_year_wise_snapshot(df, result_all_years)[[
        "Forecast Year", "Baseline SE", "After Attrition SE",
        "Forecast Required SE", "Additional Required SE", "Final SE",
    ]]

    addl_by_year_exec = result_all_years.groupby("Forecast Year")["Combined Additional Required"].sum().to_dict()
    hiring_2027_exec = int(addl_by_year_exec.get(2027, 0))
    hiring_2028_exec = int(addl_by_year_exec.get(2028, 0))
    hiring_2029_exec = int(addl_by_year_exec.get(2029, 0))
    total_hiring_exec = hiring_2027_exec + hiring_2028_exec + hiring_2029_exec
    final_2029_exec = int(result_all_years.loc[result_all_years["Forecast Year"].astype(int) == 2029, "Final Engineers"].sum())
    forecast_required_2029_exec = int(result_all_years.loc[result_all_years["Forecast Year"].astype(int) == 2029, "Combined Required Engineers"].sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Current Base SE", total_current)
    c2.metric("Hiring 2027", hiring_2027_exec)
    c3.metric("Hiring 2028", hiring_2028_exec)
    c4.metric("Hiring 2029", hiring_2029_exec)
    c5.metric("Final SE 2029", final_2029_exec)
    c6.metric("Total Hiring", total_hiring_exec)

    st.markdown("### Three-Year Forecast Summary")
    st.dataframe(style_year_summary_table(executive_summary_table), use_container_width=True, hide_index=True, height=245)

    exec_action_lines = build_actionable_insights(result_all_years)
    st.markdown(
        f"""
        <div class="leadership-box">
            <b>Executive Summary and Important Action Points</b>
            <ul>
                <li>Current installed base is <span class="highlight">{total_current} SE</span>. Projected final workforce by 2029 is <span class="warning">{final_2029_exec} SE</span>.</li>
                <li>Forecast requirement by 2029 is <span class="warning">{forecast_required_2029_exec} SE</span>. Total hiring requirement across 2027 to 2029 is <span class="warning">{total_hiring_exec} SE</span>.</li>
                <li>Year-wise hiring ask is <span class="highlight">{hiring_2027_exec} SE in 2027</span>, <span class="highlight">{hiring_2028_exec} SE in 2028</span>, and <span class="highlight">{hiring_2029_exec} SE in 2029</span>.</li>
                <li>Input filter: <span class="highlight">Year {selected_input_year_text}</span>, Region <span class="highlight">{selected_region_text}</span>. Forecast years selected: <span class="highlight">{selected_forecast_year_text}</span>.</li>
                <li>Planning logic: 2027 baseline uses uploaded Current_SE, 2028 baseline uses 2027 final engineers, and 2029 baseline uses 2028 final engineers.</li>
                {''.join([f'<li>{line}</li>' for line in exec_action_lines])}
                <li><span class="warning">Decision required:</span> approve year-wise hiring phasing for 2027, 2028, and 2029.</li>
                <li><span class="warning">Recruitment action:</span> confirm whether hiring should be front-loaded in the highest-demand BU and region.</li>
                <li><span class="warning">Execution focus:</span> align sourcing, onboarding, training, deployment readiness, and regional capacity before the hiring peak year.</li>
                <li><span class="warning">Governance cadence:</span> review BAU growth, DC growth, and attrition assumptions monthly because each forecast year compounds from the previous year final SE base.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

with tab1:
    st.subheader("Uploaded Input Data")
    st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("Workforce Planning Results")
    st.dataframe(result, use_container_width=True)

with tab3:
    st.subheader("BU Requirement Comparison")
    st.info(f"This table compares existing 2026 resources with selected forecast requirement for {summary_year}.")
    st.dataframe(build_bu_requirement_comparison(df=df, result=summary_result), use_container_width=True)

with tab4:
    st.subheader("DC Addition Requirement Table")
    dc_table = summary_result.pivot_table(values="DC Incremental Engineers", index="Product", columns="Region", fill_value=0, aggfunc="sum")
    st.dataframe(add_total_row_and_column(dc_table), use_container_width=True)

    st.subheader("Combined BAU + DC Requirement Table")
    combined_table = summary_result.pivot_table(values="Combined Required Engineers", index="Product", columns="Region", fill_value=0, aggfunc="sum")
    st.dataframe(add_total_row_and_column(combined_table), use_container_width=True)

    st.subheader("Combined Hiring Requirement Table")
    hiring_table = summary_result.pivot_table(values="Combined Additional Required", index="Product", columns="Region", fill_value=0, aggfunc="sum")
    st.dataframe(add_total_row_and_column(hiring_table), use_container_width=True)

with tab5:
    st.subheader("Yearly Forecast Summary")
    yearly_summary = build_year_wise_snapshot(df, result_all_years)
    st.dataframe(style_year_summary_table(yearly_summary), use_container_width=True, hide_index=True, height=245)

    st.markdown("---")
    st.subheader("2027 and 2028 Multiplication Factor Table")
    factor_table = result_all_years[result_all_years["Forecast Year"].astype(int).isin([2027, 2028])][[
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
    ]].copy()
    factor_table = factor_table.sort_values(["Forecast Year", "Region", "Product"])
    st.dataframe(factor_table, use_container_width=True)
    st.caption("Multiplication Factor = 1 + ((BAU Growth % + DC Growth %) / 100). All headcount values are shown as integers.")

    st.markdown("---")
    for forecast_year in selected_forecast_years:
        st.markdown(f"### {forecast_year} Detailed Forecast")
        year_result = result_all_years[result_all_years["Forecast Year"].astype(int) == int(forecast_year)].copy()
        st.dataframe(year_result, use_container_width=True)

with tab6:
    st.subheader("Download Output")
    csv_output = result.to_csv(index=False).encode("utf-8")
    st.download_button(label="Download Workforce Planning Output", data=csv_output, file_name="workforce_planning_output_v17.csv", mime="text/csv")
