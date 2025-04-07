import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import data_manager
from streamlit_calendar import calendar # Assuming this is installed

# --- Page Configuration ---
st.set_page_config(page_title="Reserva Rápida", page_icon="⚡", layout="wide")

# --- Authentication ---
if not data_manager.check_password():
    st.stop()  # Do not continue if not authenticated

# --- Page Title ---
st.title("⚡ Reserva Rápida: Calendario y Manual")

# --- Load Data ---
# Removing caching to ensure data is always reloaded for conflict checks
def load_data():
    """Loads properties and bookings, ensuring date columns are datetime."""
    properties = data_manager.load_properties()
    bookings = data_manager.load_bookings()
    # Ensure date columns are datetime objects after loading
    if not bookings.empty:
        for col in ['start_date', 'end_date']:
            if col in bookings.columns:
                bookings[col] = pd.to_datetime(bookings[col], errors='coerce') # Coerce errors to NaT
        # Drop rows where conversion failed
        bookings.dropna(subset=['start_date', 'end_date'], inplace=True)
    return properties, bookings

try:
    properties_df, bookings_df = load_data()
except Exception as e:
    st.error(f"Error crítico al cargar datos iniciales: {e}")
    # Initialize empty DataFrames with correct columns to prevent downstream errors
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS if hasattr(data_manager, 'PROPERTIES_COLS') else ['id', 'name'])
    bookings_df = pd.DataFrame(columns=data_manager.BOOKINGS_COLS if hasattr(data_manager, 'BOOKINGS_COLS') else ['id', 'property_id', 'start_date', 'end_date'])
    st.stop() # Stop execution if basic data loading fails


if properties_df.empty:
    st.warning("No se encontraron propiedades. Agregue propiedades en 'Gestionar Propiedades'.", icon="⚠️")
    st.stop()

# --- Property Selection ---
property_names = properties_df['name'].tolist()
# Use session state to remember selection across reruns
if 'selected_property_name' not in st.session_state or st.session_state.selected_property_name not in property_names:
    st.session_state.selected_property_name = property_names[0] if property_names else None

selected_property_name = st.selectbox(
    "Seleccionar Propiedad",
    options=property_names,
    key='selected_property_name_widget', # Use a distinct key for the widget
    index=property_names.index(st.session_state.selected_property_name) if st.session_state.selected_property_name in property_names else 0,
    on_change=lambda: st.session_state.update(selected_property_name=st.session_state.selected_property_name_widget) # Update main state on change
)

# Update session state if widget changed it (handles the on_change)
if 'selected_property_name' not in st.session_state:
    st.session_state.selected_property_name = selected_property_name

if not st.session_state.selected_property_name:
    st.info("Seleccione una propiedad para ver su calendario y reservar.")
    st.stop()

# Get property ID based on session state selection
selected_property = properties_df[properties_df['name'] == st.session_state.selected_property_name].iloc[0]
property_id = selected_property['id']
today = date.today()

# --- Filter bookings for the selected property ---
prop_bookings = pd.DataFrame(columns=data_manager.BOOKINGS_COLS if hasattr(data_manager, 'BOOKINGS_COLS') else []) # Initialize empty
if not bookings_df.empty and 'property_id' in bookings_df.columns:
    prop_bookings = bookings_df[bookings_df['property_id'] == property_id].copy()
    # Ensure date types again after filtering
    if not prop_bookings.empty:
        prop_bookings['start_date'] = pd.to_datetime(prop_bookings['start_date'])
        prop_bookings['end_date'] = pd.to_datetime(prop_bookings['end_date'])

# --- Initialize Session State for Dates and Interaction Flag ---
# This ensures date inputs persist their state across interactions
# Reset dates if property changes or first load for this property
property_changed = st.session_state.get('current_property_id') != property_id
if 'start_date' not in st.session_state or property_changed:
    first_available = data_manager.get_first_available_date_for_property(property_id) # Pass bookings_df
    suggested_start = max(first_available, today) if first_available else today
    st.session_state.start_date = suggested_start
    st.session_state.end_date = suggested_start + timedelta(days=1)
    st.session_state.current_property_id = property_id # Track current property for reset
    st.session_state.calendar_interaction_processed = False # Reset flag on property change

