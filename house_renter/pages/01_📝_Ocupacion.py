import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import data_manager # Assuming data_manager.py is in the src directory or PYTHONPATH
import locale

# Set the locale to Spanish (Spain)
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

# --- Page Configuration ---
# Set in app.py, but good practice to note title here
# st.set_page_config(layout="wide", page_title="Occupancy Overview")

st.title("🏠 Resumen de Ocupación")
st.markdown("Visualice el estado actual de las propiedades y las líneas de tiempo de las reservas.")

# --- Load Data ---
# Use functions from data_manager, benefiting from @st.cache_data
try:
    properties_df = data_manager.load_properties()
    bookings_df = data_manager.load_bookings()

    # Ensure date columns are datetime objects (data_manager should handle this, but double-check)
    if not bookings_df.empty:
        bookings_df['start_date'] = pd.to_datetime(bookings_df['start_date'])
        bookings_df['end_date'] = pd.to_datetime(bookings_df['end_date'])

except FileNotFoundError as e:
    st.error(f"Archivo de datos no encontrado: {e}. Asegúrese de que 'properties.csv' y 'bookings.csv' existan en el directorio 'data'.")
    st.stop()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.exception(e) # Show traceback for debugging
    st.stop() # Stop execution if data loading fails

# Check if essential dataframes are empty
if properties_df.empty:
    st.warning("No se encontraron propiedades. Por favor, agregue propiedades en la página 'Administrar Propiedades'.")
    st.stop()

# --- OCC-001: Quick Summary ---
st.header("Estado Actual de las Propiedades")

today = pd.Timestamp.now().normalize() # Get today's date at midnight for accurate comparison

status_data = []

# Calculate status for each property
for index, prop in properties_df.iterrows():
    prop_id = prop['id']
    prop_name = prop['name'] if pd.notna(prop['name']) else f"Propiedad ID {prop_id}"

    # Filter bookings for this property and sort by start date
    prop_bookings = bookings_df[bookings_df['property_id'] == prop_id].sort_values('start_date')

    # Find booking covering today
    current_booking = prop_bookings[
        (prop_bookings['start_date'] <= today) & (prop_bookings['end_date'] >= today)
    ]

    status_label = "✅ Libre"
    status_detail = "Actualmente disponible."

    if not current_booking.empty:
        # Property is Occupied today
        current = current_booking.iloc[0]
        status_label = "🔴 Ocupado"
        end_date_str = current['end_date'].strftime('%Y-%m-%d')
        tenant = current['tenant_name'] if pd.notna(current['tenant_name']) else "N/A"
        status_detail = f"Ocupado hasta: {end_date_str}\nInquilino: {tenant}"
    else:
        # Property is Free today, find the *next* booking starting after today
        future_bookings = prop_bookings[prop_bookings['start_date'] > today]
        if not future_bookings.empty:
            next_booking = future_bookings.iloc[0]
            start_date_str = next_booking['start_date'].strftime('%Y-%m-%d')
            status_detail = f"Libre hasta la próxima reserva que comienza el: {start_date_str}"
        else:
            # Free indefinitely (no current or future bookings)
            status_detail = "No se encontraron reservas próximas."

    status_data.append({
        'Property': prop_name,
        'Status': status_label,
        'Details': status_detail
    })

# Display statuses using st.metric in columns
if status_data:
    # Dynamically adjust columns based on number of properties
    num_properties = len(status_data)
    num_columns = min(num_properties, 4) # Max 4 columns for readability
    cols = st.columns(num_columns)
    for i, data in enumerate(status_data):
        col_index = i % num_columns
        with cols[col_index]:
            st.metric(label=data['Property'], value=data['Status'], help=data['Details'])
else:
    # This case should not be reached if properties_df is not empty, but included for safety
    st.info("No hay propiedades para mostrar el estado.")


# --- OCC-002: Occupancy Timeline (Gantt Chart) ---
st.divider()
st.header("Cronograma de Reservas")

if bookings_df.empty:
    st.info("No se encontraron reservas. Agregue reservas en la página 'Administrar Reservas' para ver el cronograma.")
