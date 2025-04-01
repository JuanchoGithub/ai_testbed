import streamlit as st

# --- APP-001: Set Up Main App Entry Point & Basic Config ---
# Configure the Streamlit page settings
st.set_page_config(
    page_title="Gestor de Alquileres",
    page_icon="🏠",  # Optional: Add a relevant emoji or icon path
    layout="wide"    # Use wide layout for better data display
)

# Display a title and a brief welcome/instruction message on the main page
st.title("Bienvenido al Gestor de Alquileres 🏠")
st.markdown(
    """
    Esta aplicación te ayuda a gestionar tus propiedades de alquiler, reservas y gastos.

    **Navega usando la barra lateral** para acceder a diferentes secciones:
    - **Resumen de Ocupación:** Ver el estado de ocupación actual y próximo.
    - **Gestionar Propiedades:** Agregar o ver detalles de propiedades.
    - **Gestionar Reservas:** Agregar o ver información de reservas.
    - **Gestionar Gastos:** Registrar y rastrear gastos relacionados con la propiedad.
    - **Reportes:** Generar resúmenes financieros (próximamente).

    Selecciona una página de la barra lateral para comenzar.
    """
)

# Note: Streamlit automatically discovers and lists pages
# from the 'pages/' directory in the sidebar. No extra code needed here for navigation.
