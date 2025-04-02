import streamlit as st
import pandas as pd
import datetime
import data_manager # Assuming data_manager.py is in src/

# --- Page Configuration ---
st.set_page_config(page_title="Gestionar Reservas", page_icon="📅", layout="wide")
st.title("Gestionar Reservas 📅")

if not data_manager.check_password():
    st.stop()  # Do not continue if not authenticated



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
            #merged_df.drop(columns=['id_y'] if 'id_y' in merged_df.columns else ['id'], inplace=True, errors='ignore') # Drop the id from properties
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

            # display_df = display_df.apply(format_currency_amount, axis=1) # Apply formatting for display only

            # --- Display Dataframe with Selection ---
            # Configure columns for display formatting without changing underlying data
            st.dataframe(
                display_df, # Use the dataframe with renamed columns but original types for selection
                hide_index=True,
                use_container_width=True,
                on_select="rerun", # Trigger rerun on selection
                selection_mode="single-row", # Allow only single row selection
                key="booking_selector", # Assign a key to access selection state
                column_config={
                    "ID de Reserva": st.column_config.NumberColumn(
                        label="ID Reserva", # Short label
                        disabled=True, # Make ID non-editable in the grid display
                        help="ID único de la reserva (no editable aquí)"
                    ),
                    "Nombre de Propiedad": st.column_config.TextColumn(
                        label="Propiedad",
                        disabled=True,
                    ),
                    "Nombre del Inquilino": st.column_config.TextColumn(
                        label="Inquilino",
                        disabled=True,
                    ),
                    "Fecha de Inicio": st.column_config.DateColumn(
                        label="Inicio",
                        format="YYYY-MM-DD",
                        disabled=True,
                    ),
                    "Fecha de Fin": st.column_config.DateColumn(
                        label="Fin",
                        format="YYYY-MM-DD",
                        disabled=True,
                    ),
                    "Monto del Alquiler": st.column_config.NumberColumn(
                        label="Monto Alq.",
                        format="%.2f", # Format as number, currency shown separately
                        disabled=True,
                    ),
                    "Moneda Alquiler": st.column_config.TextColumn(
                        label="Moneda",
                        disabled=True,
                    ),
                     "Fuente": st.column_config.TextColumn(
                        label="Fuente",
                        disabled=True,
                    ),
                    "Comisión": st.column_config.NumberColumn(
                        label="Comisión",
                        format="%.2f", # Format as number, currency shown separately
                        disabled=True,
                    ),
                    "Moneda Comisión": st.column_config.TextColumn(
                        label="Moneda Com.",
                        disabled=True,
                    ),
                    "Notas": st.column_config.TextColumn(
                        label="Notas",
                        disabled=True,
                    ),
                }
            )

            # --- Edit/Delete Selected Booking ---
            if "booking_selector" in st.session_state and st.session_state.booking_selector.selection.rows:
                selected_index = st.session_state.booking_selector.selection.rows[0] # Get index of the selected row
                # Use filtered_df which has the original data before renaming/formatting
                selected_booking = filtered_df.iloc[selected_index].to_dict()
                st.text(selected_booking)
                selected_booking_id = selected_booking['id_x'] # Get the original ID

                st.divider()
                st.subheader(f"Editar/Eliminar Reserva ID: {selected_booking_id}")

                with st.form(key=f"edit_booking_{selected_booking_id}"):
                    # Get current property name from the selected booking's property_id
                    current_property_name = property_name_map.get(selected_booking['property_id'], None)
                    property_names_list = list(property_options.keys())
                    current_property_index = property_names_list.index(current_property_name) if current_property_name in property_names_list else 0

                    # --- Form Fields ---
                    col1, col2 = st.columns(2)
                    with col1:
                        edited_property_name = st.selectbox(
                            "Propiedad",
                            options=property_names_list,
                            index=current_property_index,
                            key=f"edit_prop_{selected_booking_id}"
                        )
                        edited_tenant_name = st.text_input(
                            "Nombre del Inquilino",
                            value=selected_booking['tenant_name'],
                            key=f"edit_tenant_{selected_booking_id}"
                        )
                        edited_start_date = st.date_input(
                            "Fecha de Inicio",
                            value=pd.to_datetime(selected_booking['start_date']).date(), # Ensure it's a date object
                            key=f"edit_start_{selected_booking_id}"
                        )
                        edited_end_date = st.date_input(
                            "Fecha de Fin",
                            value=pd.to_datetime(selected_booking['end_date']).date(), # Ensure it's a date object
                            key=f"edit_end_{selected_booking_id}"
                        )

                    with col2:
                        edited_rent_amount = st.number_input(
                            "Monto del Alquiler",
                            value=float(selected_booking['rent_amount']) if pd.notna(selected_booking['rent_amount']) else 0.0,
                            format="%.2f",
                            step=10.0,
                            key=f"edit_rent_{selected_booking_id}"
                        )
                        current_rent_currency_index = data_manager.CURRENCIES.index(selected_booking['rent_currency']) if selected_booking['rent_currency'] in data_manager.CURRENCIES else 0
                        edited_rent_currency = st.selectbox(
                            "Moneda Alquiler",
                            options=data_manager.CURRENCIES,
                            index=current_rent_currency_index,
                            key=f"edit_rent_curr_{selected_booking_id}"
                        )
                        current_source_index = BOOKING_SOURCES.index(selected_booking['source']) if selected_booking['source'] in BOOKING_SOURCES else 0
                        edited_source = st.selectbox(
                            "Fuente",
                            options=BOOKING_SOURCES,
                            index=current_source_index,
                            key=f"edit_source_{selected_booking_id}"
                        )

                        # Conditional Commission Fields
                        show_commission_edit = edited_source in SOURCES_REQUIRING_COMMISSION
                        edited_commission_paid = 0.0
                        edited_commission_currency = None
                        if show_commission_edit:
                            edited_commission_paid = st.number_input(
                                "Comisión Pagada",
                                value=float(selected_booking['commission_paid']) if pd.notna(selected_booking['commission_paid']) else 0.0,
                                format="%.2f",
                                step=5.0,
                                key=f"edit_comm_{selected_booking_id}"
                            )
                            current_comm_currency_index = data_manager.CURRENCIES.index(selected_booking['commission_currency']) if selected_booking['commission_currency'] in data_manager.CURRENCIES else current_rent_currency_index # Default to rent currency
                            edited_commission_currency = st.selectbox(
                                "Moneda Comisión",
                                options=data_manager.CURRENCIES,
                                index=current_comm_currency_index,
                                key=f"edit_comm_curr_{selected_booking_id}"
                            )

                    edited_notes = st.text_area(
                        "Notas",
                        value=selected_booking['notes'] if pd.notna(selected_booking['notes']) else "",
                        key=f"edit_notes_{selected_booking_id}"
                        )

                    # --- Form Buttons ---
                    save_button = st.form_submit_button("Guardar Cambios")
                    delete_button = st.form_submit_button("Eliminar Reserva", type="secondary")

                    # --- Save Logic ---
                    if save_button:
                        # Basic Validation (similar to add form)
                        edit_errors = []
                        if not edited_property_name:
                            edit_errors.append("Se debe seleccionar una propiedad.")
                        if not edited_tenant_name:
                            edit_errors.append("El nombre del inquilino no puede estar vacío.")
                        if edited_start_date >= edited_end_date:
                            edit_errors.append("La fecha de inicio debe ser anterior a la fecha de fin.")
                        if edited_rent_amount < 0:
                            edit_errors.append("El monto del alquiler no puede ser negativo.")
                        if show_commission_edit and edited_commission_paid < 0:
                             edit_errors.append("El monto de la comisión no puede ser negativo.")
                        # Add more validation as needed

                        if edit_errors:
                            for error in edit_errors:
                                st.error(error)
                        else:
                            try:
                                edited_property_id = property_options[edited_property_name]

                                booking_data = {
                                    'property_id': edited_property_id,
                                    'tenant_name': edited_tenant_name,
                                    'start_date': edited_start_date,
                                    'end_date': edited_end_date,
                                    'rent_amount': float(edited_rent_amount),
                                    'rent_currency': edited_rent_currency,
                                    'source': edited_source,
                                    'commission_paid': float(edited_commission_paid) if show_commission_edit else 0.0,
                                    'commission_currency': edited_commission_currency if show_commission_edit else None,
                                    'notes': edited_notes
                                }

                                success = data_manager.update_booking(selected_booking_id, **booking_data)

                                if success:
                                    st.success(f"¡Reserva ID {selected_booking_id} actualizada exitosamente!")
                                    # Clear selection state (indirectly via rerun)
                                    st.rerun()
                                else:
                                    st.error(f"Error al actualizar la reserva ID {selected_booking_id}. Consulte los logs.")

                            except Exception as e:
                                st.error(f"Ocurrió un error al guardar los cambios: {e}")

                    # --- Delete Logic --- 
                    if delete_button:
                        # Simple confirmation for now
                        st.warning(f"¿Está seguro de que desea eliminar la reserva ID {selected_booking_id} para '{selected_booking['tenant_name']}'?", icon="⚠️")
                        confirm_delete = st.checkbox("Sí, deseo eliminar esta reserva", key=f"delete_confirm_{selected_booking_id}")

                        if confirm_delete:
                            try:
                                success = data_manager.delete_booking(selected_booking_id)
                                if success:
                                    st.success(f"¡Reserva ID {selected_booking_id} eliminada exitosamente!")
                                    # Clear selection state (indirectly via rerun)
                                    st.rerun()
                                else:
                                    st.error(f"Error al eliminar la reserva ID {selected_booking_id}. Consulte los logs.")
                            except Exception as e:
                                st.error(f"Ocurrió un error al eliminar la reserva: {e}")


            # Clear selection if the selected row is no longer in the dataframe after filtering/updates
            # This might happen if the filter changes while a row was selected
            if "booking_selector" in st.session_state and st.session_state.booking_selector.selection.rows:
                 selected_index = st.session_state.booking_selector.selection.rows[0]
                 if selected_index >= len(filtered_df):
                      # The selected index is out of bounds, likely due to filtering
                      # We can't easily reset selection state directly, but rerun helps
                      # Or we could try: del st.session_state.booking_selector - but rerun is safer
                      pass # Rerun usually handles this implicitly


except FileNotFoundError:
    st.info("No se encontró el archivo de reservas. Se creará cuando agregue la primera reserva.")
except Exception as e:
    st.error(f"Ocurrió un error al cargar o mostrar las reservas: {e}")
    st.dataframe(pd.DataFrame()) # Display empty dataframe on error