# Initialize the interaction flag if it doesn't exist
if 'calendar_interaction_processed' not in st.session_state:
    st.session_state.calendar_interaction_processed = False

# --- Prepare Events for the Calendar Component ---
calendar_events = []
# Add existing bookings as events
if not prop_bookings.empty:
    for _, booking in prop_bookings.iterrows():
        # Ensure dates are valid datetime objects before formatting
        if pd.notna(booking['start_date']) and pd.notna(booking['end_date']):
            calendar_events.append({
                "title": f"Ocupado ({booking.get('tenant_name', 'N/A')})",
                "start": booking['start_date'].strftime("%Y-%m-%d"),
                "end": booking['end_date'].strftime("%Y-%m-%d"), # FullCalendar end is exclusive
                "color": "#FF6347", # Tomato Red for booked slots
                "textColor": "#FFFFFF",
                "allDay": True,
                "display": "block", # Regular block event
            })

# Add the dynamic current selection highlight event based on session state
# Ensure dates are valid date/datetime objects and end > start
if isinstance(st.session_state.start_date, (date, datetime)) and \
   isinstance(st.session_state.end_date, (date, datetime)) and \
   st.session_state.end_date > st.session_state.start_date:
    calendar_events.append({
        "id": "current_selection_highlight", # Unique ID for potential targeting
        "title": "Selección Actual",
        "start": st.session_state.start_date.strftime("%Y-%m-%d"),
        "end": st.session_state.end_date.strftime("%Y-%m-%d"), # End is exclusive
        #"color": "#90EE90",        # Light Green background
        "backgroundColor": 'rgba(144, 238, 144, 0.5)', # Light Green with transparency
        "borderColor": '#006400', # Dark Green border
        "textColor": '#006400',    # Dark Green text
        "allDay": True,
        "display": 'background', # Render as a background highlight
    })

# --- Calendar Configuration ---
calendar_options = {
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth",
    },
    "initialView": "dayGridMonth",
    "locale": 'es',
    "selectable": True,        # Allow date selection
    "selectMirror": True,      # Show placeholder during selection drag
    "unselectAuto": False,     # Keep selection until explicitly changed
    "navLinks": True,
    "editable": False,         # Don't allow dragging/resizing existing events
    "dayMaxEvents": True,
    "validRange": { "start": today.strftime("%Y-%m-%d") }, # Prevent selecting past dates
    "contentHeight": "auto",
    "selectOverlap": False,    # Prevent selecting dates that overlap existing events visually
    "events": calendar_events, # Pass events directly here
    "eventDisplay": 'block',   # Default display for events unless overridden
    "eventBackgroundColor": '#FF6347', # Default for booked
    "eventBorderColor": '#FF6347',
    # "eventDidMount": """
    # function(info) {
    #   if (info.event.id === 'current_selection_highlight') {
    #     // Optional: Add specific JS manipulation if needed
    #   }
    # }
    # """
}

# --- Display Interactive Calendar ---
st.subheader(f"📅 Calendario Interactivo para {st.session_state.selected_property_name}")
st.caption("Haga clic/arrastre en el calendario para seleccionar fechas, o ingréselas manualmente abajo. La selección actual se muestra en verde claro.")

# Use a stable key for the calendar component based on the property ID
calendar_key = f"calendar_for_{property_id}"

# Reset interaction flag at the start of this specific interaction check cycle
# This ensures that if the user clicks the calendar multiple times without other actions,
# each click is processed, but prevents reprocessing the *same* click data after the rerun.
st.session_state.calendar_interaction_processed = False

calendar_return = calendar(
    # events=calendar_events, # Pass events via options for better structure
    options=calendar_options,
    custom_css="""
        /* Style for booked events */
        .fc-event:not(.fc-bg-event) { /* Target non-background events */
            font-size: 0.8em;
            background-color: #FF6347 !important; /* Ensure override */
            border-color: #FF6347 !important;
        }
        /* Style for past days */
        .fc-day-past { background-color: #f0f0f0; }
        /* Style for the temporary selection highlight during drag */
        .fc-highlight { background: rgba(144, 238, 144, 0.3) !important; }
        /* Style for the background event representing current selection */
        .fc-bg-event#current_selection_highlight { /* Target specific ID if needed, otherwise rely on options */
             /* Handled by backgroundColor in options, but can override here */
             /* Example: border: 1px dashed #006400 !important; */
        }
        .fc-event-title { /* Ensure title text is visible */
            font-weight: bold;
        }
    """,
    key=calendar_key
)

