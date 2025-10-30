
# Refinance Optimizer (Starter)

A modular starter for comparing refinance options, including PMI and (future) side-portfolio investing of avoided fees.
Data files are Excel-based (`.xlsx`).

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
streamlit run main.py
```

## Where to add logic
- `core/refi_compare.py`: orchestrate comparisons, fees financing, avoided-cost investing, portfolio factors
- `core/invest.py`: grow side portfolio with monthly total return factors
- `core/pmi.py`: PMI rules
- `core/amort.py`: amortization engine

## Data
- `data/factors_spx.xlsx`
- `data/factors_global.xlsx`
- `data/cpi_factors.xlsx`
- `data/pmi_assumptions.xlsx`
- `data/sample_inputs.xlsx`
