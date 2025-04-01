import streamlit as st
import pandas as pd
import datetime
import data_manager # Assuming data_manager.py is in src/

# --- Page Configuration ---
st.set_page_config(page_title="Manage Bookings", layout="wide")
st.title("Manage Bookings 📅")

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
        st.warning("No properties found. Please add properties on the 'Manage Properties' page first.", icon="⚠️")

except Exception as e:
    st.error(f"Error loading properties: {e}")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS) # Empty df
    property_options = {}
    property_name_map = {}

# Define booking sources (Ideally, these might come from data_manager or a config file)
BOOKING_SOURCES = ['Direct', 'Airbnb', 'Booking.com', 'Vrbo', 'Other']
SOURCES_REQUIRING_COMMISSION = ['Airbnb', 'Booking.com', 'Vrbo'] # Example sources where commission is typical

# --- BOOK-001: Add Booking Form ---
with st.expander("Add New Booking"):
    st.subheader("Add New Booking")

    # Use a form for batch input
    with st.form("add_booking_form", clear_on_submit=True):
        st.write("Enter the details for the new booking:")

        # Property Selection
        if not property_options:
            st.error("Cannot add booking: No properties available.")
            selected_property_name = None
        else:
            selected_property_name = st.selectbox(
                "Select Property*",
                options=list(property_options.keys()),
                index=None, # No default selection
                placeholder="Choose a property...",
                help="Select the property this booking is for."
            )

        # Booking Details Columns
        col1, col2 = st.columns(2)
        with col1:
            tenant_name = st.text_input("Tenant Name*", help="Enter the primary tenant's name.")
            start_date = st.date_input("Start Date*", value=None, help="Booking start date.") # Defaults to today if value=datetime.date.today()
            rent_amount = st.number_input("Rent Amount*", min_value=0.0, value=None, step=50.0, format="%.2f", help="Total rent for the booking period.")
            source = st.selectbox(
                "Booking Source*",
                options=BOOKING_SOURCES,
                index=None,
                placeholder="Select the source...",
                help="How was this booking made?"
            )

        with col2:
            # Empty space or add other fields here if needed
            st.empty() # Placeholder to maintain layout balance if needed
            end_date = st.date_input("End Date*", value=None, help="Booking end date.")
            # Conditional Commission Input
            commission_paid = 0.0 # Default to 0
            show_commission = source in SOURCES_REQUIRING_COMMISSION if source else False
            if show_commission:
                commission_paid = st.number_input(
                    "Commission Paid",
                    min_value=0.0,
                    value=0.0, # Default to 0 even when shown
                    step=10.0,
                    format="%.2f",
                    help=f"Commission paid to {source} (if applicable)."
                )
            else:
                # Optionally display a disabled field or hide it completely
                st.empty() # Hide if not applicable

        # Notes (spans across columns)
        notes = st.text_area("Notes", placeholder="Enter any relevant notes about the booking...", help="Optional notes.")

        # Submit Button
        submitted = st.form_submit_button("Add Booking")

        if submitted:
            # --- Form Validation ---
            validation_passed = True
            if not selected_property_name:
                st.warning("Please select a property.", icon="⚠️")
                validation_passed = False
            if not tenant_name:
                st.warning("Tenant Name is required.", icon="⚠️")
                validation_passed = False
            if not start_date:
                st.warning("Start Date is required.", icon="⚠️")
                validation_passed = False
            if not end_date:
                st.warning("End Date is required.", icon="⚠️")
                validation_passed = False
            if start_date and end_date and end_date < start_date:
                st.warning("End Date cannot be before Start Date.", icon="⚠️")
                validation_passed = False
            if rent_amount is None: # Check for None explicitly as 0 is valid
                 st.warning("Rent Amount is required.", icon="⚠️")
                 validation_passed = False
            elif rent_amount < 0:
                 st.warning("Rent Amount cannot be negative.", icon="⚠️")
                 validation_passed = False
            if not source:
                st.warning("Booking Source is required.", icon="⚠️")
                validation_passed = False
            if show_commission and commission_paid < 0:
                 st.warning("Commission Paid cannot be negative.", icon="⚠️")
                 validation_passed = False

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
                        source=source,
                        commission_paid=float(commission_paid) if show_commission else 0.0, # Ensure commission is 0 if not applicable
                        notes=notes
                    )

                    if success:
                        st.success(f"Booking for '{tenant_name}' at property '{selected_property_name}' added successfully!")
                        # Form clears automatically due to clear_on_submit=True
                        # Rerun will load updated bookings
                    else:
                        # Error message likely shown by _save_data in data_manager
                        st.error("Failed to add booking. Check logs for details.")

                except Exception as e:
                    st.error(f"An error occurred while adding the booking: {e}")
            elif not selected_property_name and validation_passed:
                 st.error("Cannot add booking: No property was selected (this should not happen if validation passed).")