# --- Process Calendar Interaction -> Update Session State ---
# This happens *after* the calendar component runs and returns a value
rerun_needed = False
if calendar_return and calendar_return.get("callback") == "select":
    # Process only if this interaction hasn't been processed in this cycle
    if not st.session_state.calendar_interaction_processed:
        try:
            # Use 'start' and 'end' keys, not 'startStr'/'endStr' based on common component patterns
            raw_start = calendar_return.get("start")
            raw_end = calendar_return.get("end")

            if raw_start and raw_end:
                # FullCalendar's select callback often gives YYYY-MM-DD format
                cal_start = datetime.strptime(raw_start, '%Y-%m-%d').date()
                 # The 'end' date from FullCalendar select is exclusive (the day *after* the last selected day)
                cal_end = datetime.strptime(raw_end, '%Y-%m-%d').date()

                # Basic validation: Ensure dates are valid and in the future/today
                if cal_start >= today and cal_end > cal_start:
                    # --- Optional: Quick visual conflict check (Calendar's selectOverlap should prevent this) ---
                    # cal_start_dt = pd.to_datetime(cal_start)
                    # cal_end_dt = pd.to_datetime(cal_end)
                    # conflict_from_cal = False
                    # if not prop_bookings.empty:
                    #     for _, booking in prop_bookings.iterrows():
                    #         if max(cal_start_dt, booking['start_date']) < min(cal_end_dt, booking['end_date']):
                    #             conflict_from_cal = True
                    #             st.toast(f"⚠️ Selección de calendario ({cal_start.strftime('%d-%b')} - {cal_end.strftime('%d-%b')}) parece tener conflicto.", icon="🚨")
                    #             break
                    # if not conflict_from_cal: # Proceed only if no immediate visual conflict

                    # Update session state - this is the SOURCE OF TRUTH
                    st.session_state.start_date = cal_start
                    st.session_state.end_date = cal_end

                    # Mark that this interaction was processed to prevent re-processing on the immediate rerun
                    st.session_state.calendar_interaction_processed = True
                    rerun_needed = True # Signal that a rerun is required

        except (ValueError, TypeError, KeyError) as e:
            st.warning(f"Error al procesar selección del calendario: {e}. Datos recibidos: {calendar_return}")

# If a calendar interaction was processed and updated state, rerun the script
if rerun_needed:
    st.rerun()


# --- Manual Date Input ---
st.divider()
st.subheader("Seleccionar Fechas Manualmente")
st.caption("Use los selectores o edite las fechas directamente. El calendario se actualizará.")

# Define callbacks to update session state when manual input changes
# These implicitly trigger a rerun, which will redraw the calendar with the new highlight
def update_start_date_state():
    # Update state from widget
    st.session_state.start_date = st.session_state.start_date_widget
    # Adjust end date if necessary
    min_end = st.session_state.start_date + timedelta(days=1)
    if st.session_state.end_date <= st.session_state.start_date:
        st.session_state.end_date = min_end
        # Also update the end date *widget's* state if we adjusted programmatically
        # Streamlit should handle this redraw, but explicit can be safer if complex interaction
        # st.session_state.end_date_widget = st.session_state.end_date # Not usually needed

def update_end_date_state():
    # Update state from widget
    st.session_state.end_date = st.session_state.end_date_widget

col1, col2 = st.columns(2)
with col1:
    st.date_input(
        "Fecha de Inicio",
        key='start_date_widget', # Unique key for the widget
        value=st.session_state.start_date, # Value comes FROM session state
        min_value=today,
        on_change=update_start_date_state # Callback updates session state
    )

