import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar # Import Python's calendar module
import data_manager
# Import the new helper functions (adjust path if needed)
from data_manager import get_occupied_dates, generate_month_calendar_html, get_calendar_css

# --- Page Configuration ---
st.set_page_config(page_title="Reserva Rápida", layout="wide")
st.title("⚡ Reserva Rápida")

# --- Inject CSS for Calendar ---
st.markdown(get_calendar_css(), unsafe_allow_html=True) # Inject CSS

# --- Load Data ---
try:
    properties_df = data_manager.load_properties()
    bookings_df = data_manager.load_bookings()

    # Ensure date columns are datetime objects after loading
    if not bookings_df.empty:
        bookings_df['start_date'] = pd.to_datetime(bookings_df['start_date'])
        bookings_df['end_date'] = pd.to_datetime(bookings_df['end_date'])

except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS)
    bookings_df = pd.DataFrame(columns=data_manager.BOOKINGS_COLS)

if properties_df.empty:
    st.warning("No se encontraron propiedades. Por favor, agregue propiedades primero en la página 'Gestionar Propiedades'.", icon="⚠️")
    st.stop()

# --- Property Selection ---
property_names = properties_df['name'].tolist()
selected_property_name = st.selectbox(
    "Seleccionar Propiedad",
    options=property_names,
    index=0 if property_names else None,
    placeholder="Elegir una propiedad..."
)

if not selected_property_name:
    st.info("Seleccione una propiedad para gestionar sus reservas.")
    st.stop()

selected_property = properties_df[properties_df['name'] == selected_property_name].iloc[0]
property_id = selected_property['id']

# --- Calculate Availability & Display Calendar ---
st.subheader("🗓️ Visualizador de Disponibilidad")

# Get occupied dates for the selected property
occupied_dates = get_occupied_dates(property_id, bookings_df)
today = date.today()

# Determine which months to show (e.g., current and next 2 months)
current_year = today.year
current_month = today.month

num_months_to_show = 3 # How many months to display
cols = st.columns(num_months_to_show) # Create columns for calendars

