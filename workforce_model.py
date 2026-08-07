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
    df