with col2:
    # Ensure min_value for end date is always after start date from session state
    min_end_date_for_widget = st.session_state.start_date + timedelta(days=1)

    st.date_input(
        "Fecha de Fin (Exclusivo)", # Clarify end date is exclusive like calendar
        key='end_date_widget', # Unique key for the widget
        value=st.session_state.end_date, # Value comes FROM session state
        min_value=min_end_date_for_widget,
        on_change=update_end_date_state, # Callback updates session state
        help="El día de salida. La reserva es HASTA este día (no inclusive)."
    )

# --- Validate Manual Dates (from Session State) and Check Conflicts ---
manual_start_date = st.session_state.start_date
manual_end_date = st.session_state.end_date
dates_valid = True
conflict_warning_placeholder = st.empty() # Placeholder for warning/success messages

# Convert to datetime for comparison if they are date objects
manual_start_dt = pd.to_datetime(manual_start_date)
manual_end_dt = pd.to_datetime(manual_end_date)

if manual_end_date <= manual_start_date:
    conflict_warning_placeholder.error("⛔ La fecha de fin debe ser posterior a la fecha de inicio.")
    dates_valid = False
elif manual_start_date < today:
    # This check might be redundant due to date_input min_value, but good as safeguard
    conflict_warning_placeholder.error("⛔ La fecha de inicio no puede ser en el pasado.")
    dates_valid = False
else:
    # Check for conflicts with the MANUALLY entered/adjusted dates (from session state)
    conflict = False
    conflicting_booking_details = ""
    if not prop_bookings.empty:
        for _, booking in prop_bookings.iterrows():
            # Ensure comparison with datetime objects
            booking_start_dt = pd.to_datetime(booking['start_date'])
            booking_end_dt = pd.to_datetime(booking['end_date'])
            # Check if [manual_start, manual_end) overlaps with [booking_start, booking_end)
            if max(manual_start_dt, booking_start_dt) < min(manual_end_dt, booking_end_dt):
                conflict = True
                conflicting_booking_details = f"({booking_start_dt.strftime('%d-%b')} - {booking_end_dt.strftime('%d-%b')}, {booking.get('tenant_name', 'N/A')})"
                break # Stop checking once a conflict is found

    if conflict:
        conflict_warning_placeholder.warning(
            f"⚠️ **Advertencia:** Las fechas seleccionadas ({manual_start_date.strftime('%d-%b')} - {manual_end_date.strftime('%d-%b')}) "
            f"**tienen conflicto** con una reserva existente {conflicting_booking_details}. "
            "Puede reservar igualmente bajo su responsabilidad, pero verifique cuidadosamente.", icon="🚨"
        )
        # We allow proceeding even with conflict, so dates_valid remains True if start/end order is ok
    else:
        conflict_warning_placeholder.success(f"✅ Fechas seleccionadas ({manual_start_date.strftime('%d-%b')} - {manual_end_date.strftime('%d-%b')}) parecen disponibles.")


# --- Booking Details (Enabled based on date validity) ---
st.subheader("Detalles de la Reserva")
details_disabled = not dates_valid # Disable if end <= start or start < today (basic validity)
col_details1, col_details2, col_details3 = st.columns(3)

with col_details1:
    tenant_name = st.text_input("Nombre del Inquilino", placeholder="Ingrese el nombre (opcional)", disabled=details_disabled, key="tenant_name_input")
with col_details2:
    # Ensure rent amount persists if user changes dates causing temp disable
    if 'rent_amount_input' not in st.session_state:
        st.session_state.rent_amount_input = 1000.0
    rent_amount = st.number_input("Monto del Alquiler", min_value=0.0, step=100.0, disabled=details_disabled, key="rent_amount_input")
with col_details3:
    # Ensure currency persists
    if 'rent_currency_input' not in st.session_state:
         st.session_state.rent_currency_input = data_manager.CURRENCIES[0] if hasattr(data_manager, 'CURRENCIES') and data_manager.CURRENCIES else "USD"
    rent_currency = st.selectbox("Moneda", options=data_manager.CURRENCIES if hasattr(data_manager, 'CURRENCIES') else ["USD"],
                                 index=(data_manager.CURRENCIES.index(st.session_state.rent_currency_input)
                                        if hasattr(data_manager, 'CURRENCIES') and st.session_state.rent_currency_input in data_manager.CURRENCIES else 0),
                                 disabled=details_disabled, key="rent_currency_input_widget",
                                 on_change=lambda: st.session_state.update(rent_currency_input=st.session_state.rent_currency_input_widget))
    # Update state if widget changed it
    if 'rent_currency_input' not in st.session_state:
        st.session_state.rent_currency_input = rent_currency


