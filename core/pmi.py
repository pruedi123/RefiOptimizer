
import numpy as np

def pmi_stream(bal_series, home_val_series, pmi_rate, basis="original", cancel_rule="78"):
    """Return a numpy array of monthly PMI payments.

    basis: "original" or "current"
    cancel_rule: "78", "80", or "FHA_life"
    """
    n = len(bal_series)
    pmi = np.zeros(n)
    active = True
    orig_bal = bal_series[0]

    for t in range(n):
        ltv = bal_series[t] / home_val_series[t]
        if cancel_rule == "FHA_life":
            active = True
        elif cancel_rule == "78" and ltv <= 0.78:
            active = False
        elif cancel_rule == "80" and ltv <= 0.80:
            active = False

        if active:
            base = bal_series[t] if basis == "current" else orig_bal
            pmi[t] = (pmi_rate / 12.0) * base
        else:
            pmi[t] = 0.0
    return pmi
