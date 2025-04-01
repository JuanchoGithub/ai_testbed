import streamlit as st
import pandas as pd
import sys
import os

# Add the parent directory (src) to the Python path to allow importing data_manager
# This assumes the pages directory is directly inside src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import data_manager
except ImportError:
    st.error("Could not import the data_manager module. Make sure it's in the 'src' directory.")
    st.stop() # Stop execution if data_manager cannot be imported

# --- Page Configuration (Optional but Recommended) ---
# st.set_page_config(page_title="Manage Properties", layout="wide") # Can be set in main app.py or here

st.title("🏘️ Manage Properties")
st.markdown("Add new properties or view existing ones.")

# --- PROP-001: Add Property Form ---
st.subheader("Add New Property")

# Use a form for adding properties
# clear_on_submit=True ensures fields are reset after successful submission
with st.form("add_property_form", clear_on_submit=True):
    property_name = st.text_input("Property Name*", help="Enter the name or identifier for the property (e.g., 'Downtown Condo', 'Beach House').")
    property_address = st.text_area("Address", help="Enter the full address of the property.")

    # Submit button for the form
    submitted = st.form_submit_button("Add Property")

    if submitted:
        # Basic validation
        if not property_name:
            st.warning("Property Name is required.")
        else:
            # Call the function from data_manager to add the property
            success = data_manager.add_property(name=property_name, address=property_address)
            if success:
                st.success(f"Property '{property_name}' added successfully!")
                # No need to manually clear fields due to clear_on_submit=True
                # Streamlit will rerun, and load_properties will fetch the updated list
            else:
                # data_manager._save_data already shows an st.error
                st.error("Failed to add property. Please check the application logs.")
                # Form fields will persist in case of error for correction

# --- PROP-002: Display Property List ---
st.divider() # Add a visual separator
st.subheader("Existing Properties")

# Load properties using the function from data_manager
# This benefits from @st.cache_data in data_manager
try:
    properties_df = data_manager.load_properties()
except Exception as e:
    st.error(f"Error loading properties: {e}")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS) # Provide empty df

if properties_df.empty:
    st.info("No properties found. Add a property using the form above.")
else:
    # Display properties in a dataframe
    # Select and potentially rename columns for better presentation
    # Ensure 'id', 'name', 'address' exist before trying to access them
    display_columns = [col for col in ['id', 'name', 'address'] if col in properties_df.columns]
    if not display_columns:
        st.warning("Property data is missing expected columns ('id', 'name', 'address'). Displaying raw data.")
        st.dataframe(properties_df, use_container_width=True)
    else:
        display_df = properties_df[display_columns].copy()
        # Optional: Rename columns for display
        display_df.rename(columns={'name': 'Name', 'address': 'Address', 'id': 'ID'}, inplace=True)
        st.dataframe(
            display_df,
            hide_index=True, # Don't show the default pandas index
            use_container_width=True # Make the table use the full container width
        )
