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


def _capacity_per_engineer(productive_hours, working_days, target_utilization):
    productive_hours = _safe_float(productive_hours, 7.0)
    working_days = _safe_float(working_days, 20.0)
    target_utilization = _safe_float(target_utilization, 90.0)
    capacity = productive_hours * working_days * (target_utilization / 100.0)
    if capacity <= 0:
        raise ValueError("Monthly capacity per engineer must be greater than zero.")
    return capacity


def calculate_workforce(df, growth_parameters, attrition_parameters, productive_hours, working_days, target_utilization):
    results = []
    monthly_capacity = _capacity_per_engineer(productive_hours, working_days, target_utilization)

    for _, row in df.iterrows():
        region = str(row["Region"]).strip()
        product = str(row["Product"]).strip()
        current_se = _safe_float(row["Current_SE"], 0.0)

        base_workload_hours = (
            _safe_float(row["Breakdown_WO"], 0.0) * _safe_float(row["Breakdown_Hrs"], 0.0)
            + _safe_float(row["PM_WO"], 0.0) * _safe_float(row["PM_Hrs"], 0.0)
            + _safe_float(row["Startup_WO"], 0.0) * _safe_float(row["Startup_Hrs"], 0.0)
        )

        previous_year_final_engineers = current_se

        for forecast_year in FORECAST_YEARS:
            bau_growth_pct = _growth_value(growth_parameters, forecast_year, region, product, "BAU")
            dc_growth_pct = _growth_value(growth_parameters, forecast_year, region, product, "DC")
            attrition_pct = _safe_float(attrition_parameters.get(product, 0.0), 0.0)
            total_growth_pct = bau_growth_pct + dc_growth_pct
            multiplication_factor = 1 + (total_growth_pct / 100.0)

            available_engineers = previous_year_final_engineers * (1 - attrition_pct / 100.0)

            if int(forecast_year) == 2027:
                baseline_engineers = current_se
                base_required_engineers = base_workload_hours / monthly_capacity
                bau_required_engineers = base_required_engineers * (1 + bau_growth_pct / 100.0)
                dc_incremental_engineers = base_required_engineers * (dc_growth_pct / 100.0)
                combined_required_engineers = bau_required_engineers + dc_incremental_engineers
                calculation_basis = "Original workload-based 2027 calculation"
            else:
                baseline_engineers = previous_year_final_engineers
                bau_required_engineers = baseline_engineers * (1 + bau_growth_pct / 100.0)
                dc_incremental_engineers = baseline_engineers * (dc_growth_pct / 100.0)
                combined_required_engineers = baseline_engineers * multiplication_factor
                calculation_basis = "Rolling headcount baseline from previous year final engineers"

            additional_required = max(math.ceil(combined_required_engineers - available_engineers), 0)
            final_engineers = available_engineers + additional_required

            results.append({
                "Forecast Year": int(forecast_year),
                "Region": region,
                "Product": product,
                "Calculation Basis": calculation_basis,
                "Baseline Engineers": round(baseline_engineers, 2),
                "Opening Engineers": round(previous_year_final_engineers, 2),
                "Attrition %": round(attrition_pct, 2),
                "Available Engineers": round(available_engineers, 2),
                "BAU Growth %": round(bau_growth_pct, 2),
                "DC Growth %": round(dc_growth_pct, 2),
                "Total Growth %": round(total_growth_pct, 2),
                "Multiplication Factor": round(multiplication_factor, 4),
                "Base Workload Hours": round(base_workload_hours, 2),
                "Monthly Capacity / Engineer": round(monthly_capacity, 2),
                "BAU Required Engineers": round(bau_required_engineers, 2),
                "DC Incremental Engineers": round(dc_incremental_engineers, 2),
                "Combined Required Engineers": round(combined_required_engineers, 2),
                "Combined Additional Required": int(additional_required),
                "Closing Engineers": round(final_engineers, 2),
                "Final Engineers": round(final_engineers, 2),
            })

            previous_year_final_engineers = final_engineers

    return pd.DataFrame(results)
