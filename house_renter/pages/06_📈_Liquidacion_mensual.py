# liquidation_page.py
import streamlit as st
import pandas as pd
import data_manager # Import the new data manager module
from datetime import datetime, timedelta
import calendar
import os # Keep os only if needed for path joining OUTSIDE data_manager scope (unlikely now)


if not data_manager.check_password():
    st.stop()  # Do not continue if not authenticated

# --- Constants (mostly UI related or derived) ---
# LIQUIDATIONS_DIR and LIQUIDATION_COLS are now managed by data_manager
# Keep month names here as it's for UI display
MONTH_NAMES_ES = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
DEFAULT_CURRENCY = '$' # Default currency if not found in data

# --- Helper Functions (UI/Reporting Specific) ---

def generate_liquidation_report_html(results, filtered_bookings_for_display, filtered_expenses_for_display, properties_df, month_names_es, currency):
    """Generates an HTML report for liquidation, designed for print-to-pdf."""
    if not results:
        return "<p>Error: No results data to generate report.</p>"

    # Ensure results has necessary keys, provide defaults if missing
    year = results.get('year', 'N/A')
    month = results.get('month', 0)
    liq_type = results.get('type', 'N/A').replace('_', ' ').capitalize()
    identifier = results.get('identifier', 'N/A')
    comm_perc = results.get('commission_percentage', 0.0)
    total_inc = results.get('total_income', 0.0)
    total_exp = results.get('total_expenses', 0.0)
    comm_amt = results.get('commission_amount', 0.0)
    owner_net = results.get('owner_net', 0.0)

    month_name = month_names_es.get(month, 'Mes Inválido')
    report_title = f"Liquidación Mensual - {month_name} {year}"
    identifier_display = f"{liq_type} - {identifier}"

    report_html = f"""
    <html>
    <head>
        <title>{report_title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .header-info p {{ margin: 2px 0; }}
            .totals {{ margin: 20px 0; border-top: 1px solid #eee; border-bottom: 1px solid #eee; padding: 15px 0; }}
            .total-metric {{ font-size: 1.1em; margin-right: 25px; display: inline-block; min-width: 200px;}}
            .daily-section {{ margin-top: 25px; border-top: 1px solid #ccc; padding-top: 15px; }}
            .daily-header {{ font-weight: bold; margin-bottom: 8px; font-size: 1.2em; }}
            .daily-sub-header {{ font-weight: bold; margin-top: 10px; margin-bottom: 5px; font-size: 1.1em;}}
            .daily-item {{ margin-bottom: 4px; list-style-type: disc; margin-left: 20px;}}
            .daily-summary {{ font-weight: bold; margin-top: 12px; }}
            .no-data {{ color: #777; font-style: italic; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; font-size: 0.9em; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f0f0f0; font-weight: bold; }}
            .currency {{ text-align: right; }}
            .number {{ text-align: right; }}
        </style>
    </head>
    <body>
        <h1>{report_title}</h1>
        <div class="header-info">
            <p><strong>Liquidación para:</strong> {identifier_display}</p>
            <p><strong>Periodo:</strong> {month_name} {year}</p>
            <p><strong>Comisión Aplicada:</strong> {comm_perc:.2f}%</p>
        </div>

        <div class="totals">
            <span class="total-metric"><strong>💰 Ingresos Totales:</strong> {currency}{total_inc:,.2f}</span>
            <span class="total-metric"><strong>💸 Gastos Totales:</strong> {currency}{total_exp:,.2f}</span><br>
            <span class="total-metric"><strong>📊 Comisión Gestor:</strong> {currency}{comm_amt:,.2f}</span>
            <span class="total-metric"><strong>🏦 Neto para Propietario:</strong> {currency}{owner_net:,.2f}</span>
        </div>

        <h2>Desglose Diario</h2>
    """

    # Daily Breakdown
    if month > 0 and isinstance(year, int):
        try:
            num_days = calendar.monthrange(year, month)[1]
            date_range = pd.date_range(start=f"{year}-{month:02d}-01", periods=num_days)

            # Pre-calculate property names map for efficiency
            property_names_map = {}
            if properties_df is not None and not properties_df.empty:
                 property_names_map = pd.Series(properties_df.name.values, index=properties_df.id).to_dict()

            for day_date in date_range:
                day_str = day_date.strftime('%Y-%m-%d')
                report_html += f'<div class="daily-section"><h3 class="daily-header">{day_str}</h3>'

                # Daily Income
                report_html += '<h4 class="daily-sub-header">Ingresos</h4>'
                daily_bookings = filtered_bookings_for_display[pd.to_datetime(filtered_bookings_for_display['end_date']).dt.date == day_date.date()]
                daily_income_total = 0
                if not daily_bookings.empty:
                    report_html += "<ul>"
                    for _, booking in daily_bookings.iterrows():
                        prop_id = booking.get('property_id', 'N/A')
                        prop_name = property_names_map.get(prop_id, f"ID: {prop_id}") # Use map
                        tenant = booking.get('tenant_name', 'N/A')
                        amount = booking.get('rent_amount', 0.0)
                        source = booking.get('source', 'N/A')
                        daily_income_total += amount
                        report_html += f'<li class="daily-item">Reserva: {prop_name}, Inquilino: {tenant}, Monto: {currency}{amount:.2f} ({source})</li>'
                    report_html += "</ul>"
                else:
                    report_html += f'<p class="no-data">No hubo finalización de reservas este día.</p>'

                # Daily Expenses
                report_html += '<h4 class="daily-sub-header">Gastos</h4>'
                daily_expenses = filtered_expenses_for_display[pd.to_datetime(filtered_expenses_for_display['expense_date']).dt.date == day_date.date()]
                daily_expense_total = 0
                if not daily_expenses.empty:
                    report_html += "<ul>"
                    for _, expense in daily_expenses.iterrows():
                        prop_id = expense.get('property_id', 'N/A')
                        prop_name = property_names_map.get(prop_id, f"ID: {prop_id}") # Use map
                        category = expense.get('category', 'N/A')
                        amount = expense.get('amount', 0.0)
                        desc = expense.get('description', 'N/A')
                        daily_expense_total += amount
                        report_html += f'<li class="daily-item">Gasto: {prop_name}, Categoría: {category}, Monto: {currency}{amount:.2f} ({desc})</li>'
                    report_html += "</ul>"
                else:
                    report_html += f'<p class="no-data">No hubo gastos este día.</p>'

                daily_net = daily_income_total - daily_expense_total
                report_html += f'<p class="daily-summary"><strong>Resumen Diario:</strong> Ingresos: {currency}{daily_income_total:.2f}, Gastos: {currency}{daily_expense_total:.2f}, Neto Diario: {currency}{daily_net:.2f}</p>'
                report_html += '</div>' # Close daily-section

        except ValueError:
             report_html += "<p>Error: Fechas inválidas para generar desglose diario.</p>"
    else:
        report_html += "<p>No se puede generar desglose diario (mes o año inválido).</p>"


    # Detailed Tables
    report_html += '<h2>Detalle de Ingresos (Reservas Finalizadas en el Mes)</h2>'
    if not filtered_bookings_for_display.empty:
        bookings_display_report = filtered_bookings_for_display.copy()
        # Use the pre-calculated map
        bookings_display_report['property'] = bookings_display_report['property_id'].map(property_names_map).fillna('N/A')
        bookings_display_report['start_date'] = bookings_display_report['start_date'].dt.strftime('%Y-%m-%d')
        bookings_display_report['end_date'] = bookings_display_report['end_date'].dt.strftime('%Y-%m-%d')

        # Handle currency column presence
        currency_col_name = 'rent_currency' if 'rent_currency' in bookings_display_report.columns else None
        if currency_col_name is None:
             # If no currency column, don't try to display it
             display_cols_report = ['property', 'tenant_name', 'start_date', 'end_date', 'rent_amount', 'source']
             rename_map_report = {'property': 'Propiedad', 'tenant_name': 'Inquilino', 'start_date': 'Fecha Inicio', 'end_date': 'Fecha Fin', 'rent_amount': 'Monto Alquiler', 'source': 'Origen'}
        else:
            display_cols_report = ['property', 'tenant_name', 'start_date', 'end_date', 'rent_amount', currency_col_name, 'source']
            rename_map_report = {'property': 'Propiedad', 'tenant_name': 'Inquilino', 'start_date': 'Fecha Inicio', 'end_date': 'Fecha Fin', 'rent_amount': 'Monto Alquiler', currency_col_name: 'Moneda', 'source': 'Origen'}

        bookings_display_report = bookings_display_report[display_cols_report]
        bookings_display_report.rename(columns=rename_map_report, inplace=True)

        # Apply formatting for HTML table
        formatted_bookings = bookings_display_report.style.format({
            'Monto Alquiler': '{:,.2f}'.format,
        }).set_table_attributes('class="dataframe table table-striped"').hide(axis="index").to_html()

        report_html += formatted_bookings
    else:
        report_html += "<p class='no-data'>No se encontraron reservas finalizadas en este periodo para la selección.</p>"

    report_html += '<h2>Detalle de Gastos del Mes</h2>'
    if not filtered_expenses_for_display.empty:
        expenses_display_report = filtered_expenses_for_display.copy()
        # Use the pre-calculated map
        expenses_display_report['property'] = expenses_display_report['property_id'].map(property_names_map).fillna('N/A')
        expenses_display_report['expense_date'] = expenses_display_report['expense_date'].dt.strftime('%Y-%m-%d')

         # Handle currency column presence
        currency_col_name_exp = 'currency' if 'currency' in expenses_display_report.columns else None
        if currency_col_name_exp is None:
            display_cols_exp_report = ['property', 'expense_date', 'category', 'amount', 'description']
            rename_map_exp_report = {'property': 'Propiedad', 'expense_date': 'Fecha Gasto', 'category': 'Categoría', 'amount': 'Monto', 'description': 'Descripción'}
        else:
            display_cols_exp_report = ['property', 'expense_date', 'category', 'amount', currency_col_name_exp, 'description']
            rename_map_exp_report = {'property': 'Propiedad', 'expense_date': 'Fecha Gasto', 'category': 'Categoría', 'amount': 'Monto', currency_col_name_exp: 'Moneda', 'description': 'Descripción'}

        expenses_display_report = expenses_display_report[display_cols_exp_report]
        expenses_display_report.rename(columns=rename_map_exp_report, inplace=True)

        # Apply formatting for HTML table
        formatted_expenses = expenses_display_report.style.format({
            'Monto': '{:,.2f}'.format,
        }).set_table_attributes('class="dataframe table table-striped"').hide(axis="index").to_html()

        report_html += formatted_expenses
    else:
        report_html += "<p class='no-data'>No se encontraron gastos en este periodo para la selección.</p>"


    report_html += """
    </body>
    </html>
    """
    return report_html

