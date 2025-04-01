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

    # Confirm property details
    confirm_property_add(message)

def confirm_property_add(message):
    """Confirms the property details with the user before adding."""
    chat_id = message.chat.id
    data = property_data[chat_id]

    confirmation_text = f"¿Confirmar la creación de la siguiente propiedad?\n" \
                        f"Nombre de propiedad: {data['property_name']}"

    keyboard = types.InlineKeyboardMarkup()
    key_yes = types.InlineKeyboardButton(text='Sí', callback_data='property_confirm_yes')
    key_no = types.InlineKeyboardButton(text='No', callback_data='property_confirm_no')
    keyboard.add(key_yes, key_no)

    bot.send_message(chat_id, confirmation_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('property_confirm'))
def property_callback_worker(call):
    """Handles inline keyboard callbacks for property confirmation."""
    chat_id = call.message.chat.id
    if call.data == 'property_confirm_yes':
        # Add property to database
        data = property_data[chat_id]
        try:
            success = dm.add_property(
                property_name=data['property_name']
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
