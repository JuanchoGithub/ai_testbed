from flask import Flask, request
import re
from datetime import datetime
import os
import sys
import pandas as pd  # Needed for dummy data_manager if import fails
import telebot  # Import the Telebot library

# Replace with your actual Telegram bot token
TELEGRAM_BOT_TOKEN = ""  #os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


# Add the parent directory (project root) to the Python path
# This allows importing modules from the 'house_renter' directory (like data_manager)
# Assumes this script is run from within the 'house_renter' directory or the project root is configured in PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
# If whatsapp.py is directly inside house_renter, the parent is the project root
# If whatsapp.py is in a subdirectory, adjust accordingly (e.g., os.path.dirname(project_root))
# Assuming whatsapp.py is inside house_renter, project_root is correct.
# Let's adjust assuming house_renter is the main package directory
# sys.path.insert(0, os.path.dirname(project_root)) # Add parent of house_renter dir
# Or more directly if structure is known:
# sys.path.insert(0, os.path.join(project_root, '..')) # If whatsapp.py is in house_renter/

# Assuming data_manager.py is in the same directory (house_renter)
try:
    from house_renter import data_manager as dm

    print("Successfully imported data_manager.")
except ImportError as e:
    print(f"Error importing data_manager: {e}")
    print("Attempting to define a dummy data_manager for basic functionality.")
    # Define dummy functions or raise an error if essential
    class DummyDataManager:
        def add_booking(self, *args, **kwargs):
            print("DummyDataManager: add_booking called")
            # Simulate failure unless specific conditions met for testing
            return False

        CURRENCIES = ['USD', 'EUR', 'ARS', 'XXX']  # Add XXX for testing
        BOOKING_SOURCES = ['Personal', 'Booking.com', 'Airbnb', 'Other']

        def load_properties(self):
            print("DummyDataManager: load_properties called")
            # Return an empty DataFrame or one with sample data if pandas is available
            try:
                return pd.DataFrame(
                    {'id': [1, 2], 'name': ['Dummy Property 1', 'Dummy Property 2']})
            except NameError:  # If pandas failed to import
                return {'id': [], 'name': []}  # Fallback to dict if no pandas

        def get_db_connection(self):
            return None  # Avoid database operations

        def _initialize_database(self):
            pass  # Avoid database operations

    dm = DummyDataManager()
    # Check if pandas is available for the dummy load_properties
    try:
        import pandas as pd
    except ImportError:
        print("Warning: pandas not found. Dummy property validation will be limited.")


# app = Flask(__name__) # No flask needed for telegram

# --- Helper Functions ---

def get_property_id_from_input(prop_id_str: str) -> int | None:
    """
    Validates if the property ID exists in the database.
    Returns the integer ID if valid, otherwise None.
    """
    try:
        prop_id = int(prop_id_str)
        properties_df = dm.load_properties()

        # Handle case where dummy dm returns a dict or list
        if isinstance(properties_df, pd.DataFrame):
            if properties_df.empty or prop_id not in properties_df['id'].unique():
                print(f"Property ID {prop_id} not found in DataFrame.")
                return None
        elif isinstance(properties_df, dict) and 'id' in properties_df:
            if prop_id not in properties_df['id']:
                print(f"Property ID {prop_id} not found in dummy data.")
                return None
        elif properties_df is None:  # Handle potential None return on error
            print("Could not load properties for validation.")
            return None  # Cannot validate
        else:
            print("Warning: Unexpected format for properties data during validation.")
            # Cautiously allow if format is unknown, or return None
            # For safety, let's return None if we can't validate
            return None

        return prop_id  # ID seems valid
    except (ValueError, TypeError):
        print(f"Invalid format for property ID: {prop_id_str}")
        return None
    except Exception as e:  # Catch potential errors during property loading
        print(f"Error during property ID validation: {e}")
        return None


