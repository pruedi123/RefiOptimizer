import streamlit as st
import pandas as pd
from core.refi_compare import compare_refi_scenarios
from core.factors import prepare_portfolio_factors

st.set_page_config(page_title="Refinance Optimizer", layout="wide", initial_sidebar_state="expanded")
st.title("Refinance Optimizer (Starter)")

def _monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    if term_months <= 0:
        return 0.0
    r = annual_rate / 12.0
    if r == 0:
        return principal / term_months
    return (r * principal) / (1 - (1 + r) ** (-term_months))

st.sidebar.header("Current Loan")
cur_balance = st.sidebar.slider("Current balance ($)", min_value=0.0, max_value=2000000.0, value=700000.0, step=1000.0)
cur_rate = st.sidebar.slider("Current rate (APR, %)", min_value=0.0, max_value=20.0, value=8.55, step=0.01) / 100.0
cur_term = st.sidebar.slider("Remaining term (months)", min_value=1, max_value=480, value=360, step=1)
home_value = st.sidebar.slider("Home value ($)", min_value=0.0, max_value=5000000.0, value=875000.0, step=1000.0)

default_cur_payment = _monthly_payment(cur_balance, cur_rate, int(cur_term))
cur_payment = st.sidebar.number_input(
    "Current monthly payment ($)",
    min_value=0.0,
    max_value=50000.0,
    value=float(round(default_cur_payment, 2)),
    step=10.0,
    format="%.2f",
    help="Monthly principal & interest you currently pay. Defaults to the scheduled payment."
)

st.sidebar.header("Horizon & PMI")
horizon = st.sidebar.slider("Analysis horizon (months)", min_value=1, max_value=480, value=120, step=1)
pmi_rate = st.sidebar.slider("PMI annual rate (e.g., 0.7% as 0.7)", min_value=0.0, max_value=10.0, value=0.7, step=0.05) / 100.0
cancel_rule = st.sidebar.selectbox("PMI cancel rule", ["78", "80", "FHA_life"])
pmi_basis = st.sidebar.selectbox("PMI basis", ["original", "current"])
appr = st.sidebar.slider("Home appreciation (%/yr)", min_value=-50.0, max_value=50.0, value=3.0, step=0.5) / 100.0

st.sidebar.header("Options")
st.sidebar.markdown("Add two sample options below. (Edit in code or enhance UI later.)")
base_options = [
    {"name":"Offer 1","rate":0.0646,"term":360,"fees":0.0,"points":0.0,"finance_fees":True, "portfolio":"global_60e"},
    {"name":"Offer 2","rate":0.0615,"term":360,"fees":5000.0,"points":0.0,"finance_fees":False,"portfolio":"spx_60e"}
]

@st.cache_data(show_spinner=False)
def load_factor_data():
    return prepare_portfolio_factors()

factor_data = load_factor_data()

portfolio_map = {
    "SPX 100/0": "spx100e",
    "SPX 90/10": "spx90e",
    "SPX 80/20": "spx80e",
    "SPX 70/30": "spx70e",
    "SPX 60/40": "spx60e",
    "SPX 50/50": "spx50e",
    "SPX 40/60": "spx40e",
    "SPX 30/70": "spx30e",
    "SPX 20/80": "spx20e",
    "SPX 10/90": "spx10e",
    "SPX 0/100": "spx0e",
    "Global 100/0": "global_100e",
    "Global 90/10": "global_90e",
    "Global 80/20": "global_80e",
    "Global 70/30": "global_70e",
    "Global 60/40": "global_60e",
    "Global 50/50": "global_50e",
    "Global 40/60": "global_40e",
    "Global 30/70": "global_30e",
    "Global 20/80": "global_20e",
    "Global 10/90": "global_10e",
    "Global 0/100": "global_100f"
}
portfolio_choices = list(portfolio_map.keys())
allocation_choice = st.sidebar.selectbox(
    "Invest savings into",
    options=portfolio_choices,
    index=portfolio_choices.index("Global 60/40")
)
allocation_key = portfolio_map[allocation_choice]

