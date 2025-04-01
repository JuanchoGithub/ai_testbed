import streamlit as st
import pandas as pd
import data_manager
from datetime import datetime, timedelta
import os
import calendar

# --- Constants ---
LIQUIDATIONS_DIR = os.path.join(data_manager.DATA_DIR, "liquidations")
LIQUIDATION_COLS = ['year', 'month', 'type', 'identifier', 'commission_percentage', 'total_income', 'total_expenses', 'commission_amount', 'owner_net', 'calculation_timestamp']

# --- Helper Functions ---
def _ensure_liquidations_dir():
    """Ensures the liquidations directory exists."""
    if not os.path.exists(LIQUIDATIONS_DIR):
        os.makedirs(LIQUIDATIONS_DIR)
        print(f"Created liquidations directory: {LIQUIDATIONS_DIR}")

def _get_liquidation_filepath(year, month, liq_type, identifier):
    """Generates a unique filepath for a liquidation report."""
    _ensure_liquidations_dir()
    # Sanitize identifier for filename
    safe_identifier = "".join(c if c.isalnum() else "_" for c in str(identifier))
    # Ensure type is clean
    safe_liq_type = liq_type.lower().replace(" ", "_")
    filename = f"liq_{year}_{month:02d}_{safe_liq_type}_{safe_identifier}.csv"
    return os.path.join(LIQUIDATIONS_DIR, filename)

def load_liquidation(filepath):
    """Loads a specific liquidation report if it exists."""
    if os.path.exists(filepath):
        try:
            # Load the single row CSV
            df = pd.read_csv(filepath)
            if not df.empty:
                # Convert to dictionary for easier access
                data = df.iloc[0].to_dict()
                # Basic validation/type conversion
                data['year'] = int(data['year'])
                data['month'] = int(data['month'])
                data['commission_percentage'] = float(data['commission_percentage'])
                data['total_income'] = float(data['total_income'])
                data['total_expenses'] = float(data['total_expenses'])
                data['commission_amount'] = float(data['commission_amount'])
                data['owner_net'] = float(data['owner_net'])
                return data
            else:
                print(f"Liquidation file is empty: {filepath}")
                return None
        except Exception as e:
            st.error(f"Error al cargar liquidación guardada ({filepath}): {e}")
            return None
    return None

def save_liquidation(data, filepath):
    """Saves the liquidation data to a CSV file."""
    try:
        df = pd.DataFrame([data])
        # Ensure correct column order
        df = df[LIQUIDATION_COLS]
        df.to_csv(filepath, index=False)
        return True
    except Exception as e:
        st.error(f"Error al guardar liquidación ({filepath}): {e}")
        return False

