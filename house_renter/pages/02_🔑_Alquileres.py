import streamlit as st
import pandas as pd
import datetime
import data_manager # Assuming data_manager.py is in src/

# --- Page Configuration ---
st.set_page_config(page_title="Gestionar Reservas", layout="wide")
st.title("Gestionar Reservas 📅")

# --- Load Data ---
# Load properties for dropdowns and merging
try:
    properties_df = data_manager.load_properties()
    # Create a mapping from property name to ID for the form
    # Handle potential duplicate names if necessary, though ideally names are unique
    # If no properties, provide an empty dict and handle downstream
    if not properties_df.empty:
        property_options = pd.Series(properties_df.id.values, index=properties_df.name).to_dict()
        property_name_map = pd.Series(properties_df.name.values, index=properties_df.id).to_dict() # For display table
    else:
        property_options = {}
        property_name_map = {}
        st.warning("No se encontraron propiedades. Por favor, agregue propiedades en la página 'Gestionar Propiedades' primero.", icon="⚠️")

except Exception as e:
    st.error(f"Error al cargar propiedades: {e}")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS) # Empty df
    property_options = {}
    property_name_map = {}

# Define booking sources (Ideally, these might come from data_manager or a config file)
BOOKING_SOURCES = ['Direct', 'Airbnb', 'Booking.com', 'Vrbo', 'Other']
SOURCES_REQUIRING_COMMISSION = ['Airbnb', 'Booking.com', 'Vrbo'] # Example sources where commission is typical

