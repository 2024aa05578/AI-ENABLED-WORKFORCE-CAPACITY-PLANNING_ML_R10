import math
import pandas as pd

FORECAST_YEARS = [2027, 2028, 2029]


def _safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _growth_value(growth_parameters, year, region, product, kind):
    try:
        return float(growth_parameters[int(year)][region][product][kind])
    except Exception:
        return 0.0


def calculate_workforce(
    df,
    growth_parameters,
    attrition_parameters,
    productive_hours,
    working_days,
    target_utilization,
):
    results = []

    productive_hours = _safe_float(productive_hours, 7.0)
    working_days = _safe_float(working_days, 20.0)
    target_utilization = _safe_float(target_utilization, 90.0)

    monthly_capacity_per_engineer = productive_hours * working_days * (target_utilization / 100.0)
    if monthly_capacity_per_engineer <= 0:
        raise ValueError("Monthly capacity per engineer must be greater than zero.")

    for _, row in df.iterrows():
        region = str(row["Region"]).strip()
        product = str(row["Product"]).strip()
        current_se = _safe_float(row["Current_SE"], 0.0)

        breakdown_workload = _safe_float(row["Breakdown_WO"], 0.0) * _safe_float(row["Breakdown_Hrs"], 0.0)
        pm_workload = _safe_float(row["PM_WO"], 0.0) * _safe_float(row["PM_Hrs"], 0.0)
        startup_workload = _safe_float(row["Startup_WO"], 0.0) * _safe_float(row["Startup_Hrs"], 0.0)
        base_workload_hours = breakdown_workload + pm_workload + startup_workload

        opening_engineers = current_se
        opening_workload_hours = base_workload_hours

        for forecast_year in FORECAST_YEARS:
            bau_growth_pct = _growth_value(growth_parameters, forecast_year, region, product, "BAU")
            dc_growth_pct = _growth_value(growth_parameters, forecast_year, region, product, "DC")
            attrition_pct = _safe_float(attrition_parameters.get(product, 0.0), 0.0)

            available_engineers = opening_engineers * (1 - attrition_pct / 100.0)
            bau_required_hours = opening_workload_hours * (1 + bau_growth_pct / 100.0)
            dc_incremental_hours = opening_workload_hours * (dc_growth_pct / 100.0)
            combined_required_hours = bau_required_hours + dc_incremental_hours

            bau_required_engineers = bau_required_hours / monthly_capacity_per_engineer
            dc_incremental_engineers = dc_incremental_hours / monthly_capacity_per_engineer
            combined_required_engineers = combined_required_hours / monthly_capacity_per_engineer

            additional_required = max(math.ceil(combined_required_engineers - available_engineers), 0)
            closing_engineers = available_engineers + additional_required

            results.append(
                {
                    "Forecast Year": int(forecast_year),
                    "Region": region,
                    "Product": product,
                    "Opening Engineers": round(opening_engineers, 2),
                    "Attrition %": round(attrition_pct, 2),
                    "Available Engineers": round(available_engineers, 2),
                    "BAU Growth %": round(bau_growth_pct, 2),
                    "DC Growth %": round(dc_growth_pct, 2),
                    "Opening Workload Hours": round(opening_workload_hours, 2),
                    "BAU Required Hours": round(bau_required_hours, 2),
                    "DC Incremental Hours": round(dc_incremental_hours, 2),
                    "Combined Required Hours": round(combined_required_hours, 2),
                    "BAU Required Engineers": round(bau_required_engineers, 2),
                    "DC Incremental Engineers": round(dc_incremental_engineers, 2),
                    "Combined Required Engineers": round(combined_required_engineers, 2),
                    "Combined Additional Required": int(additional_required),
                    "Closing Engineers": round(closing_engineers, 2),
                }
            )

            opening_engineers = closing_engineers
            opening_workload_hours = combined_required_hours

    return pd.DataFrame(results)
