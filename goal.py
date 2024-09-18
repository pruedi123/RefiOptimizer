import pandas as pd

def simulate_ending_value(df_column, annual_investment, num_years, row_increment):
    results = []
    for start_row in range(0, len(df_column) - (row_increment * (num_years - 1))):
        investment_value = 0  # Starting with 0, as we're calculating for annual savings
        for year in range(num_years):
            current_row = start_row + (row_increment * year)
            factor = df_column[current_row]
            investment_value = (investment_value + annual_investment) * factor
        results.append(investment_value)
    return results

def calculate_success_probability(ending_values, goal):
    count_meeting_goal = sum(1 for value in ending_values if value >= goal)
    total_periods = len(ending_values)
    return count_meeting_goal / total_periods

def find_minimum_investment_for_success(df_column, goal, num_years, success_threshold, row_increment, max_iterations=1000):
    low = 0.10  # Start with a very low minimum investment
    high = 1000000  # Set a high upper bound for the binary search
    tolerance = 0.001  # Allow a small tolerance in success rate
    
    for iteration in range(max_iterations):
        current_investment = (low + high) / 2  # Mid-point investment
        ending_values = simulate_ending_value(df_column, current_investment, num_years, row_increment)
        success_probability = calculate_success_probability(ending_values, goal)
        
        if abs(success_probability - success_threshold) <= tolerance:
            return current_investment  # Return the investment if we hit the target probability
        elif success_probability < success_threshold:
            low = current_investment  # Increase investment to raise probability
        else:
            high = current_investment  # Decrease investment to lower probability
    
    return current_investment  # Return the closest we found after iterations

# Load the Excel file with historical return factors
file_path = 'all_portfolio_annual_factor_20_bps.xlsx'
sheet_name = 'allocation_factors'
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Parameters
goal = 1000000  # Example goal of $1,000,000
num_years = 2  # Example of saving for 25 years
success_threshold = 0.98  # 90% probability of meeting or exceeding the goal
row_increment = 12  # Assuming monthly data, skip 12 rows to get annual factors

# Select the historical return column (e.g., LBM 100E)
df_column = df['LBM 100E']

# Find the minimum annual investment needed to achieve the goal with the given success threshold
minimum_investment = find_minimum_investment_for_success(df_column, goal, num_years, success_threshold, row_increment)

print(f"Minimum annual investment to meet the goal with {success_threshold * 100}% probability: ${minimum_investment:.2f}")