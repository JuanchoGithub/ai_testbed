import streamlit as st

# --- APP-001: Set Up Main App Entry Point & Basic Config ---
# Configure the Streamlit page settings
st.set_page_config(
    page_title="Rental Manager",
    page_icon="🏠",  # Optional: Add a relevant emoji or icon path
    layout="wide"    # Use wide layout for better data display
)

# Display a title and a brief welcome/instruction message on the main page
st.title("Welcome to the Rental Manager 🏠")
st.markdown(
    """
    This application helps you manage your rental properties, bookings, and expenses.

    **Navigate using the sidebar** to access different sections:
    - **Occupancy Overview:** View current and upcoming occupancy status.
    - **Manage Properties:** Add or view property details.
    - **Manage Bookings:** Add or view booking information.
    - **Manage Expenses:** Log and track property-related expenses.
    - **Reporting:** Generate financial summaries (coming soon).

    Select a page from the sidebar to begin.
    """
)

# Note: Streamlit automatically discovers and lists pages
# from the 'pages/' directory in the sidebar. No extra code needed here for navigation.