# --- Page Configuration ---
st.set_page_config(page_title="Liquidación Mensual", page_icon="📈", layout="wide")
st.title("📈 Liquidación Mensual")
st.markdown("Calcule y visualice los ingresos, gastos y beneficios netos mensuales para un propietario o propiedad específica.")

# --- Load Data using Data Manager ---
try:
    properties_df = data_manager.load_properties()
    bookings_df = data_manager.load_bookings()
    expenses_df = data_manager.load_expenses()
    # Basic type conversions are now handled within data_manager load functions
    # We still might need to handle potential NaT/NaN if errors='coerce' was used

except Exception as e:
    st.error(f"Error crítico al cargar datos iniciales usando data_manager: {e}")
    # Initialize empty dataframes with expected columns from data_manager
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS)
    bookings_df = pd.DataFrame(columns=data_manager.BOOKINGS_COLS)
    expenses_df = pd.DataFrame(columns=data_manager.EXPENSES_COLS)
    st.stop() # Stop execution if basic data loading fails

# --- Check if data is available ---
if properties_df.empty:
    st.warning("No se encontraron propiedades. Agregue propiedades (necesita 'data/properties.csv').")
    # Don't stop necessarily, allow user to see message, but disable controls later

# Check for essential columns after loading
essential_prop_cols = ['id', 'name', 'owner']
essential_book_cols = ['property_id', 'end_date', 'rent_amount']
essential_exp_cols = ['property_id', 'expense_date', 'amount']