def generate_liquidation_report_html(results, filtered_bookings_for_display, filtered_expenses_for_display, properties_df, month_names_es, currency):
    """Generates an HTML report for liquidation, designed for print-to-pdf."""

    month_name = month_names_es[results['month']]
    report_title = f"Liquidación Mensual - {month_name} {results['year']}"
    identifier_display = f"{results['type'].replace('_', ' ').capitalize()} - {results['identifier']}"

    report_html = f"""
    <html>
    <head>
        <title>{report_title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1, h2, h3 {{ color: #333; }}
            .totals {{ margin-bottom: 20px; }}
            .total-metric {{ font-size: 1.2em; margin-right: 20px; }}
            .daily-section {{ margin-top: 20px; border-top: 1px solid #ccc; padding-top: 10px; }}
            .daily-header {{ font-weight: bold; margin-bottom: 5px; }}
            .daily-item {{ margin-bottom: 3px; }}
            .daily-summary {{ font-weight: bold; margin-top: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f0f0f0; }}
        </style>
    </head>
    <body>
        <h1>{report_title}</h1>
        <p><strong>Liquidación para:</strong> {identifier_display}</p>
        <p><strong>Periodo:</strong> {month_name} {results['year']}</p>
        <p><strong>Comisión Aplicada:</strong> {results['commission_percentage']:.2f}%</p>

        <div class="totals">
            <span class="total-metric"><strong>💰 Ingresos Totales:</strong> {currency}{results['total_income']:,.2f}</span>
            <span class="total-metric"><strong>💸 Gastos Totales:</strong> {currency}{results['total_expenses']:,.2f}</span>
            <span class="total-metric"><strong>📊 Comisión Gestor:</strong> {currency}{results['commission_amount']:,.2f}</span>
            <span class="total-metric"><strong>🏦 Neto para Propietario:</strong> {currency}{results['owner_net']:,.2f}</span>
        </div>
    """

    # Daily Breakdown
    date_range = pd.date_range(start=f"{results['year']}-{results['month']}-01", periods=calendar.monthrange(results['year'], results['month'])[1])
    for day_date in date_range:
        daily_bookings = filtered_bookings_for_display[filtered_bookings_for_display['end_date'].dt.date == day_date.date()]
        daily_expenses = filtered_expenses_for_display[filtered_expenses_for_display['expense_date'].dt.date == day_date.date()]

        daily_income_total = daily_bookings['rent_amount'].sum()
        daily_expense_total = daily_expenses['amount'].sum()
        daily_net = daily_income_total - daily_expense_total

        report_html += f"""
        <div class="daily-section">
            <h3 class="daily-header">{day_date.strftime('%Y-%m-%d')}</h3>
            <h4>Ingresos:</h4>
        """
        if not daily_bookings.empty:
            report_html += "<ul>"
            for index, booking in daily_bookings.iterrows():
                property_name = properties_df.loc[properties_df['id'] == booking['property_id'], 'name'].iloc[0] if booking['property_id'] in properties_df['id'].values else 'N/A'
                report_html += f"""<li class="daily-item">Reserva Propiedad: {property_name}, Inquilino: {booking['tenant_name']}, Monto: {currency}{booking['rent_amount']:.2f} ({booking['source']})</li>"""
            report_html += "</ul>"
        else:
            report_html += "<p>No hay ingresos este día.</p>"

        report_html += f"<h4>Gastos:</h4>"
        if not daily_expenses.empty:
            report_html += "<ul>"
            for index, expense in daily_expenses.iterrows():
                property_name = properties_df.loc[properties_df['id'] == expense['property_id'], 'name'].iloc[0] if expense['property_id'] in properties_df['id'].values else 'N/A'
                report_html += f"""<li class="daily-item">Propiedad: {property_name}, Categoría: {expense['category']}, Monto: {currency}{expense['amount']:.2f} ({expense['description']})</li>"""
            report_html += "</ul>"
        else:
            report_html += "<p>No hay gastos este día.</p>"

        report_html += f"""
            <p class="daily-summary"><strong>Resumen Diario:</strong> Ingresos: {currency}{daily_income_total:.2f}, Gastos: {currency}{daily_expense_total:.2f}, Neto Diario: {currency}{daily_net:.2f}</p>
        </div>
        """

    # Detailed Tables (optional - can be added back if needed in PDF)
    report_html += """
        <h2>Detalle de Ingresos (Reservas Finalizadas en el Mes)</h2>
    """
    if not filtered_bookings_for_display.empty:
        # Prepare a user-friendly dataframe for display in HTML table
        bookings_display_report = filtered_bookings_for_display.copy()
        property_names = {}
        for index, row in properties_df.iterrows():
            property_names[row['id']] = row['name']
        bookings_display_report['property'] = bookings_display_report['property_id'].map(property_names)
        bookings_display_report['start_date'] = bookings_display_report['start_date'].dt.strftime('%Y-%m-%d')
        bookings_display_report['end_date'] = bookings_display_report['end_date'].dt.strftime('%Y-%m-%d')

        # Add currency column if it doesn't exist
        if 'currency' not in bookings_display_report.columns:
            bookings_display_report['currency'] = currency  # Use the determined currency

        display_cols_report = ['property', 'tenant_name', 'start_date', 'end_date', 'rent_amount', 'currency', 'source']
        # Ensure all columns in display_cols_report exist in bookings_display_report
        existing_cols = [col for col in display_cols_report if col in bookings_display_report.columns]
        bookings_display_report = bookings_display_report[existing_cols]
        bookings_display_report.columns = ['Propiedad', 'Inquilino', 'Fecha Inicio', 'Fecha Fin', 'Monto Alquiler', 'Moneda', 'Origen'][:len(existing_cols)] # Rename for display

        report_html += bookings_display_report.to_html(index=False, classes='table table-striped') # Convert DataFrame to HTML table
    else:
        report_html += "<p>No se encontraron reservas finalizadas en este periodo para la selección.</p>"

    report_html += """
        <h2>Detalle de Gastos del Mes</h2>
    """
    if not filtered_expenses_for_display.empty:
        expenses_display_report = filtered_expenses_for_display[['id', 'property_id', 'expense_date', 'category', 'amount', 'currency', 'description']].copy()
        expenses_display_report['expense_date'] = expenses_display_report['expense_date'].dt.strftime('%Y-%m-%d') #format date
        expenses_display_report.columns = ['ID', 'ID Propiedad', 'Fecha Gasto', 'Categoría', 'Monto', 'Moneda', 'Descripción'] # Rename columns for display in report

        report_html += expenses_display_report.to_html(index=False, classes='table table-striped')
    else:
        report_html += "<p>No se encontraron gastos en este periodo para la selección.</p>"


    report_html += """
    </body>
    </html>
    """
    return report_html


