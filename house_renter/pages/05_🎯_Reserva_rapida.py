import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import data_manager
from streamlit_calendar import calendar # Assuming this is installed

# --- Page Configuration ---
st.set_page_config(page_title="Reserva Rápida", layout="wide")
st.title("⚡ Reserva Rápida: Calendario y Manual")

# --- Load Data ---
# Removing caching to ensure data is always reloaded
def load_data():
    properties = data_manager.load_properties()
    bookings = data_manager.load_bookings()
    # Ensure date columns are datetime objects after loading
    if not bookings.empty:
        bookings['start_date'] = pd.to_datetime(bookings['start_date'])
        bookings['end_date'] = pd.to_datetime(bookings['end_date'])
    return properties, bookings

try:
    properties_df, bookings_df = load_data()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS)
    bookings_df = pd.DataFrame(columns=data_manager.BOOKINGS_COLS)


if properties_df.empty:
    st.warning("No se encontraron propiedades. Agregue propiedades en 'Gestionar Propiedades'.", icon="⚠️")
    st.stop()

# --- Property Selection ---
property_names = properties_df['name'].tolist()
# Use session state to remember selection across reruns caused by calendar interaction
if 'selected_property_name' not in st.session_state:
    st.session_state.selected_property_name = property_names[0] if property_names else None

selected_property_name = st.selectbox(
    "Seleccionar Propiedad",
    options=property_names,
    key='selected_property_name', # Use key to bind to session state
    placeholder="Elegir una propiedad..."
)

if not selected_property_name:
    st.info("Seleccione una propiedad para ver su calendario y reservar.")
    st.stop()

# Get property ID based on session state selection
selected_property = properties_df[properties_df['name'] == st.session_state.selected_property_name].iloc[0]
property_id = selected_property['id']
today = date.today()

# --- Filter bookings for the selected property ---
# Initialize prop_bookings as an empty DataFrame first
prop_bookings = pd.DataFrame(columns=data_manager.BOOKINGS_COLS)
if not bookings_df.empty and 'property_id' in bookings_df.columns:
    # Filter the bookings for the current property
    prop_bookings = bookings_df[bookings_df['property_id'] == property_id].copy() # Use .copy() to avoid SettingWithCopyWarning
    # Ensure date columns are still datetime objects after filtering
    if not prop_bookings.empty:
        prop_bookings['start_date'] = pd.to_datetime(prop_bookings['start_date'])
        prop_bookings['end_date'] = pd.to_datetime(prop_bookings['end_date'])


# --- Initialize Session State for Dates ---
# This ensures date inputs persist their state across calendar interactions
if 'start_date' not in st.session_state or st.session_state.get('current_property_id') != property_id:
    # Reset dates if property changes or first load for this property
    first_available = data_manager.get_first_available_date_for_property(property_id)
    suggested_start = max(first_available, today) if first_available else today
    st.session_state.start_date = suggested_start
    st.session_state.end_date = suggested_start + timedelta(days=1)
    st.session_state.current_property_id = property_id # Track current property for reset

# --- Prepare Events for the Calendar Component ---
calendar_events = []
# Now use the guaranteed-to-exist prop_bookings DataFrame
if not prop_bookings.empty: # Check if the filtered DataFrame has data
    for _, booking in prop_bookings.iterrows():
        calendar_events.append({
            "title": f"Ocupado ({booking.get('tenant_name', 'N/A')})",
            "start": booking['start_date'].strftime("%Y-%m-%d"),
            "end": booking['end_date'].strftime("%Y-%m-%d"),
            "color": "#FF6347", # Tomato Red
            "allDay": True,
        })

# --- Calendar Configuration ---
calendar_options = {
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth", # Keep it simple
    },
    "initialView": "dayGridMonth",
    "selectable": True,
    "selectMirror": True,
    "unselectAuto": True, # Allow unselecting
    "navLinks": True,
    "editable": False,
    "dayMaxEvents": True,
    "locale": 'es',
    "validRange": { "start": today.strftime("%Y-%m-%d") },
    "contentHeight": "auto", # Adjust height automatically
    # "selectConstraint": { # Visually constrain selection (might not fully prevent overlap data-wise)
    #     "resourceId": "available" # Hypothetical, needs component support or JS
    # },
}