options = []
for opt in base_options:
    st.sidebar.markdown(f"**{opt['name']}**")
    rate = st.sidebar.slider(
        f"{opt['name']} rate (APR, %)",
        min_value=0.0,
        max_value=20.0,
        value=float(opt["rate"]) * 100.0,
        step=0.01
    ) / 100.0
    term = st.sidebar.slider(
        f"{opt['name']} term (months)",
        min_value=1,
        max_value=480,
        value=int(opt["term"]),
        step=1
    )
    fees = st.sidebar.slider(
        f"{opt['name']} closing costs ($)",
        min_value=0.0,
        max_value=100000.0,
        value=float(opt["fees"]),
        step=100.0
    )
    points = st.sidebar.slider(
        f"{opt['name']} points (% of balance)",
        min_value=0.0,
        max_value=5.0,
        value=float(opt.get("points", 0.0)) * 100.0,
        step=0.01
    ) / 100.0
    finance_fees = st.sidebar.checkbox(
        f"{opt['name']} finance closing costs?",
        value=bool(opt.get("finance_fees", False))
    )
    options.append({
        "name": opt["name"],
        "rate": rate,
        "term": int(term),
        "fees": float(fees),
        "points": float(points),
        "finance_fees": finance_fees,
        "portfolio": allocation_key
    })
    st.sidebar.divider()

apply_savings = st.sidebar.checkbox(
    "Apply payment savings to principal",
    value=False,
    help="If a refi lowers the required payment, keep paying the current amount and send the savings to extra principal."
)

invest_savings = st.sidebar.checkbox(
    "Invest payment savings",
    value=False,
    help="Direct any monthly savings into the selected portfolio once per month."
)

fee_drag_pct = st.sidebar.slider(
    "Annual investment fee drag (%)",
    min_value=0.0,
    max_value=1.0,
    value=0.0,
    step=0.05,
    help="Reduces side-portfolio returns to account for advisory or fund fees.",
)
fee_drag = fee_drag_pct / 100.0

current = {
    "balance": cur_balance,
    "rate": cur_rate,
    "remaining_term": int(cur_term),
    "home_value": home_value,
    "home_appreciation": appr,
    "pmi_rate": pmi_rate,
    "pmi_basis": pmi_basis,
    "cancel_rule": cancel_rule
}

st.write("🔧 Tip: use the sidebar toggles to apply payment savings to principal or invest them in a chosen portfolio.")
results = compare_refi_scenarios(
    current=current,
    options=options,
    factors=factor_data,
    horizon_months=int(horizon),
    keep_payment=apply_savings,
    invest_savings=invest_savings,
    fee_drag=fee_drag,
    current_payment=cur_payment
)

baseline = results.loc[results["Option"] == "Keep Current"].iloc[0]
summary = results.copy()
summary["Monthly Payment Change ($)"] = summary["Monthly Payment"] - baseline["Monthly Payment"]
summary["Net Worth Change vs Current ($)"] = summary["Net Worth @H"] - baseline["Net Worth @H"]

summary = summary[[
    "Option",
    "Monthly Payment",
    "Monthly Payment Change ($)",
    "PMI First Mo",
    "Total Cash Out (H)",
    "Cash Savings @H",
    "Side @H",
    "Net Worth @H",
    "Net Worth Change vs Current ($)"
]].rename(columns={
    "Monthly Payment": "Monthly Payment ($/mo)",
    "Monthly Payment Change ($)": "Change vs Current ($/mo)",
    "PMI First Mo": "PMI First Month ($)",
    "Total Cash Out (H)": "Total Paid to Horizon ($)",
    "Cash Savings @H": "Cash Saved vs Current ($)",
    "Side @H": "Invested Balance ($)",
    "Net Worth @H": "Net Worth at Horizon ($)",
    "Net Worth Change vs Current ($)": "Net Worth Change vs Current ($)"
})