if not all(col in properties_df.columns for col in essential_prop_cols):
    st.error(f"Faltan columnas esenciales ({', '.join(essential_prop_cols)}) en 'properties.csv'. Verifique el archivo.")
    st.stop()
if not all(col in bookings_df.columns for col in essential_book_cols):
    st.warning(f"Faltan columnas esenciales ({', '.join(essential_book_cols)}) en 'bookings.csv'. Los cálculos de ingresos pueden ser incorrectos.")
    # Allow continuation but warn
if not all(col in expenses_df.columns for col in essential_exp_cols):
     st.warning(f"Faltan columnas esenciales ({', '.join(essential_exp_cols)}) en 'expenses.csv'. Los cálculos de gastos pueden ser incorrectos.")
     # Allow continuation but warn


# --- UI Elements for Selection ---
st.subheader("Seleccionar Periodo y Criterio")

# Get unique owners and properties for selectors safely
owners = sorted(properties_df['owner'].unique()) if 'owner' in properties_df.columns else []
property_options = {}
if 'id' in properties_df.columns and 'name' in properties_df.columns:
    property_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in properties_df.iterrows()}
property_display_names = list(property_options.keys())

col1, col2, col3 = st.columns(3)
with col1:
    current_year = datetime.now().year
    # Adjust range as needed, ensure default is valid
    year_options = list(range(current_year - 5, current_year + 2))
    default_year_index = year_options.index(current_year) if current_year in year_options else len(year_options) - 2 # Default to current year or second last if current is not in list
    selected_year = st.selectbox("Año", year_options, index=default_year_index)
