import streamlit as st
import pandas as pd
import sys
import os
import data_manager

if not data_manager.check_password():
    st.stop()  # Do not continue if not authenticated

# Add the parent directory (src) to the Python path to allow importing data_manager
# This assumes the pages directory is directly inside src
# Adjust the path if your structure is different
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

st.title("🏘️ Gestionar Propiedades")
st.markdown("Agregue nuevas propiedades, vea o edite las existentes.")

# --- PROP-001: Add Property Form ---
with st.expander("Agregar Nueva Propiedad"):
    # Use a form for adding properties
    # clear_on_submit=True ensures fields are reset after successful submission
    with st.form("add_property_form", clear_on_submit=True):
        property_name = st.text_input("Nombre de la Propiedad*", help="Ingrese el nombre o identificador de la propiedad (ej., 'Departamento Centro', 'Casa de Playa').")
        property_address = st.text_area("Dirección", help="Ingrese la dirección completa de la propiedad.")
        property_owner = st.text_input("Propietario*", help="Ingrese el nombre del propietario de la propiedad.")

        # Submit button for the form
        submitted_add = st.form_submit_button("Agregar Propiedad")

        if submitted_add:
            # Basic validation
            if not property_name:
                st.warning("El Nombre de la Propiedad es obligatorio.")
            elif not property_owner:
                st.warning("El Propietario es obligatorio.")
            else:
                # Call the function from data_manager to add the property
                try:
                    success = data_manager.add_property(name=property_name, address=property_address, owner=property_owner)
                    if success:
                        st.success(f"¡Propiedad '{property_name}' agregada exitosamente para el propietario '{property_owner}'!")
                        # No need to manually clear fields due to clear_on_submit=True
                        # Streamlit will rerun, and load_properties will fetch the updated list
                    else:
                        # data_manager._save_data already shows an st.error
                        st.error(f"Error al agregar la propiedad '{property_name}'. Por favor, revise los registros de la aplicación.")
                        # Form fields will persist in case of error for correction
                except Exception as e:
                    st.error(f"Error inesperado al agregar la propiedad '{property_name}': {e}")


# --- PROP-002: Display Property List ---
st.divider() # Add a visual separator
st.subheader("Propiedades Existentes")

# Load properties using the function from data_manager
# This benefits from @st.cache_data in data_manager
try:
    properties_df = data_manager.load_properties()
except Exception as e:
    st.error(f"Error al cargar propiedades: {e}. Por favor, asegúrese de que el archivo de datos exista y sea accesible.")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS) # Provide empty df

if properties_df.empty:
    st.info("No se encontraron propiedades. Agregue una propiedad usando el formulario de arriba.")
else:
    # Display properties in a dataframe
    # Select and potentially rename columns for better presentation
    # Ensure 'id', 'name', 'address', 'owner' exist before trying to access them
    display_columns = [col for col in ['id', 'name', 'address', 'owner'] if col in properties_df.columns]
    if not display_columns or 'name' not in display_columns: # Ensure at least 'name' is present
        st.warning("Los datos de la propiedad no tienen las columnas esperadas ('id', 'name', 'address', 'owner'). Mostrando datos sin procesar.")
        st.dataframe(properties_df, use_container_width=True)
    else:
        display_df = properties_df[display_columns].copy()
        # Optional: Rename columns for display
        display_df.rename(columns={'name': 'Nombre', 'address': 'Dirección', 'id': 'ID', 'owner': 'Propietario'}, inplace=True)
        st.dataframe(
            display_df,
            hide_index=True, # Don't show the default pandas index
            use_container_width=True # Make the table use the full container width
        )

    # --- PROP-003: Edit Property Section ---
    st.divider()
    st.subheader("Editar Propiedad Existente")

    # Create a mapping from a display string (Name (ID)) to the actual ID
    # Ensure 'id' and 'name' columns exist and handle potential missing values gracefully
    if 'id' in properties_df.columns and 'name' in properties_df.columns:
        property_options = {
            f"{row['name']} (ID: {row['id']})": row['id']
            for index, row in properties_df.dropna(subset=['id', 'name']).iterrows()
        }
        if not property_options:
             st.warning("No hay propiedades válidas (con ID y Nombre) para seleccionar.")
             selected_property_display = None
        else:
            selected_property_display = st.selectbox(
                "Seleccione la propiedad a editar:",
                options=list(property_options.keys()),
                index=None, # Default to no selection
                placeholder="Elija una propiedad..."
            )
    else:
        st.warning("El archivo de propiedades no contiene las columnas 'id' o 'name' necesarias para la edición.")
        selected_property_display = None


    if selected_property_display:
        selected_property_id = property_options[selected_property_display]
        # Get the details of the selected property
        # Use .loc for safer indexing and handle potential type issues
        try:
            # Ensure we compare with the correct type if 'id' is Int64
            property_to_edit = properties_df.loc[properties_df['id'] == selected_property_id].iloc[0]
        except IndexError:
            st.error(f"No se pudo encontrar la propiedad con ID {selected_property_id} seleccionada. Intente recargar.")
            st.stop() # Stop if the selected property vanished somehow

        with st.form(f"edit_property_form_{selected_property_id}"): # Unique key for the form
            st.markdown(f"**Editando:** {property_to_edit.get('name', 'N/A')} (ID: {property_to_edit.get('id', 'N/A')})")

            # Pre-fill form fields, using .get for safety if columns are missing unexpectedly
            edit_name = st.text_input("Nuevo Nombre*", value=property_to_edit.get('name', ''))
            edit_address = st.text_area("Nueva Dirección", value=property_to_edit.get('address', ''))
            edit_owner = st.text_input("Nuevo Propietario*", value=property_to_edit.get('owner', ''))

            submitted_update = st.form_submit_button("Actualizar Propiedad")

            if submitted_update:
                # Validation
                if not edit_name:
                    st.warning("El Nombre de la Propiedad es obligatorio.")
                elif not edit_owner:
                    st.warning("El Propietario es obligatorio.")
                else:
                    # Call update function from data_manager
                    try:
                        success = data_manager.update_property(
                            property_id=selected_property_id, # Pass the actual ID
                            name=edit_name,
                            address=edit_address,
                            owner=edit_owner
                        )
                        if success:
                            st.success(f"¡Propiedad (ID: {selected_property_id}) actualizada exitosamente!")
                            # Use st.rerun() to refresh the page state, clear the form, and update the list
                            st.rerun()
                        else:
                            # data_manager should show specific error via st.error
                            st.error(f"Error al actualizar la propiedad (ID: {selected_property_id}). Revise los mensajes anteriores o los registros.")
                            # Form fields persist on error for correction
                    except Exception as e:
                        st.error(f"Error inesperado al actualizar la propiedad (ID: {selected_property_id}): {e}")
    elif selected_property_display is None and property_options: # Only show if options were available but none selected
         st.info("Seleccione una propiedad de la lista de arriba para editarla.")