else:
    # Prepare data for Plotly Gantt chart
    # Merge bookings with properties to get property names
    try:
        # Ensure IDs are compatible for merging (handle potential Int64Dtype)
        prop_ids_str = properties_df['id'].astype(str)
        book_prop_ids_str = bookings_df['property_id'].astype(str)

        # Create temporary DFs for merge to avoid modifying originals unnecessarily
        props_temp = pd.DataFrame({'id_str': prop_ids_str, 'Property': properties_df['name']})
        books_temp = bookings_df.copy()
        books_temp['property_id_str'] = book_prop_ids_str

        merged_df = pd.merge(
            books_temp,
            props_temp,
            left_on='property_id_str',
            right_on='id_str',
            how='left' # Keep all bookings; property name might be NaN if property was deleted
        )

        # Handle cases where property might be missing after merge
        merged_df['Property'].fillna('Propiedad Desconocida', inplace=True)
        # Rename columns for clarity in the chart
        merged_df.rename(columns={'tenant_name': 'Tenant'}, inplace=True)

        # Select and ensure necessary columns exist
        timeline_cols = ['start_date', 'end_date', 'Property', 'Tenant', 'rent_amount', 'source']
        for col in timeline_cols:
            if col not in merged_df.columns:
                 merged_df[col] = pd.NA # Add missing columns with NA

        # Filter out bookings without valid dates if any snuck through
        merged_df = merged_df.dropna(subset=['start_date', 'end_date'])

    except Exception as merge_err:
         st.error(f"Error al fusionar reservas y propiedades para el cronograma: {merge_err}")
         st.dataframe(bookings_df) # Show raw bookings if merge fails
         merged_df = pd.DataFrame() # Ensure merged_df exists but is empty

    if not merged_df.empty:

        # --- Date Range Selector ---
        min_date_overall = merged_df['start_date'].min()
        max_date_overall = merged_df['end_date'].max()

        # Define reasonable default range (e.g., 3 months back, 6 months forward from today)
        default_start_dt = today - timedelta(days=90)
        default_end_dt = today + timedelta(days=180)

        # Clamp defaults to actual data range if needed
        start_val = max(min_date_overall.date(), default_start_dt.date()) if pd.notna(min_date_overall) else default_start_dt.date()
        end_val = min(max_date_overall.date(), default_end_dt.date()) if pd.notna(max_date_overall) else default_end_dt.date()
        min_val = min_date_overall.date() if pd.notna(min_date_overall) else start_val - timedelta(days=365)
        max_val = max_date_overall.date() if pd.notna(max_date_overall) else end_val + timedelta(days=365)


        st.markdown("Seleccione el rango de fechas para el cronograma:")
        col1, col2 = st.columns(2)
        with col1:
            start_date_filter = st.date_input(
                "Fecha de Inicio del Cronograma",
                value=start_val,
                min_value=min_val,
                max_value=max_val,
                key="timeline_start"
            )
        with col2:
            end_date_filter = st.date_input(
                "Fecha de Fin del Cronograma",
                value=end_val,
                min_value=min_val, # Allow start date to be selected
                max_value=max_val,
                key="timeline_end"
            )

        if start_date_filter > end_date_filter:
            st.warning("La fecha de inicio del cronograma no puede ser posterior a la fecha de fin.")
            filtered_timeline_df = pd.DataFrame() # Empty df if dates invalid
        else:
            # Convert filter dates to Timestamps for comparison
            start_ts = pd.Timestamp(start_date_filter)
            # Add one day to end_ts for inclusive filtering if needed, but Plotly handles ranges well.
            # For filtering, we need bookings that *overlap* the range:
            # Booking starts before range ends AND Booking ends after range starts
            end_ts = pd.Timestamp(end_date_filter)

            filtered_timeline_df = merged_df[
                (merged_df['start_date'] <= end_ts) & (merged_df['end_date'] >= start_ts)
            ].copy() # Create a copy to avoid SettingWithCopyWarning

            # Clip the start/end dates to the filter range for visualization if desired
            # This prevents bars from extending far beyond the selected window
            # filtered_timeline_df['viz_start'] = filtered_timeline_df['start_date'].clip(lower=start_ts)
            # filtered_timeline_df['viz_end'] = filtered_timeline_df['end_date'].clip(upper=end_ts)
            # Use viz_start and viz_end in px.timeline if clipping is desired


        # --- Create and Display Gantt Chart ---
        if filtered_timeline_df.empty:
            st.info("No se encontraron reservas dentro del rango de fechas seleccionado.")
        else:
            try:
                # Sort properties for consistent Y-axis order
                property_order = sorted(filtered_timeline_df['Property'].unique())

                # Determine occupancy status for coloring
                today = pd.Timestamp.now().normalize()
                filtered_timeline_df['Is_Occupied'] = (filtered_timeline_df['start_date'] <= today) & (filtered_timeline_df['end_date'] >= today)
                filtered_timeline_df.rename(columns={'Is_Occupied': 'Está Ocupado'}, inplace=True)

                # Define color mapping
                color_discrete_map = {True: "red", False: "green"}

                # Create the Plotly Gantt chart (Timeline)
                fig = px.timeline(
                    filtered_timeline_df,
                    x_start="start_date", # Use original dates for accuracy
                    x_end="end_date",
                    y="Property",
                    color="Está Ocupado", # Color bars by occupancy status
                    color_discrete_map=color_discrete_map,
                    title="Cronograma de Reservas",
                    hover_name="Tenant", # Show tenant name prominently on hover
                    hover_data={ # Customize hover data tooltips
                        'Property': False, # Already shown on Y axis and legend
                        'Tenant': True,
                        'start_date': "|%b %d, %Y", # Format start date (e.g., Jan 01, 2023)
                        'end_date': "|%b %d, %Y",   # Format end date
                        'rent_amount': ':.2f', # Show rent amount formatted as float
                        'source': True,
                        'Está Ocupado': False # Do not show Is_Occupied in tooltip
                    },
                    category_orders={"Property": property_order} # Ensure consistent Y-axis order
                )

                # Improve layout
                fig.update_yaxes(autorange="reversed") # Optional: Show properties top-down
                # Set the x-axis range explicitly to the filter dates for focus
                fig.update_layout(xaxis_range=[start_date_filter, end_date_filter])

                # Optional: Adjust height based on number of properties for better visibility
                num_properties_in_view = len(property_order)
                chart_height = max(300, num_properties_in_view * 25 + 100) # Base height + per property height
                fig.update_layout(height=chart_height)

                # Make timeline bars slightly thinner
                fig.update_traces(width=0.6)

                st.plotly_chart(fig, use_container_width=True)

            except Exception as plot_err:
                st.error(f"Error al crear el gráfico del cronograma: {plot_err}")
                st.exception(plot_err) # Show traceback
                st.dataframe(filtered_timeline_df) # Show data that caused the error

    elif 'Property' not in merged_df.columns and not bookings_df.empty:
        # This case indicates the merge likely failed substantially
        st.warning("No se pudieron fusionar los datos de reserva con los nombres de propiedad de manera confiable. Se muestran los datos de reserva sin procesar.")
        st.dataframe(bookings_df)