# --- Page Configuration ---
st.set_page_config(page_title="Liquidación Mensual", page_icon="📈", layout="wide")
st.title("📈 Liquidación Mensual")
st.markdown("Calcule y visualice los ingresos, gastos y beneficios netos mensuales para un propietario o propiedad específica.")

# --- Load Data ---
try:
    properties_df = data_manager.load_properties()
    bookings_df = data_manager.load_bookings()
    expenses_df = data_manager.load_expenses()

    # Ensure date columns are datetime objects and handle potential errors
    if not bookings_df.empty:
        bookings_df['start_date'] = pd.to_datetime(bookings_df['start_date'], errors='coerce')
        bookings_df['end_date'] = pd.to_datetime(bookings_df['end_date'], errors='coerce')
        bookings_df.dropna(subset=['start_date', 'end_date'], inplace=True)
    if not expenses_df.empty:
        expenses_df['expense_date'] = pd.to_datetime(expenses_df['expense_date'], errors='coerce')
        expenses_df.dropna(subset=['expense_date'], inplace=True)

    # Ensure numeric columns are numeric
    if 'rent_amount' in bookings_df.columns:
        bookings_df['rent_amount'] = pd.to_numeric(bookings_df['rent_amount'], errors='coerce').fillna(0)
    if 'commission_paid' in bookings_df.columns: # This is commission paid to platforms, not manager commission
         bookings_df['commission_paid'] = pd.to_numeric(bookings_df['commission_paid'], errors='coerce').fillna(0)
    if 'amount' in expenses_df.columns:
        expenses_df['amount'] = pd.to_numeric(expenses_df['amount'], errors='coerce').fillna(0)

except Exception as e:
    st.error(f"Error crítico al cargar o procesar datos iniciales: {e}")
    # Initialize empty dataframes with expected columns if loading fails
    properties_df = pd.DataFrame(columns=getattr(data_manager, 'PROPERTIES_COLS', ['id', 'name', 'address', 'owner']))
    bookings_df = pd.DataFrame(columns=getattr(data_manager, 'BOOKINGS_COLS', ['id', 'property_id', 'tenant_name', 'start_date', 'end_date', 'rent_amount', 'source', 'commission_paid', 'notes']))
    expenses_df = pd.DataFrame(columns=getattr(data_manager, 'EXPENSES_COLS', ['id', 'property_id', 'expense_date', 'category', 'amount', 'description']))
    st.stop() # Stop execution if basic data loading fails

# --- Check if data is available ---
if properties_df.empty:
    st.warning("No se encontraron propiedades. Agregue propiedades en 'Gestionar Propiedades'.")
    st.stop()
if 'owner' not in properties_df.columns or 'id' not in properties_df.columns or 'name' not in properties_df.columns:
    st.error("Faltan columnas esenciales ('id', 'name', 'owner') en los datos de propiedades. Verifique 'properties.csv'.")
    st.stop()
if 'property_id' not in bookings_df.columns or 'property_id' not in expenses_df.columns:
     st.error("Falta la columna 'property_id' en los datos de reservas o gastos. Verifique 'bookings.csv' y 'expenses.csv'.")
     st.stop()


# --- UI Elements for Selection ---
st.subheader("Seleccionar Periodo y Criterio")

# Get unique owners and properties for selectors
owners = sorted(properties_df['owner'].unique())
property_options = {f"{row['name']} (ID: {row['id']})": row['id'] for index, row in properties_df.iterrows()}
property_display_names = list(property_options.keys())

col1, col2, col3 = st.columns(3)
with col1:
    current_year = datetime.now().year
    selected_year = st.selectbox("Año", range(current_year - 5, current_year + 2), index=5) # Default to current year
