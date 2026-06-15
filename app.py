import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Seguimiento Clínico", layout="wide")

DB_NAME = "seguimiento_clinico.db"


def conectar_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def crear_tablas():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            id_paciente TEXT NOT NULL,
            servicio TEXT,
            fecha_ingreso TEXT,
            diagnosticos TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evoluciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            fecha TEXT,
            evolucion_clinica TEXT,
            resultados_laboratorio TEXT,
            resultados_microbiologia TEXT,
            antimicrobianos_activos TEXT,
            intervencion_farmaceutica TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        )
    """)

    conn.commit()
    conn.close()


def guardar_paciente(nombre, id_paciente, servicio, fecha_ingreso, diagnosticos):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pacientes (
            nombre, id_paciente, servicio, fecha_ingreso, diagnosticos
        )
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, id_paciente, servicio, str(fecha_ingreso), diagnosticos))
    conn.commit()
    conn.close()


def actualizar_paciente(paciente_id, nombre, id_paciente, servicio, fecha_ingreso, diagnosticos):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pacientes
        SET nombre = ?, id_paciente = ?, servicio = ?, fecha_ingreso = ?, diagnosticos = ?
        WHERE id = ?
    """, (nombre, id_paciente, servicio, str(fecha_ingreso), diagnosticos, int(paciente_id)))
    conn.commit()
    conn.close()


def obtener_pacientes():
    conn = conectar_db()
    df = pd.read_sql_query("SELECT * FROM pacientes", conn)
    conn.close()
    return df


def guardar_evolucion(
    paciente_id,
    fecha,
    evolucion_clinica,
    resultados_laboratorio,
    resultados_microbiologia,
    antimicrobianos_activos,
    intervencion_farmaceutica
):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO evoluciones (
            paciente_id, fecha, evolucion_clinica, resultados_laboratorio,
            resultados_microbiologia, antimicrobianos_activos, intervencion_farmaceutica
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        int(paciente_id),
        str(fecha),
        evolucion_clinica,
        resultados_laboratorio,
        resultados_microbiologia,
        antimicrobianos_activos,
        intervencion_farmaceutica
    ))

    conn.commit()
    conn.close()


def actualizar_evolucion(
    evolucion_id,
    fecha,
    evolucion_clinica,
    resultados_laboratorio,
    resultados_microbiologia,
    antimicrobianos_activos,
    intervencion_farmaceutica
):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE evoluciones
        SET
            fecha = ?,
            evolucion_clinica = ?,
            resultados_laboratorio = ?,
            resultados_microbiologia = ?,
            antimicrobianos_activos = ?,
            intervencion_farmaceutica = ?
        WHERE id = ?
    """, (
        str(fecha),
        evolucion_clinica,
        resultados_laboratorio,
        resultados_microbiologia,
        antimicrobianos_activos,
        intervencion_farmaceutica,
        int(evolucion_id)
    ))

    conn.commit()
    conn.close()

def eliminar_evolucion(evolucion_id):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM evoluciones
        WHERE id = ?
    """, (int(evolucion_id),))

    conn.commit()
    conn.close()
    
