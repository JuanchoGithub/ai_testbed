import streamlit as st
import pandas as pd
import data_manager
from datetime import date, timedelta

if not data_manager.check_password():
    st.stop()  # Do not continue if not authenticated
# --- Page Configuration ---
st.title("💸 Gestionar Gastos")

# --- Constants ---
EXPENSE_CATEGORIES = [
    "Mantenimiento", "Reparaciones", "Servicios", "Honorarios de Gestión",
    "Impuestos", "Seguros", "Suministros", "Limpieza", "Viajes", "Otros"
]
CURRENCY_OPTIONS = ["ARS", "USD", "EUR"] # Add more if needed, EUR already there as default

# --- Load Data ---
try:
    properties_df = data_manager.load_properties()
    expenses_df = data_manager.load_expenses()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS)
    expenses_df = pd.DataFrame(columns=data_manager.EXPENSES_COLS)

# --- EXP-001: Add Expense Form ---
with st.expander("Agregar Nuevo Gasto"):
    if properties_df.empty:
        st.warning("No se encontraron propiedades. Por favor, agregue una propiedad primero en la página 'Administrar Propiedades'.")
    else:
        # Create a dictionary mapping property names to IDs for the selectbox
        property_options = {row['name']: row['id'] for index, row in properties_df.iterrows()}
        property_names = list(property_options.keys())

        with st.form("add_expense_form", clear_on_submit=True):
            st.write("Registrar un nuevo gasto para una propiedad:")

            # Property Selection
            selected_property_name = st.selectbox(
                "Seleccionar Propiedad*",
                options=property_names,
                index=0, # Default to the first property
                help="Elija la propiedad a la que corresponde este gasto."
            )

            # Expense Date
            expense_date = st.date_input(
                "Fecha del Gasto*",
                value=date.today(), # Default to today
                help="La fecha en que se incurrió en el gasto."
            )

            # Category
            category = st.selectbox(
                "Categoría*",
                options=EXPENSE_CATEGORIES,
                index=0, # Default to the first category
                help="Seleccione el tipo de gasto."
            )

            # Amount
            amount = st.number_input(
                "Monto*",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help="Ingrese el costo del gasto."
            )

            # Currency
            currency = st.selectbox(
                "Moneda",
                options=CURRENCY_OPTIONS,
                index=0, # Default to ARS
                help="Seleccione la moneda del gasto."
            )

            # Description
            description = st.text_area(
                "Descripción",
                placeholder="Opcional: Agregue detalles sobre el gasto (ej., número de factura, servicio específico).",
                help="Proporcione cualquier detalle relevante sobre el gasto."
            )

            # Submit Button
            submitted = st.form_submit_button("Agregar Gasto")

            if submitted:
                # Basic validation (although some is handled by widgets)
                if not selected_property_name or not expense_date or not category or amount <= 0:
                    st.warning("Por favor, complete todos los campos obligatorios (*) con valores válidos.")
                else:
                    # Get the property ID from the selected name
                    property_id = property_options[selected_property_name]

                    # Call data_manager function to add the expense
                    try:
                        success = data_manager.add_expense(
                            property_id=property_id,
                            expense_date=expense_date,
                            category=category,
                            amount=amount,
                            currency=currency, # Pass the selected currency
                            description=description if description else None # Pass None if empty
                        )

                        if success:
                            st.success(f"¡Gasto de {currency} {amount:.2f} para '{selected_property_name}' el {expense_date} agregado exitosamente!")
                            # Form clears automatically due to clear_on_submit=True
                            # Rerun will load updated expenses
                        else:
                            st.error("Error al agregar gasto. Por favor, revise los datos ingresados e intente nuevamente.")

                    except Exception as e:
                        st.error(f"Error inesperado al agregar gasto: {e}")

# --- EXP-002: Display Expenses List ---
st.divider()
st.subheader("Gastos Existentes")

if expenses_df.empty:
    st.info("Aún no se han registrado gastos. Utilice el formulario de arriba para agregar uno.")
