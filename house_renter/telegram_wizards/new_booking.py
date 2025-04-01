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
    key_yes = types.InlineKeyboardButton(text='Sí', callback_data='confirm_yes')
    key_no = types.InlineKeyboardButton(text='No', callback_data='confirm_no')
    keyboard.add(key_yes, key_no)

    bot.send_message(chat_id, confirmation_text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    """Handles inline keyboard callbacks."""
    chat_id = call.message.chat.id
    if call.data == 'confirm_yes':
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


    elif call.data == 'confirm_no':
        bot.send_message(chat_id, "Reserva cancelada.")
        # Clean up booking data
        del booking_data[chat_id]
