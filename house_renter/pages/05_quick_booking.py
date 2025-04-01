import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import data_manager

# --- Page Configuration ---
st.set_page_config(page_title="Quick Booking", layout="wide")
st.title("⚡ Quick Booking")

# --- Load Data ---
try:
    properties_df = data_manager.load_properties()
    bookings_df = data_manager.load_bookings()
except Exception as e:
    st.error(f"Error loading data: {e}")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS)
    bookings_df = pd.DataFrame(columns=data_manager.BOOKINGS_COLS)

if properties_df.empty:
    st.warning("No properties found. Please add properties on the 'Manage Properties' page first.", icon="⚠️")
    st.stop()

# --- Property Selection ---
property_names = properties_df['name'].tolist()
selected_property_name = st.selectbox("Select Property", options=property_names, index=0 if property_names else None, placeholder="Choose a property...")

if not selected_property_name:
    st.info("Select a property to manage its bookings.")
    st.stop()

selected_property = properties_df[properties_df['name'] == selected_property_name].iloc[0]
property_id = selected_property['id']

# --- Date Range Selection ---
today = date.today()
start_date = st.date_input("Start Date", value=today, min_value=today)
end_date = st.date_input("End Date", value=today + timedelta(days=7), min_value=start_date)

# --- Check for Existing Bookings ---
existing_bookings = bookings_df[
    (bookings_df['property_id'] == property_id) &
    ((bookings_df['start_date'] <= pd.to_datetime(end_date)) & (bookings_df['end_date'] >= pd.to_datetime(start_date)))
]

if not existing_bookings.empty:
    st.warning(f"This property is already booked for the selected dates.  Overlapping bookings:")
    st.dataframe(existing_bookings)
    # Option to delete bookings could be added here, but requires careful consideration
else:
    st.success("Property is available for the selected dates.")

# --- Booking Details (Simplified) ---
tenant_name = st.text_input("Tenant Name", placeholder="Enter tenant name (optional)")
rent_amount = st.number_input("Rent Amount", min_value=0.0, value=1000.0, step=100.0)

# --- Add Booking Button ---
if st.button("Book Property"):
    # --- Validation ---
    if not start_date or not end_date:
        st.error("Please select both start and end dates.")
    elif end_date <= start_date:
        st.error("End date must be after start date.")
    else:
        # --- Add Booking ---
        try:
            success = data_manager.add_booking(
                property_id=property_id,
                tenant_name=tenant_name or "Quick Booking",
                start_date=start_date,
                end_date=end_date,
                rent_amount=float(rent_amount),
                source="Quick Booking",  # Or a default source
                commission_paid=0.0,
                notes="Quick booking via Quick Booking page"
            )

            if success:
                st.success(f"Property '{selected_property_name}' booked successfully for {start_date} - {end_date}!")
            else:
                st.error("Failed to add booking. Check logs for details.")

        except Exception as e:
            st.error(f"An error occurred: {e}")

# --- Display existing bookings for this property ---
st.subheader(f"Existing Bookings for {selected_property_name}")
property_bookings = bookings_df[bookings_df['property_id'] == property_id]

if property_bookings.empty:
    st.info("No bookings found for this property.")
else:
    st.dataframe(property_bookings)