with col2:
    # Use the constant MONTH_NAMES_ES
    selected_month_name = st.selectbox("Mes", list(MONTH_NAMES_ES.values()), index=datetime.now().month - 1)
    selected_month = list(MONTH_NAMES_ES.keys())[list(MONTH_NAMES_ES.values()).index(selected_month_name)]

with col3:
    liquidation_type = st.radio("Tipo de Liquidación", ["Por Propietario", "Por Propiedad"], key="liq_type_radio", horizontal=True)

identifier = None
identifier_value = None # User-friendly display value
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

commission_percentage = st.number_input("Tu Comisión (%)", min_value=0.0, max_value=100.0, value=50.0, step=0.5, format="%.2f")

# --- Calculation and Display Logic ---
st.divider()
st.subheader("Resultados de la Liquidación")

# Initialize session state keys if they don't exist
if 'liquidation_results' not in st.session_state:
    st.session_state.liquidation_results = None
if 'liquidation_params' not in st.session_state:
    st.session_state.liquidation_params = None
if 'just_calculated' not in st.session_state:
    st.session_state.just_calculated = False

# Check if parameters changed and try to load existing liquidation
# Ensure identifier is not None before comparing/loading
current_params = None
if identifier is not None:
    current_params = (selected_year, selected_month, liquidation_type, identifier, commission_percentage)

params_changed = st.session_state.liquidation_params != current_params

