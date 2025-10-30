
import numpy as np
import pandas as pd
from .amort import amort_schedule
from .pmi import pmi_stream
from .utils import home_value_path

def compare_refi_scenarios(
    current,
    options,
    factors,
    horizon_months=120,
    keep_payment=False,
    invest_savings=False,
    fee_drag=0.0,
    current_payment=None,
):
    """Skeleton comparator that you can expand.

    current: dict with keys balance, rate, remaining_term, home_value, home_appreciation, pmi_rate, pmi_basis, cancel_rule
    options: list of dicts with keys name, rate, term, fees, points, finance_fees, portfolio
    factors: placeholder (wire your factor series here per option.portfolio)
    keep_payment: if True, apply any payment savings versus the current loan as extra principal
    invest_savings: if True, invest monthly savings according to option.portfolio using rolling annual factor paths
    fee_drag: annual fee drag (decimal) applied to investment returns
    current_payment: optional override for the current loan's monthly payment (principal & interest)
    """
    fee_drag = float(fee_drag or 0.0)
    if fee_drag < 0.0:
        fee_drag = 0.0
    fee_drag = min(fee_drag, 1.0)
    if current_payment is not None:
        current_payment = float(current_payment)
        if current_payment <= 0.0:
            current_payment = None

    def years_from_months(months: int) -> int:
        if months <= 0:
            return 0
        return (months + 11) // 12

    def build_annual_contributions(monthly_values, years_required):
        annual = []
        for year in range(years_required):
            start = year * 12
            end = min(start + 12, len(monthly_values))
            if start >= len(monthly_values):
                annual.append(0.0)
            else:
                annual.append(float(sum(monthly_values[start:end])))
        return annual

    def build_annual_factor_paths(portfolio_key, years_required):
        if years_required <= 0 or not invest_savings or not factors:
            return []

        portfolios = factors.get("portfolios", {})
        geo = factors.get("portfolio_cagr", {})
        series = portfolios.get(portfolio_key)
        fee_multiplier = max(0.0, 1.0 - fee_drag)

        if series is None or len(series) == 0:
            fallback = float(geo.get(portfolio_key, 1.0) or 1.0)
            if not np.isfinite(fallback) or fallback <= 0.0:
                fallback = 1.0
            return [[fallback * fee_multiplier] * years_required]

        series = series.astype(float)
        max_start = len(series) - (years_required - 1) * 12
        paths = []
        for start in range(max(0, max_start)):
            path = []
            for step in range(years_required):
                idx = start + step * 12
                if idx >= len(series):
                    break
                factor = float(series.iloc[idx])
                if not np.isfinite(factor) or factor <= 0.0:
                    factor = 1.0
                path.append(factor * fee_multiplier)
            if len(path) == years_required:
                paths.append(path)

        if not paths:
            fallback = float(geo.get(portfolio_key, 1.0) or 1.0)
            if not np.isfinite(fallback) or fallback <= 0.0:
                fallback = 1.0
            paths.append([fallback * fee_multiplier] * years_required)
        return paths

    def grow_side_value_paths(side0, annual_contribs, factor_paths):
        if not factor_paths:
            return [float(side0)]

        values = []
        for factors in factor_paths:
            v = float(side0)
            for year, factor in enumerate(factors):
                contrib = annual_contribs[year] if year < len(annual_contribs) else 0.0
                v += contrib
                v *= factor
            # Handle any residual contributions beyond the final factor year.
            if len(annual_contribs) > len(factors):
                for year in range(len(factors), len(annual_contribs)):
                    v += annual_contribs[year]
            values.append(v)
        return values

    def pad_schedule(schedule, horizon):
        if len(schedule) >= horizon:
            return schedule.iloc[:horizon].copy()

        last_month = int(schedule.iloc[-1]["Month"]) if len(schedule) else 0
        last_balance = float(schedule.iloc[-1]["Balance"]) if len(schedule) else 0.0
        padding = []
        remaining = horizon - len(schedule)
        for i in range(remaining):
            padding.append([
                last_month + i + 1,
                0.0,
                0.0,
                0.0,
                0.0,
                last_balance
            ])

        if padding:
            pad_df = pd.DataFrame(padding, columns=schedule.columns)
            schedule = pd.concat([schedule, pad_df], ignore_index=True)
        return schedule.iloc[:horizon].copy()

    results = []
    # Baseline schedule (keep current loan as-is)
    sched_cur = amort_schedule(
        current["balance"],
        current["rate"],
        int(current["remaining_term"]),
        payment=current_payment
    )
    sched_cur = pad_schedule(sched_cur, horizon_months)
    hv = home_value_path(current["home_value"], current["home_appreciation"], horizon_months)
    pmi_cur = pmi_stream(sched_cur["Balance"].values, hv.values, current["pmi_rate"], current["pmi_basis"], current["cancel_rule"])
    total_cur = (sched_cur["Payment"] + sched_cur["Extra"]).sum() + pmi_cur.sum()
    equity_cur = hv.iloc[-1] - sched_cur.iloc[-1]["Balance"]
    side_cur = 0.0  # no side portfolio in baseline by default
    cash_delta_cur = 0.0
    networth_cur = float(equity_cur + side_cur + cash_delta_cur)
    base_payment = float(sched_cur.iloc[0]["Payment"] + sched_cur.iloc[0]["Extra"])

    results.append({
        "Option": "Keep Current",
        "Monthly Payment": float(base_payment),
        "PMI First Mo": pmi_cur[0],
        "Total Cash Out (H)": total_cur,
        "Cash Savings @H": float(cash_delta_cur),
        "Equity @H": float(equity_cur),
        "Side @H": float(side_cur),
        "Side 75th @H": float(side_cur),
        "Side Min @H": float(side_cur),
        "Net Worth @H": float(networth_cur),
        "Net Worth 75th @H": float(networth_cur),
        "Net Worth Min @H": float(networth_cur),
    })

    # Pre-calc fee info for investment and financing logic
    opt_info = []
    max_cash_needed = 0.0
    for opt in options:
        points_amt = float(opt.get("points", 0.0)) * current["balance"]
        fees_amt = float(opt.get("fees", 0.0)) + points_amt
        finance = bool(opt.get("finance_fees", False))
        cash_needed = 0.0 if finance else fees_amt
        max_cash_needed = max(max_cash_needed, cash_needed)
        opt_info.append({
            "opt": opt,
            "points_amt": points_amt,
            "fees_amt": fees_amt,
            "finance": finance,
            "cash_needed": cash_needed,
        })

    # Placeholder for refi options; expand with fees/points/financing and side-portfolio logic
    for info in opt_info:
        opt = info["opt"]
        points_amt = info["points_amt"]
        fees_amt = info["fees_amt"]
        finance = info["finance"]
        cash_needed = info["cash_needed"]
        start_principal = current["balance"] + (fees_amt if finance else 0.0)
        base_sched = amort_schedule(start_principal, float(opt["rate"]), int(opt["term"]))
        base_pmt = float(base_sched.iloc[0]["Payment"])

        extra_payment = 0.0
        if keep_payment:
            extra_payment = max(0.0, base_payment - base_pmt)

        if extra_payment > 0.0:
            sched = amort_schedule(
                start_principal,
                float(opt["rate"]),
                int(opt["term"]),
                extra_fn=lambda _t, extra=extra_payment: extra
            )
        else:
            sched = base_sched

        sched = pad_schedule(sched, horizon_months)

        hv_opt = home_value_path(current["home_value"], current["home_appreciation"], horizon_months)
        pmi_opt = pmi_stream(sched["Balance"].values, hv_opt.values, current["pmi_rate"], current["pmi_basis"], current["cancel_rule"])

        total_cash = (sched["Payment"] + sched["Extra"]).sum() + pmi_opt.sum()
        equity = hv_opt.iloc[-1] - sched.iloc[-1]["Balance"]
        # Side portfolio: lump sum equals unused upfront cash when investing is enabled
        side0 = 0.0
        if invest_savings:
            side0 = max(0.0, max_cash_needed - cash_needed)
        cash_delta = float(total_cur - total_cash)
        years_needed = years_from_months(horizon_months)
        if invest_savings:
            monthly_actual = (sched["Payment"] + sched["Extra"]).tolist()
            monthly_savings = [float(base_payment - val) for val in monthly_actual]
            annual_contribs = build_annual_contributions(monthly_savings, years_needed)
            factor_paths = build_annual_factor_paths(opt.get("portfolio"), years_needed)
            side_values = grow_side_value_paths(side0, annual_contribs, factor_paths)
        else:
            side_values = [float(side0)]

        side_array = np.array(side_values, dtype=float)
        side_median = float(np.median(side_array))
        side_p75 = float(np.percentile(side_array, 75))
        side_min = float(np.min(side_array))

        cash_effect = 0.0 if invest_savings else cash_delta
        networth_values = [
            float(equity + side_val + cash_effect - (0.0 if finance else fees_amt))
            for side_val in side_array
        ]
        networth_array = np.array(networth_values, dtype=float)
        networth_median = float(np.median(networth_array))
        networth_p75 = float(np.percentile(networth_array, 75))
        networth_min = float(np.min(networth_array))

        results.append({
            "Option": opt["name"],
            "Monthly Payment": float(sched.iloc[0]["Payment"] + sched.iloc[0]["Extra"]),
            "PMI First Mo": pmi_opt[0],
            "Total Cash Out (H)": total_cash,
            "Cash Savings @H": cash_delta,
            "Equity @H": float(equity),
            "Side @H": side_median,
            "Side 75th @H": side_p75,
            "Side Min @H": side_min,
            "Net Worth @H": networth_median,
            "Net Worth 75th @H": networth_p75,
            "Net Worth Min @H": networth_min,
        })

    return pd.DataFrame(results)
