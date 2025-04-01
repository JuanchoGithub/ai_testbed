import pandas as pd
import os
import streamlit as st
from pandas.errors import EmptyDataError

# Define the directory where data files are stored (relative to this script)
# Assuming src/data_manager.py and data/ are siblings under the project root
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# Define data file paths and expected columns
PROPERTIES_FILE = os.path.join(DATA_DIR, "properties.csv")
PROPERTIES_COLS = ['id', 'name', 'address', 'owner'] # Add 'owner'

BOOKINGS_FILE = os.path.join(DATA_DIR, "bookings.csv")
BOOKINGS_COLS = ["id", "property_id", "tenant_name", "start_date", "end_date", "rent_amount", "rent_currency", "source", "commission_paid", "commission_currency", "notes"]
BOOKINGS_DATE_COLS = ["start_date", "end_date"]

EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.csv")
EXPENSES_COLS = ["id", "property_id", "expense_date", "category", "amount", "currency", "description"]
EXPENSES_DATE_COLS = ["expense_date"]

# --- DATA-004: Define Data Constants ---
BOOKING_SOURCES = ['Personal', 'Booking.com', 'Airbnb', 'Other']
EXPENSE_CATEGORIES = ['Cleaning', 'Maintenance', 'Utilities', 'Service Fee', 'Taxes', 'Insurance', 'Other']
CURRENCIES = ['ARS', 'USD', 'EUR']


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
        # Ensure ID columns are stored as integers, but handle potential NA for saving
        if 'id' in df.columns and pd.api.types.is_integer_dtype(df['id'].dtype):
             df['id'] = df['id'].astype(float).astype(pd.Int64Dtype()) # Convert to nullable int via float
        if 'property_id' in df.columns and pd.api.types.is_integer_dtype(df['property_id'].dtype):
             df['property_id'] = df['property_id'].astype(float).astype(pd.Int64Dtype())

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

def add_property(name: str, address: str, owner: str) -> bool:
    """Adds a new property to properties.csv."""
    df = load_properties() # df already has correct types from load_properties
    next_id = _get_next_id(df)
    new_property_data = {
        'id': next_id,
        'name': name,
        'address': address,
        'owner': owner
    }
    new_property_df = pd.DataFrame([new_property_data])

    # Ensure the new DataFrame fragment has the same dtypes as the loaded DataFrame
    if not df.empty:
        for col, dtype in df.dtypes.items():
            if col in new_property_df.columns:
                try:
                    new_property_df[col] = new_property_df[col].astype(dtype)
                except Exception as e:
                     print(f"Warning: Could not cast column {col} during add_property. Error: {e}")
                     # Fallback for id if needed
                     if col == 'id':
                         new_property_df[col] = new_property_df[col].astype(pd.Int64Dtype())

    elif 'id' in new_property_df.columns: # Handle case where df is empty but we add the first row
         new_property_df['id'] = new_property_df['id'].astype(pd.Int64Dtype())
         # Other columns will likely be object/string by default, which is fine

    updated_df = pd.concat([df, new_property_df], ignore_index=True)
    return _save_data(updated_df, PROPERTIES_FILE)

def update_property(property_id: int, name: str, address: str, owner: str) -> bool:
    """Updates an existing property in properties.csv."""
    df = load_properties()

    # Find the index of the property to update
    # Ensure property_id is treated as the same type as the 'id' column (Int64)
    try:
        property_id_int = pd.NA if property_id is None else int(property_id)
        idx = df.index[df['id'] == property_id_int].tolist()
    except ValueError:
        st.error(f"ID de propiedad inválido: {property_id}")
        return False


    if not idx:
        print(f"Error: Property with ID {property_id} not found for update.")
        st.error(f"Error: No se encontró la propiedad con ID {property_id} para actualizar.")
        return False

    if len(idx) > 1:
        # This shouldn't happen with unique IDs, but good to check
        print(f"Error: Found multiple properties with ID {property_id}. Data integrity issue.")
        st.error(f"Error: Se encontraron múltiples propiedades con ID {property_id}. Problema de integridad de datos.")
        return False

    property_index = idx[0]

    # Update the property details in the DataFrame
    df.loc[property_index, 'name'] = name
    df.loc[property_index, 'address'] = address
    df.loc[property_index, 'owner'] = owner

    # Save the updated dataframe
    return _save_data(df, PROPERTIES_FILE)