if params_changed:
    st.session_state.liquidation_params = current_params
    st.session_state.just_calculated = False # Reset flag on param change
    if identifier is not None:
        # Use data_manager to load
        liq_type_key = liquidation_type.lower().replace(" ", "_")
        loaded_data = data_manager.load_liquidation(selected_year, selected_month, liq_type_key, identifier)
        st.session_state.liquidation_results = loaded_data # Store loaded data (dict) or None
        if loaded_data and abs(loaded_data.get('commission_percentage', -1) - commission_percentage) > 0.001:
             st.warning(f"Se cargó una liquidación guardada con comisión del {loaded_data.get('commission_percentage')}%. La recalculación usará el valor actual ({commission_percentage}%).")
    else:
        st.session_state.liquidation_results = None # Clear results if no identifier selected

# Determine button label and display info message if data was loaded
# Check if results exist AND calculation hasn't just happened in this run
saved_data_exists_and_loaded = st.session_state.liquidation_results is not None and not st.session_state.just_calculated

if saved_data_exists_and_loaded:
     st.info("Se encontró una liquidación guardada para esta selección. Revísela o presione 'Recalcular' para actualizarla con los datos y comisión actuales.")

button_label = "Recalcular Liquidación" if st.session_state.liquidation_results is not None else "Calcular Liquidación"
calculate_pressed = st.button(button_label, type="primary", disabled=not identifier or properties_df.empty)

# Reset just_calculated flag after button rendering and before potential calculation
# This prevents the "loaded data" message showing incorrectly if params change back/forth without calculation
if not calculate_pressed:
    st.session_state.just_calculated = False

# --- Perform Calculation if Button Pressed ---
if calculate_pressed and identifier:
    st.session_state.just_calculated = True # Set flag: calculation happened in this run
    try:
        # Define the start and end of the selected month
        month_start = pd.Timestamp(f"{selected_year}-{selected_month}-01")
        month_end = month_start + pd.offsets.MonthEnd(0)

        # Determine property IDs to filter by
        property_ids_to_filter = []
        liq_type_key = liquidation_type.lower().replace(" ", "_")

        if liq_type_key == "por_propietario":
            if 'owner' in properties_df.columns and 'id' in properties_df.columns:
                property_ids_to_filter = properties_df.loc[properties_df['owner'] == identifier, 'id'].tolist()
            else:
                 st.error("Falta columna 'owner' o 'id' en propiedades para filtrar por propietario.")
                 st.stop()
        elif liq_type_key == "por_propiedad":
            property_ids_to_filter = [identifier] # Identifier is the property ID

        if not property_ids_to_filter:
             st.warning(f"No se encontraron propiedades asociadas a {liquidation_type}: {identifier_value}")
             st.session_state.liquidation_results = None # Clear results if no properties found
        else:
            # Filter Bookings: ENDING within the selected month
            filtered_bookings = pd.DataFrame(columns=data_manager.BOOKINGS_COLS) # Initialize empty
            if not bookings_df.empty and 'property_id' in bookings_df.columns and 'end_date' in bookings_df.columns:
                 mask_bookings = (
                     bookings_df['property_id'].isin(property_ids_to_filter) &
                     (bookings_df['end_date'] >= month_start) &
                     (bookings_df['end_date'] <= month_end) &
                     pd.notna(bookings_df['end_date']) # Ensure end_date is not NaT
                 )
                 filtered_bookings = bookings_df.loc[mask_bookings].copy()

            # Filter Expenses: Occurring within the selected month
            filtered_expenses = pd.DataFrame(columns=data_manager.EXPENSES_COLS) # Initialize empty
            if not expenses_df.empty and 'property_id' in expenses_df.columns and 'expense_date' in expenses_df.columns:
                mask_expenses = (
                    expenses_df['property_id'].isin(property_ids_to_filter) &
                    (expenses_df['expense_date'] >= month_start) &
                    (expenses_df['expense_date'] <= month_end) &
                     pd.notna(expenses_df['expense_date']) # Ensure expense_date is not NaT
                )
                filtered_expenses = expenses_df.loc[mask_expenses].copy()

            # Calculate Totals safely (handle potential NaNs if columns missing/empty)
            total_income = filtered_bookings['rent_amount'].sum() if 'rent_amount' in filtered_bookings else 0
            total_expenses = filtered_expenses['amount'].sum() if 'amount' in filtered_expenses else 0

            # Calculate Commission using the current UI percentage
            commission_amount = total_income * (commission_percentage / 100.0)

            # Calculate Net Amount for Owner
            owner_net = total_income - total_expenses - commission_amount

            # Prepare results dictionary
            results = {
                'year': selected_year,
                'month': selected_month,
                'type': liq_type_key,
                'identifier': identifier, # Store the actual identifier
                'commission_percentage': commission_percentage,
                'total_income': total_income,
                'total_expenses': total_expenses,
                'commission_amount': commission_amount,
                'owner_net': owner_net,
                'calculation_timestamp': datetime.now().isoformat()
            }
            st.session_state.liquidation_results = results

            # Save the results using data_manager
            if data_manager.save_liquidation(results, selected_year, selected_month, liq_type_key, identifier):
                # Use f-string for dynamic message
                action = "recalculada" if saved_data_exists_and_loaded else "calculada"
                st.success(f"Liquidación {action} y guardada correctamente.")
            else:
                st.error("Error al guardar la liquidación. Revise los permisos o el archivo.")
                # The error details should be printed in the console by data_manager

    except Exception as e:
        st.error(f"Ocurrió un error durante el cálculo: {e}")
        st.session_state.liquidation_results = None # Clear results on error

