import pandas as pd
import os

# Define the data files and their headers
DATA_FILES = {
    "properties.csv": ["id", "name", "address"],
    "bookings.csv": ["id", "property_id", "tenant_name", "start_date", "end_date", "rent_amount", "source", "commission_paid", "notes"],
    "expenses.csv": ["id", "property_id", "expense_date", "category", "amount", "description"]
}

# Define the directory where data files should be stored (relative to this script)
# Assuming the script is in src/ and data should be in data/ at the root level
# Adjust the path as necessary based on your project structure
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def initialize_data_files():
    """
    Checks for the existence of required CSV data files.
    If a file doesn't exist, it creates an empty CSV file with the correct header row.
    """
    # Ensure the data directory exists
    if not os.path.exists(DATA_DIR):
        print(f"Creating data directory: {DATA_DIR}")
        os.makedirs(DATA_DIR)
    else:
        print(f"Data directory already exists: {DATA_DIR}")

    for filename, headers in DATA_FILES.items():
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(file_path):
            print(f"File '{filename}' not found. Creating it with headers...")
            # Create an empty DataFrame with the specified headers
            df = pd.DataFrame(columns=headers)
            # Save the empty DataFrame to a CSV file
            df.to_csv(file_path, index=False, encoding='utf-8')
            print(f"'{filename}' created successfully at '{file_path}'.")
        else:
            print(f"File '{filename}' already exists at '{file_path}'. No action taken.")

if __name__ == "__main__":
    print("Initializing data files...")
    initialize_data_files()
    print("Data file initialization process complete.")