# --- BOOK-002: Display Bookings List ---
st.divider()
st.subheader("Existing Bookings")

# --- Filtering ---
# Prepare filter options, including "All"
filter_property_options = ["All Properties"] + list(property_options.keys())
selected_filter_property_name = st.selectbox(
    "Filter by Property",
    options=filter_property_options,
    index=0, # Default to "All Properties"
    help="Select a property to view only its bookings."
)

# --- Load and Display Bookings ---
try:
    bookings_df = data_manager.load_bookings()

    if bookings_df.empty:
        st.info("No bookings found. Add a booking using the form above.")
    else:
        # Merge with properties to get names
        # Ensure property_id types match for merging (Int64Dtype handles NA)
        if 'property_id' in bookings_df.columns and not properties_df.empty:
             # Convert property_id in properties_df to Int64Dtype if needed for merge compatibility
            if 'id' in properties_df.columns and properties_df['id'].dtype != bookings_df['property_id'].dtype:
                 try:
                     properties_df_merged = properties_df.astype({'id': bookings_df['property_id'].dtype})
                 except Exception as e:
                     st.warning(f"Could not align property ID types for merging: {e}. Displaying IDs instead of names.")
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
            merged_df.rename(columns={'name': 'Property Name'}, inplace=True)
            merged_df.drop(columns=['id_y'] if 'id_y' in merged_df.columns else ['id'], inplace=True, errors='ignore') # Drop the id from properties
            # Fill missing property names if any occurred during merge
            merged_df['Property Name'].fillna('Unknown Property', inplace=True)

        else:
            merged_df = bookings_df.copy() # Work with bookings_df directly if no properties or ID column
            if 'property_id' in merged_df.columns:
                 merged_df['Property Name'] = merged_df['property_id'].map(property_name_map).fillna('Unknown Property')
            else:
                 merged_df['Property Name'] = 'N/A' # Or handle as appropriate if property_id is missing


        # Apply Filter
        if selected_filter_property_name != "All Properties":
            filtered_df = merged_df[merged_df['Property Name'] == selected_filter_property_name]
        else:
            filtered_df = merged_df

        if filtered_df.empty and selected_filter_property_name != "All Properties":
             st.info(f"No bookings found for property '{selected_filter_property_name}'.")
        elif filtered_df.empty:
             st.info("No bookings match the current filter.") # Should not happen if "All" selected unless df was empty initially
        else:
            # Select and order columns for display
            display_columns = [
                'Property Name', 'tenant_name', 'start_date', 'end_date',
                'rent_amount', 'source', 'commission_paid', 'notes', 'id' # Keep 'id' for reference if needed, maybe hide later
            ]
            # Filter columns that actually exist in the dataframe
            display_columns = [col for col in display_columns if col in filtered_df.columns]

            display_df = filtered_df[display_columns].copy()

            # Rename columns for better readability
            display_df.rename(columns={
                'tenant_name': 'Tenant Name',
                'start_date': 'Start Date',
                'end_date': 'End Date',
                'rent_amount': 'Rent Amount (€)', # Assuming Euro, adjust as needed
                'source': 'Source',
                'commission_paid': 'Commission (€)', # Assuming Euro
                'notes': 'Notes',
                'id': 'Booking ID'
            }, inplace=True)

            # Format date columns if they are not already strings
            if 'Start Date' in display_df.columns:
                 display_df['Start Date'] = pd.to_datetime(display_df['Start Date']).dt.strftime('%Y-%m-%d')
            if 'End Date' in display_df.columns:
                 display_df['End Date'] = pd.to_datetime(display_df['End Date']).dt.strftime('%Y-%m-%d')

            # Format currency columns
            if 'Rent Amount (€)' in display_df.columns:
                display_df['Rent Amount (€)'] = display_df['Rent Amount (€)'].map('{:,.2f}'.format)
            if 'Commission (€)' in display_df.columns:
                display_df['Commission (€)'] = display_df['Commission (€)'].map('{:,.2f}'.format)


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
    st.info("Bookings file not found. It will be created when you add the first booking.")
except Exception as e:
    st.error(f"An error occurred while loading or displaying bookings: {e}")
    st.dataframe(pd.DataFrame()) # Display empty dataframe on error