with col2:
    # Create a dictionary mapping month number to month name (Spanish)
    month_names_es = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    # Use Spanish month names in the selectbox, but store the month number
    selected_month_name = st.selectbox("Mes", list(month_names_es.values()), index=datetime.now().month - 1)
    # Find the month number corresponding to the selected name
    selected_month = list(month_names_es.keys())[list(month_names_es.values()).index(selected_month_name)]

with col3:
    liquidation_type = st.radio("Tipo de Liquidación", ["Por Propietario", "Por Propiedad"], key="liq_type_radio")

identifier = None
identifier_value = None # User-friendly display value (owner name or property name+id)
if liquidation_type == "Por Propietario":
    if owners:
        selected_owner = st.selectbox("Seleccionar Propietario", [""] + owners)
        if selected_owner:
            identifier = selected_owner
            identifier_value = selected_owner
    else:
        st.warning("No hay propietarios definidos en las propiedades.")
elif liquidation_type == "Por Propiedad":
    if property_display_names:
        selected_property_display = st.selectbox("Seleccionar Propiedad", [""] + property_display_names)
        if selected_property_display:
            identifier = property_options[selected_property_display] # Use property ID as identifier
            identifier_value = selected_property_display
    else:
        st.warning("No hay propiedades definidas.")

commission_percentage = st.number_input("Tu Comisión (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.5, format="%.2f")

# --- Calculation and Display Logic ---
st.divider()
st.subheader("Resultados de la Liquidación")

# Initialize session state
if 'liquidation_results' not in st.session_state:
    st.session_state.liquidation_results = None
if 'liquidation_params' not in st.session_state:
    st.session_state.liquidation_params = None
if 'just_calculated' not in st.session_state:
    st.session_state.just_calculated = False

# Check if parameters changed and try to load existing liquidation
current_params = (selected_year, selected_month, liquidation_type, identifier, commission_percentage)
params_changed = st.session_state.liquidation_params != current_params

if params_changed:
    st.session_state.liquidation_params = current_params
    st.session_state.just_calculated = False # Reset flag on param change
    if identifier:
        filepath = _get_liquidation_filepath(selected_year, selected_month, liquidation_type, identifier)
        loaded_data = load_liquidation(filepath)
        st.session_state.liquidation_results = loaded_data # Store loaded data or None
        # Warn if loaded commission differs from current input, but still load
        if loaded_data and abs(loaded_data.get('commission_percentage', -1) - commission_percentage) > 0.001: # Compare floats carefully
             st.warning(f"La comisión guardada ({loaded_data.get('commission_percentage')}%) difiere de la comisión seleccionada ({commission_percentage}%). La recalculación usará el valor {commission_percentage}%.")
    else:
        st.session_state.liquidation_results = None # Clear results if no identifier

# Determine button label and display info message if data was loaded
saved_data_exists_and_loaded = st.session_state.liquidation_results is not None and not st.session_state.just_calculated

if saved_data_exists_and_loaded:
     st.info("Se encontró una liquidación guardada para esta selección. Puede revisarla a continuación o presionar 'Recalcular Liquidación' para actualizarla con los datos y comisión actuales.")

button_label = "Recalcular Liquidación" if st.session_state.liquidation_results is not None else "Calcular Liquidación"
calculate_pressed = st.button(button_label, type="primary", disabled=not identifier)

# Reset just_calculated flag after potential display/button rendering based on its previous state
# Ensures the "loaded data" message doesn't reappear incorrectly if params change back and forth
if not calculate_pressed:
    st.session_state.just_calculated = False

# --- Perform Calculation if Button Pressed ---
if calculate_pressed:
    if not identifier:
        st.warning("Por favor, seleccione un propietario o propiedad.") # Should be disabled, but safety check
    else:
        st.session_state.just_calculated = True # Set flag: calculation happened in this run
        # Define the start and end of the selected month
        month_start = pd.Timestamp(f"{selected_year}-{selected_month}-01")
        month_end = month_start + pd.offsets.MonthEnd(0)

        # Determine property IDs to filter by based on current UI selection
        property_ids_to_filter = []
        if liquidation_type == "Por Propietario":
            property_ids_to_filter = properties_df[properties_df['owner'] == identifier]['id'].tolist()
        elif liquidation_type == "Por Propiedad":
            property_ids_to_filter = [identifier] # Identifier is the property ID

        if not property_ids_to_filter:
             st.warning(f"No se encontraron propiedades para {liquidation_type}: {identifier_value}")
             st.session_state.liquidation_results = None # Clear results if no properties found
        else:
            # Filter Bookings: Include bookings ENDING within the selected month
            filtered_bookings = bookings_df[
                (bookings_df['property_id'].isin(property_ids_to_filter)) &
                (bookings_df['end_date'] >= month_start) &
                (bookings_df['end_date'] <= month_end)
            ].copy()

            # Filter Expenses: Include expenses occurring within the selected month
            filtered_expenses = expenses_df[
                (expenses_df['property_id'].isin(property_ids_to_filter)) &
                (expenses_df['expense_date'] >= month_start) &
                (expenses_df['expense_date'] <= month_end)
            ].copy()

            # Calculate Totals
            total_income = filtered_bookings['rent_amount'].sum()
            total_expenses = filtered_expenses['amount'].sum()

            # Calculate Commission (Manager's Share) using the current UI percentage
            commission_amount = total_income * (commission_percentage / 100.0)

            # Calculate Net Amount for Owner
            owner_net = total_income - total_expenses - commission_amount

            # Store results in session state
            results = {
                'year': selected_year,
                'month': selected_month,
                'type': liquidation_type.lower().replace(" ", "_"),
                'identifier': identifier, # Store the actual identifier (owner name or prop id)
                'commission_percentage': commission_percentage, # Store the used percentage
                'total_income': total_income,
                'total_expenses': total_expenses,
                'commission_amount': commission_amount,
                'owner_net': owner_net,
                'calculation_timestamp': datetime.now().isoformat()
            }
            st.session_state.liquidation_results = results

            # Save the results
            filepath = _get_liquidation_filepath(selected_year, selected_month, results['type'], identifier)
            if save_liquidation(results, filepath):
                st.success(f"Liquidación {'recalculada' if saved_data_exists_and_loaded else 'calculada'} y guardada en: {filepath}")
            else:
                st.error("No se pudo guardar la liquidación.")
        # Streamlit reruns after button press, the display logic below will execute

# --- Prepare Data for Display (if results exist) ---
filtered_bookings_for_display = pd.DataFrame()
filtered_expenses_for_display = pd.DataFrame()

if st.session_state.liquidation_results:
    results = st.session_state.liquidation_results
    # Re-calculate filters based on the parameters stored in results for consistent display
    display_year = results['year']
    display_month = results['month']
    display_type = results['type'] # 'por_propietario' or 'por_propiedad'
    display_identifier = results['identifier'] # Actual owner name or property ID

    month_start = pd.Timestamp(f"{display_year}-{display_month}-01")
    month_end = month_start + pd.offsets.MonthEnd(0)

    property_ids_to_filter = []
    if display_type == "por_propietario":
        if not properties_df.empty and 'owner' in properties_df.columns and 'id' in properties_df.columns:
             property_ids_to_filter = properties_df[properties_df['owner'] == display_identifier]['id'].tolist()
        else:
             st.error("No se pudieron cargar los datos de propiedades para filtrar por propietario.")
    elif display_type == "por_propiedad":
        property_ids_to_filter = [display_identifier]

    if property_ids_to_filter:
         # Filter Bookings for display
         if not bookings_df.empty:
             filtered_bookings_for_display = bookings_df[
                 (bookings_df['property_id'].isin(property_ids_to_filter)) &
                 (bookings_df['end_date'] >= month_start) &
                 (bookings_df['end_date'] <= month_end)
             ].copy()
         # Filter Expenses for display
         if not expenses_df.empty:
             filtered_expenses_for_display = expenses_df[
                 (expenses_df['property_id'].isin(property_ids_to_filter)) &
                 (expenses_df['expense_date'] >= month_start) &
                 (expenses_df['expense_date'] <= month_end)
             ].copy()

# --- Display Results ---
if st.session_state.liquidation_results:
    results = st.session_state.liquidation_results
    # Use identifier_value from the current UI selection for the display title for consistency
    display_title_identifier = identifier_value if identifier_value else results['identifier']

    st.markdown(f"**Periodo:** {month_names_es[results['month']]} {results['year']}")
    st.markdown(f"**Liquidación para:** {results['type'].replace('_', ' ').capitalize()} - **{display_title_identifier}**")
    st.markdown(f"**Comisión Aplicada:** {results['commission_percentage']:.2f}%")

    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    with res_col1:
        # Get currency from bookings if available, otherwise expenses, default to '$'
        currency = ''
        if not filtered_bookings_for_display.empty and 'rent_currency' in filtered_bookings_for_display.columns:
            currency = filtered_bookings_for_display['rent_currency'].iloc[0]
        elif not filtered_expenses_for_display.empty and 'currency' in filtered_expenses_for_display.columns:
            currency = filtered_expenses_for_display['currency'].iloc[0]
        else:
            currency = '$' # Default currency if not found in data

        st.metric("💰 Ingresos Totales", f"{currency}{results['total_income']:,.2f}")
    with res_col2:
        st.metric("💸 Gastos Totales", f"{currency}{results['total_expenses']:,.2f}")
    with res_col3:
        st.metric("📊 Comisión Gestor", f"{currency}{results['commission_amount']:,.2f}")
    with res_col4:
        # Calculate gross profit before manager commission for delta comparison
        gross_profit = results['total_income'] - results['total_expenses']
        delta_vs_gross = results['owner_net'] - gross_profit # This will be negative (equal to -commission_amount)
        st.metric("🏦 Neto para Propietario", f"{currency}{results['owner_net']:,.2f}",
                  delta=f"{currency}{delta_vs_gross:,.2f} vs sin comisión gestor",
                  delta_color="normal") # Show difference vs gross profit

    try:
        timestamp_str = pd.to_datetime(results.get('calculation_timestamp', 'N/A')).strftime('%Y-%m-%d %H:%M:%S')
    except:
        timestamp_str = "Fecha inválida" if results.get('calculation_timestamp') else "N/A"
    st.markdown(f"_(Último cálculo guardado: {timestamp_str})_")

    # Add download button for PDF report
    report_html = generate_liquidation_report_html(results, filtered_bookings_for_display, filtered_expenses_for_display, properties_df, month_names_es, currency)
    st.download_button(
        label="Descargar Reporte PDF",
        data=report_html,
        file_name=f"liquidacion_{results['year']}_{results['month']:02d}_{results['type']}_{results['identifier']}.html",
        mime="text/html",
        help="Click para descargar el reporte en formato HTML (puedes imprimir a PDF desde el navegador)."
    )


    # Display the detailed bookings and expenses used (re-filtered above)
    with st.expander("Ver Detalles de Ingresos (Reservas Finalizadas en el Mes)"):
        if not filtered_bookings_for_display.empty:
            # Prepare a user-friendly dataframe for display
            bookings_display = filtered_bookings_for_display.copy()

            # Try to get property names instead of IDs
            property_names = {}
            for index, row in properties_df.iterrows():
                property_names[row['id']] = row['name']

            # Replace property_id with property name
            bookings_display['property'] = bookings_display['property_id'].map(property_names)

            # Format dates
            bookings_display['start_date'] = bookings_display['start_date'].dt.strftime('%Y-%m-%d')
            bookings_display['end_date'] = bookings_display['end_date'].dt.strftime('%Y-%m-%d')

            # Select and order columns for display
            display_cols = ['property', 'tenant_name', 'start_date', 'end_date', 'rent_amount']
            if 'rent_currency' in bookings_display.columns:
                display_cols.append('rent_currency')
            display_cols.append('source')
            bookings_display = bookings_display[display_cols]


            bookings_display.rename(columns={
                'property': 'Propiedad',
                'tenant_name': 'Inquilino',
                'start_date': 'Fecha Inicio',
                'end_date': 'Fecha Fin',
                'rent_amount': 'Monto Alquiler',
                'rent_currency': 'Moneda',
                'source': 'Origen'
            }, inplace=True)

            st.dataframe(bookings_display)
        else:
            st.info("No se encontraron reservas finalizadas en este periodo para la selección.")

    with st.expander("Ver Detalles de Gastos del Mes"):
        if not filtered_expenses_for_display.empty:
            expenses_display = filtered_expenses_for_display[['id', 'property_id', 'expense_date', 'category', 'amount', 'description']]
            if 'currency' in filtered_expenses_for_display.columns:
                expenses_display['Moneda'] = filtered_expenses_for_display['currency'] #add currency column if exists
                expenses_display = expenses_display[['id', 'property_id', 'expense_date', 'category', 'amount', 'Moneda', 'description']] #reorder columns to show currency near amount

            st.dataframe(expenses_display)
        else:
            st.info("No se encontraron gastos en este periodo para la selección.")

# --- Display Prompts if no results ---
elif not identifier:
    st.info("Seleccione un tipo de liquidación y un propietario o propiedad para comenzar.")
elif identifier: # Identifier selected, but no results loaded and button not pressed yet
     st.info("Seleccione los criterios y presione 'Calcular Liquidación'.")

