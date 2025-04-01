from flask import Flask, request
import re
from datetime import datetime, date
import os
import sys
import pandas as pd  # Needed for dummy data_manager if import fails
import telebot  # Import the Telebot library
from telebot import types

# Replace with your actual Telegram bot token
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    sys.exit(1)  # Exit if token is not set

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
    import data_manager as dm

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
        def add_property(self, property_name, owner, address): # Dummy add_property
            print(f"DummyDataManager: add_property called with name: {property_name}, owner: {owner}, address: {address}")
            return True

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

def get_property_id_from_input(property_name: str) -> int | None:
    """
    Validates if the property name exists in the database.
    Returns the integer ID if valid, otherwise None.
    """
    try:
        properties_df = dm.load_properties()

        # Handle case where dummy dm returns a dict or list
        if isinstance(properties_df, pd.DataFrame):
            if properties_df.empty or property_name not in properties_df['name'].values:
                print(f"Property Name {property_name} not found in DataFrame.")
                return None
            else:
                return properties_df[properties_df['name'] == property_name]['id'].iloc[0]

        elif isinstance(properties_df, dict) and 'name' in properties_df:
            if property_name not in properties_df['name']:
                print(f"Property Name {property_name} not found in dummy data.")
                return None
            else:
                # Assuming the 'id' and 'name' lists are aligned
                try:
                    index = properties_df['name'].index(property_name)
                    return properties_df['id'][index]
                except ValueError:
                    print(f"Property Name {property_name} found, but no corresponding ID.")
                    return None


        elif properties_df is None:  # Handle potential None return on error
            print("Could not load properties for validation.")
            return None  # Cannot validate
        else:
            print("Warning: Unexpected format for properties data during validation.")
            # Cautiously allow if format is unknown, or return None
            # For safety, let's return None if we can't validate
            return None

    except (ValueError, TypeError) as e:
        print(f"Invalid format for property Name: {property_name} - {e}")
        return None
    except Exception as e:  # Catch potential errors during property loading
        print(f"Error during property Name validation: {e}")
        return None


# --- Telegram Handler ---

# States for the booking wizard
PROPERTY_ID = 1
TENANT_NAME = 2
START_DATE = 3
END_DATE = 4
RENT_AMOUNT = 5
RENT_CURRENCY = 6
SOURCE = 7
NOTES = 8

# States for the property wizard
PROPERTY_NAME_ADD = 100
PROPERTY_OWNER_ADD = 101
PROPERTY_ADDRESS_ADD = 102


booking_data = {}  # Store booking data for each user
property_data = {} # Store property data for each user during property creation

# --- Inline Calendar ---
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