def add_booking(property_id: int, tenant_name: str, start_date, end_date,
                rent_amount: float, rent_currency: str, source: str, commission_paid: float = None, commission_currency: str = None, notes: str = None):
    """Adds a new booking to bookings.csv."""
    df = load_bookings()
    next_id = _get_next_id(df)

    # Ensure dates are in a consistent format (e.g., pd.Timestamp) if not already
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    new_booking_data = {
        "id": next_id,
        "property_id": property_id,
        "tenant_name": tenant_name,
        "start_date": start_date,
        "end_date": end_date,
        "rent_amount": rent_amount,
        "rent_currency": rent_currency,
        "source": source,
        "commission_paid": commission_paid,
        "commission_currency": commission_currency,
        "notes": notes
    }
    new_booking_df = pd.DataFrame([new_booking_data])

    # Ensure the new DataFrame fragment has the same dtypes as the loaded DataFrame
    if not df.empty:
        for col, dtype in df.dtypes.items():
            if col in new_booking_df.columns:
                try:
                    # Special handling for nullable integers
                    if pd.api.types.is_integer_dtype(dtype) and not pd.api.types.is_float_dtype(new_booking_df[col].dtype):
                         # Attempt conversion, allowing NA
                         new_booking_df[col] = pd.to_numeric(new_booking_df[col], errors='coerce').astype(dtype)
                    else:
                        new_booking_df[col] = new_booking_df[col].astype(dtype)
                except Exception as e:
                    print(f"Warning: Could not cast column {col} during add_booking. Error: {e}")
                    # Fallback for id/property_id if needed
                    if col in ['id', 'property_id']:
                        new_booking_df[col] = new_booking_df[col].astype(pd.Int64Dtype())
    else: # Handle case where df is empty
        if 'id' in new_booking_df.columns: new_booking_df['id'] = new_booking_df['id'].astype(pd.Int64Dtype())
        if 'property_id' in new_booking_df.columns: new_booking_df['property_id'] = new_booking_df['property_id'].astype(pd.Int64Dtype())
        if 'start_date' in new_booking_df.columns: new_booking_df['start_date'] = pd.to_datetime(new_booking_df['start_date'])
        if 'end_date' in new_booking_df.columns: new_booking_df['end_date'] = pd.to_datetime(new_booking_df['end_date'])
        if 'rent_amount' in new_booking_df.columns: new_booking_df['rent_amount'] = pd.to_numeric(new_booking_df['rent_amount'], errors='coerce')
        if 'commission_paid' in new_booking_df.columns: new_booking_df['commission_paid'] = pd.to_numeric(new_booking_df['commission_paid'], errors='coerce')


    updated_df = pd.concat([df, new_booking_df], ignore_index=True)
    return _save_data(updated_df, BOOKINGS_FILE)

def add_expense(property_id: int, expense_date, category: str, amount: float, currency: str, description: str = None):
    """Adds a new expense to expenses.csv."""
    df = load_expenses()
    next_id = _get_next_id(df)

    # Ensure date is a pd.Timestamp
    expense_date = pd.to_datetime(expense_date)

    new_expense_data = {
        "id": next_id,
        "property_id": property_id,
        "expense_date": expense_date,
        "category": category,
        "amount": amount,
        "currency": currency,
        "description": description
    }
    new_expense_df = pd.DataFrame([new_expense_data])

    # Ensure the new DataFrame fragment has the same dtypes as the loaded DataFrame
    if not df.empty:
        for col, dtype in df.dtypes.items():
            if col in new_expense_df.columns:
                try:
                     # Special handling for nullable integers
                    if pd.api.types.is_integer_dtype(dtype) and not pd.api.types.is_float_dtype(new_expense_df[col].dtype):
                         new_expense_df[col] = pd.to_numeric(new_expense_df[col], errors='coerce').astype(dtype)
                    else:
                        new_expense_df[col] = new_expense_df[col].astype(dtype)
                except Exception as e:
                    print(f"Warning: Could not cast column {col} during add_expense. Error: {e}")
                    if col in ['id', 'property_id']:
                        new_expense_df[col] = new_expense_df[col].astype(pd.Int64Dtype())
    else: # Handle case where df is empty
        if 'id' in new_expense_df.columns: new_expense_df['id'] = new_expense_df['id'].astype(pd.Int64Dtype())
        if 'property_id' in new_expense_df.columns: new_expense_df['property_id'] = new_expense_df['property_id'].astype(pd.Int64Dtype())
        if 'expense_date' in new_expense_df.columns: new_expense_df['expense_date'] = pd.to_datetime(new_expense_df['expense_date'])
        if 'amount' in new_expense_df.columns: new_expense_df['amount'] = pd.to_numeric(new_expense_df['amount'], errors='coerce')


    updated_df = pd.concat([df, new_expense_df], ignore_index=True)
    return _save_data(updated_df, EXPENSES_FILE)

# Example of how to potentially initialize if needed (though handled by _load_csv_safe returning empty DF)
# def initialize_if_needed():
#     from initialize_data import initialize_data_files # Be careful with circular imports
#     # Check if files exist, if not, call initialize
#     if not all(os.path.exists(f) for f in [PROPERTIES_FILE, BOOKINGS_FILE, EXPENSES_FILE]):
#          print("One or more data files missing, attempting initialization...")
#          initialize_data_files()

# --- Optional: Add functions for updating/deleting data later ---
# Placeholder for delete_property, delete_booking, delete_expense if needed

