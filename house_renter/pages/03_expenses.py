import streamlit as st
import pandas as pd
import data_manager
from datetime import date, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="Manage Expenses", page_icon="💸", layout="wide")
st.title("💸 Manage Expenses")

# --- Constants ---
EXPENSE_CATEGORIES = [
    "Maintenance", "Repairs", "Utilities", "Management Fees",
    "Taxes", "Insurance", "Supplies", "Cleaning", "Travel", "Other"
]

# --- Load Data ---
try:
    properties_df = data_manager.load_properties()
    expenses_df = data_manager.load_expenses()
except Exception as e:
    st.error(f"Error loading data: {e}")
    properties_df = pd.DataFrame(columns=data_manager.PROPERTIES_COLS)
    expenses_df = pd.DataFrame(columns=data_manager.EXPENSES_COLS)

# --- EXP-001: Add Expense Form ---
st.subheader("Add New Expense")

if properties_df.empty:
    st.warning("No properties found. Please add a property first on the 'Manage Properties' page.")
else:
    # Create a dictionary mapping property names to IDs for the selectbox
    property_options = {row['name']: row['id'] for index, row in properties_df.iterrows()}
    property_names = list(property_options.keys())

    with st.form("add_expense_form", clear_on_submit=True):
        st.write("Log a new expense for a property:")

        # Property Selection
        selected_property_name = st.selectbox(
            "Select Property*",
            options=property_names,
            index=0, # Default to the first property
            help="Choose the property this expense relates to."
        )

        # Expense Date
        expense_date = st.date_input(
            "Expense Date*",
            value=date.today(), # Default to today
            help="The date the expense was incurred."
        )

        # Category
        category = st.selectbox(
            "Category*",
            options=EXPENSE_CATEGORIES,
            index=0, # Default to the first category
            help="Select the type of expense."
        )

        # Amount
        amount = st.number_input(
            "Amount (€)*",
            min_value=0.01,
            step=0.01,
            format="%.2f",
            help="Enter the cost of the expense."
        )

        # Description
        description = st.text_area(
            "Description",
            placeholder="Optional: Add details about the expense (e.g., invoice number, specific service).",
            help="Provide any relevant details about the expense."
        )

        # Submit Button
        submitted = st.form_submit_button("Add Expense")

        if submitted:
            # Basic validation (although some is handled by widgets)
            if not selected_property_name or not expense_date or not category or amount <= 0:
                st.warning("Please fill in all required fields (*) with valid values.")
            else:
                # Get the property ID from the selected name
                property_id = property_options[selected_property_name]

                # Call data_manager function to add the expense
                success = data_manager.add_expense(
                    property_id=property_id,
                    expense_date=expense_date,
                    category=category,
                    amount=amount,
                    description=description if description else None # Pass None if empty
                )

                if success:
                    st.success(f"Expense of €{amount:.2f} for '{selected_property_name}' on {expense_date} added successfully!")
                    # Form clears automatically due to clear_on_submit=True
                    # Rerun will load updated expenses
                else:
                    # Error message is usually shown by _save_data in data_manager
                    st.error("Failed to add expense. Check logs for details.")

# --- EXP-002: Display Expenses List ---
st.divider()
st.subheader("Existing Expenses")

if expenses_df.empty:
    st.info("No expenses recorded yet. Use the form above to add one.")
else:
    # --- Filtering Options ---
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        # Property Filter
        filter_property_options = {"All Properties": None}
        filter_property_options.update({name: prop_id for name, prop_id in property_options.items()})
        selected_filter_property_name = st.selectbox(
            "Filter by Property",
            options=list(filter_property_options.keys()),
            index=0 # Default to "All Properties"
        )
        selected_filter_property_id = filter_property_options[selected_filter_property_name]

    # Date Range Filter - Default to last 90 days or min/max dates
    min_date = expenses_df['expense_date'].min().date() if not expenses_df['expense_date'].isnull().all() else date.today() - timedelta(days=90)
    max_date = expenses_df['expense_date'].max().date() if not expenses_df['expense_date'].isnull().all() else date.today()

    with col2:
        filter_start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
    with col3:
        filter_end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

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
            st.info("No expenses match the current filter criteria.")
        else:
            # Select and order columns for display
            display_columns = [
                'Property Name', 'expense_date', 'category', 'amount', 'description', 'id'
            ]
            # Filter columns that actually exist in the dataframe
            display_columns = [col for col in display_columns if col in filtered_df.columns]
            display_df = filtered_df[display_columns].copy()

            # Rename columns for better readability
            display_df.rename(columns={
                'expense_date': 'Date',
                'category': 'Category',
                'amount': 'Amount (€)',
                'description': 'Description',
                'id': 'Expense ID'
            }, inplace=True)

            # Format date column
            if 'Date' in display_df.columns:
                 display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d')

            # Format currency column
            if 'Amount (€)' in display_df.columns:
                display_df['Amount (€)'] = display_df['Amount (€)'].map('{:,.2f}'.format)

            # Display the dataframe
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_order=[col for col in ['Property Name', 'Date', 'Category', 'Amount (€)', 'Description', 'Expense ID'] if col in display_df.columns]
                # Optional: Configure column widths or types if needed
                # column_config={ ... }
            )

            # --- Summary Statistics ---
            st.subheader("Filtered Expense Summary")
            total_expenses = pd.to_numeric(filtered_df['amount'], errors='coerce').sum()
            st.metric("Total Expenses (Filtered)", f"€{total_expenses:,.2f}")

            # Optional: Add more summary stats like count or average

    except Exception as e:
        st.error(f"An error occurred while preparing or displaying expenses: {e}")
        st.dataframe(pd.DataFrame()) # Display empty dataframe on error

