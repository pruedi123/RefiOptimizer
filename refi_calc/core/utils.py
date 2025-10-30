
import pandas as pd

def currency(x):
    return f"${x:,.0f}"

def home_value_path(v0, annual_appreciation, months):
    monthly = (1 + annual_appreciation) ** (1/12) - 1
    vals = [v0]
    for _ in range(1, months):
        vals.append(vals[-1] * (1 + monthly))
    return pd.Series(vals)