# --- Prepare Data for Display (if results exist in session state) ---
filtered_bookings_for_display = pd.DataFrame(columns=data_manager.BOOKINGS_COLS)
filtered_expenses_for_display = pd.DataFrame(columns=data_manager.EXPENSES_COLS)
currency = DEFAULT_CURRENCY # Initialize default currency

if st.session_state.liquidation_results:
    results = st.session_state.liquidation_results
    try:
        # Re-calculate filters based on the parameters stored in results for consistent display
        display_year = int(results['year'])
        display_month = int(results['month'])
        display_type = results['type'] # 'por_propietario' or 'por_propiedad'
        display_identifier = results['identifier'] # Actual owner name or property ID

        month_start = pd.Timestamp(f"{display_year}-{display_month}-01")
        month_end = month_start + pd.offsets.MonthEnd(0)

        property_ids_to_filter_display = []
        if display_type == "por_propietario":
            if not properties_df.empty and 'owner' in properties_df.columns and 'id' in properties_df.columns:
                 property_ids_to_filter_display = properties_df.loc[properties_df['owner'] == display_identifier, 'id'].tolist()
            # No error here, just might result in empty list if data missing
        elif display_type == "por_propiedad":
            property_ids_to_filter_display = [display_identifier]

        if property_ids_to_filter_display:
             # Filter Bookings for display
             if not bookings_df.empty:
                 mask_bookings_display = (
                     bookings_df['property_id'].isin(property_ids_to_filter_display) &
                     (bookings_df['end_date'] >= month_start) &
                     (bookings_df['end_date'] <= month_end) &
                     pd.notna(bookings_df['end_date'])
                 )
                 filtered_bookings_for_display = bookings_df.loc[mask_bookings_display].copy()

             # Filter Expenses for display
             if not expenses_df.empty:
                 mask_expenses_display = (
                    expenses_df['property_id'].isin(property_ids_to_filter_display) &
                    (expenses_df['expense_date'] >= month_start) &
                    (expenses_df['expense_date'] <= month_end) &
                    pd.notna(expenses_df['expense_date'])
                 )
                 filtered_expenses_for_display = expenses_df.loc[mask_expenses_display].copy()

        # Determine Currency (more robustly)
        currencies_found = set()
        if not filtered_bookings_for_display.empty and 'rent_currency' in filtered_bookings_for_display.columns:
            currencies_found.update(filtered_bookings_for_display['rent_currency'].dropna().unique())
        if not filtered_expenses_for_display.empty and 'currency' in filtered_expenses_for_display.columns:
            currencies_found.update(filtered_expenses_for_display['currency'].dropna().unique())
        # Add property base currency if available
        if not properties_df.empty and 'currency' in properties_df.columns and property_ids_to_filter_display:
             prop_currencies = properties_df.loc[properties_df['id'].isin(property_ids_to_filter_display), 'currency']
             currencies_found.update(prop_currencies.dropna().unique())


        if len(currencies_found) == 1:
            currency = list(currencies_found)[0]
        elif len(currencies_found) > 1:
            st.warning(f"Se encontraron múltiples monedas ({', '.join(currencies_found)}) en los datos filtrados. Mostrando totales con '{DEFAULT_CURRENCY}', pero los cálculos asumen una única moneda implícita.")
            currency = DEFAULT_CURRENCY # Use default but warn
        else:
            currency = DEFAULT_CURRENCY # Use default if none found

    except Exception as e:
        st.error(f"Error preparando datos para visualización: {e}")
        # Keep results, but display might be incomplete
        st.session_state.liquidation_results = None # Clear results if prep fails badly

