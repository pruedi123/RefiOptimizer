import math
import re
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _coerce_month(series: pd.Series) -> pd.Series:
    """Convert a string column to a monthly PeriodIndex-compatible series."""
    dt = pd.to_datetime(series, errors="coerce")
    return dt.dt.to_period("M")


def load_cpi_index(path: Optional[Path] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return the CPI series indexed by month plus annual aggregates.

    Monthly columns:
        CPI                - raw CPI index from the sheet
        CPI_YoY            - trailing 12-month change (decimal)
        CPI_Factor_Month   - simple month-over-month factor

    Annual frame (index = year):
        cpi_year_end       - CPI level at the end of the year
        cpi_yoy            - year-over-year change (decimal)
        cpi_factor_yoy     - growth factor versus prior year (1 + cpi_yoy)
    """
    path = Path(path or DATA_DIR / "cpi_index.xlsx")
    df = pd.read_excel(path)
    if "Date" not in df.columns or "CPI" not in df.columns:
        raise ValueError("Expected 'Date' and 'CPI' columns in CPI sheet.")

    df["Date"] = _coerce_month(df["Date"])
    df = df.dropna(subset=["Date"]).copy()
    df = df.set_index("Date").sort_index()

    cpi = df["CPI"].astype(float)
    annual = (
        cpi.groupby(cpi.index.year)
        .last()
        .rename("cpi_year_end")
        .to_frame()
    )
    annual["cpi_yoy"] = annual["cpi_year_end"].pct_change()
    annual["cpi_factor_yoy"] = 1.0 + annual["cpi_yoy"]
    annual.index.name = "year"

    df = df.assign(
        CPI=cpi,
        CPI_YoY=df["CPI"].pct_change(12),
        CPI_Factor_Month=1.0 + df["CPI"].pct_change()
    )

    return df[["CPI", "CPI_YoY", "CPI_Factor_Month"]], annual


def _clean_column(name: str) -> str:
    """Normalize column headers to snake_case without spaces."""
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip())
    name = re.sub(r"_+", "_", name)
    return name.lower().strip("_")


def load_factor_table(
    filename: str,
    begin_col: Optional[str] = None,
    end_col: Optional[str] = None,
    keep_columns: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Load a factor workbook and return a tidy DataFrame.

    Args:
        filename: Excel file located under the data directory.
        begin_col/end_col: Column names that mark the rolling window bounds.
        keep_columns: Optional subset of factor columns to retain.
    """
    path = DATA_DIR / filename
    df = pd.read_excel(path)

    column_map: Dict[str, str] = {}
    for col in df.columns:
        column_map[col] = _clean_column(col)
    df = df.rename(columns=column_map)

    if begin_col:
        begin_key = _clean_column(begin_col)
        if begin_key not in df.columns:
            raise ValueError(f"Column '{begin_col}' not found in {filename}")
        df[begin_key] = _coerce_month(df[begin_key])
    else:
        begin_key = None

    if end_col:
        end_key = _clean_column(end_col)
        if end_key not in df.columns:
            raise ValueError(f"Column '{end_col}' not found in {filename}")
        df[end_key] = _coerce_month(df[end_key])
    else:
        end_key = None

    factor_cols = [
        c for c in df.columns
        if c not in {begin_key, end_key} and not c.startswith("unnamed")
    ]
    if keep_columns:
        normalized = {_clean_column(c) for c in keep_columns}
        factor_cols = [c for c in factor_cols if c in normalized]

    # Coerce factor columns to numeric and drop trailing commentary rows.
    for col in factor_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=factor_cols, how="all")

    result_cols = []
    if begin_key:
        result_cols.append(begin_key)
    if end_key:
        result_cols.append(end_key)
    result_cols.extend(factor_cols)

    tidy = df[result_cols].copy()
    if begin_key:
        tidy = tidy.set_index(begin_key)
        tidy.index.name = "begin_month"
    return tidy.sort_index()


def load_spx_factors() -> pd.DataFrame:
    """Convenience wrapper for the SPX factor workbook."""
    return load_factor_table("spx_factors.xlsx", begin_col="begin month", end_col="end month")


def load_global_factors() -> pd.DataFrame:
    """Convenience wrapper for the Global factor workbook."""
    df = load_factor_table("global_factors.xlsx")
    rename_map = {
        col: col.replace("lbm_", "global_")
        for col in df.columns
        if col.startswith("lbm_")
    }
    return df.rename(columns=rename_map)


def geometric_mean(series: pd.Series) -> float:
    s = series.dropna().astype(float)
    if s.empty:
        return 1.0
    logs = np.log(s)
    return float(np.exp(logs.mean()))


def prepare_portfolio_factors() -> Dict[str, Dict[str, object]]:
    """Load CPI, SPX, and Global factors and harmonize into a single bundle."""
    cpi_monthly, cpi_annual = load_cpi_index()
    spx = load_spx_factors()
    global_df = load_global_factors()

    # Align Global rows to SPX length by trimming to the overlapping tail.
    common_len = min(len(spx), len(global_df))
    spx_aligned = spx.iloc[-common_len:].copy()
    global_aligned = global_df.iloc[-common_len:].copy()
    global_aligned.index = spx_aligned.index

    portfolio_series: Dict[str, pd.Series] = {}
    portfolio_cagr: Dict[str, float] = {}

    for col in spx_aligned.columns:
        if col == "end_month":
            continue
        series = spx_aligned[col].astype(float)
        portfolio_series[col] = series.reset_index(drop=True)
        portfolio_cagr[col] = geometric_mean(series)

    for col in global_aligned.columns:
        if col == "end_month":
            continue
        series = global_aligned[col].astype(float)
        portfolio_series[col] = series.reset_index(drop=True)
        portfolio_cagr[col] = geometric_mean(series)

    return {
        "cpi_monthly": cpi_monthly,
        "cpi_annual": cpi_annual,
        "spx": spx_aligned,
        "global": global_aligned,
        "portfolios": portfolio_series,
        "portfolio_cagr": portfolio_cagr,
    }
