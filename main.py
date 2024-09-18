import pandas as pd

# Load the Excel file
file_path = 'all_portfolio_annual_factor_20_bps.xlsx'
sheet_name = 'allocation_factors'
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Parameters
initial_investment = 10000
num_years = 30
row_increment = 12  # Move 12 rows down for each year
goal = 1000000  # Goal to meet or exceed

# Create an Excel writer to save results for all columns
output_file = 'investment_results_with_stats.xlsx'
writer = pd.ExcelWriter(output_file, engine='openpyxl', mode='w')

# Loop through each column in the dataframe (excluding non-numeric ones if any)
for column_name in df.columns:
    if pd.api.types.is_numeric_dtype(df[column_name]):
        print(f"Running calculations for column: {column_name}")
        
        # Extract relevant column (e.g., LBM 100E, LBM 90E, etc.)
        factors = df[column_name]

        # Store results for each valid period, along with the factors and row numbers
        results = []
        factors_used = []
        rows_used = []

        # Loop through valid starting rows
        for start_row in range(0, len(factors) - (row_increment * (num_years - 1))):
            investment_value = initial_investment
            factor_list = []  # To store the factors for each year
            row_list = []     # To store the row numbers used for each year

            for year in range(num_years):
                # Calculate the current row for the factor
                current_row = start_row + (row_increment * year)
                row_list.append(current_row + 1)  # Add 1 to match human-readable row numbers (Excel-style)
                factor_list.append(factors[current_row])

                # Multiply investment by factor
                investment_value *= factors[current_row]
                # Add $1000 for next year (except after the final year)
                if year < num_years - 1:
                    investment_value += initial_investment

            # Store the ending value, factors used, and rows used for this period
            results.append(investment_value)
            factors_used.append(factor_list)
            rows_used.append(row_list)

        # Convert results to a DataFrame
        results_df = pd.DataFrame({
            'Ending Value': results,
            'Factors Used': factors_used,
            'Rows Used': rows_used
        })

        # Save the results to a new sheet for the current column
        results_df.to_excel(writer, sheet_name=f'results_{column_name}', index=False)

        # Calculate statistics for the current column
        average_ending_value = results_df['Ending Value'].mean()
        median_ending_value = results_df['Ending Value'].median()
        minimum_ending_value = results_df['Ending Value'].min()

        # Calculate probability of meeting or exceeding the goal
        count_meeting_goal = (results_df['Ending Value'] >= goal).sum()
        total_periods = len(results_df)
        probability_of_meeting_goal = count_meeting_goal / total_periods

        # Add statistics to the output DataFrame for the current column
        stats_df = pd.DataFrame({
            'Average Ending Value': [average_ending_value],
            'Median Ending Value': [median_ending_value],
            'Minimum Ending Value': [minimum_ending_value],
            'Probability of Meeting or Exceeding Goal': [probability_of_meeting_goal]
        })

        # Save the statistics to a new sheet for the current column
        stats_df.to_excel(writer, sheet_name=f'statistics_{column_name}', index=False)

# Close the Excel writer and save the file
writer.save()

print(f"Results and statistics for all columns have been written to {output_file}.")