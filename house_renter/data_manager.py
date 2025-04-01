import pandas as pd
import os
import streamlit as st
from pandas.errors import EmptyDataError

# Define the directory where data files are stored (relative to this script)
# Assuming src/data_manager.py and data/ are siblings under the project root
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# Define data file paths and expected columns
PROPERTIES_FILE = os.path.join(DATA_DIR, "properties.csv")
PROPERTIES_COLS = ["id", "name", "address"]

BOOKINGS_FILE = os.path.join(DATA_DIR, "bookings.csv")
BOOKINGS_COLS = ["id", "property_id", "tenant_name", "start_date", "end_date", "rent_amount", "source", "commission_paid", "notes"]
BOOKINGS_DATE_COLS = ["start_date", "end_date"]

EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
EXPENSES_COLS = ["id", "property_id", "expense_date", "category", "amount", "description"]
EXPENSES_DATE_COLS = ["expense_date"]

# --- DATA-004: Define Data Constants ---
BOOKING_SOURCES = ['Personal', 'Booking.com', 'Airbnb', 'Other']
EXPENSE_CATEGORIES = ['Cleaning', 'Maintenance', 'Utilities', 'Service Fee', 'Taxes', 'Insurance', 'Other']

# --- Helper Function to Ensure Data Directory ---
def _ensure_data_dir():
    """Ensures the data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created data directory: {DATA_DIR}")

# --- Helper Function to Load CSV Safely ---
def _load_csv_safe(filepath, columns, parse_dates=None):
    """Loads a CSV file safely, returning an empty DataFrame if not found or empty."""
    _ensure_data_dir() # Ensure directory exists before trying to read/write
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath, parse_dates=parse_dates)
            # Ensure all expected columns exist, adding missing ones with NaN
            for col in columns:
                if col not in df.columns:
                    df[col] = pd.NA # Or appropriate default like 0, '', etc.
            # Ensure correct column order and select only expected columns
            df = df[columns]
            return df
        except EmptyDataError:
            print(f"Warning: File '{filepath}' is empty. Returning empty DataFrame.")
            return pd.DataFrame(columns=columns)
        except Exception as e:
            print(f"Error loading file '{filepath}': {e}. Returning empty DataFrame.")
            # Consider more specific error handling or logging
            return pd.DataFrame(columns=columns)
    else:
        print(f"Warning: File '{filepath}' not found. Returning empty DataFrame.")
        # Optionally, create the file with headers here
        # df = pd.DataFrame(columns=columns)
        # df.to_csv(filepath, index=False, encoding='utf-8')
        # print(f"Created empty file '{filepath}' with headers.")
        return pd.DataFrame(columns=columns)

# --- DATA-002: Implement Data Loading Functions ---

@st.cache_data
def load_properties():
    """Loads property data from properties.csv."""
    print("Loading properties...") # Add print statement to observe caching
    df = _load_csv_safe(PROPERTIES_FILE, PROPERTIES_COLS)
    # Ensure 'id' column is integer type, handling potential NA values if necessary
    if 'id' in df.columns:
         # Convert to Int64 (nullable integer) to handle potential NaNs if file was manually edited
        df['id'] = df['id'].astype(pd.Int64Dtype())
    return df

@st.cache_data
def load_bookings():
    """Loads booking data from bookings.csv, parsing dates."""
    print("Loading bookings...") # Add print statement to observe caching
    df = _load_csv_safe(BOOKINGS_FILE, BOOKINGS_COLS, parse_dates=BOOKINGS_DATE_COLS)
    # Ensure 'id' and 'property_id' are integer types
    if 'id' in df.columns:
        df['id'] = df['id'].astype(pd.Int64Dtype())
    if 'property_id' in df.columns:
        df['property_id'] = df['property_id'].astype(pd.Int64Dtype())
    # Ensure numeric types for amounts
    if 'rent_amount' in df.columns:
        df['rent_amount'] = pd.to_numeric(df['rent_amount'], errors='coerce')
    if 'commission_paid' in df.columns:
        df['commission_paid'] = pd.to_numeric(df['commission_paid'], errors='coerce')
    return df

@st.cache_data
def load_expenses():
    """Loads expense data from expenses.csv, parsing dates."""
    print("Loading expenses...") # Add print statement to observe caching
    df = _load_csv_safe(EXPENSES_FILE, EXPENSES_COLS, parse_dates=EXPENSES_DATE_COLS)
    # Ensure 'id' and 'property_id' are integer types
    if 'id' in df.columns:
        df['id'] = df['id'].astype(pd.Int64Dtype())
    if 'property_id' in df.columns:
        df['property_id'] = df['property_id'].astype(pd.Int64Dtype())
    # Ensure numeric type for amount
    if 'amount' in df.columns:
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    return df

# --- Helper Function for Saving Data ---
def _save_data(df, filepath):
    """Saves DataFrame to CSV, clearing relevant caches."""
    try:
        df.to_csv(filepath, index=False, encoding='utf-8')
        # Clear caches after successful save
        if filepath == PROPERTIES_FILE:
            load_properties.clear()
        elif filepath == BOOKINGS_FILE:
            load_bookings.clear()
        elif filepath == EXPENSES_FILE:
            load_expenses.clear()
        print(f"Data saved to {filepath} and cache cleared.")
        return True
    except Exception as e:
        print(f"Error saving data to {filepath}: {e}")
        st.error(f"Failed to save data to {os.path.basename(filepath)}: {e}")
        return False

# --- Helper Function to Get Next ID ---
def _get_next_id(df):
    """Calculates the next available ID."""
    if df.empty or 'id' not in df.columns or df['id'].isnull().all():
        return 1
    else:
        # Ensure 'id' is numeric, coercing errors, then fill NA with 0 before finding max
        return int(pd.to_numeric(df['id'], errors='coerce').fillna(0).max()) + 1

# --- DATA-003: Implement Data Saving Functions ---

def add_property(name: str, address: str):
    """Adds a new property to properties.csv."""
    df = load_properties()
    next_id = _get_next_id(df)
    new_property = pd.DataFrame([{
        "id": next_id,
        "name": name,
        "address": address
    }])
    # Ensure new data has same types as existing dataframe where possible
    new_property = new_property.astype(df.dtypes.to_dict())

    updated_df = pd.concat([df, new_property], ignore_index=True)
    return _save_data(updated_df, PROPERTIES_FILE)

def add_booking(property_id: int, tenant_name: str, start_date, end_date,
                rent_amount: float, source: str, commission_paid: float = None, notes: str = None):
    """Adds a new booking to bookings.csv."""
    df = load_bookings()
    next_id = _get_next_id(df)

    # Ensure dates are in a consistent format (e.g., pd.Timestamp) if not already
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    new_booking = pd.DataFrame([{
        "id": next_id,
        "property_id": property_id,
        "tenant_name": tenant_name,
        "start_date": start_date,
        "end_date": end_date,
        "rent_amount": rent_amount,
        "source": source,
        "commission_paid": commission_paid,
        "notes": notes
    }])
    # Ensure new data has same types as existing dataframe where possible
    # Handle potential type differences carefully, especially for dates and nullable ints
    for col in BOOKINGS_COLS:
         if col in new_booking.columns and col in df.columns:
             try:
                 new_booking[col] = new_booking[col].astype(df[col].dtype)
             except Exception as e:
                 print(f"Warning: Could not cast column {col} during add_booking. Error: {e}")
                 # Fallback or specific handling might be needed depending on column type

    updated_df = pd.concat([df, new_booking], ignore_index=True)
    return _save_data(updated_df, BOOKINGS_FILE)

def add_expense(property_id: int, expense_date, category: str, amount: float, description: str = None):
    """Adds a new expense to expenses.csv."""
    df = load_expenses()
    next_id = _get_next_id(df)

    # Ensure date is a pd.Timestamp
    expense_date = pd.to_datetime(expense_date)

    new_expense = pd.DataFrame([{
        "id": next_id,
        "property_id": property_id,
        "expense_date": expense_date,
        "category": category,
        "amount": amount,
        "description": description
    }])
    # Ensure new data has same types as existing dataframe where possible
    for col in EXPENSES_COLS:
         if col in new_expense.columns and col in df.columns:
             try:
                 new_expense[col] = new_expense[col].astype(df[col].dtype)
             except Exception as e:
                 print(f"Warning: Could not cast column {col} during add_expense. Error: {e}")

    updated_df = pd.concat([df, new_expense], ignore_index=True)
    return _save_data(updated_df, EXPENSES_FILE)

# Example of how to potentially initialize if needed (though handled by _load_csv_safe returning empty DF)
# def initialize_if_needed():
#     from initialize_data import initialize_data_files # Be careful with circular imports
#     # Check if files exist, if not, call initialize
#     if not all(os.path.exists(f) for f in [PROPERTIES_FILE, BOOKINGS_FILE, EXPENSES_FILE]):
#          print("One or more data files missing, attempting initialization...")
#          initialize_data_files()

# --- Optional: Add functions for updating/deleting data later ---

