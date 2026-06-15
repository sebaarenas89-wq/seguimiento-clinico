import streamlit as st

st.set_page_config(
    page_title="Seguimiento Clínico Farmacéutico",
    layout="wide"
)

st.title("🏥 Seguimiento Clínico Farmacéutico")

menu = st.sidebar.radio(
    "Menú",
    ["Pacientes", "Ficha clínica", "Evolución diaria"]
)

if menu == "Pacientes":

    st.header("👤 Ingreso de paciente")

    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input("Nombre paciente")
        rut = st.text_input("ID paciente")
        servicio = st.selectbox(
            "Servicio",
            ["UCI", "UTI", "Medicina", "Cirugía", "Cardiología"]
        )

    with col2:
        fecha_ingreso = st.date_input("Fecha ingreso")
        diagnostico = st.text_area("Diagnósticos")

    if st.button("Guardar paciente"):
        st.success("Paciente guardado (versión demostración)")

elif menu == "Ficha clínica":

    st.header("📋 Ficha clínica")

    st.selectbox(
        "Seleccionar paciente",
        [
            "Paciente ejemplo 1",
            "Paciente ejemplo 2"
        ]
    )

    st.subheader("Motivo de ingreso")
    st.text_area("", height=120)

    st.subheader("Antecedentes")
    st.text_area(" ", height=120)

    st.subheader("Terapia antimicrobiana")
    st.text_area("  ", height=120)

elif menu == "Evolución diaria":

    st.header("📝 Evolución diaria")

    fecha = st.date_input("Fecha evolución")

    evolucion = st.text_area(
        "Registrar evolución clínica",
        height=200
    )

    if st.button("Guardar evolución"):
        st.success("Evolución guardada (versión demostración)")