# --- Display Interactive Calendar ---
st.subheader(f"📅 Calendario Interactivo para {st.session_state.selected_property_name}")
st.caption("Haga clic/arrastre en el calendario para pre-seleccionar fechas abajo, o ingréselas manualmente.")

calendar_key = f"cal_{property_id}" # Unique key per property

calendar_return = calendar(
    events=calendar_events,
    options=calendar_options,
    custom_css="""
        .fc-event { font-size: 0.8em; }
        .fc-daygrid-day.fc-day-past { background-color: #f0f0f0; }
        .fc-highlight { background: #90EE90 !important; } /* Light green for selection */
    """,
    key=calendar_key
)

# --- Process Calendar Interaction -> Update Session State ---
# This happens *after* the calendar component runs and potentially returns a value
if calendar_return and calendar_return.get("callback") == "select":
    try:
        raw_start = calendar_return.get("select", {}).get("startStr")
        raw_end = calendar_return.get("select", {}).get("endStr")

        if raw_start and raw_end:
            cal_start = datetime.strptime(raw_start, '%Y-%m-%d').date()
            cal_end = datetime.strptime(raw_end, '%Y-%m-%d').date() # Day *after* last selected

            # Only update if dates are valid (avoid setting past dates from calendar)
            if cal_start >= today and cal_end > cal_start:
                 # Check for visual conflict from calendar selection before updating inputs
                 cal_start_dt = pd.to_datetime(cal_start)
                 cal_end_dt = pd.to_datetime(cal_end)
                 conflict_from_cal = False
                 # Use the guaranteed-to-exist prop_bookings DataFrame
                 if not prop_bookings.empty:
                     for _, booking in prop_bookings.iterrows():
                         if max(cal_start_dt, booking['start_date']) < min(cal_end_dt, booking['end_date']):
                             conflict_from_cal = True
                             st.toast(f"⚠️ Selección de calendario ({cal_start.strftime('%d-%b')} - {cal_end.strftime('%d-%b')}) tiene conflicto.", icon="🚨")
                             break

                 # Update session state, which will update date_input values on rerun
                 st.session_state.start_date = cal_start
                 st.session_state.end_date = cal_end
                 # Update widget values as well
                 st.session_state.start_date_widget = cal_start
                 st.session_state.end_date_widget = cal_end
                 # Rerun to reflect changes in date inputs
                 st.rerun()

    except (ValueError, TypeError) as e:
        st.warning(f"Error al procesar selección del calendario: {e}")

# --- Manual Date Input ---
st.divider()
st.subheader("Seleccionar Fechas Manualmente")
st.caption("Las fechas del calendario son sugerencias. Estas son las fechas finales que se usarán.")

# Define callbacks to update session state when manual input changes
def update_start_date():
    st.session_state.start_date = st.session_state.start_date_widget
def update_end_date():
    st.session_state.end_date = st.session_state.end_date_widget

col1, col2 = st.columns(2)
with col1:
    st.date_input(
        "Fecha de Inicio",
        key='start_date_widget', # Use a different key for the widget itself
        value=st.session_state.start_date, # Read from session state
        min_value=today,
        on_change=update_start_date # Update session state on change
    )

with col2:
    # Ensure min_value for end date is always after start date
    min_end_date = st.session_state.start_date + timedelta(days=1)
    # Adjust end date in state if it becomes invalid due to start date change
    if st.session_state.end_date <= st.session_state.start_date:
        st.session_state.end_date = min_end_date

    st.date_input(
        "Fecha de Fin (Salida)",
        key='end_date_widget', # Use a different key for the widget itself
        value=st.session_state.end_date, # Read from session state
        min_value=min_end_date,
        on_change=update_end_date # Update session state on change
    )

# --- Validate Manual Dates and Check Conflicts ---
manual_start_date = st.session_state.start_date
manual_end_date = st.session_state.end_date
dates_valid = True
conflict_warning_placeholder = st.empty() # Placeholder for warning/success messages

if manual_end_date <= manual_start_date:
    conflict_warning_placeholder.error("⛔ La fecha de fin debe ser posterior a la fecha de inicio.")
    dates_valid = False
elif manual_start_date < today:
    conflict_warning_placeholder.error("⛔ La fecha de inicio no puede ser en el pasado.")
    dates_valid = False