# --- BOOK-001: Add Booking Form ---
with st.expander("Agregar Nueva Reserva"):
    st.subheader("Agregar Nueva Reserva")

    # Initialize error flags - No longer needed, using error messages list
    # property_error = False
    # tenant_name_error = False
    # start_date_error = False
    # end_date_error = False
    # rent_amount_error = False
    # source_error = False
    # commission_error = False

    # Use a form for batch input
    with st.form("add_booking_form"): # Removed clear_on_submit=True
        st.write("Ingrese los detalles para la nueva reserva:")

        # Property Selection
        if not property_options:
            st.error("No se puede agregar la reserva: No hay propiedades disponibles.")
            selected_property_name = None
        else:
            selected_property_name = st.selectbox(
                "Seleccionar Propiedad*",
                options=list(property_options.keys()),
                index=None, # No default selection
                placeholder="Elegir una propiedad...",
                help="Seleccione la propiedad para esta reserva."
            )
            # if property_error: # No longer needed
            #     st.error("Por favor, seleccione una propiedad.") # Will be shown in validation block


        # Booking Details Columns
        col1, col2 = st.columns(2)
        with col1:
            tenant_name = st.text_input("Nombre del Inquilino*", help="Ingrese el nombre del inquilino principal.")
            # if tenant_name_error: # No longer needed
            #     st.error("El Nombre del Inquilino es obligatorio.") # Will be shown in validation block

            start_date = st.date_input("Fecha de Inicio*", value=None, help="Fecha de inicio de la reserva.") # Defaults to today if value=datetime.date.today()
            # if start_date_error: # No longer needed
            #     st.error("La Fecha de Inicio es obligatoria.") # Will be shown in validation block

            rent_amount = st.number_input("Monto del Alquiler*", min_value=0.0, value=None, step=50.0, format="%.2f", help="Alquiler total para el período de la reserva.")
            # if rent_amount_error: # No longer needed
            #     st.error("El Monto del Alquiler es obligatorio y no puede ser negativo.") # Will be shown in validation block

            currency = st.selectbox(
                "Moneda Alquiler",
                options=data_manager.CURRENCIES,
                index=0,  # Default to the first currency
                help="Seleccione la moneda para el monto del alquiler."
            )
            source = st.selectbox(
                "Fuente de Reserva*",
                options=BOOKING_SOURCES,
                index=None,
                placeholder="Seleccione la fuente...",
                help="¿Cómo se realizó esta reserva?"
            )
            # if source_error: # No longer needed
            #     st.error("La Fuente de Reserva es obligatoria.") # Will be shown in validation block


        with col2:
            # Empty space or add other fields here if needed
            st.empty() # Placeholder to maintain layout balance if needed
            end_date = st.date_input("Fecha de Fin*", value=None, help="Fecha de fin de la reserva.")
            # if end_date_error: # No longer needed
            #     st.error("La Fecha de Fin es obligatoria y no puede ser anterior a la Fecha de Inicio.") # Will be shown in validation block

            # Conditional Commission Input
            commission_paid = 0.0 # Default to 0
            show_commission = source in SOURCES_REQUIRING_COMMISSION if source else False
            if show_commission:
                commission_paid = st.number_input(
                    "Comisión Pagada",
                    min_value=0.0,
                    value=0.0, # Default to 0 even when shown
                    step=10.0,
                    format="%.2f",
                    help=f"Comisión pagada a {source} (si aplica)."
                )
                # if commission_error: # No longer needed
                #     st.error("La Comisión Pagada no puede ser negativa.") # Will be shown in validation block
                commission_currency = st.selectbox(
                    "Moneda Comisión",
                    options=data_manager.CURRENCIES,
                    index=0,  # Default to the first currency
                    help="Seleccione la moneda para la comisión."
                )
            else:
                # Optionally display a disabled field or hide it completely
                st.empty() # Hide if not applicable
                commission_currency = None # Ensure commission_currency is None when no commission


        # Notes (spans across columns)
        notes = st.text_area("Notas", placeholder="Ingrese cualquier nota relevante sobre la reserva...", help="Notas opcionales.")

        # Submit Button
        submitted = st.form_submit_button("Agregar Reserva")

        if submitted:
            # --- Form Validation ---
            validation_passed = True
            error_messages = [] # List to collect error messages

            if not selected_property_name:
                # property_error = True # No longer needed
                validation_passed = False
                error_messages.append("Por favor, seleccione una propiedad.")
            if not tenant_name:
                # tenant_name_error = True # No longer needed
                validation_passed = False
                error_messages.append("El Nombre del Inquilino es obligatorio.")
            if not start_date:
                # start_date_error = True # No longer needed
                validation_passed = False
                error_messages.append("La Fecha de Inicio es obligatoria.")
            if not end_date:
                # end_date_error = True # No longer needed
                validation_passed = False
                error_messages.append("La Fecha de Fin es obligatoria.")
            if start_date and end_date and end_date < start_date:
                # end_date_error = True # Reusing end_date_error for date range issue # No longer needed
                validation_passed = False
                error_messages.append("La Fecha de Fin no puede ser anterior a la Fecha de Inicio.")
            if rent_amount is None or rent_amount < 0: # Check for None explicitly as 0 is valid
                 # rent_amount_error = True # No longer needed
                 validation_passed = False
                 error_messages.append("El Monto del Alquiler es obligatorio y no puede ser negativo.")
            if not source:
                # source_error = True # No longer needed
                validation_passed = False
                error_messages.append("La Fuente de Reserva es obligatoria.")
            if show_commission and commission_paid < 0:
                 # commission_error = True # No longer needed
                 validation_passed = False
                 error_messages.append("La Comisión Pagada no puede ser negativa.")

            if not validation_passed:
                for error_message in error_messages:
                    st.error(error_message) # Show all error messages

            # --- Add Booking if Validation Passed ---
            if validation_passed and selected_property_name:
                try:
                    selected_property_id = property_options[selected_property_name]


                    # Call data_manager function
                    success = data_manager.add_booking(
                        property_id=selected_property_id,
                        tenant_name=tenant_name,
                        start_date=start_date,
                        end_date=end_date,
                        rent_amount=float(rent_amount),
                        rent_currency=currency,
                        source=source,
                        commission_paid=float(commission_paid) if show_commission else 0.0, # Ensure commission is 0 if not applicable
                        commission_currency=currency if show_commission else None,
                        notes=notes
                    )

                    if success:
                        st.success(f"¡Reserva para '{tenant_name}' en la propiedad '{selected_property_name}' agregada exitosamente!")
                        # Form does not clear automatically now
                        # Rerun will load updated bookings
                    else:
                        # Error message likely shown by _save_data in data_manager
                        st.error("Error al agregar la reserva. Consulte los registros para obtener detalles.")

                except Exception as e:
                    st.error(f"Ocurrió un error al agregar la reserva: {e}")
            elif not selected_property_name and validation_passed:
                 st.error("No se puede agregar la reserva: No se seleccionó ninguna propiedad (esto no debería suceder si la validación pasó).")


# --- BOOK-002: Display Bookings List ---
st.divider()
st.subheader("Reservas Existentes")

# --- Filtering ---
# Prepare filter options, including "All"
filter_property_options = ["Todas las Propiedades"] + list(property_options.keys())
selected_filter_property_name = st.selectbox(
    "Filtrar por Propiedad",
    options=filter_property_options,
    index=0, # Default to "All Properties"
    help="Seleccione una propiedad para ver solo sus reservas."
)