fmt = {
    "Monthly Payment ($/mo)": "${:,.0f}",
    "Change vs Current ($/mo)": "${:,.0f}",
    "PMI First Month ($)": "${:,.0f}",
    "Total Paid to Horizon ($)": "${:,.0f}",
    "Cash Saved vs Current ($)": "${:,.0f}",
    "Invested Balance ($)": "${:,.0f}",
    "Net Worth at Horizon ($)": "${:,.0f}",
    "Net Worth Change vs Current ($)": "${:,.0f}",
}

best_option = summary.sort_values("Net Worth at Horizon ($)", ascending=False).iloc[0]
if best_option["Option"] == "Keep Current":
    st.info("Keeping the current loan leads to the highest net worth at your analysis horizon.")
else:
    st.success(
        f"**{best_option['Option']}** builds the most wealth by your horizon "
        f"({fmt['Net Worth Change vs Current ($)'].format(best_option['Net Worth Change vs Current ($)'])} "
        "more than keeping the current loan)."
    )

st.markdown(
    "#### How to read the table\n"
    "- **Monthly Payment**: what you would actually pay each month.\n"
    "- **Change vs Current**: negative numbers mean you pay less than today.\n"
    "- **PMI First Month**: private mortgage insurance due in month one under that option.\n"
    "- **Cash Saved vs Current**: total dollars you still have because you paid less than the current loan.\n"
    "- **Invested Balance**: value of the side account built from payment savings (zero if you keep the cash).\n"
    "- **Net Worth Change**: how much richer or poorer you are at the horizon after accounting for equity, fees, and saved cash."
)

st.dataframe(summary.style.format(fmt), use_container_width=True)

def option_by_name(name: str):
    for opt in options:
        if opt["name"] == name:
            return opt
    return None

if best_option["Option"] != "Keep Current":
    competitor_row = summary[summary["Option"] != best_option["Option"]].sort_values(
        "Net Worth at Horizon ($)", ascending=False
    ).iloc[0]
    target_name = best_option["Option"]
    target_opt = option_by_name(target_name)
    competitor_value = competitor_row["Net Worth at Horizon ($)"]

    def evaluate_networth_with_fee(candidate_fee: float):
        modified = []
        for opt in options:
            new_opt = dict(opt)
            if new_opt["name"] == target_name:
                new_opt["fees"] = float(candidate_fee)
                new_opt["finance_fees"] = False
            modified.append(new_opt)
        df = compare_refi_scenarios(
            current=current,
            options=modified,
            factors=factor_data,
            horizon_months=int(horizon),
            keep_payment=apply_savings,
            invest_savings=invest_savings
        )
        return df.loc[df["Option"] == target_name, "Net Worth @H"].iloc[0]

    if st.button("Solve break-even closing costs for preferred offer"):
        if target_opt is None:
            st.warning("Could not locate the preferred offer details.")
        else:
            current_fee = float(target_opt.get("fees", 0.0))
            current_networth = float(best_option["Net Worth at Horizon ($)"])

            if current_networth <= competitor_value + 1e-6:
                st.info("Preferred option is already no better than the alternative; adjust fees directly.")
            else:
                low = 0.0
                low_value = evaluate_networth_with_fee(low)
                if low_value < competitor_value:
                    st.info(
                        "Even at $0 closing costs this offer would not beat the alternative."
                    )
                else:
                    high = max(current_fee, 1000.0)
                    high_value = evaluate_networth_with_fee(high)
                    attempts = 0
                    while high_value > competitor_value and high < 1_000_000 and attempts < 20:
                        high *= 2
                        high_value = evaluate_networth_with_fee(high)
                        attempts += 1

                    if high_value > competitor_value:
                        st.info("The offer remains better even with extremely high closing costs.")
                    else:
                        for _ in range(30):
                            mid = (low + high) / 2.0
                            mid_value = evaluate_networth_with_fee(mid)
                            if abs(mid_value - competitor_value) <= 1.0:
                                low = high = mid
                                break
                            if mid_value > competitor_value:
                                low = mid
                            else:
                                high = mid
                        breakeven_fee = (low + high) / 2.0
                        st.info(
                            f"{target_name} would tie {competitor_row['Option']} if its cash closing costs were about "
                            f"${breakeven_fee:,.0f} (paid out of pocket)."
                        )