import datetime


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handles the /start and /help commands."""
    help_text = "¡Hola! Soy un bot para ayudarte a gestionar las reservas de casas.\n\n" \
                "Usa /new_booking para comenzar a agregar una reserva.\n" \
                "Usa /new_property para agregar una nueva propiedad.\n" \
                "Si tenés alguna duda, podés usar el comando /help."
    bot.reply_to(message, help_text)  # Remove parse_mode

@bot.message_handler(commands=['new_booking'])
def new_booking(message):
    """Starts the new booking wizard."""
    chat_id = message.chat.id
    booking_data[chat_id] = {}  # Initialize booking data for the user

    # Ask for property ID
    try:
        properties_df = dm.load_properties()
        if isinstance(properties_df, pd.DataFrame):
            property_names = properties_df['name'].tolist()
        elif isinstance(properties_df, dict) and 'name' in properties_df:
            property_names = properties_df['name']
        else:
            bot.reply_to(message, "No se pudieron cargar las propiedades. Intenta más tarde.")
            return

        if not property_names:
            bot.reply_to(message, "No hay propiedades disponibles. Intenta más tarde.")
            return

        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=3)  # Adjust row_width as needed
        for name in property_names:
            keyboard.add(name)

        msg = bot.reply_to(message, "Por favor, selecciona la propiedad:", reply_markup=keyboard)
        bot.register_next_step_handler(msg, process_property_name)

    except Exception as e:
        print(f"Error in new_booking: {e}")
        bot.reply_to(message, "Ocurrió un error al cargar las propiedades. Intenta más tarde.")

def process_property_name(message):
    """Processes the property name input."""
    chat_id = message.chat.id
    property_name = message.text.strip()

    property_id = get_property_id_from_input(property_name)
    if property_id is None:
        bot.reply_to(message, "Nombre de propiedad inválido. Por favor, intenta de nuevo con un nombre válido.")
        return  # Stop the wizard

    booking_data[chat_id]['property_id'] = property_id

    # Remove keyboard
    markup = types.ReplyKeyboardRemove(selective=False)

    # Ask for tenant name
    msg = bot.reply_to(message, "Ahora, ingresa el nombre del inquilino:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_tenant_name)

def process_tenant_name(message):
    """Processes the tenant name input."""
    chat_id = message.chat.id
    tenant_name = message.text.strip()
    booking_data[chat_id]['tenant_name'] = tenant_name

    calendar, step = DetailedTelegramCalendar(calendar_id=1).build()
    bot.send_message(chat_id,
                     f"Selecciona la fecha de inicio {LSTEP[step]}",
                     reply_markup=calendar)

@bot.callback_query_handler(func=DetailedTelegramCalendar().func(calendar_id=1))
def cal_start(c):
    result, key, step = DetailedTelegramCalendar(calendar_id=1).process(c.data)
    if not result and key:
        bot.edit_message_text(f"Selecciona la fecha de INICIO {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        booking_data[c.message.chat.id]['start_date'] = result
        bot.edit_message_text(f"Fecha de inicio seleccionada: {result}",
            c.message.chat.id,
            c.message.message_id)

        calendar, step = DetailedTelegramCalendar(calendar_id=2, min_date=booking_data[c.message.chat.id]['start_date']).build()
        bot.send_message(c.message.chat.id,
                        f"Selecciona la fecha de FIN {LSTEP[step]}",
                        reply_markup=calendar)

@bot.callback_query_handler(func=DetailedTelegramCalendar().func(calendar_id=2))
def cal_start(c):
    result, key, step = DetailedTelegramCalendar(calendar_id=2, min_date=booking_data[c.message.chat.id]['start_date']).process(c.data)
    if not result and key:
        bot.edit_message_text(f"Selecciona la fecha de fin {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        booking_data[c.message.chat.id]['end_date'] = result
        bot.edit_message_text(f"Fecha de fin seleccionada: {result}",
            c.message.chat.id,
            c.message.message_id)
        # Remove keyboard
        markup = types.ReplyKeyboardRemove(selective=False)

        # Ask for tenant name
        msg = bot.reply_to(c.message, "Ingresa el monto del alquiler:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_rent_amount)

def process_rent_amount(message):
    """Processes the rent amount input."""

    # Ask for rent amount
    #bot.send_message(chat_id, "Ingresa el monto del alquiler:")
    #bot.register_next_step_handler(c.message, process_rent_amount)

    chat_id = message.chat.id
    rent_amount_str = message.text.strip()

    try:
        rent_amount = float(rent_amount_str)
        if rent_amount < 0:
            raise ValueError("El monto del alquiler no puede ser negativo.")
        booking_data[chat_id]['rent_amount'] = rent_amount
    except ValueError as e:
        bot.reply_to(message, f"Monto inválido: {e}. Intenta de nuevo.")
        return

    # Ask for rent currency
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for currency in dm.CURRENCIES:
        keyboard.add(currency)
    msg = bot.reply_to(message, "Selecciona la moneda:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, process_rent_currency)

def process_rent_currency(message):
    """Processes the rent currency input."""
    chat_id = message.chat.id
    rent_currency = message.text.strip().upper()

    if rent_currency not in dm.CURRENCIES:
        bot.reply_to(message, f"Moneda inválida. Permitidas: {', '.join(dm.CURRENCIES)}. Intenta de nuevo.")
        return

    booking_data[chat_id]['rent_currency'] = rent_currency

    # Ask for source
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for source in dm.BOOKING_SOURCES:
        keyboard.add(source)
    msg = bot.reply_to(message, "Selecciona la fuente:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, process_source)

def process_source(message):
    """Processes the booking source input."""
    chat_id = message.chat.id
    source = message.text.strip()

    if source not in dm.BOOKING_SOURCES:
        print(f"Warning: Source '{source}' is not in the standard list: {dm.BOOKING_SOURCES}")

    booking_data[chat_id]['source'] = source

    # Ask for notes (optional)
    msg = bot.reply_to(message, "Ingresa notas adicionales (opcional):")
    bot.register_next_step_handler(msg, process_notes)

def process_notes(message):
    """Processes the notes input and confirms the booking."""
    chat_id = message.chat.id
    notes = message.text.strip()
    booking_data[chat_id]['notes'] = notes if notes else None

    # Confirm booking
    confirm_booking(message)

def confirm_booking(message):
    """Confirms the booking details with the user."""
    chat_id = message.chat.id
    data = booking_data[chat_id]

    confirmation_text = f"¿Confirmar la siguiente reserva?\n" \
                        f"ID de propiedad: {data['property_id']}\n" \
                        f"Inquilino: {data['tenant_name']}\n" \
                        f"Fecha de inicio: {data['start_date']}\n" \
                        f"Fecha de fin: {data['end_date']}\n" \
                        f"Alquiler: {data['rent_amount']} {data['rent_currency']}\n" \
                        f"Fuente: {data['source']}\n" \
                        f"Notas: {data['notes'] if data['notes'] else 'Ninguna'}"

    keyboard = types.InlineKeyboardMarkup()
    key_yes = types.InlineKeyboardButton(text='Sí', callback_data='booking_confirm_yes')
    key_no = types.InlineKeyboardButton(text='No', callback_data='booking_confirm_no')
    keyboard.add(key_yes, key_no)

    bot.send_message(chat_id, confirmation_text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    """Handles inline keyboard callbacks."""
    chat_id = call.message.chat.id
    if call.data == 'booking_confirm_yes':
        # Add booking to database
        data = booking_data[chat_id]
        try:
            success = dm.add_booking(
                property_id=data['property_id'],
                tenant_name=data['tenant_name'],
                start_date=data['start_date'], # Format date to string
                end_date=data['end_date'],     # Format date to string
                rent_amount=data['rent_amount'],
                rent_currency=data['rent_currency'],
                source=data['source'],
                notes=data['notes']
            )

            if success:
                response_text = "✅ ¡Reserva agregada exitosamente!"
            else:
                response_text = "❌ No se pudo agregar la reserva. Por favor, revisá los registros del servidor."

            bot.send_message(chat_id, response_text)
            # Clean up booking data
            del booking_data[chat_id]

        except Exception as e:
            print(f"Error adding booking: {e}")
            bot.send_message(chat_id, "❌ Ocurrió un error al agregar la reserva. Por favor, revisá los registros del servidor.")

    elif call.data == 'booking_confirm_no':
        bot.send_message(chat_id, "Reserva cancelada.")
        # Clean up booking data
        del booking_data[chat_id]

    elif call.data == 'property_confirm_yes':
        # Add property to database
        data = property_data[chat_id]
        try:
            success = dm.add_property(
                name=data['property_name'],
                owner=data['property_owner'],
                address=data['property_address']
            )

            if success:
                response_text = "✅ ¡Propiedad agregada exitosamente!"
            else:
                response_text = "❌ No se pudo agregar la propiedad. Por favor, revisá los registros del servidor."

            bot.send_message(chat_id, response_text)
            # Clean up property data
            del property_data[chat_id]

        except Exception as e:
            print(f"Error adding property: {e}")
            bot.send_message(chat_id, "❌ Ocurrió un error al agregar la propiedad. Por favor, revisá los registros del servidor.")
    elif call.data == 'property_confirm_no':
        bot.send_message(chat_id, "Creación de propiedad cancelada.")
        # Clean up property data
        del property_data[chat_id]
        # Edit message to remove keyboard


# --- New Property Wizard ---
@bot.message_handler(commands=['new_property'])
def new_property(message):
    """Starts the new property wizard."""
    chat_id = message.chat.id
    property_data[chat_id] = {}  # Initialize property data for the user

    msg = bot.reply_to(message, "Por favor, ingresa el nombre de la nueva propiedad:")
    bot.register_next_step_handler(msg, process_property_name_add)

def process_property_name_add(message):
    """Processes the property name input for adding a new property."""
    chat_id = message.chat.id
    property_name = message.text.strip()

    if not property_name:
        msg = bot.reply_to(message, "El nombre de la propiedad no puede estar vacío. Por favor, intenta de nuevo:")
        bot.register_next_step_handler(msg, process_property_name_add)
        return

    property_data[chat_id]['property_name'] = property_name

    msg = bot.reply_to(message, "Por favor, ingresa el nombre del propietario:")
    bot.register_next_step_handler(msg, process_property_owner_add)

def process_property_owner_add(message):
    """Processes the property owner input for adding a new property."""
    chat_id = message.chat.id
    owner_name = message.text.strip()

    if not owner_name: # Consider if owner name can be empty or not
        msg = bot.reply_to(message, "El nombre del propietario no puede estar vacío. Por favor, intenta de nuevo:")
        bot.register_next_step_handler(msg, process_property_owner_add)
        return

    property_data[chat_id]['property_owner'] = owner_name

    msg = bot.reply_to(message, "Por favor, ingresa la dirección de la propiedad:")
    bot.register_next_step_handler(msg, process_property_address_add)

def process_property_address_add(message):
    """Processes the property address input for adding a new property."""
    chat_id = message.chat.id
    property_address = message.text.strip()

    if not property_address: # Consider if address can be empty or not
        msg = bot.reply_to(message, "La dirección de la propiedad no puede estar vacía. Por favor, intenta de nuevo:")
        bot.register_next_step_handler(msg, process_property_address_add)
        return

    property_data[chat_id]['property_address'] = property_address

    # Confirm property details
    confirm_property_add(message)

def confirm_property_add(message):
    """Confirms the property details with the user before adding."""
    chat_id = message.chat.id
    data = property_data[chat_id]

    confirmation_text = f"¿Confirmar la creación de la siguiente propiedad?\n" \
                        f"Nombre de propiedad: {data['property_name']}\n" \
                        f"Propietario: {data['property_owner']}\n" \
                        f"Dirección: {data['property_address']}"

    keyboard = types.InlineKeyboardMarkup()
    key_yes = types.InlineKeyboardButton(text='Sí', callback_data='property_confirm_yes')
    key_no = types.InlineKeyboardButton(text='No', callback_data=f'property_confirm_no')
    keyboard.add(key_yes, key_no)

    bot.send_message(chat_id, confirmation_text, reply_markup=keyboard)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handles all incoming messages."""
    # Removed command parsing logic
    bot.reply_to(message, "Usa /new_booking para comenzar a agregar una reserva o /new_property para agregar una propiedad.")

# --- Main Execution ---
if __name__ == "__main__":
    # Start the Telegram bot
    print("Starting Telegram bot...")
    bot.infinity_polling()
