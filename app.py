import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Seguimiento Clínico",
    layout="wide"
)

# Base temporal de pacientes
if "pacientes" not in st.session_state:
    st.session_state.pacientes = []

st.title("🏥 Seguimiento Clínico Farmacéutico")

menu = st.sidebar.radio(
    "Menú",
    ["Pacientes", "Ficha clínica", "Evolución diaria"]
)

# --------------------------
# INGRESO DE PACIENTES
# --------------------------

if menu == "Pacientes":

    st.header("👤 Ingreso de paciente")

    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input("Nombre paciente")
        id_paciente = st.text_input("ID paciente")
        servicio = st.selectbox(
            "Servicio",
            [
                "UCI",
                "UTI",
                "UCO",
                "Medicina",
                "Cirugía"
            ]
        )

    with col2:
        fecha_ingreso = st.date_input("Fecha ingreso")
        diagnosticos = st.text_area("Diagnósticos")

    if st.button("Guardar paciente"):

        st.session_state.pacientes.append(
            {
                "Nombre": nombre,
                "ID": id_paciente,
                "Servicio": servicio,
                "Ingreso": fecha_ingreso,
                "Diagnósticos": diagnosticos
            }
        )

        st.success("Paciente guardado correctamente")

    st.divider()

    st.subheader("Pacientes registrados")

    if len(st.session_state.pacientes) > 0:

        df = pd.DataFrame(st.session_state.pacientes)

        st.dataframe(
            df,
            use_container_width=True
        )

    else:
        st.info("No existen pacientes registrados")

# --------------------------
# FICHA CLÍNICA
# --------------------------

elif menu == "Ficha clínica":

    st.header("📋 Ficha clínica")

    if len(st.session_state.pacientes) == 0:

        st.warning("No existen pacientes")

    else:

        nombres = [
            p["Nombre"]
            for p in st.session_state.pacientes
        ]

        paciente = st.selectbox(
            "Seleccione paciente",
            nombres
        )

        datos = next(
            p
            for p in st.session_state.pacientes
            if p["Nombre"] == paciente
        )

        st.write("### Datos generales")

        st.write(f"**Nombre:** {datos['Nombre']}")
        st.write(f"**ID:** {datos['ID']}")
        st.write(f"**Servicio:** {datos['Servicio']}")
        st.write(f"**Diagnósticos:** {datos['Diagnósticos']}")

# --------------------------
# EVOLUCIÓN
# --------------------------

elif menu == "Evolución diaria":

    st.header("📝 Evolución diaria")

    st.info(
        "Aquí construiremos la evolución clínica diaria."
    )