with st.container(border=False): # Group calendars visually
    st.caption("Referencia rápida de ocupación ( Rojo = Ocupado, Verde = Libre, Gris = Pasado ). Use los selectores de fecha abajo para reservar.")
    for i in range(num_months_to_show):
        target_month = current_month + i
        target_year = current_year
        if target_month > 12:
            target_month -= 12
            target_year += 1

        with cols[i]:
            # Add a class to the column div if needed for more specific CSS later
            st.markdown(f"<div class='calendar-column'>", unsafe_allow_html=True)
            calendar_html = generate_month_calendar_html(target_year, target_month, occupied_dates, today)
            st.markdown(calendar_html, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# --- Date Range Selection ---
st.divider() # Separate calendar from inputs
st.subheader("Seleccionar Fechas de Reserva")

# Find the first theoretical available date (might still be in the past)
first_available_date_obj = data_manager.get_first_available_date_for_property(property_id)
# Ensure the default start date is not in the past
suggested_start_date = max(first_available_date_obj, today) if first_available_date_obj else today

# Use columns for date inputs
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input(
        "Fecha de Inicio",
        value=suggested_start_date,
        min_value=today # Cannot book past dates
    )

# Calculate default end date based on start date weekday
if start_date:
    weekday = start_date.weekday()
    caption_text = ""
    if weekday == 4: # Friday
        default_end_date = start_date + timedelta(days=2)
        caption_text = "Viernes seleccionado. Fin por defecto: Domingo (2 noches)."
    elif weekday == 5: # Saturday
        default_end_date = start_date + timedelta(days=1)
        caption_text = "Sábado seleccionado. Fin por defecto: Domingo (1 noche)."
    else: # Other days
        default_end_date = start_date + timedelta(days=1)
        caption_text = "Fin por defecto: día siguiente (1 noche)."

    # Ensure default end date is valid
    min_end = start_date + timedelta(days=1)
    default_end_date = max(default_end_date, min_end)

else:
    # Fallback default if start_date is somehow None initially
    default_end_date = today + timedelta(days=1)
    caption_text = ""
    min_end = today + timedelta(days=1)


with col2:
    end_date = st.date_input(
        "Fecha de Fin",
        value=default_end_date,
        min_value=min_end, # End date must be at least one day after start date
        help="La fecha de fin se ajusta automáticamente para fines de semana. Puede cambiarla manualmente."
    )
    if caption_text:
        st.caption(caption_text)


# --- Check for Existing Bookings (Conflict Check) ---
# Convert date objects to datetime for comparison with DataFrame
start_datetime = pd.to_datetime(start_date)
end_datetime = pd.to_datetime(end_date) # This is the check-out day

# Check dates *strictly before* the end_datetime
# A booking ends *before* the new one starts OR starts *on or after* the new one ends
# Simplified check for CONFLICT: existing_start < new_end AND existing_end > new_start
# Note: existing_end is the CHECK-OUT day in the data.
# Note: new_end_datetime is the CHECK-OUT day selected by the user.
# Conflict if an existing booking's range [start, end) overlaps with the new booking's range [start, end)

existing_bookings = bookings_df[
    (bookings_df['property_id'] == property_id) &
    (bookings_df['start_date'] < end_datetime) & # Existing booking starts before the new one *ends*
    (bookings_df['end_date'] > start_datetime)   # Existing booking ends *after* the new one *starts*
]


conflict_status_placeholder = st.empty() # Placeholder for success/warning message

if not existing_bookings.empty:
    conflict_status_placeholder.warning(f"⚠️ **¡Conflicto de fechas!** La propiedad ya tiene reservas que se superponen con el período seleccionado ({start_date.strftime('%d-%b-%Y')} al {end_date.strftime('%d-%b-%Y')}). Verifique el calendario de disponibilidad arriba o las reservas existentes abajo.", icon="🚨")
    # Optional: Show conflicting bookings details immediately
    # st.write("Reservas superpuestas:")
    # st.dataframe(...) # As before
    add_booking_disabled = True # Disable button if conflict
else:
    conflict_status_placeholder.success(f"✅ Propiedad disponible para las fechas seleccionadas: {start_date.strftime('%d-%b-%Y')} a {end_date.strftime('%d-%b-%Y')}.")
    add_booking_disabled = False # Enable button if no conflict

# --- Booking Details ---
st.subheader("Detalles de la Reserva")
col_details1, col_details2, col_details3 = st.columns(3)

with col_details1:
    tenant_name = st.text_input("Nombre del Inquilino", placeholder="Ingrese el nombre (opcional)")
with col_details2:
    rent_amount = st.number_input("Monto del Alquiler", min_value=0.0, value=1000.0, step=100.0)
with col_details3:
    rent_currency = st.selectbox("Moneda", options=data_manager.CURRENCIES, index=0)


# --- Add Booking Button ---
st.divider()
if st.button("Confirmar y Reservar Propiedad", type="primary", disabled=add_booking_disabled, use_container_width=True):
    # --- Final Validation ---
    if not start_date or not end_date:
        st.error("Por favor, seleccione las fechas de inicio y fin.")
    elif end_date <= start_date:
        st.error("La fecha de fin debe ser posterior a la fecha de inicio.")
    else:
        # Re-check for conflicts just before adding
        start_dt_final = pd.to_datetime(start_date)
        end_dt_final = pd.to_datetime(end_date)
        final_conflict_check = data_manager.load_bookings() # Reload fresh data
        final_conflict = final_conflict_check[
            (final_conflict_check['property_id'] == property_id) &
            (final_conflict_check['start_date'] < end_dt_final) &
            (final_conflict_check['end_date'] > start_dt_final)
        ]
        if not final_conflict.empty:
             st.error("Error: Conflicto de fechas detectado justo antes de guardar. Alguien más pudo haber reservado. Por favor, actualice la página y verifique las fechas.")
        else:
            # --- Add Booking ---
            try:
                success = data_manager.add_booking(
                    property_id=property_id,
                    tenant_name=tenant_name or "Reserva Rápida",
                    start_date=start_date, # Pass date object
                    end_date=end_date,     # Pass date object
                    rent_amount=float(rent_amount),
                    rent_currency=rent_currency,
                    source="Reserva Rápida",
                    commission_paid=0.0,
                    commission_currency=None, # Explicitly None if no commission
                    notes="Reserva creada desde la página de Reserva Rápida"
                )

                if success:
                    st.success(f"¡Propiedad '{selected_property_name}' reservada exitosamente para {tenant_name or 'Reserva Rápida'} desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}!")
                    # Optionally clear inputs using session state or trigger rerun
                    st.rerun() # Rerun to refresh data and calendar
                else:
                    st.error("Error al guardar la reserva en el archivo. Revise los permisos o el espacio.")

            except Exception as e:
                st.error(f"Ocurrió un error inesperado al intentar agregar la reserva: {e}")
                st.exception(e)

# --- Display existing bookings for this property ---
st.divider()
st.subheader(f"Historial de Reservas para {selected_property_name}")
property_bookings = bookings_df[bookings_df['property_id'] == property_id].sort_values('start_date', ascending=False)

if property_bookings.empty:
    st.info("No se encontraron reservas para esta propiedad.")
else:
    # Display relevant columns and format dates
    display_cols = ['tenant_name', 'start_date', 'end_date', 'rent_amount', 'rent_currency', 'source', 'notes']
    display_df = property_bookings[display_cols].copy()
    display_df.rename(columns={
        'tenant_name': 'Inquilino',
        'start_date': 'Inicio',
        'end_date': 'Fin',
        'rent_amount': 'Monto',
        'rent_currency': 'Moneda',
        'source': 'Origen',
        'notes': 'Notas'
    }, inplace=True)

    # Format dates as strings for display and amount
    display_df['Inicio'] = display_df['Inicio'].dt.strftime('%Y-%m-%d')
    # Display end date as the last night stayed for clarity (end_date - 1 day)
    # display_df['Fin'] = (pd.to_datetime(display_df['Fin']) - timedelta(days=1)).dt.strftime('%Y-%m-%d')
    # OR display check-out date as is
    display_df['Fin'] = display_df['Fin'].dt.strftime('%Y-%m-%d')
    # Format currency
    display_df['Monto'] = display_df.apply(lambda row: f"{row['Monto']:,.2f} {row['Moneda']}" if pd.notna(row['Monto']) else '', axis=1)
    display_df.drop(columns=['Moneda'], inplace=True) # Remove original currency col


    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True
    )