def eliminar_paciente(paciente_id):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM evoluciones
        WHERE paciente_id = ?
    """, (int(paciente_id),))

    cursor.execute("""
        DELETE FROM pacientes
        WHERE id = ?
    """, (int(paciente_id),))

    conn.commit()
    conn.close()

def obtener_evoluciones_paciente(paciente_id):
    conn = conectar_db()
    df = pd.read_sql_query(
        """
        SELECT
            id,
            fecha,
            evolucion_clinica,
            resultados_laboratorio,
            resultados_microbiologia,
            antimicrobianos_activos,
            intervencion_farmaceutica
        FROM evoluciones
        WHERE paciente_id = ?
        ORDER BY fecha DESC
        """,
        conn,
        params=(int(paciente_id),)
    )
    conn.close()
    return df


crear_tablas()

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
        id_paciente = st.text_input("ID paciente")
        servicio = st.selectbox("Servicio", ["UCI", "UTI", "UCO", "Medicina", "Cirugía"])

    with col2:
        fecha_ingreso = st.date_input("Fecha ingreso")
        diagnosticos = st.text_area("Diagnósticos")

    if st.button("Guardar paciente"):
        if nombre == "" or id_paciente == "":
            st.error("Debe ingresar nombre e ID del paciente")
        else:
            guardar_paciente(nombre, id_paciente, servicio, fecha_ingreso, diagnosticos)
            st.success("Paciente guardado correctamente")

    st.divider()
    st.subheader("Pacientes registrados")

    pacientes_df = obtener_pacientes()

    if len(pacientes_df) > 0:
        st.dataframe(pacientes_df, use_container_width=True)
    else:
        st.info("No existen pacientes registrados")


elif menu == "Ficha clínica":

    st.header("📋 Ficha clínica")

    pacientes_df = obtener_pacientes()

    if len(pacientes_df) == 0:
        st.warning("No existen pacientes registrados")

    else:
        pacientes_df["selector"] = pacientes_df["nombre"] + " | ID: " + pacientes_df["id_paciente"]

        seleccion = st.selectbox("Seleccione paciente", pacientes_df["selector"].tolist())

        paciente = pacientes_df[pacientes_df["selector"] == seleccion].iloc[0]

        st.subheader(paciente["nombre"])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Servicio", paciente["servicio"])
        with col2:
            st.metric("ID paciente", paciente["id_paciente"])
        with col3:
            st.metric("Fecha ingreso", paciente["fecha_ingreso"])

        st.write("### Diagnósticos")
        st.info(paciente["diagnosticos"])

        with st.expander("✏️ Editar datos del paciente"):

            nuevo_nombre = st.text_input("Nombre paciente", value=paciente["nombre"])
            nuevo_id_paciente = st.text_input("ID paciente", value=paciente["id_paciente"])

            servicios = ["UCI", "UTI", "UCO", "Medicina", "Cirugía"]
            servicio_actual = paciente["servicio"] if paciente["servicio"] in servicios else "UCI"

            nuevo_servicio = st.selectbox(
                "Servicio",
                servicios,
                index=servicios.index(servicio_actual)
            )

            nueva_fecha_ingreso = st.date_input(
                "Fecha ingreso",
                value=pd.to_datetime(paciente["fecha_ingreso"]).date()
            )

            nuevos_diagnosticos = st.text_area(
                "Diagnósticos",
                value=paciente["diagnosticos"],
                height=160
            )

            if st.button("Guardar cambios del paciente"):
                st.divider()

            with st.expander("⚠️ Eliminar paciente"):

                confirmar_paciente = st.checkbox(
                    "Confirmo que deseo eliminar este paciente y todas sus evoluciones",
                    key=f"confirmar_eliminar_paciente_{paciente['id']}"
                )

                if st.button(
                    "🗑️ Eliminar paciente",
                    key=f"eliminar_paciente_{paciente['id']}"
                ):

                    if confirmar_paciente:
                        eliminar_paciente(paciente["id"])
                        st.success("Paciente eliminado correctamente")
                        st.rerun()
                    else:
                        st.warning("Debe confirmar antes de eliminar")
                if nuevo_nombre == "" or nuevo_id_paciente == "":
                    st.error("Nombre e ID no pueden quedar vacíos")
                else:
                    actualizar_paciente(
                        paciente["id"],
                        nuevo_nombre,
                        nuevo_id_paciente,
                        nuevo_servicio,
                        nueva_fecha_ingreso,
                        nuevos_diagnosticos
                    )
                    st.success("Paciente actualizado correctamente")
                    st.rerun()

        st.divider()
        st.write("### Evoluciones registradas")

        evoluciones_df = obtener_evoluciones_paciente(paciente["id"])

        if len(evoluciones_df) > 0:
            for _, evo in evoluciones_df.iterrows():
                with st.expander(f"📅 {evo['fecha']}"):
                    st.subheader(f"📅 {evo['fecha']}")

                    st.markdown("**Evolución clínica**")
                    st.write(evo["evolucion_clinica"])

                    st.markdown("**Resultados laboratorio**")
                    st.write(evo["resultados_laboratorio"])

                    st.markdown("**Resultados microbiología**")
                    st.write(evo["resultados_microbiologia"])

                    st.markdown("**Antimicrobianos activos**")
                    st.write(evo["antimicrobianos_activos"])

                    st.markdown("**Intervención farmacéutica**")
                    st.write(evo["intervencion_farmaceutica"])
                    with st.expander("✏️ Editar evolución"):

                        nueva_fecha = st.date_input(
                            "Fecha",
                            value=pd.to_datetime(evo["fecha"]).date(),
                            key=f"fecha_{evo['id']}"
                        )

                        nueva_evolucion = st.text_area(
                            "Evolución clínica",
                            value=evo["evolucion_clinica"],
                            height=150,
                            key=f"evolucion_{evo['id']}"
                        )

                        nuevo_lab = st.text_area(
                            "Resultados laboratorio",
                            value=evo["resultados_laboratorio"],
                            height=120,
                            key=f"lab_{evo['id']}"
                        )

                        nueva_micro = st.text_area(
                            "Resultados microbiología",
                            value=evo["resultados_microbiologia"],
                            height=120,
                            key=f"micro_{evo['id']}"
                        )

                        nuevo_atb = st.text_area(
                            "Antimicrobianos activos",
                            value=evo["antimicrobianos_activos"],
                            height=100,
                            key=f"atb_{evo['id']}"
                        )

                        nueva_intervencion = st.text_area(
                            "Intervención farmacéutica",
                            value=evo["intervencion_farmaceutica"],
                            height=120,
                            key=f"interv_{evo['id']}"
                        )

                        if st.button(
                            "Guardar cambios evolución",
                            key=f"guardar_evo_{evo['id']}"
                        ):
                            actualizar_evolucion(
                                evo["id"],
                                nueva_fecha,
                                nueva_evolucion,
                                nuevo_lab,
                                nueva_micro,
                                nuevo_atb,
                                nueva_intervencion
                            )

                            st.success("Evolución actualizada correctamente")
                            st.rerun()
                    with st.expander("⚠️ Opciones de eliminación"):

                        confirmar = st.checkbox(
                            "Confirmo que deseo eliminar esta evolución",
                            key=f"confirmar_eliminar_{evo['id']}"
                        )

                        if st.button(
                            "🗑️ Eliminar evolución",
                            key=f"eliminar_evo_{evo['id']}"
                        ):

                            if confirmar:
                                eliminar_evolucion(evo["id"])
                                st.success("Evolución eliminada correctamente")
                                st.rerun()
                            else:
                                st.warning("Debe confirmar antes de eliminar")

        else:
            st.warning("Debe confirmar antes de eliminar")
                        
        else:
            st.info("Este paciente aún no tiene evoluciones registradas")


elif menu == "Evolución diaria":

    st.header("📝 Evolución clínica diaria")

    pacientes_df = obtener_pacientes()

    if len(pacientes_df) == 0:
        st.warning("Debe ingresar al menos un paciente antes de registrar evolución")

    else:
        pacientes_df["selector"] = pacientes_df["nombre"] + " | ID: " + pacientes_df["id_paciente"]

        seleccion = st.selectbox("Paciente", pacientes_df["selector"].tolist())

        paciente = pacientes_df[pacientes_df["selector"] == seleccion].iloc[0]

        fecha_evolucion = st.date_input("Fecha evolución", value=date.today())

        evolucion_clinica = st.text_area("Evolución clínica", height=150)
        resultados_laboratorio = st.text_area("Resultados laboratorio", height=120)
        resultados_microbiologia = st.text_area("Resultados microbiología", height=120)
        antimicrobianos_activos = st.text_area("Antimicrobianos activos", height=100)
        intervencion_farmaceutica = st.text_area("Intervención farmacéutica", height=120)

        if st.button("Guardar evolución"):
            guardar_evolucion(
                paciente["id"],
                fecha_evolucion,
                evolucion_clinica,
                resultados_laboratorio,
                resultados_microbiologia,
                antimicrobianos_activos,
                intervencion_farmaceutica
            )

            st.success("Evolución guardada correctamente")

        st.divider()
        st.subheader("Evoluciones del paciente")

        evoluciones_df = obtener_evoluciones_paciente(paciente["id"])

        if len(evoluciones_df) > 0:
            st.dataframe(evoluciones_df, use_container_width=True)
        else:
            st.info("No hay evoluciones registradas para este paciente")
