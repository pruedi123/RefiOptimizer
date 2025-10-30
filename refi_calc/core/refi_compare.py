
import pandas as pd
from .amort import amort_schedule
from .pmi import pmi_stream
from .invest import side_portfolio
from .utils import home_value_path

def compare_refi_scenarios(current, options, factors, horizon_months=120, keep_payment=False, invest_savings=False):
    """Skeleton comparator that you can expand.

    current: dict with keys balance, rate, remaining_term, home_value, home_appreciation, pmi_rate, pmi_basis, cancel_rule
    options: list of dicts with keys name, rate, term, fees, points, finance_fees, portfolio
    factors: placeholder (wire your factor series here per option.portfolio)
    keep_payment: if True, apply any payment savings versus the current loan as extra principal
    invest_savings: if True, invest monthly savings according to option.portfolio
    """
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

    def build_monthly_factors(portfolio_key, months):
        if not invest_savings or not factors:
            return [1.0] * months

        portfolios = factors.get("portfolios", {})
        geo = factors.get("portfolio_cagr", {})
        series = portfolios.get(portfolio_key)
        monthly = []
        idx = 0
        while len(monthly) < months:
            if series is not None and idx < len(series):
                annual_factor = float(series.iloc[idx])
            else:
                annual_factor = float(geo.get(portfolio_key, 1.0))
            idx += 1
            if annual_factor <= 0.0:
                monthly_factor = 1.0
            else:
                monthly_factor = annual_factor ** (1.0 / 12.0)
            months_to_add = min(12, months - len(monthly))
            monthly.extend([monthly_factor] * months_to_add)
        return monthly[:months]

    results = []
    # Baseline schedule (keep current loan as-is)
    sched_cur = amort_schedule(current["balance"], current["rate"], int(current["remaining_term"]))
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
        "Net Worth @H": float(networth_cur),
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
        if invest_savings:
            monthly_actual = sched["Payment"] + sched["Extra"]
            monthly_savings = (base_payment - monthly_actual).tolist()
            monthly_factors = build_monthly_factors(opt.get("portfolio"), len(monthly_savings))
            side_series = side_portfolio(side0, monthly_savings, monthly_factors)
            side = float(side_series.iloc[-1]) if len(side_series) else float(side0)
        else:
            side = float(side0)
        cash_effect = 0.0 if invest_savings else cash_delta
        networth = float(equity + side + cash_effect - (0.0 if finance else fees_amt))

        results.append({
            "Option": opt["name"],
            "Monthly Payment": float(sched.iloc[0]["Payment"] + sched.iloc[0]["Extra"]),
            "PMI First Mo": pmi_opt[0],
            "Total Cash Out (H)": total_cash,
            "Cash Savings @H": cash_delta,
            "Equity @H": float(equity),
            "Side @H": float(side),
            "Net Worth @H": float(networth),
        })

    return pd.DataFrame(results)