else:
    # Check for conflicts with the MANUALLY entered/adjusted dates
    manual_start_dt = pd.to_datetime(manual_start_date)
    manual_end_dt = pd.to_datetime(manual_end_date)
    conflict = False
    conflicting_booking_details = ""
    # Use the guaranteed-to-exist prop_bookings DataFrame here
    if not prop_bookings.empty:
        for _, booking in prop_bookings.iterrows():
            # Check if [manual_start, manual_end) overlaps with [booking_start, booking_end)
            if max(manual_start_dt, booking['start_date']) < min(manual_end_dt, booking['end_date']):
                conflict = True
                conflicting_booking_details = f"({booking['start_date'].strftime('%d-%b')} - {booking['end_date'].strftime('%d-%b')})"
                break # Stop checking once a conflict is found

    if conflict:
        conflict_warning_placeholder.warning(f"⚠️ **Advertencia:** Las fechas seleccionadas ({manual_start_date.strftime('%d-%b')} - {manual_end_date.strftime('%d-%b')}) **tienen conflicto** con una reserva existente {conflicting_booking_details}. Puede reservar igualmente, pero verifique.", icon="🚨")
        # We allow proceeding, so dates_valid remains True if start/end order is ok
    else:
        conflict_warning_placeholder.success(f"✅ Fechas seleccionadas ({manual_start_date.strftime('%d-%b')} - {manual_end_date.strftime('%d-%b')}) parecen disponibles.")


# --- Booking Details (Now always enabled if dates are valid) ---
st.subheader("Detalles de la Reserva")
details_disabled = not dates_valid # Disable if end <= start or start < today
col_details1, col_details2, col_details3 = st.columns(3)

with col_details1:
    tenant_name = st.text_input("Nombre del Inquilino", placeholder="Ingrese el nombre (opcional)", disabled=details_disabled)
with col_details2:
    rent_amount = st.number_input("Monto del Alquiler", min_value=0.0, value=1000.0, step=100.0, disabled=details_disabled)
with col_details3:
    rent_currency = st.selectbox("Moneda", options=data_manager.CURRENCIES, index=0, disabled=details_disabled)


# --- Add Booking Button (Disabled only if dates invalid, not on conflict warning) ---
st.divider()
confirm_button_disabled = not dates_valid # Only disable if end<=start or past date

if st.button("Confirmar y Reservar Propiedad", type="primary", disabled=confirm_button_disabled, use_container_width=True):
    # Use the dates from session state (which reflect manual inputs)
    final_start_date = st.session_state.start_date
    final_end_date = st.session_state.end_date

    # Perform FINAL conflict check against LATEST data just before saving
    try:
        latest_bookings = data_manager.load_bookings() # Reload fresh data
        if not latest_bookings.empty:
            latest_bookings['start_date'] = pd.to_datetime(latest_bookings['start_date'])
            latest_bookings['end_date'] = pd.to_datetime(latest_bookings['end_date'])

        final_start_dt = pd.to_datetime(final_start_date)
        final_end_dt = pd.to_datetime(final_end_date)
        final_conflict = False
        latest_prop_bookings = pd.DataFrame(columns=data_manager.BOOKINGS_COLS) # Initialize empty
        if not latest_bookings.empty and 'property_id' in latest_bookings.columns:
            latest_prop_bookings = latest_bookings[latest_bookings['property_id'] == property_id]

        # Check against the latest bookings for the property
        if not latest_prop_bookings.empty:
            for _, booking in latest_prop_bookings.iterrows():
                # Ensure booking dates are datetime before comparison
                booking_start_dt = pd.to_datetime(booking['start_date'])
                booking_end_dt = pd.to_datetime(booking['end_date'])
                if max(final_start_dt, booking_start_dt) < min(final_end_dt, booking_end_dt):
                    final_conflict = True
                    st.error(f"⛔ **¡Error Crítico!** Conflicto detectado justo antes de guardar con reserva ({booking_start_dt.strftime('%d-%b')} - {booking_end_dt.strftime('%d-%b')}). Alguien más reservó. Actualice la página (F5) e intente de nuevo.", icon="🛑")
                    break

        if not final_conflict:
            # --- Add Booking ---
            success = data_manager.add_booking(
                property_id=property_id,
                tenant_name=tenant_name or "Reserva Rápida",
                start_date=final_start_date, # Use final date from state
                end_date=final_end_date,     # Use final date from state
                rent_amount=float(rent_amount) if rent_amount else 0.0,
                rent_currency=rent_currency,
                source="Reserva Rápida (Cal/Manual)",
                commission_paid=0.0,
                commission_currency=None,
                notes="Reserva creada desde Reserva Rápida"
            )

            if success:
                st.success(f"¡Propiedad '{selected_property_name}' reservada exitosamente para {tenant_name or 'Reserva Rápida'} desde {final_start_date.strftime('%Y-%m-%d')} hasta {final_end_date.strftime('%Y-%m-%d')}!")
                st.balloons()
                # Clear relevant state and rerun
                keys_to_reset = ['start_date', 'end_date', 'start_date_widget', 'end_date_widget']
                for key in keys_to_reset:
                    if key in st.session_state:
                         del st.session_state[key]
                # Optionally reset tenant name, etc.
                st.rerun()
            else:
                st.error("Error al guardar la reserva en el archivo.")

    except Exception as e:
        st.error(f"Ocurrió un error inesperado al intentar agregar la reserva: {e}")
        st.exception(e)


