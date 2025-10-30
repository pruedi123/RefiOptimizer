
import numpy as np
import pandas as pd

def amort_schedule(principal, annual_rate, term_months, extra_fn=lambda t: 0.0):
    """Generate an amortization DataFrame for fixed-rate loans.

    Returns columns: Month, Payment, Interest, Principal, Extra, Balance
    """
    r = annual_rate / 12.0
    if r == 0:
        pmt = principal / term_months
    else:
        # numpy financial pmt replacement
        pmt = (r * principal) / (1 - (1 + r) ** (-term_months))

    bal = principal
    rows = []

    for t in range(1, term_months + 1):
        interest = bal * r
        principal_paid = pmt - interest
        extra = float(extra_fn(t) or 0.0)
        total_principal = principal_paid + extra
        bal = max(0.0, bal - total_principal)
        rows.append([t, pmt, interest, principal_paid, extra, bal])
        if bal <= 0.0:
            break

    return pd.DataFrame(rows, columns=[
        "Month","Payment","Interest","Principal","Extra","Balance"
    ])