# --- Display Results ---
if st.session_state.liquidation_results:
    results = st.session_state.liquidation_results
    # Use identifier_value from the current UI selection if available, otherwise fallback
    display_title_identifier = identifier_value if identifier_value else results.get('identifier', 'N/A')
    display_type_friendly = results.get('type', 'N/A').replace('_', ' ').capitalize()
    month_name_display = MONTH_NAMES_ES.get(results.get('month', 0), 'Inválido')

    st.markdown(f"**Periodo:** {month_name_display} {results.get('year', 'N/A')}")
    st.markdown(f"**Liquidación para:** {display_type_friendly} - **{display_title_identifier}**")
    st.markdown(f"**Comisión Aplicada:** {results.get('commission_percentage', 0.0):.2f}%")

    res_col1, res_col2, res_col3 = st.columns(3)
    total_income_res = results.get('total_income', 0.0)
    total_expenses_res = results.get('total_expenses', 0.0)
    owner_net_res = results.get('owner_net', 0.0)

    with res_col1:
        st.metric("💰 Ingresos Totales", f"{currency}{total_income_res:,.2f}")
    with res_col2:
        st.metric("💸 Gastos Totales", f"{currency}{total_expenses_res:,.2f}")
    with res_col3:
        st.metric("📊 Comisión Gestor", f"{currency}{results.get('commission_amount', 0.0):,.2f}")

    res_col4 = st.columns(1)[0] # Create a single column for the last metric
    with res_col4:
        gross_profit = total_income_res - total_expenses_res
        # Delta calculation remains the same logic        
        delta_vs_gross = owner_net_res - gross_profit
        st.metric("🏦 Neto para Propietario", f"{currency}{owner_net_res:,.2f}",
                  delta=f"{currency}{delta_vs_gross:,.2f} vs bruto",
                  delta_color="normal")

    # Display timestamp safely
    timestamp_val = results.get('calculation_timestamp')
    timestamp_str = "N/A"
    if timestamp_val:
        try:
            timestamp_str = pd.to_datetime(timestamp_val).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            timestamp_str = str(timestamp_val) # Show raw if parsing fails
    st.caption(f"Último cálculo guardado: {timestamp_str}")


    # Add download button for PDF/HTML report
    try:
        report_html = generate_liquidation_report_html(results, filtered_bookings_for_display, filtered_expenses_for_display, properties_df, MONTH_NAMES_ES, currency)
        safe_identifier_name = "".join(c if c.isalnum() else "_" for c in str(results.get('identifier', 'report')))
        file_name=f"liquidacion_{results.get('year', 'YYYY')}_{results.get('month', 0):02d}_{results.get('type', 'type')}_{safe_identifier_name}.html"

        st.download_button(
            label="⬇️ Descargar Reporte HTML",
            data=report_html,
            file_name=file_name,
            mime="text/html",
            help="Descargar el reporte detallado en formato HTML (abrir en navegador e imprimir a PDF)."
        )
    except Exception as e:
        st.error(f"Error al generar el reporte HTML descargable: {e}")


    # Display the detailed bookings and expenses used
    with st.expander("Ver Detalles de Ingresos (Reservas Finalizadas en el Mes)"):
        if not filtered_bookings_for_display.empty:
            bookings_display = filtered_bookings_for_display.copy()
            # Map property names safely
            if 'id' in properties_df.columns and 'name' in properties_df.columns:
                prop_map = pd.Series(properties_df.name.values, index=properties_df.id).to_dict()
                bookings_display['property'] = bookings_display['property_id'].map(prop_map).fillna('ID Desconocido')
            else:
                bookings_display['property'] = bookings_display['property_id']

            # Format dates safely
            bookings_display['start_date'] = bookings_display['start_date'].dt.strftime('%Y-%m-%d')
            bookings_display['end_date'] = bookings_display['end_date'].dt.strftime('%Y-%m-%d')

            # Select, order, and rename columns for display
            display_cols = ['property', 'tenant_name', 'start_date', 'end_date', 'rent_amount']
            rename_map = {'property': 'Propiedad', 'tenant_name': 'Inquilino', 'start_date': 'Fecha Inicio', 'end_date': 'Fecha Fin', 'rent_amount': 'Monto'}
            if 'rent_currency' in bookings_display.columns:
                display_cols.append('rent_currency')
                rename_map['rent_currency'] = 'Moneda'
            if 'source' in bookings_display.columns:
                 display_cols.append('source')
                 rename_map['source'] = 'Origen'

            # Filter only existing columns before rename
            display_cols = [col for col in display_cols if col in bookings_display.columns]
            bookings_display = bookings_display[display_cols]
            bookings_display.rename(columns=rename_map, inplace=True)

            st.dataframe(bookings_display, use_container_width=True)
        else:
            st.info("No se encontraron reservas finalizadas en este periodo para la selección.")

    with st.expander("Ver Detalles de Gastos del Mes"):
        if not filtered_expenses_for_display.empty:
            expenses_display = filtered_expenses_for_display.copy()
             # Map property names safely
            if 'id' in properties_df.columns and 'name' in properties_df.columns:
                prop_map = pd.Series(properties_df.name.values, index=properties_df.id).to_dict()
                expenses_display['property'] = expenses_display['property_id'].map(prop_map).fillna('ID Desconocido')
            else:
                expenses_display['property'] = expenses_display['property_id']

            expenses_display['expense_date'] = expenses_display['expense_date'].dt.strftime('%Y-%m-%d')

            display_cols_exp = ['property', 'expense_date', 'category', 'amount']
            rename_map_exp = {'property': 'Propiedad', 'expense_date': 'Fecha Gasto', 'category': 'Categoría', 'amount': 'Monto'}
            if 'currency' in expenses_display.columns:
                display_cols_exp.append('currency')
                rename_map_exp['currency'] = 'Moneda'
            if 'description' in expenses_display.columns:
                 display_cols_exp.append('description')
                 rename_map_exp['description'] = 'Descripción'

            # Filter only existing columns before rename
            display_cols_exp = [col for col in display_cols_exp if col in expenses_display.columns]
            expenses_display = expenses_display[display_cols_exp]
            expenses_display.rename(columns=rename_map_exp, inplace=True)

            st.dataframe(expenses_display, use_container_width=True)
        else:
            st.info("No se encontraron gastos en este periodo para la selección.")

# --- Display Prompts if no results ---
elif not calculate_pressed and not saved_data_exists_and_loaded: # Only show prompts if not displaying loaded/calculated results
    if not identifier:
        st.info("⬅️ Seleccione un tipo de liquidación y un propietario o propiedad en el panel lateral (o superior) para comenzar.")
    elif identifier: # Identifier selected, but no results loaded and button not pressed yet
        st.info("⬆️ Presione 'Calcular Liquidación' (o 'Recalcular') para generar el reporte con los criterios seleccionados.")