# --- Display existing bookings for this property (As before) ---
st.divider()
st.subheader(f"Historial de Reservas para {st.session_state.selected_property_name}")
# Use the prop_bookings DataFrame defined earlier for display
# Force reload data by calling load_data() again
properties_df, bookings_df = load_data()
prop_bookings = pd.DataFrame(columns=data_manager.BOOKINGS_COLS)
if not bookings_df.empty and 'property_id' in bookings_df.columns:
    # Filter the bookings for the current property
    prop_bookings = bookings_df[bookings_df['property_id'] == property_id].copy() # Use .copy() to avoid SettingWithCopyWarning
    # Ensure date columns are still datetime objects after filtering
    if not prop_bookings.empty:
        prop_bookings['start_date'] = pd.to_datetime(prop_bookings['start_date'])
        prop_bookings['end_date'] = pd.to_datetime(prop_bookings['end_date'])

property_bookings_display = prop_bookings.sort_values('start_date', ascending=False)

if property_bookings_display.empty:
    st.info("No se encontraron reservas para esta propiedad.")
else:
    # Prepare DataFrame for display (same code as before)
    display_cols = ['tenant_name', 'start_date', 'end_date', 'rent_amount', 'rent_currency', 'source', 'notes']
    # Ensure columns exist before selecting
    display_cols = [col for col in display_cols if col in property_bookings_display.columns]
    display_df = property_bookings_display[display_cols].copy()

    # Rename columns if they exist
    rename_map = {
        'tenant_name': 'Inquilino',
        'start_date': 'Inicio',
        'end_date': 'Fin (Salida)',
        'rent_amount': 'Monto',
        'rent_currency': 'Moneda',
        'source': 'Origen',
        'notes': 'Notas'
    }
    display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns}, inplace=True)

    # Format columns if they exist
    if 'Inicio' in display_df.columns:
        display_df['Inicio'] = display_df['Inicio'].dt.strftime('%Y-%m-%d')
    if 'Fin (Salida)' in display_df.columns:
        display_df['Fin (Salida)'] = display_df['Fin (Salida)'].dt.strftime('%Y-%m-%d')
    if 'Monto' in display_df.columns and 'Moneda' in display_df.columns:
        display_df['Monto'] = display_df.apply(lambda row: f"{row['Monto']:,.2f} {row['Moneda']}" if pd.notna(row['Monto']) and row['Monto'] is not None else '', axis=1)
        display_df.drop(columns=['Moneda'], inplace=True)
    elif 'Monto' in display_df.columns: # Handle case where Moneda might be missing
         display_df['Monto'] = display_df['Monto'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else '')


    # Define final columns for display based on what exists
    final_display_cols_order = ['Inquilino', 'Inicio', 'Fin (Salida)', 'Monto', 'Origen', 'Notas']
    final_display_cols = [col for col in final_display_cols_order if col in display_df.columns]

    st.dataframe(
        display_df[final_display_cols], # Select and order columns that exist
        hide_index=True,
        use_container_width=True
    )