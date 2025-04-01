import pandas as pd
import os
import streamlit as st
import sqlite3
from datetime import date, timedelta, datetime
import calendar

# Define the directory where data files are stored (relative to this script)
# Assuming src/data_manager.py and data/ are siblings under the project root
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DB_FILE = os.path.join(DATA_DIR, "house_renter.db")

# Define table names and expected columns (useful for reference and potential validation)
PROPERTIES_TABLE = 'properties'
PROPERTIES_COLS = ['id', 'name', 'address', 'owner']

BOOKINGS_TABLE = 'bookings'
BOOKINGS_COLS = ["id", "property_id", "tenant_name", "start_date", "end_date", "rent_amount", "rent_currency", "source", "commission_paid", "commission_currency", "notes"]
BOOKINGS_DATE_COLS = ["start_date", "end_date"] # Columns to parse as dates when reading

EXPENSES_TABLE = 'expenses'
EXPENSES_COLS = ["id", "property_id", "expense_date", "category", "amount", "currency", "description"]
EXPENSES_DATE_COLS = ["expense_date"] # Columns to parse as dates when reading

# --- DATA-004: Define Data Constants ---
BOOKING_SOURCES = ['Personal', 'Booking.com', 'Airbnb', 'Other']
EXPENSE_CATEGORIES = ['Cleaning', 'Maintenance', 'Utilities', 'Service Fee', 'Taxes', 'Insurance', 'Other']
CURRENCIES = ['ARS', 'USD', 'EUR']


# --- Database Helper Functions ---

