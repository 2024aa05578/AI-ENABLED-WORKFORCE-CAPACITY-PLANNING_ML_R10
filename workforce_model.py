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
    """
    v17_headcount_based_forecast

    Corrected rolling headcount forecast logic:
    - 2027 baseline = uploaded Current_SE.
    - 2028 baseline = 2027 Final / Closing Engineers.
    - 2029 baseline = 2028 Final / Closing Engineers.

    Required SE is calculated using multiplication factor:
        Multiplication Factor = 1 + ((BAU Growth % + DC Growth %) / 100)

        Combined Required Engineers =
            Opening Engineers * Multiplication Factor
    """

    results = []

    for _, row in df.iterrows():
        region = str(row["Region"]).strip()
        product = str(row["Product"]).strip()

        opening_engineers = _safe_float(row["Current_SE"], 0.0)

        for forecast_year in FORECAST_YEARS:
            bau_growth_pct = _growth_value(
                growth_parameters,
                forecast_year,
                region,
                product,
                "BAU",
            )

            dc_growth_pct = _growth_value(
                growth_parameters,
                forecast_year,
                region,
                product,
                "DC",
            )

            attrition_pct = _safe_float(
                attrition_parameters.get(product, 0.0),
                0.0,
            )

            total_growth_pct = bau_growth_pct + dc_growth_pct
            multiplication_factor = 1 + (total_growth_pct / 100.0)

            available_engineers = opening_engineers * (
                1 - attrition_pct / 100.0
            )

            bau_required_engineers = opening_engineers * (
                1 + bau_growth_pct / 100.0
            )

            dc_incremental_engineers = opening_engineers * (
                dc_growth_pct / 100.0
            )

            combined_required_engineers = (
                opening_engineers * multiplication_factor
            )

            additional_required = max(
                math.ceil(combined_required_engineers - available_engineers),
                0,
            )

            closing_engineers = available_engineers + additional_required

            results.append(
                {
                    "Forecast Year": int(forecast_year),
                    "Region": region,
                    "Product": product,
                    "Opening Engineers": round(opening_engineers, 2),
                    "Baseline Engineers": round(opening_engineers, 2),
                    "BAU Growth %": round(bau_growth_pct, 2),
                    "DC Growth %": round(dc_growth_pct, 2),
                    "Total Growth %": round(total_growth_pct, 2),
                    "Multiplication Factor": round(multiplication_factor, 4),
                    "Attrition %": round(attrition_pct, 2),
                    "Available Engineers": round(available_engineers, 2),
                    "BAU Required Engineers": round(bau_required_engineers, 2),
                    "DC Incremental Engineers": round(dc_incremental_engineers, 2),
                    "Combined Required Engineers": round(
                        combined_required_engineers,
                        2,
                    ),
                    "Combined Additional Required": int(additional_required),
                    "Closing Engineers": round(closing_engineers, 2),
                    "Final Engineers": round(closing_engineers, 2),
                }
            )

            opening_engineers = closing_engineers

    return pd.DataFrame(results)