else:
    # --- Filtering Options ---
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        # Property Filter
        filter_property_options = {"Todas las Propiedades": None}
        filter_property_options.update({name: prop_id for name, prop_id in property_options.items()})
        selected_filter_property_name = st.selectbox(
            "Filtrar por Propiedad",
            options=list(filter_property_options.keys()),
            index=0 # Default to "All Properties"
        )
        selected_filter_property_id = filter_property_options[selected_filter_property_name]

    # Date Range Filter - Default to last 90 days or min/max dates
    min_date = expenses_df['expense_date'].min().date() if not expenses_df['expense_date'].isnull().all() else date.today() - timedelta(days=90)
    max_date = expenses_df['expense_date'].max().date() if not expenses_df['expense_date'].isnull().all() else date.today()

    with col2:
        filter_start_date = st.date_input("Fecha de Inicio", value=min_date, min_value=min_date, max_value=max_date)
    with col3:
        filter_end_date = st.date_input("Fecha de Fin", value=max_date, min_value=min_date, max_value=max_date)

    # --- Data Preparation and Filtering ---
    try:
        # Merge with properties to get names
        # Ensure 'id' in properties_df is the correct type for merging if needed
        if 'id' in properties_df.columns:
            properties_df['id'] = properties_df['id'].astype(pd.Int64Dtype()) # Match type if needed
        if 'property_id' in expenses_df.columns:
             expenses_df['property_id'] = expenses_df['property_id'].astype(pd.Int64Dtype())

        # Perform the merge
        merged_df = pd.merge(
            expenses_df,
            properties_df[['id', 'name']],
            left_on='property_id',
            right_on='id',
            how='left' # Keep all expenses even if property is deleted/missing
        )
        # Fill missing property names if any occurred during merge
        merged_df['name'] = merged_df['name'].fillna('Unknown Property')
        merged_df.rename(columns={'name': 'Property Name'}, inplace=True)

        # Apply filters
        filtered_df = merged_df.copy()

        # Filter by Property
        if selected_filter_property_id is not None:
            filtered_df = filtered_df[filtered_df['property_id'] == selected_filter_property_id]

        # Filter by Date Range (ensure comparison is between date objects or timestamps)
        # Convert filter dates to datetime objects for comparison
        start_datetime = pd.to_datetime(filter_start_date)
        end_datetime = pd.to_datetime(filter_end_date)
        # Ensure expense_date is also datetime
        filtered_df['expense_date'] = pd.to_datetime(filtered_df['expense_date'])

        filtered_df = filtered_df[
            (filtered_df['expense_date'] >= start_datetime) &
            (filtered_df['expense_date'] <= end_datetime)
        ]

        # --- Display Table ---
        if filtered_df.empty:
            st.info("No hay gastos que coincidan con los criterios de filtro actuales.")
        else:
            # Select and order columns for display
            display_columns = [
                'Property Name', 'expense_date', 'category', 'amount', 'currency', 'description', 'id'
            ]
            # Filter columns that actually exist in the dataframe
            display_columns = [col for col in display_columns if col in filtered_df.columns]
            display_df = filtered_df[display_columns].copy()

            # Rename columns for better readability
            display_df.rename(columns={
                'expense_date': 'Fecha',
                'category': 'Categoría',
                'amount': 'Amount', # Remove currency symbol from column name
                'currency': 'Moneda',
                'description': 'Descripción',
                'id': 'ID de Gasto'
            }, inplace=True)

            # Format date column
            if 'Fecha' in display_df.columns:
                 display_df['Fecha'] = pd.to_datetime(display_df['Fecha']).dt.strftime('%Y-%m-%d')

            # Format currency column - now format amount and append currency symbol
            if 'Amount' in display_df.columns:
                display_df['Amount'] = display_df.apply(lambda row: f"{row['Moneda']} {row['Amount']:.2f}", axis=1)


            # Display the dataframe
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_order=[col for col in ['Nombre de Propiedad', 'Fecha', 'Categoría', 'Amount', 'Moneda', 'Descripción', 'ID de Gasto'] if col in display_df.columns]
                # Optional: Configure column widths or types if needed
                # column_config={ ... }
            )

            # --- Summary Statistics ---
            st.subheader("Resumen de Gastos Filtrados")
            total_expenses = pd.to_numeric(filtered_df['amount'], errors='coerce').sum()
            display_currency_summary = filtered_df['currency'].iloc[0] if not filtered_df.empty else "ARS" # Default to ARS for summary if no data
            st.metric("Total de Gastos (Filtrados)", f"{display_currency_summary} {total_expenses:,.2f}")

            # Optional: Add more summary stats like count or average

    except Exception as e:
        st.error(f"Ocurrió un error al preparar o mostrar los gastos: {e}")
        st.dataframe(pd.DataFrame()) # Display empty dataframe on error

        if not filtered_df.empty and 'currency' in filtered_df.columns:
            # Get the first currency from the filtered data to display in the table header and summary
            # Assuming all expenses in the filtered view are in the same currency for simplicity in display.
            # If mixed currencies are expected, more complex handling would be needed.
            display_currency = filtered_df['currency'].iloc[0]
        else:
            display_currency = 'ARS' # Default to ARS if no data or currency info

        # Rename columns for better readability, using dynamic currency symbol
        display_df.rename(columns={
            'expense_date': 'Fecha',
            'category': 'Categoría',
            'amount': f'Amount', # Remove currency symbol from column name
            'currency': 'Moneda',
            'description': 'Descripción',
            'id': 'ID de Gasto'
        }, inplace=True)

        # Format currency column, using dynamic currency symbol in column name
        amount_column_name = 'Amount' # Column name is now 'Amount'
        if amount_column_name in display_df.columns:
            display_df[amount_column_name] = display_df.apply(lambda row: f"{display_currency} {row['Moneda']:.2f}" if 'Moneda' in row else f"{display_currency} {row['Amount']:.2f}", axis=1)


        # Update column order to use dynamic currency column name
        column_order = [col for col in ['Nombre de Propiedad', 'Fecha', 'Categoría', amount_column_name, 'Moneda', 'Descripción', 'ID de Gasto'] if col in display_df.columns]

        # Display the dataframe with dynamic column order
        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            column_order=column_order
            # Optional: Configure column widths or types if needed
            # column_config={ ... }
        )

        # --- Summary Statistics ---
        st.subheader("Resumen de Gastos Filtrados")
        total_expenses = pd.to_numeric(filtered_df['amount'], errors='coerce').sum()
        st.metric("Total de Gastos (Filtrados)", f"{display_currency} {total_expenses:,.2f}")

        # Optional: Add more summary stats like count or average