def _ensure_data_dir():
    """Ensures the data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created data directory: {DATA_DIR}")

def _get_db_connection():
    """Establishes a connection to the SQLite database."""
    _ensure_data_dir() # Ensure directory exists before connecting
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    # Use Row factory for easier access to columns by name (optional but convenient)
    # conn.row_factory = sqlite3.Row
    return conn

def _initialize_database():
    """Creates the database tables if they don't exist."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Properties Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {PROPERTIES_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            owner TEXT
        )
        """)

        # Bookings Table
        # Storing dates as TEXT in ISO format (YYYY-MM-DD) is common and simple
        # Storing amounts as REAL
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {BOOKINGS_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER NOT NULL,
            tenant_name TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            rent_amount REAL,
            rent_currency TEXT,
            source TEXT,
            commission_paid REAL,
            commission_currency TEXT,
            notes TEXT,
            FOREIGN KEY (property_id) REFERENCES {PROPERTIES_TABLE}(id) ON DELETE CASCADE
        )
        """)

        # Expenses Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {EXPENSES_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER NOT NULL,
            expense_date TEXT NOT NULL,
            category TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (property_id) REFERENCES {PROPERTIES_TABLE}(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
        print("Database tables checked/initialized successfully.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
        st.error(f"Database initialization failed: {e}")
    finally:
        if conn:
            conn.close()

# Call initialization once when the module is loaded
_initialize_database()


# --- DATA-002: Implement Data Loading Functions ---

@st.cache_data
def load_properties():
    """Loads property data from the database."""
    print("Loading properties from DB...") # Add print statement to observe caching
    try:
        conn = _get_db_connection()
        # Read data using pandas read_sql_query
        df = pd.read_sql_query(f"SELECT * FROM {PROPERTIES_TABLE}", conn)
        # Ensure 'id' column is integer type (pandas read_sql usually handles this, but Int64 is safer for potential nulls if needed)
        if 'id' in df.columns:
            df['id'] = df['id'].astype(pd.Int64Dtype())
        return df
    except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
        print(f"Error loading properties: {e}")
        st.error(f"Failed to load properties: {e}")
        # Return empty DataFrame with correct columns on error
        return pd.DataFrame(columns=PROPERTIES_COLS)
    finally:
        if conn:
            conn.close()


@st.cache_data
def load_bookings():
    """Loads booking data from the database, parsing dates."""
    print("Loading bookings from DB...") # Add print statement to observe caching
    try:
        conn = _get_db_connection()
        # Use parse_dates with read_sql_query
        df = pd.read_sql_query(f"SELECT * FROM {BOOKINGS_TABLE}", conn, parse_dates=BOOKINGS_DATE_COLS)
        # Ensure integer types for IDs
        if 'id' in df.columns:
            df['id'] = df['id'].astype(pd.Int64Dtype())
        if 'property_id' in df.columns:
            df['property_id'] = df['property_id'].astype(pd.Int64Dtype())
        # Ensure numeric types for amounts (read_sql usually handles REAL to float)
        # No explicit conversion needed unless specific handling of errors/nulls required beyond default
        return df
    except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
        print(f"Error loading bookings: {e}")
        st.error(f"Failed to load bookings: {e}")
        return pd.DataFrame(columns=BOOKINGS_COLS) # Return empty DataFrame on error
    finally:
        if conn:
            conn.close()


@st.cache_data
def load_expenses():
    """Loads expense data from the database, parsing dates."""
    print("Loading expenses from DB...") # Add print statement to observe caching
    try:
        conn = _get_db_connection()
        df = pd.read_sql_query(f"SELECT * FROM {EXPENSES_TABLE}", conn, parse_dates=EXPENSES_DATE_COLS)
        # Ensure integer types for IDs
        if 'id' in df.columns:
            df['id'] = df['id'].astype(pd.Int64Dtype())
        if 'property_id' in df.columns:
            df['property_id'] = df['property_id'].astype(pd.Int64Dtype())
        # Ensure numeric type for amount
        return df
    except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
        print(f"Error loading expenses: {e}")
        st.error(f"Failed to load expenses: {e}")
        return pd.DataFrame(columns=EXPENSES_COLS) # Return empty DataFrame on error
    finally:
        if conn:
            conn.close()


# --- DATA-003: Implement Data Saving/Updating Functions ---

def add_property(name: str, address: str, owner: str) -> bool:
    """Adds a new property to the database."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        sql = f"INSERT INTO {PROPERTIES_TABLE} (name, address, owner) VALUES (?, ?, ?)"
        cursor.execute(sql, (name, address, owner))
        conn.commit()
        load_properties.clear() # Clear cache after modification
        print(f"Property '{name}' added successfully.")
        return True
    except sqlite3.Error as e:
        print(f"Error adding property: {e}")
        st.error(f"Failed to add property '{name}': {e}")
        if conn:
            conn.rollback() # Rollback changes on error
        return False
    finally:
        if conn:
            conn.close()

def update_property(property_id: int, name: str, address: str, owner: str) -> bool:
    """Updates an existing property in the database."""
    conn = None
    if property_id is None:
         st.error("Invalid property ID for update.")
         return False
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        sql = f"UPDATE {PROPERTIES_TABLE} SET name = ?, address = ?, owner = ? WHERE id = ?"
        cursor.execute(sql, (name, address, owner, int(property_id)))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Warning: No property found with ID {property_id} to update.")
            st.warning(f"No property found with ID {property_id} to update.")
            return False # Indicate that no row was updated
        else:
            load_properties.clear() # Clear cache after successful modification
            print(f"Property ID {property_id} updated successfully.")
            return True
    except (sqlite3.Error, ValueError) as e: # Catch ValueError for int conversion
        print(f"Error updating property ID {property_id}: {e}")
        st.error(f"Failed to update property ID {property_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def add_booking(property_id: int, tenant_name: str, start_date, end_date,
                rent_amount: float, rent_currency: str, source: str,
                commission_paid: float = None, commission_currency: str = None, notes: str = None) -> bool:
    """Adds a new booking to the database."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        sql = f"""
        INSERT INTO {BOOKINGS_TABLE}
        (property_id, tenant_name, start_date, end_date, rent_amount, rent_currency, source, commission_paid, commission_currency, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        # Convert dates to ISO format strings for storage
        start_date_str = pd.to_datetime(start_date).strftime('%Y-%m-%d')
        end_date_str = pd.to_datetime(end_date).strftime('%Y-%m-%d')

        cursor.execute(sql, (
            int(property_id), tenant_name, start_date_str, end_date_str,
            rent_amount, rent_currency, source, commission_paid, commission_currency, notes
        ))
        conn.commit()
        load_bookings.clear() # Clear cache
        print(f"Booking for property ID {property_id} added successfully.")
        return True
    except (sqlite3.Error, ValueError) as e:
        print(f"Error adding booking: {e}")
        st.error(f"Failed to add booking: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def add_expense(property_id: int, expense_date, category: str, amount: float, currency: str, description: str = None) -> bool:
    """Adds a new expense to the database."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        sql = f"""
        INSERT INTO {EXPENSES_TABLE}
        (property_id, expense_date, category, amount, currency, description)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        # Convert date to ISO format string
        expense_date_str = pd.to_datetime(expense_date).strftime('%Y-%m-%d')

        cursor.execute(sql, (
            int(property_id), expense_date_str, category, amount, currency, description
        ))
        conn.commit()
        load_expenses.clear() # Clear cache
        print(f"Expense for property ID {property_id} added successfully.")
        return True
    except (sqlite3.Error, ValueError) as e:
        print(f"Error adding expense: {e}")
        st.error(f"Failed to add expense: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


# --- Optional: Add functions for updating/deleting data later ---
# Placeholder for delete_property, delete_booking, delete_expense if needed
# Example:
# def delete_property(property_id: int) -> bool:
#     conn = None
#     try:
#         conn = _get_db_connection()
#         cursor = conn.cursor()
#         # Ensure foreign key constraints are handled (e.g., ON DELETE CASCADE)
#         # or delete related bookings/expenses first if necessary.
#         sql = f"DELETE FROM {PROPERTIES_TABLE} WHERE id = ?"
#         cursor.execute(sql, (int(property_id),))
#         conn.commit()
#         if cursor.rowcount == 0:
#             print(f"Warning: No property found with ID {property_id} to delete.")
#             st.warning(f"No property found with ID {property_id} to delete.")
#             return False
#         else:
#             load_properties.clear()
#             load_bookings.clear() # Clear related data caches too
#             load_expenses.clear()
#             print(f"Property ID {property_id} deleted successfully.")
#             return True
#     except (sqlite3.Error, ValueError) as e:
#         print(f"Error deleting property ID {property_id}: {e}")
#         st.error(f"Failed to delete property ID {property_id}: {e}")
#         if conn:
#             conn.rollback()
#         return False
#     finally:
#         if conn:
#             conn.close()


# --- DATA-005: Implement function to get first free date for a property ---
# This function relies on load_bookings(), which now reads from the DB.
# The logic remains the same as it operates on the resulting DataFrame.
def get_first_available_date_for_property(property_id: int):
    """
    Finds the first available date for a given property, starting from today.
    Uses the load_bookings function which now reads from the database.

    Args:
        property_id (int): The ID of the property to check.

    Returns:
        datetime.date: The first available date, or today's date if no bookings.
    """
    bookings_df = load_bookings() # Gets data from DB via cached function
    today_date = pd.to_datetime('today').normalize() # Normalize to remove time part

    # Ensure property_id is the correct type for comparison with DataFrame column
    try:
        property_id_int = int(property_id)
    except (ValueError, TypeError):
         st.error(f"Invalid property ID type: {property_id}")
         return today_date.date() # Or handle error differently

    property_bookings = bookings_df[bookings_df['property_id'] == property_id_int].copy() # Avoid SettingWithCopyWarning
    if property_bookings.empty:
        return today_date.date() # If no bookings, today is free

    # Ensure dates are datetime objects (should be handled by load_bookings parse_dates)
    # and sort by start_date
    property_bookings = property_bookings.sort_values(by='start_date')

    available_date = today_date

    for _, booking in property_bookings.iterrows():
        # Ensure comparison is between datetime objects
        booking_start = pd.to_datetime(booking['start_date']).normalize()
        booking_end = pd.to_datetime(booking['end_date']).normalize()

        # Check if the current available slot is before the next booking starts
        # Note: Booking end date is the check-out day, so the property is free *on* that day.
        # We look for a gap *before* booking_start.
        if available_date < booking_start:
            return available_date.date() # Found a gap

        # If the current available date is within or before the booking,
        # the next possible available date is the day *after* the booking ends.
        # The end date itself is the check-out day, so it's available the next day.
        available_date = max(available_date, booking_end) # No +1 needed as end_date is check-out

    # If loop finishes, the first available date is after the last booking found
    return available_date.date()


# --- Calendar Helper Functions (depend on load_bookings) ---

def get_occupied_dates(property_id: int, bookings_df: pd.DataFrame) -> set:
    """
    Gets a set of all dates occupied by bookings for a specific property.
    Operates on the DataFrame returned by load_bookings.

    Args:
        property_id: The ID of the property.
        bookings_df: DataFrame containing booking data (typically from load_bookings).

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
        print(f"Invalid property ID type for get_occupied_dates: {property_id}")
        return occupied # Invalid property ID type

    # Filter bookings for the specific property
    # Ensure dates are datetime objects (should be handled by load_bookings)
    prop_bookings = bookings_df[bookings_df['property_id'] == property_id_int].copy()
    if prop_bookings.empty:
        return occupied

    # Ensure date columns are datetime type if not already
    prop_bookings['start_date'] = pd.to_datetime(prop_bookings['start_date'])
    prop_bookings['end_date'] = pd.to_datetime(prop_bookings['end_date'])

    for _, booking in prop_bookings.iterrows():
        # .date() converts Timestamp to standard library date object
        current_date = booking['start_date'].date()
        # Booking end date is the check-out day, so the *last occupied night* is end_date - 1 day.
        # The loop should go up to, but not include, the end_date.
        end_date_exclusive = booking['end_date'].date()
        while current_date < end_date_exclusive:
            occupied.add(current_date)
            current_date += timedelta(days=1)
    return occupied

# --- Calendar HTML Generation (No changes needed, purely presentation) ---

def generate_month_calendar_html(year: int, month: int, occupied_dates: set, today: date) -> str:
    """
    Generates an HTML calendar for a given month, marking occupied/past dates.
    """
    cal = calendar.monthcalendar(year, month)
    month_name = date(year, month, 1).strftime('%B %Y')

    # Use f-string for cleaner HTML construction
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

                # Ensure proper HTML escaping if titles could contain special chars, though unlikely here.
                html += f"<td class='{cell_class}' title='{current_date.strftime('%Y-%m-%d')}: {title}'>{day}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def get_calendar_css() -> str:
    """Returns the CSS styling for the availability calendar."""
    # Using triple quotes for multi-line string is cleaner
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
            width: 14.28%; /* Approx 1/7th */
            box-sizing: border-box; /* Include padding/border in width */
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
             padding-left: 15px; /* Add left padding too for balance */
        }
        /* Ensure h6 styling is reasonable */
        h6 {
            text-align: center;
            margin-top: 0.5em;
            margin-bottom: 0.5em;
            font-size: 1em;
        }
    </style>
    """
# --- End of functions to add ---

# --- Liquidation Specific Functions ---

# Define the liquidation table name
LIQUIDATIONS_TABLE = 'liquidations'
LIQUIDATION_COLS = ["year", "month", "type", "identifier", "commission_percentage", "total_income", "total_expenses", "commission_amount", "owner_net", "calculation_timestamp"]

def _ensure_liquidations_table():
    """Ensures the liquidations table exists in the database."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {LIQUIDATIONS_TABLE} (
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                type TEXT NOT NULL,
                identifier TEXT NOT NULL,
                commission_percentage REAL,
                total_income REAL,
                total_expenses REAL,
                commission_amount REAL,
                owner_net REAL,
                calculation_timestamp TEXT
            )
        """)
        conn.commit()
        print("Liquidations table checked/initialized successfully.")
    except sqlite3.Error as e:
        print(f"Error initializing liquidations table: {e}")
    finally:
        if conn:
            conn.close()

# Call the function to ensure the table exists
_ensure_liquidations_table()


def load_liquidation(year, month, liq_type, identifier):
    """Loads a specific liquidation report from the database."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        sql = f"""
            SELECT * FROM {LIQUIDATIONS_TABLE}
            WHERE year = ? AND month = ? AND type = ? AND identifier = ?
        """
        cursor.execute(sql, (year, month, liq_type, identifier))
        row = cursor.fetchone()

        if row:
            # Convert row to dictionary
            data = {}
            for i, col in enumerate(LIQUIDATION_COLS):
                data[col] = row[i]

            # Basic validation/type conversion (already done by sqlite, but good to check)
            data['year'] = int(data['year'])
            data['month'] = int(data['month'])
            data['commission_percentage'] = float(data['commission_percentage'])
            data['total_income'] = float(data['total_income'])
            data['total_expenses'] = float(data['total_expenses'])
            data['commission_amount'] = float(data['commission_amount'])
            data['owner_net'] = float(data['owner_net'])

            # Handle calculation_timestamp (convert from string)
            if data['calculation_timestamp']:
                try:
                    data['calculation_timestamp'] = pd.to_datetime(data['calculation_timestamp']).isoformat()
                except:
                    print(f"Warning: Invalid timestamp format. Setting to None.")
                    data['calculation_timestamp'] = None
            return data
        else:
            print("Liquidation not found in database.")
            return None
    except sqlite3.Error as e:
        print(f"Error loading liquidation from database: {e}")
        return None
    finally:
        if conn:
            conn.close()


def save_liquidation(data, year, month, liq_type, identifier):
    """Saves the liquidation data (dictionary) to the database.
    If a liquidation already exists for that year, month, type, and identifier, it will be updated.
    Otherwise, a new record will be inserted.
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Convert timestamp to string format for database storage
        timestamp = data.get('calculation_timestamp')
        # Ensure timestamp is properly formatted for SQLite (ISO format)
        timestamp_str = pd.to_datetime(timestamp).isoformat() if timestamp else None

        # Attempt to update the record
        sql_update = f"""
            UPDATE {LIQUIDATIONS_TABLE}
            SET commission_percentage = ?,
                total_income = ?,
                total_expenses = ?,
                commission_amount = ?,
                owner_net = ?,
                calculation_timestamp = ?
            WHERE year = ? AND month = ? AND type = ? AND identifier = ?
        """
        cursor.execute(sql_update, (
            data['commission_percentage'], data['total_income'], data['total_expenses'],
            data['commission_amount'], data['owner_net'], timestamp_str,
            year, month, liq_type, identifier
        ))

        # If no rows were updated, insert a new record
        if cursor.rowcount == 0:
            sql_insert = f"""
                INSERT INTO {LIQUIDATIONS_TABLE}
                (year, month, type, identifier, commission_percentage, total_income, total_expenses, commission_amount, owner_net, calculation_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_insert, (
                year, month, liq_type, identifier,
                data['commission_percentage'], data['total_income'], data['total_expenses'],
                data['commission_amount'], data['owner_net'], timestamp_str
            ))

        conn.commit()
        print("Liquidation saved to database successfully.")
        return True
    except sqlite3.Error as e:
        print(f"Error saving liquidation to database: {e}")
        if conn:
            conn.rollback()
        return False
    except ValueError as e:
        print(f"Error formatting timestamp: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
