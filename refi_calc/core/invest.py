
import pandas as pd
import numpy as np

def side_portfolio(lump_sum, monthly_contribs, factor_series):
    """Grow a side portfolio using monthly total return factors.
    factor_series: iterable of monthly multipliers (e.g., 1.01 = +1%)
    """
    v = float(lump_sum or 0.0)
    values = []
    n = len(monthly_contribs)
    for i in range(n):
        f = float(factor_series[i]) if i < len(factor_series) else 1.0
        v = v * f + float(monthly_contribs[i] or 0.0)
        values.append(v)
    return pd.Series(values)
