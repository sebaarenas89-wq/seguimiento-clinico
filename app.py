import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="Seguimiento Clínico",
    layout="wide"
)

# --------------------------
# BASE TEMPORAL
# --------------------------

if "pacientes" not in st.session_state:
    st.session_state.pacientes = []

if "evoluciones" not in st.session_state:
    st.session_state.evoluciones = []

# --------------------------
# TÍTULO Y MENÚ
# --------------------------

st.title("🏥 Seguimiento Clínico Farmacéutico")

menu = st.sidebar.radio(
    "Menú",
    ["Pacientes", "Ficha clínica", "Evolución diaria"]
)

# --------------------------
# PACIENTES
# --------------------------

if menu == "Pacientes":

    st.header("👤 Ingreso de paciente")

    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input("Nombre paciente")
        id_paciente = st.text_input("ID paciente")
        servicio = st.selectbox(
            "Servicio",
            ["UCI", "UTI", "UCO", "Medicina", "Cirugía"]
        )

    with col2:
        fecha_ingreso = st.date_input("Fecha ingreso")
        diagnosticos = st.text_area("Diagnósticos")

    if st.button("Guardar paciente"):

        if nombre == "" or id_paciente == "":
            st.error("Debe ingresar nombre e ID del paciente")

        else:
            nuevo_paciente = {
                "Nombre": nombre,
                "ID": id_paciente,
                "Servicio": servicio,
                "Ingreso": fecha_ingreso,
                "Diagnósticos": diagnosticos
            }

            st.session_state.pacientes.append(nuevo_paciente)
            st.success("Paciente guardado correctamente")

    st.divider()

    st.subheader("Pacientes registrados")

    if len(st.session_state.pacientes) > 0:
        df = pd.DataFrame(st.session_state.pacientes)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No existen pacientes registrados")

# --------------------------
# FICHA CLÍNICA
# --------------------------

elif menu == "Ficha clínica":

    st.header("📋 Ficha clínica")

    if len(st.session_state.pacientes) == 0:
        st.warning("No existen pacientes registrados")

    else:
        nombres = [p["Nombre"] for p in st.session_state.pacientes]

        paciente = st.selectbox(
            "Seleccione paciente",
            nombres
        )

        datos = next(
            p for p in st.session_state.pacientes
            if p["Nombre"] == paciente
        )

        st.subheader(datos["Nombre"])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Servicio", datos["Servicio"])

        with col2:
            st.metric("ID paciente", datos["ID"])

        with col3:
            st.metric("Fecha ingreso", str(datos["Ingreso"]))

        st.write("### Diagnósticos")
        st.info(datos["Diagnósticos"])

        st.divider()

        st.write("### Evoluciones registradas")

        evoluciones_paciente = [
            e for e in st.session_state.evoluciones
            if e["Paciente"] == paciente
        ]

        if len(evoluciones_paciente) > 0:

    evoluciones_paciente = sorted(
        evoluciones_paciente,
        key=lambda x: x["Fecha"],
        reverse=True
    )

    for evo in evoluciones_paciente:

        with st.container(border=True):
            st.subheader(f"📅 {evo['Fecha']}")

            st.markdown("**Evolución clínica**")
            st.write(evo["Evolución clínica"])

            st.markdown("**Resultados laboratorio**")
            st.write(evo["Resultados laboratorio"])

            st.markdown("**Resultados microbiología**")
            st.write(evo["Resultados microbiología"])

            st.markdown("**Antimicrobianos activos**")
            st.write(evo["Antimicrobianos activos"])

            st.markdown("**Intervención farmacéutica**")
            st.write(evo["Intervención farmacéutica"])

else:
    st.info("Este paciente aún no tiene evoluciones registradas")

# --------------------------
# EVOLUCIÓN DIARIA
# --------------------------

elif menu == "Evolución diaria":

    st.header("📝 Evolución clínica diaria")

    if len(st.session_state.pacientes) == 0:
        st.warning("Debe ingresar al menos un paciente antes de registrar evolución")

    else:
        nombres = [p["Nombre"] for p in st.session_state.pacientes]

        paciente = st.selectbox(
            "Paciente",
            nombres
        )

        fecha_evolucion = st.date_input(
            "Fecha evolución",
            value=date.today()
        )

        evolucion_clinica = st.text_area(
            "Evolución clínica",
            height=150
        )

        resultados_laboratorio = st.text_area(
            "Resultados laboratorio",
            height=120
        )

        resultados_microbiologia = st.text_area(
            "Resultados microbiología",
            height=120
        )

        antimicrobianos_activos = st.text_area(
            "Antimicrobianos activos",
            height=100
        )

        intervencion_farmaceutica = st.text_area(
            "Intervención farmacéutica",
            height=120
        )

        if st.button("Guardar evolución"):

            nueva_evolucion = {
                "Paciente": paciente,
                "Fecha": fecha_evolucion,
                "Evolución clínica": evolucion_clinica,
                "Resultados laboratorio": resultados_laboratorio,
                "Resultados microbiología": resultados_microbiologia,
                "Antimicrobianos activos": antimicrobianos_activos,
                "Intervención farmacéutica": intervencion_farmaceutica
            }

            st.session_state.evoluciones.append(nueva_evolucion)

            st.success("Evolución guardada correctamente")

        st.divider()

        st.subheader("Evoluciones del paciente")

        evoluciones_paciente = [
            e for e in st.session_state.evoluciones
            if e["Paciente"] == paciente
        ]

        if len(evoluciones_paciente) > 0:
            df = pd.DataFrame(evoluciones_paciente)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay evoluciones registradas para este paciente")