# --- DATA-005: Implement function to get first free date for a property ---
def get_first_available_date_for_property(property_id: int):
    """
    Finds the first available date for a given property, starting from today.

    Args:
        property_id (int): The ID of the property to check.

    Returns:
        datetime.date: The first available date, or today's date if no bookings.
    """
    bookings_df = load_bookings()
    today_date = pd.to_datetime('today').normalize() # Normalize to remove time part

    property_bookings = bookings_df[bookings_df['property_id'] == property_id].copy() # Avoid SettingWithCopyWarning
    if property_bookings.empty:
        return today_date.date() # If no bookings, today is free

    # Convert start_date and end_date to datetime objects and sort by start_date
    property_bookings.loc[:, 'start_date'] = pd.to_datetime(property_bookings['start_date'])
    property_bookings.loc[:, 'end_date'] = pd.to_datetime(property_bookings['end_date'])
    property_bookings = property_bookings.sort_values(by='start_date')

    available_date = today_date

    for _, booking in property_bookings.iterrows():
        booking_start = booking['start_date'].normalize()
        booking_end = booking['end_date'].normalize()

        if available_date <= booking_start:
            return available_date.date() # Found a gap before this booking
        else:
            available_date = max(available_date, booking_end + pd.Timedelta(days=1)) # Update to day after booking end

    return available_date.date() # No gaps found, return date after all bookings


# --- Add these functions to your data_manager.py or a utils.py ---
from datetime import date, timedelta, datetime
import calendar
import pandas as pd

def get_occupied_dates(property_id: int, bookings_df: pd.DataFrame) -> set:
    """
    Gets a set of all dates occupied by bookings for a specific property.

    Args:
        property_id: The ID of the property.
        bookings_df: DataFrame containing all bookings.

    Returns:
        A set of date objects representing occupied dates.
    """
    occupied = set()
    if bookings_df.empty or 'property_id' not in bookings_df.columns:
        return occupied

    # Ensure property_id is the correct type for comparison
    try:
        property_id_int = int(property_id)
    except (ValueError, TypeError):
        return occupied # Invalid property ID type

    # Filter bookings for the specific property and ensure dates are datetime objects
    prop_bookings = bookings_df[bookings_df['property_id'] == property_id_int].copy()
    if prop_bookings.empty:
        return occupied

    prop_bookings['start_date'] = pd.to_datetime(prop_bookings['start_date'])
    prop_bookings['end_date'] = pd.to_datetime(prop_bookings['end_date'])

    for _, booking in prop_bookings.iterrows():
        current_date = booking['start_date'].date()
        # Booking end date is the check-out day, so it's *not* occupied
        end_date_exclusive = booking['end_date'].date()
        while current_date < end_date_exclusive:
            occupied.add(current_date)
            current_date += timedelta(days=1)
    return occupied

def generate_month_calendar_html(year: int, month: int, occupied_dates: set, today: date) -> str:
    """
    Generates an HTML calendar for a given month, marking occupied/past dates.
    """
    cal = calendar.monthcalendar(year, month)
    month_name = date(year, month, 1).strftime('%B %Y')

    html = f"<h6>{month_name}</h6>"
    html += "<table class='availability-calendar'>"
    html += "<tr><th>Mo</th><th>Tu</th><th>We</th><th>Th</th><th>Fr</th><th>Sa</th><th>Su</th></tr>"

    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>" # Empty cell for days outside the month
            else:
                current_date = date(year, month, day)
                cell_class = "available"
                title = "Available"
                if current_date < today:
                    cell_class = "past"
                    title = "Past date"
                elif current_date in occupied_dates:
                    cell_class = "occupied"
                    title = "Occupied"

                html += f"<td class='{cell_class}' title='{current_date.strftime('%Y-%m-%d')}: {title}'>{day}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def get_calendar_css() -> str:
    """Returns the CSS styling for the availability calendar."""
    return """
    <style>
        .availability-calendar {
            width: 100%; /* Adjust as needed */
            border-collapse: collapse;
            margin-bottom: 1em;
            font-size: 0.85em; /* Smaller font size */
        }
        .availability-calendar th, .availability-calendar td {
            border: 1px solid #ddd;
            padding: 4px; /* Reduced padding */
            text-align: center;
            height: 30px; /* Fixed height */
            width: 14%; /* Equal width */
        }
        .availability-calendar th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .availability-calendar td.occupied {
            background-color: #ff7f7f; /* Lighter Red */
            color: white;
            font-weight: bold;
        }
        .availability-calendar td.available {
            background-color: #90ee90; /* Lighter Green */
            color: #333;
        }
        .availability-calendar td.past {
            background-color: #e0e0e0; /* Grey */
            color: #888;
            text-decoration: line-through;
        }
        .availability-calendar td:empty {
            background-color: #fafafa;
            border: none;
        }
        .calendar-container {
            margin-bottom: 20px; /* Space below the calendars */
        }
        .calendar-column {
             padding-right: 15px; /* Space between columns */
        }
    </style>
    """
# --- End of functions to add ---