# --- OCC-003: Monthly Occupancy Overview ---
st.divider()
st.header("Vista Mensual de Ocupación")

# Add a selectbox to choose the year
available_years = bookings_df['start_date'].dt.year.unique().tolist()
if available_years:
    selected_year = st.selectbox("Seleccione el año:", options=sorted(available_years, reverse=True))

    # Filter bookings for the selected year
    yearly_bookings = bookings_df[bookings_df['start_date'].dt.year == selected_year].copy()

    if not yearly_bookings.empty:
        # Group by property and month, counting occupied days
        def calculate_monthly_occupancy(df):
            # Create a date range for each booking
            date_ranges = [pd.date_range(start=row['start_date'], end=row['end_date']) for _, row in df.iterrows()]

            # Flatten the list of date ranges
            all_dates = [date for sublist in date_ranges for date in sublist]

            # Convert to a Series and extract month
            dates_series = pd.Series(all_dates)
            monthly_counts = dates_series.dt.month.value_counts().sort_index()

            # Ensure all months are represented
            all_months = pd.RangeIndex(1, 13)
            monthly_counts = monthly_counts.reindex(all_months, fill_value=0)

            return monthly_counts

        # Group bookings by property and apply the function
        # First, merge yearly_bookings with properties_df to get property names
        yearly_bookings = pd.merge(
            yearly_bookings,
            properties_df[['id', 'name']],
            left_on='property_id',
            right_on='id',
            how='left'
        )
        yearly_bookings['property_name'] = yearly_bookings['name'].fillna('Propiedad Desconocida')

        monthly_occupancy = yearly_bookings.groupby('property_name').apply(calculate_monthly_occupancy)

        # Rename index for clarity
        monthly_occupancy.index.name = "Nombre de la Propiedad"
        monthly_occupancy.columns.name = "Mes"

        # Display as a dataframe
        st.dataframe(monthly_occupancy)

        # Optional: Visualize as a heatmap
        st.subheader("Mapa de Calor de Ocupación Mensual")
        try:
            # The index needs to be strings for the heatmap to work correctly
            monthly_occupancy.index = monthly_occupancy.index.astype(str)

            # Use Spanish month names
            month_names_spanish = [
                "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
            ]

            fig_heatmap = px.imshow(
                monthly_occupancy.T, # Transpose for months as rows
                labels=dict(x="Nombre de la Propiedad", y="Mes", color="Días Ocupados"),
                x=monthly_occupancy.index,
                y=month_names_spanish,
                color_continuous_scale="Viridis"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        except Exception as e:
            st.error(f"Error al crear el mapa de calor: {e}")

    else:
        st.info(f"No se encontraron reservas para el año {selected_year}.")
else:
    st.info("No hay datos de reservas disponibles para mostrar la ocupación mensual.")
