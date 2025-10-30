
import numpy as np
import pandas as pd

def currency(x):
    return f"${x:,.0f}"

def home_value_path(v0, annual_appreciation=0.0, months=1, monthly_factors=None):
    """Return a series of projected home values.

    If monthly_factors is provided, each entry should be a growth factor (e.g., 1.002)
    applied sequentially. Otherwise, we fall back to a constant annual appreciation rate.
    """
    base_value = float(v0)
    vals = [base_value]
    if months <= 1:
        return pd.Series(vals)

    monthly_factors = list(monthly_factors or [])
    if annual_appreciation is None:
        annual_appreciation = 0.0
    try:
        annual_appreciation = float(annual_appreciation)
    except (TypeError, ValueError):
        annual_appreciation = 0.0

    fallback_factor = (1.0 + annual_appreciation) ** (1.0 / 12.0) if annual_appreciation else 1.0
    if not np.isfinite(fallback_factor) or fallback_factor <= 0.0:
        fallback_factor = 1.0

    for idx in range(1, months):
        if idx - 1 < len(monthly_factors):
            factor = float(monthly_factors[idx - 1])
            if not np.isfinite(factor) or factor <= 0.0:
                factor = fallback_factor
        else:
            factor = fallback_factor
        vals.append(vals[-1] * factor)
    return pd.Series(vals)