# --- Load and Display Bookings ---
try:
    bookings_df = data_manager.load_bookings()

    if bookings_df.empty:
        st.info("No se encontraron reservas. Agregue una reserva usando el formulario de arriba.")
    else:
        # Merge with properties to get names
        # Ensure property_id types match for merging (Int64Dtype handles NA)
        if 'property_id' in bookings_df.columns and not properties_df.empty:
             # Convert property_id in properties_df to Int64Dtype if needed for merge compatibility
            if 'id' in properties_df.columns and properties_df['id'].dtype != bookings_df['property_id'].dtype:
                 try:
                     properties_df_merged = properties_df.astype({'id': bookings_df['property_id'].dtype})
                 except Exception as e:
                     st.warning(f"No se pudieron alinear los tipos de ID de propiedad para la fusión: {e}. Se muestran los IDs en lugar de los nombres.")
                     properties_df_merged = properties_df # Use original if cast fails
            else:
                 properties_df_merged = properties_df

            # Perform the merge
            # Use left merge to keep all bookings even if property is somehow missing (though ideally shouldn't happen)
            merged_df = pd.merge(
                bookings_df,
                properties_df_merged[['id', 'name']],
                left_on='property_id',
                right_on='id',
                how='left'
            )
            # Rename property name column and drop the redundant property 'id' column from the merge
            merged_df.rename(columns={'name': 'Nombre de Propiedad'}, inplace=True)
            merged_df.drop(columns=['id_y'] if 'id_y' in merged_df.columns else ['id'], inplace=True, errors='ignore') # Drop the id from properties
            # Fill missing property names if any occurred during merge
            merged_df['Nombre de Propiedad'].fillna('Propiedad Desconocida', inplace=True)

        else:
            merged_df = bookings_df.copy() # Work with bookings_df directly if no properties or ID column
            if 'property_id' in merged_df.columns:
                 merged_df['Nombre de Propiedad'] = merged_df['property_id'].map(property_name_map).fillna('Propiedad Desconocida')
            else:
                 merged_df['Nombre de Propiedad'] = 'N/A' # Or handle as appropriate if property_id is missing


        # Apply Filter
        if selected_filter_property_name != "Todas las Propiedades":
            filtered_df = merged_df[merged_df['Nombre de Propiedad'] == selected_filter_property_name]
        else:
            filtered_df = merged_df

        if filtered_df.empty and selected_filter_property_name != "Todas las Propiedades":
             st.info(f"No se encontraron reservas para la propiedad '{selected_filter_property_name}'.")
        elif filtered_df.empty:
             st.info("No se encontraron reservas que coincidan con el filtro actual.") # Should not happen if "All" selected unless df was empty initially
        else:
            # Select and order columns for display
            display_columns = [
                'Nombre de Propiedad', 'tenant_name', 'start_date', 'end_date',
                'rent_amount', 'rent_currency', 'source', 'commission_paid', 'commission_currency', 'notes', 'id' # Keep 'id' for reference if needed, maybe hide later
            ]
            # Filter columns that actually exist in the dataframe
            display_columns = [col for col in display_columns if col in filtered_df.columns]

            display_df = filtered_df[display_columns].copy()

            # Rename columns for better readability
            display_df.rename(columns={
                'tenant_name': 'Nombre del Inquilino',
                'start_date': 'Fecha de Inicio',
                'end_date': 'Fecha de Fin',
                'rent_amount': 'Monto del Alquiler', # Removed currency from header
                'rent_currency': 'Moneda Alquiler', # Added currency column header
                'source': 'Fuente',
                'commission_paid': 'Comisión', # Removed currency from header
                'commission_currency': 'Moneda Comisión', # Added currency column header
                'notes': 'Notas',
                'id': 'ID de Reserva'
            }, inplace=True)

            # Format date columns if they are not already strings
            if 'Fecha de Inicio' in display_df.columns:
                 display_df['Fecha de Inicio'] = pd.to_datetime(display_df['Fecha de Inicio']).dt.strftime('%Y-%m-%d')
            if 'Fecha de Fin' in display_df.columns:
                 display_df['Fecha de Fin'] = pd.to_datetime(display_df['Fecha de Fin']).dt.strftime('%Y-%m-%d')

            # Format currency columns and amounts
            def format_currency_amount(row):
                rent_amount = row['Monto del Alquiler']
                rent_currency = row['Moneda Alquiler']
                commission_paid = row['Comisión']
                commission_currency = row['Moneda Comisión']

                if pd.notna(rent_amount) and pd.notna(rent_currency):
                    row['Monto del Alquiler'] = f"{rent_amount:,.2f} {rent_currency}"
                if pd.notna(commission_paid) and pd.notna(commission_currency):
                    row['Comisión'] = f"{commission_paid:,.2f} {commission_currency}"
                return row

            display_df = display_df.apply(format_currency_amount, axis=1)
            display_df.drop(columns=['Moneda Alquiler', 'Moneda Comisión'], inplace=True) # Remove separate currency columns after formatting


            # Display the dataframe
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                # Optional: Configure column widths or types if needed
                # column_config={
                #     "Rent Amount (€)": st.column_config.NumberColumn(format="€%.2f"),
                #     "Commission (€)": st.column_config.NumberColumn(format="€%.2f"),
                # }
                # Using map for formatting as column_config might require specific Streamlit versions
            )

except FileNotFoundError:
    st.info("No se encontró el archivo de reservas. Se creará cuando agregue la primera reserva.")
except Exception as e:
    st.error(f"Ocurrió un error al cargar o mostrar las reservas: {e}")
    st.dataframe(pd.DataFrame()) # Display empty dataframe on error