# --- Add Booking Button (Disabled only if basic date validity fails) ---
st.divider()
confirm_button_disabled = not dates_valid # Only disable if end<=start or past date

if st.button("Confirmar y Reservar Propiedad", type="primary", disabled=confirm_button_disabled, use_container_width=True):
    # Use the dates from session state (which reflect the synchronized inputs/calendar)
    final_start_date = st.session_state.start_date
    final_end_date = st.session_state.end_date

    # --- Perform FINAL conflict check against LATEST data just before saving ---
    try:
        _ , latest_bookings = load_data() # Reload fresh data
        final_conflict = False
        latest_prop_bookings = pd.DataFrame(columns=data_manager.BOOKINGS_COLS if hasattr(data_manager, 'BOOKINGS_COLS') else []) # Initialize empty
        if not latest_bookings.empty and 'property_id' in latest_bookings.columns:
            latest_prop_bookings = latest_bookings[latest_bookings['property_id'] == property_id].copy()
            if not latest_prop_bookings.empty:
                 latest_prop_bookings['start_date'] = pd.to_datetime(latest_prop_bookings['start_date'])
                 latest_prop_bookings['end_date'] = pd.to_datetime(latest_prop_bookings['end_date'])


        # Convert final dates to datetime for comparison
        final_start_dt = pd.to_datetime(final_start_date)
        final_end_dt = pd.to_datetime(final_end_date)

        # Check against the latest bookings for the property
        if not latest_prop_bookings.empty:
            for _, booking in latest_prop_bookings.iterrows():
                booking_start_dt = pd.to_datetime(booking['start_date'])
                booking_end_dt = pd.to_datetime(booking['end_date'])
                # Final check: Overlap? [start1, end1) vs [start2, end2)
                if max(final_start_dt, booking_start_dt) < min(final_end_dt, booking_end_dt):
                    final_conflict = True
                    st.error(f"⛔ **¡Error Crítico!** Conflicto detectado JUSTO ANTES DE GUARDAR con reserva existente "
                             f"({booking_start_dt.strftime('%d-%b')} - {booking_end_dt.strftime('%d-%b')}, {booking.get('tenant_name', 'N/A')}). "
                             "Alguien más reservó mientras confirmabas. La página se actualizará para reflejar los últimos datos. Por favor, revisa e intenta de nuevo.", icon="🛑")
                    # Force a rerun to show the latest data and clear inputs
                    st.rerun() # Use rerun to refresh state and UI
                    break # Exit loop

        # --- If no final conflict, proceed to add booking ---
        if not final_conflict:
            # Retrieve details, using state for potentially disabled fields
            tenant_name_to_save = st.session_state.get("tenant_name_input", "Reserva Rápida") or "Reserva Rápida"
            rent_amount_to_save = st.session_state.get("rent_amount_input", 0.0)
            rent_currency_to_save = st.session_state.get("rent_currency_input", "USD")

            success = data_manager.add_booking(
                property_id=property_id,
                tenant_name=tenant_name_to_save,
                start_date=final_start_date,
                end_date=final_end_date,
                rent_amount=float(rent_amount_to_save) if rent_amount_to_save else 0.0,
                rent_currency=rent_currency_to_save,
                source="Reserva Rápida (Cal/Manual)",
                commission_paid=0.0,
                commission_currency=None, # Assuming no commission for rapid booking
                notes="Reserva creada desde Reserva Rápida"
            )

            if success:
                st.success(f"¡Propiedad '{st.session_state.selected_property_name}' reservada exitosamente para '{tenant_name_to_save}' "
                           f"desde {final_start_date.strftime('%Y-%m-%d')} hasta {final_end_date.strftime('%Y-%m-%d')}!")
                st.balloons()

                # --- Reset state after successful booking ---
                # Suggest new dates (e.g., starting after the booked period)
                new_suggested_start = final_end_date
                st.session_state.start_date = new_suggested_start
                st.session_state.end_date = new_suggested_start + timedelta(days=1)
                # Clear potentially sensitive/temporary info if desired
                # if 'tenant_name_input' in st.session_state: del st.session_state['tenant_name_input']
                # Reset interaction flag
                st.session_state.calendar_interaction_processed = False

                # Rerun to reflect the new booking in the calendar/table and reset inputs
                st.rerun()

            else:
                st.error("Error desconocido al intentar guardar la reserva en el archivo/base de datos.")

    except FileNotFoundError:
         st.error("Error: No se encontró el archivo de reservas al intentar guardar. Verifica la configuración.")
    except pd.errors.EmptyDataError:
         st.error("Error: El archivo de reservas parece estar vacío o corrupto al intentar guardar.")
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante la confirmación final o al guardar la reserva: {e}")
        st.exception(e) # Log the full traceback for debugging


