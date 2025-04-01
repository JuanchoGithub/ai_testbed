import streamlit as st
import data_manager

# --- APP-001: Set Up Main App Entry Point & Basic Config ---
# Configure the Streamlit page settings
st.set_page_config(
    page_title="Gestor de Alquileres",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)


if not data_manager.check_password():
    st.stop()  # Do not continue if not authenticated


# --- APP-002: Main Page Content ---
st.title("Bienvenido al Gestor de Alquileres 🏠")
st.markdown(
    """
    Esta aplicación te ayuda a gestionar tus propiedades de alquiler, reservas y gastos de manera eficiente.

    **Navegación:** Utiliza el menú de la barra lateral para acceder a las diferentes secciones.  Cada sección está diseñada para ayudarte con una tarea específica:

    - **Resumen de Ocupación:**  Obtén una vista clara del estado de ocupación de tus propiedades.
    - **Gestionar Propiedades:**  Añade, edita y visualiza los detalles de tus propiedades de alquiler.
    - **Gestionar Reservas:**  Crea, consulta y modifica las reservas de tus propiedades.
    - **Gestionar Gastos:**  Registra y organiza los gastos asociados a cada propiedad.
    - **Reportes:**  Genera informes y resúmenes financieros (próximamente).

    """
)

st.sidebar.header("Navegación")
st.sidebar.markdown("Selecciona una opción para comenzar.")
st.sidebar.success("Autenticación exitosa") # Optional: feedback on successful auth        # Password correct.