# --- Telegram Handler ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handles the /start and /help commands."""
    help_text = "Hi there! I'm a bot to help manage house bookings.\n\n" \
                "To add a booking, use the following format:\n" \
                "`add booking property_id=[ID] tenant=\"[Tenant Name]\" start=YYYY-MM-DD end=YYYY-MM-DD amount=[Number] currency=[CUR] source=[Source Name]`\n\n" \
                "*Example:*\n" \
                "`add booking property_id=1 tenant=\"Alice Wonderland\" start=2024-12-20 end=2024-12-27 amount=700 currency=USD source=Airbnb`\n\n" \
                "You can also add optional notes at the end:\n" \
                "`... source=Airbnb notes=\"Late check-in requested\"`"
    bot.reply_to(message, help_text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handles all incoming messages."""
    incoming_msg = message.text.strip()
    chat_id = message.chat.id

    print(f"Received message from {chat_id}: \"{incoming_msg}\"")

    response_text = ""

    # --- Command Parsing ---
    # Command: add booking property_id=ID tenant="Tenant Name" start=YYYY-MM-DD end=YYYY-MM-DD amount=NUM currency=CUR source=Source [notes="Optional notes"]
    add_booking_pattern = re.compile(
        r"add booking\s+"
        r"property_id=(\d+)\s+"
        r"tenant=\"(.*?)\"\s+"
        r"start=(\d{4}-\d{2}-\d{2})\s+"
        r"end=(\d{4}-\d{2}-\d{2})\s+"
        r"amount=([\d.]+)\s+"
        r"currency=([A-Z]{3})\s+"
        r"source=([\w\s.-]+)"  # Allow words, spaces, dots, hyphens in source
        r"(?:\s+notes=\"(.*?)\")?",  # Optional notes field
        re.IGNORECASE
    )

    match = add_booking_pattern.match(incoming_msg)

    if match:
        try:
            # Extract data
            property_id_str = match.group(1)
            tenant_name = match.group(2)
            start_date_str = match.group(3)
            end_date_str = match.group(4)
            rent_amount_str = match.group(5)
            rent_currency = match.group(6).upper()
            source = match.group(7).strip()
            notes = match.group(8).strip() if match.group(8) else None

            # --- Validation ---
            property_id = get_property_id_from_input(property_id_str)
            if property_id is None:
                # Try to load properties again to give a better error message
                props = dm.load_properties()
                valid_ids = []
                if isinstance(props, pd.DataFrame):
                    valid_ids = props['id'].tolist()
                elif isinstance(props, dict):
                    valid_ids = props.get('id', [])
                raise ValueError(
                    f"Invalid or non-existent property ID: {property_id_str}. Valid IDs: {valid_ids}")

            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if start_date >= end_date:
                raise ValueError("Start date must be before end date.")
            # Basic check: Ensure start date is not excessively in the past? (Optional)
            # if start_date < (datetime.now().date() - timedelta(days=365)):
            #     raise ValueError("Start date seems too far in the past.")

            rent_amount = float(rent_amount_str)
            if rent_amount < 0:
                raise ValueError("Rent amount cannot be negative.")

            if rent_currency not in dm.CURRENCIES:
                raise ValueError(
                    f"Invalid currency: {rent_currency}. Allowed: {', '.join(dm.CURRENCIES)}")

            # Validate source (optional, could just accept any string)
            if source not in dm.BOOKING_SOURCES:
                print(f"Warning: Source '{source}' is not in the standard list: {dm.BOOKING_SOURCES}")
                # Decide whether to reject or accept non-standard sources. Let's accept for now.
                # raise ValueError(f"Invalid source: {source}. Allowed: {', '.join(dm.BOOKING_SOURCES)}")

            # --- Add Booking via Data Manager ---
            print(
                f"Attempting to add booking: PropID={property_id}, Tenant={tenant_name}, Start={start_date}, End={end_date}, Amount={rent_amount} {rent_currency}, Source={source}, Notes={notes}")
            success = dm.add_booking(
                property_id=property_id,
                tenant_name=tenant_name,
                start_date=start_date,
                end_date=end_date,
                rent_amount=rent_amount,
                rent_currency=rent_currency,
                source=source,
                notes=notes
                # commission_paid and commission_currency are not included in this basic command
            )

            if success:
                response_text = f"✅ Booking added successfully!\nProperty ID: {property_id}\nTenant: {tenant_name}\nDates: {start_date_str} to {end_date_str}\nRent: {rent_amount} {rent_currency}\nSource: {source}"
                if notes:
                    response_text += f"\nNotes: {notes}"

            else:
                response_text = "❌ Failed to add booking. There might have been an issue saving to the database. Please check server logs."

        except ValueError as e:
            response_text = f"⚠️ Error: {e}\nPlease check your input format."
        except Exception as e:
            print(f"An unexpected error occurred: {e}")  # Log the full error server-side
            response_text = "❌ An unexpected error occurred. Please contact the administrator."

    else:
        # --- Help Message ---
        response_text = "Hi there! To add a booking, please use the format:\n\n" \
                        "`add booking property_id=[ID] tenant=\"[Tenant Name]\" start=YYYY-MM-DD end=YYYY-MM-DD amount=[Number] currency=[CUR] source=[Source Name]`\n\n" \
                        "*Example:*\n" \
                        "`add booking property_id=1 tenant=\"Alice Wonderland\" start=2024-12-20 end=2024-12-27 amount=700 currency=USD source=Airbnb`\n\n" \
                        "You can also add optional notes at the end:\n" \
                        "`... source=Airbnb notes=\"Late check-in requested\"`"

    # Send the response
    bot.reply_to(message, response_text, parse_mode='Markdown')


# --- Main Execution ---
if __name__ == "__main__":
    # Start the Telegram bot
    print("Starting Telegram bot...")
    bot.infinity_polling()