# --- Display existing bookings for this property (Refreshed View) ---
st.divider()
st.subheader(f"Historial de Reservas para {st.session_state.selected_property_name}")

# Re-load and re-filter data to show the most current bookings, including any just added
try:
    _, current_bookings_df = load_data()
    current_prop_bookings = pd.DataFrame(columns=data_manager.BOOKINGS_COLS if hasattr(data_manager, 'BOOKINGS_COLS') else []) # Initialize empty
    if not current_bookings_df.empty and 'property_id' in current_bookings_df.columns:
         current_prop_bookings = current_bookings_df[current_bookings_df['property_id'] == property_id].copy()
         if not current_prop_bookings.empty:
             current_prop_bookings['start_date'] = pd.to_datetime(current_prop_bookings['start_date'])
             current_prop_bookings['end_date'] = pd.to_datetime(current_prop_bookings['end_date'])

    property_bookings_display = current_prop_bookings.sort_values('start_date', ascending=False)

    if property_bookings_display.empty:
        st.info("Todavía no hay reservas registradas para esta propiedad.")
    else:
        # Prepare DataFrame for display (using same logic as before)
        display_cols_options = ['tenant_name', 'start_date', 'end_date', 'rent_amount', 'rent_currency', 'source', 'notes']
        display_cols = [col for col in display_cols_options if col in property_bookings_display.columns]
        display_df = property_bookings_display[display_cols].copy()

        rename_map = {
            'tenant_name': 'Inquilino', 'start_date': 'Inicio', 'end_date': 'Fin (Exclusivo)',
            'rent_amount': 'Monto', 'rent_currency': 'Moneda', 'source': 'Origen', 'notes': 'Notas'
        }
        display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns}, inplace=True)

        if 'Inicio' in display_df.columns:
            display_df['Inicio'] = display_df['Inicio'].dt.strftime('%Y-%m-%d')
        if 'Fin (Exclusivo)' in display_df.columns:
            display_df['Fin (Exclusivo)'] = display_df['Fin (Exclusivo)'].dt.strftime('%Y-%m-%d') # Exclusive date
        if 'Monto' in display_df.columns and 'Moneda' in display_df.columns:
            display_df['Monto'] = display_df.apply(
                lambda row: f"{row['Monto']:,.2f} {row['Moneda']}" if pd.notna(row['Monto']) and pd.notna(row['Moneda']) else \
                            (f"{row['Monto']:,.2f}" if pd.notna(row['Monto']) else ''),
                axis=1)
            display_df.drop(columns=['Moneda'], inplace=True) # Drop currency after combining
        elif 'Monto' in display_df.columns:
             display_df['Monto'] = display_df['Monto'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else '')

        final_display_cols_order = ['Inquilino', 'Inicio', 'Fin (Exclusivo)', 'Monto', 'Origen', 'Notas']
        final_display_cols = [col for col in final_display_cols_order if col in display_df.columns]

        st.dataframe(
            display_df[final_display_cols],
            hide_index=True,
            use_container_width=True
        )
except Exception as e:
    st.error(f"Error al mostrar el historial de reservas: {e}")