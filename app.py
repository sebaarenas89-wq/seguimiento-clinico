import streamlit as st

st.set_page_config(
    page_title="Seguimiento Clínico",
    layout="wide"
)

st.title("Seguimiento Clínico Farmacéutico")

st.sidebar.title("Menú")
seccion = st.sidebar.radio(
    "Selecciona una sección",
    ["Pacientes", "Ficha clínica", "Evolución diaria"]
)

if seccion == "Pacientes":
    st.header("Pacientes")
    st.info("Aquí se ingresarán y visualizarán pacientes.")

elif seccion == "Ficha clínica":
    st.header("Ficha clínica")
    st.info("Aquí se visualizará la ficha individual del paciente.")

elif seccion == "Evolución diaria":
    st.header("Evolución diaria")
    st.info("Aquí se registrará la evolución clínica diaria.")
