import streamlit as st
import pandas as pd
import psycopg2
import bcrypt
from datetime import datetime, date
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Seguimiento Clínico", layout="wide")


def formatear_fecha(fecha):
    if fecha is None or fecha == "":
        return ""

    return pd.to_datetime(fecha).strftime("%d/%m/%Y")


def evaluar_alerta_atm(fila):
    estado = str(fila.get("estado", "")).replace("🔵", "").strip()
    fecha_termino = fila.get("fecha_termino", None)

    if fecha_termino is not None and str(fecha_termino).strip() not in ["", "NaT", "None"]:
        fecha_termino_dt = pd.to_datetime(fecha_termino).date()
        if fecha_termino_dt < date.today():
            return "⚫ Finalizado"

    if estado != "Vigente":
        return "⚫ Finalizado"

    dias = fila["dias_tratamiento"]

    if fila.get("excepcion_prolongada", False):
        return "🔵 Prolongado justificado"

    if dias >= 14:
        return "🔴 Revisar"

    if dias >= 7:
        return "🟡 Reevaluar"

    return "🟢 Dentro de rango"

def calcular_estado_visual_atm(fila):
    estado = str(fila.get("estado", "")).replace("🔵", "").strip()
    fecha_termino = fila.get("fecha_termino", None)

    if fecha_termino is not None and str(fecha_termino).strip() not in ["", "NaT", "None"]:
        fecha_termino_dt = pd.to_datetime(fecha_termino).date()
        if fecha_termino_dt < date.today():
            return "Término tratamiento"

    return estado


def conectar_db():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=int(st.secrets["postgres"]["port"]),
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        sslmode="require"
    )

def buscar_global(texto_busqueda, usuario_id):
    conn = conectar_db()
    texto = f"%{texto_busqueda}%"

    pacientes = pd.read_sql_query(
        """
        SELECT
            id,
            nombre,
            id_paciente,
            servicio,
            fecha_ingreso,
            diagnosticos
        FROM pacientes
        WHERE usuario_id = %s
        AND (
            nombre ILIKE %s
            OR id_paciente ILIKE %s
            OR diagnosticos ILIKE %s
        )
        """,
        conn,
        params=(int(usuario_id), texto, texto, texto)
    )

    pacientes["origen"] = "Datos del paciente / Diagnóstico"

    evoluciones = pd.read_sql_query(
        """
        SELECT DISTINCT
            p.id,
            p.nombre,
            p.id_paciente,
            p.servicio,
            p.fecha_ingreso,
            p.diagnosticos
        FROM pacientes p
        INNER JOIN evoluciones e ON e.paciente_id = p.id
        WHERE p.usuario_id = %s
        AND (
            e.evolucion_clinica ILIKE %s
            OR e.resultados_laboratorio ILIKE %s
            OR e.resultados_microbiologia ILIKE %s
            OR e.antimicrobianos_activos ILIKE %s
            OR e.intervencion_farmaceutica ILIKE %s
        )
        """,
        conn,
        params=(
            int(usuario_id),
            texto,
            texto,
            texto,
            texto,
            texto
        )
    )

    evoluciones["origen"] = "Evolución clínica"

    resultados = pd.concat(
        [pacientes, evoluciones],
        ignore_index=True
    ).drop_duplicates(subset=["id"])

    conn.close()
    return resultados

    terapias = pd.read_sql_query(
        """
        SELECT DISTINCT
            p.id,
            p.nombre,
            p.id_paciente,
            p.servicio,
            p.fecha_ingreso,
            p.diagnosticos
        FROM pacientes p
        INNER JOIN terapias_atm t ON t.paciente_id = p.id
        WHERE
            t.antimicrobiano ILIKE %s
            OR t.observacion ILIKE %s
            OR t.motivo_excepcion ILIKE %s
        """,
        conn,
        params=(texto, texto, texto)
    )
    terapias["origen"] = "Terapia ATM"

    conn.close()

    df = pd.concat([pacientes, evoluciones, terapias], ignore_index=True)

    if len(df) > 0:
        df = df.drop_duplicates(subset=["id", "origen"])

    return df

def crear_tablas():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
        id BIGSERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        rol TEXT DEFAULT 'usuario',
        activo BOOLEAN DEFAULT TRUE,
        creado_en TIMESTAMP DEFAULT NOW()
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id BIGSERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            id_paciente TEXT NOT NULL,
            servicio TEXT,
            fecha_ingreso DATE,
            diagnosticos TEXT,
            antecedentes TEXT,
            usuario_id BIGINT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evoluciones (
            id BIGSERIAL PRIMARY KEY,
            paciente_id BIGINT REFERENCES pacientes(id) ON DELETE CASCADE,
            fecha DATE,
            evolucion_clinica TEXT,
            resultados_laboratorio TEXT,
            resultados_microbiologia TEXT,
            antimicrobianos_activos TEXT,
            intervencion_farmaceutica TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS terapias_atm (
            id BIGSERIAL PRIMARY KEY,
            paciente_id BIGINT REFERENCES pacientes(id) ON DELETE CASCADE,
            antimicrobiano TEXT,
            fecha_inicio DATE,
            fecha_termino DATE,
            estado TEXT,
            observacion TEXT,
            excepcion_prolongada BOOLEAN DEFAULT FALSE,
            motivo_excepcion TEXT
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()
   

def guardar_paciente(nombre, id_paciente, servicio, fecha_ingreso, diagnosticos, antecedentes, usuario_id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pacientes (
            nombre, id_paciente, servicio, fecha_ingreso, diagnosticos, antecedentes, usuario_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (nombre, id_paciente, servicio, str(fecha_ingreso), diagnosticos, antecedentes, int(usuario_id)))
    conn.commit()
    conn.close()


def actualizar_paciente(paciente_id, nombre, id_paciente, servicio, fecha_ingreso, diagnosticos, antecedentes):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pacientes
        SET nombre = %s,
            id_paciente = %s,
            servicio = %s,
            fecha_ingreso = %s,
            diagnosticos = %s,
            antecedentes = %s
        WHERE id = %s
    """, (
        nombre,
        id_paciente,
        servicio,
        str(fecha_ingreso),
        diagnosticos,
        antecedentes,
        int(paciente_id)
    ))
    conn.commit()
    conn.close()

def eliminar_paciente(paciente_id):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM evoluciones
        WHERE paciente_id = %s
    """, (int(paciente_id),))

    cursor.execute("""
        DELETE FROM pacientes
        WHERE id = %s
    """, (int(paciente_id),))

    conn.commit()
    conn.close()


def obtener_pacientes(usuario_id):
    conn = conectar_db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM pacientes
        WHERE usuario_id = %s
        ORDER BY nombre
        """,
        conn,
        params=(int(usuario_id),)
    )

    conn.close()
    return df

def crear_usuario(nombre, email, password, rol="usuario"):
    conn = conectar_db()
    cursor = conn.cursor()

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    cursor.execute("""
        INSERT INTO usuarios (
            nombre,
            email,
            password_hash,
            rol
        )
        VALUES (%s, %s, %s, %s)
    """, (
        nombre,
        email.lower().strip(),
        password_hash,
        rol
    ))

    conn.commit()
    conn.close()


def obtener_usuario_por_email(email):
    conn = conectar_db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM usuarios
        WHERE email = %s
        AND activo = TRUE
        """,
        conn,
        params=(email.lower().strip(),)
    )

    conn.close()

    if len(df) == 0:
        return None

    return df.iloc[0]


def validar_login(email, password):
    usuario = obtener_usuario_por_email(email)

    if usuario is None:
        return None

    password_ok = bcrypt.checkpw(
        password.encode("utf-8"),
        usuario["password_hash"].encode("utf-8")
    )

    if not password_ok:
        return None

    return usuario    

def contar_usuarios():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total = cursor.fetchone()[0]

    conn.close()
    return total
    
def obtener_usuarios():
    conn = conectar_db()

    df = pd.read_sql_query(
        """
        SELECT
            id,
            nombre,
            email,
            rol,
            activo,
            creado_en
        FROM usuarios
        ORDER BY creado_en DESC
        """,
        conn
    )

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
            paciente_id,
            fecha,
            evolucion_clinica,
            resultados_laboratorio,
            resultados_microbiologia,
            antimicrobianos_activos,
            intervencion_farmaceutica
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            fecha = %s,
            evolucion_clinica = %s,
            resultados_laboratorio = %s,
            resultados_microbiologia = %s,
            antimicrobianos_activos = %s,
            intervencion_farmaceutica = %s
        WHERE id = %s
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
        WHERE id = %s
    """, (int(evolucion_id),))

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
        WHERE paciente_id = %s
        ORDER BY fecha DESC
        """,
        conn,
        params=(int(paciente_id),)
    )
    conn.close()
    return df
def calcular_dias_tratamiento(fecha_inicio, fecha_termino, estado):
    inicio = pd.to_datetime(fecha_inicio).date()

    if estado == "Vigente":
        fin = date.today()
    else:
        if fecha_termino:
            fin = pd.to_datetime(fecha_termino).date()
        else:
            fin = date.today()

    return (fin - inicio).days + 1


def guardar_terapia_atm(
    paciente_id,
    antimicrobiano,
    fecha_inicio,
    fecha_termino,
    estado,
    observacion,
    excepcion_prolongada,
    motivo_excepcion
):
    conn = conectar_db()
    cursor = conn.cursor()

    if not fecha_inicio:
        fecha_inicio = None

    if not fecha_termino:
        fecha_termino = None

    cursor.execute("""
        INSERT INTO terapias_atm (
            paciente_id,
            antimicrobiano,
            fecha_inicio,
            fecha_termino,
            estado,
            observacion,
            excepcion_prolongada,
            motivo_excepcion
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        int(paciente_id),
        antimicrobiano,
        fecha_inicio,
        fecha_termino,
        estado,
        observacion,
        bool(excepcion_prolongada),
        motivo_excepcion
    ))

    conn.commit()
    conn.close()

def actualizar_fechas_estado_terapia_atm(
    terapia_id,
    fecha_inicio,
    fecha_termino,
    estado
):
    conn = conectar_db()
    cursor = conn.cursor()

    if not fecha_inicio:
        fecha_inicio = None

    if not fecha_termino:
        fecha_termino = None

    cursor.execute("""
        UPDATE terapias_atm
        SET
            fecha_inicio = %s,
            fecha_termino = %s,
            estado = %s
        WHERE id = %s
    """, (
        fecha_inicio,
        fecha_termino,
        estado,
        int(terapia_id)
    ))

    conn.commit()
    conn.close()

def obtener_terapias_atm_paciente(paciente_id):
    conn = conectar_db()

    df = pd.read_sql_query(
        """
        SELECT
            id,
            paciente_id,
            antimicrobiano,
            fecha_inicio,
            fecha_termino,
            estado,
            observacion,
            excepcion_prolongada,
            motivo_excepcion
        FROM terapias_atm
        WHERE paciente_id = %s
        ORDER BY
            CASE estado
                WHEN 'Vigente' THEN 1
                WHEN 'Cambio' THEN 2
                WHEN 'Suspendida' THEN 3
                WHEN 'Término tratamiento' THEN 4
                ELSE 5
            END,
            fecha_inicio DESC
        """,
        conn,
        params=(int(paciente_id),)
    )

    conn.close()

    if len(df) > 0:
        df["dias_tratamiento"] = df.apply(
            lambda row: calcular_dias_tratamiento(
                row["fecha_inicio"],
                row["fecha_termino"],
                row["estado"]
            ),
            axis=1
        )

    return df


def actualizar_terapia_atm(
    terapia_id,
    antimicrobiano,
    fecha_inicio,
    fecha_termino,
    estado,
    observacion
):
    conn = conectar_db()
    cursor = conn.cursor()

    fecha_termino_texto = str(fecha_termino) if fecha_termino else ""

    cursor.execute("""
        UPDATE terapias_atm
        SET
            antimicrobiano = %s,
            fecha_inicio = %s,
            fecha_termino = %s,
            estado = %s,
            observacion = %s
        WHERE id = %s
    """, (
        antimicrobiano,
        str(fecha_inicio),
        fecha_termino_texto,
        estado,
        observacion,
        int(terapia_id)
    ))

    conn.commit()
    conn.close()


def eliminar_terapia_atm(terapia_id):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM terapias_atm
        WHERE id = %s
    """, (int(terapia_id),))

    conn.commit()
    conn.close()

crear_tablas()

if "usuario_logueado" not in st.session_state:
    st.session_state.usuario_logueado = None

if contar_usuarios() == 0:
    st.title("Crear usuario administrador")

    nombre_admin = st.text_input("Nombre")
    email_admin = st.text_input("Email")
    password_admin = st.text_input("Contraseña", type="password")
    password_admin_2 = st.text_input("Confirmar contraseña", type="password")

    if st.button("Crear administrador"):
        if nombre_admin == "" or email_admin == "" or password_admin == "":
            st.error("Debe completar todos los campos")
        elif password_admin != password_admin_2:
            st.error("Las contraseñas no coinciden")
        else:
            crear_usuario(
                nombre_admin,
                email_admin,
                password_admin,
                rol="admin"
            )
            st.success("Administrador creado correctamente. Inicie sesión.")
            st.rerun()

    st.stop()

if st.session_state.usuario_logueado is None:
    st.title("Ingreso al sistema")

    email_login = st.text_input("Email")
    password_login = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        usuario = validar_login(email_login, password_login)

        if usuario is None:
            st.error("Email o contraseña incorrectos")
        else:
            st.session_state.usuario_logueado = {
                "id": int(usuario["id"]),
                "nombre": usuario["nombre"],
                "email": usuario["email"],
                "rol": usuario["rol"]
            }
            st.rerun()

    st.stop()

st.header("🏥 Seguimiento Clínico")

col_user, col_logout = st.columns([4, 1])

with col_user:
    st.caption(f"Usuario: {st.session_state.usuario_logueado['nombre']}")

with col_logout:
    if st.button("Cerrar sesión"):
        st.session_state.usuario_logueado = None
        st.rerun()

opciones_menu = [
    "Pacientes", 
    "Evolución diaria",  
    "Terapia ATM", 
    "Ficha clínica",
    "Búsqueda global"
]

if st.session_state.usuario_logueado["rol"] == "admin":
    opciones_menu.append("Usuarios")

if "menu_actual" not in st.session_state:
    st.session_state.menu_actual = "Pacientes"

if "menu_radio" not in st.session_state:
    st.session_state.menu_radio = st.session_state.menu_actual

def cambiar_menu():
    st.session_state.menu_actual = st.session_state.menu_radio

# st.sidebar.radio(
#    "Menú",
#    opciones_menu,
#    key="menu_radio",
#    on_change=cambiar_menu
# )

menu = option_menu(
    menu_title=None,
    options=opciones_menu,
    icons=[
        "person-plus",
        "clipboard2-pulse",
        "capsule",
        "journal-medical",
        "search",
        "people"
    ]
    orientation="horizontal",
    default_index=opciones_menu.index(st.session_state.menu_actual)
)

if menu != st.session_state.menu_actual:
    st.session_state.menu_actual = menu
    st.rerun()

menu = st.session_state.menu_actual

# --------------------------
# PACIENTES
# --------------------------

if menu == "Pacientes":

    st.subheader("👤 Ingreso de paciente")
    
    if "paciente_form_version" not in st.session_state:
        st.session_state.paciente_form_version = 0

    version_paciente = "\u200b" * st.session_state.paciente_form_version

    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input(
            "Nombre paciente",
            key=f"nombre_paciente_nuevo_{st.session_state.paciente_form_version}"
        )

        id_paciente = st.text_input(
            "ID paciente",
            key=f"id_paciente_nuevo_{st.session_state.paciente_form_version}"
        )

        servicio = st.selectbox(
            "Servicio",
            ["UCI", "UTI", "UCO", "Medicina", "Cirugía"],
            key=f"servicio_nuevo_{st.session_state.paciente_form_version}"
        )

    with col2:
        fecha_ingreso = st.date_input(
            "Fecha ingreso",
            format="DD/MM/YYYY",
            key=f"fecha_ingreso_nuevo_{st.session_state.paciente_form_version}"
        )
        
        with st.expander(
            f"📝 Diagnósticos{version_paciente}",
            expanded=False
        ):
            diagnosticos = st.text_area(
                "Diagnósticos",
                height=220,
                key=f"diagnosticos_nuevo_{st.session_state.paciente_form_version}"
            )
            
        with st.expander(
            f"📋 Antecedentes{version_paciente}",
            expanded=False
        ):
            antecedentes = st.text_area(
                "Antecedentes",
                height=180,
                key=f"antecedentes_nuevo_{st.session_state.paciente_form_version}"
            )

        if st.button("Guardar paciente"):
            if nombre == "" or id_paciente == "":
                st.error("Debe ingresar nombre e ID del paciente")
            else:
                guardar_paciente(
                    nombre,
                    id_paciente,
                    servicio,
                    fecha_ingreso,
                    diagnosticos,
                    antecedentes,
                    st.session_state.usuario_logueado["id"]
                )
                st.success("Paciente guardado correctamente")
                st.session_state.paciente_form_version += 1
                st.rerun()

    st.divider()
    st.subheader("Pacientes registrados")

    pacientes_df = obtener_pacientes(st.session_state.usuario_logueado["id"])

    if len(pacientes_df) > 0:

        pacientes_mostrar = pacientes_df.copy()
        pacientes_mostrar["fecha_ingreso"] = pacientes_mostrar["fecha_ingreso"].apply(formatear_fecha)

        with st.expander("📋 Ver pacientes registrados", expanded=False):
            st.dataframe(
                pacientes_mostrar,
                use_container_width=True
            )

    else:
        st.info("No existen pacientes registrados")


# --------------------------
# FICHA CLÍNICA
# --------------------------

elif menu == "Ficha clínica":

    st.subheader("📋 Ficha clínica")

    pacientes_df = obtener_pacientes(st.session_state.usuario_logueado["id"])

    if len(pacientes_df) == 0:
        st.warning("No existen pacientes registrados")

    else:
        pacientes_df["selector"] = (
            pacientes_df["nombre"] + " | ID: " + pacientes_df["id_paciente"]
        )

        indice_paciente = 0

        if "paciente_ficha_id" in st.session_state:
            paciente_preseleccionado = pacientes_df[
                pacientes_df["id"] == st.session_state.paciente_ficha_id
            ]

            if len(paciente_preseleccionado) > 0:
                indice_paciente = pacientes_df.index.get_loc(paciente_preseleccionado.index[0])

        opciones_pacientes = ["-- Seleccione paciente --"] + pacientes_df["selector"].tolist()

        indice_paciente = 0

        if "paciente_ficha_id" in st.session_state:
            paciente_preseleccionado = pacientes_df[
                pacientes_df["id"] == st.session_state.paciente_ficha_id
            ]

            if len(paciente_preseleccionado) > 0:
                selector_preseleccionado = paciente_preseleccionado.iloc[0]["selector"]
                indice_paciente = opciones_pacientes.index(selector_preseleccionado)

        seleccion = st.selectbox(
            "Seleccione paciente",
            opciones_pacientes,
            index=indice_paciente
        )

        if seleccion == "-- Seleccione paciente --":
            st.info("Seleccione un paciente para visualizar la ficha clínica")
            st.stop()

        paciente = pacientes_df[pacientes_df["selector"] == seleccion].iloc[0]

        st.markdown(f"**👤 {paciente['nombre']}**")

        fecha_ingreso_unidad = pd.to_datetime(
            paciente["fecha_ingreso"]
        ).date()

        dias_unidad = (
            date.today() - fecha_ingreso_unidad
        ).days

        st.info(
            f"""
        🏥 **Servicio:** {paciente['servicio']}

        🆔 **ID paciente:** {paciente['id_paciente']}

        📅 **Ingreso a la unidad:** {formatear_fecha(paciente['fecha_ingreso'])}

        🏥 **Días en la unidad:** {dias_unidad}
        
        """
        )

        st.markdown(
            """
            <div style="margin-top:-15px;"></div>
            """,
            unsafe_allow_html=True
        )

        col_diag, col_ant = st.columns([3, 2])
         
        with col_diag:
            st.markdown("### 📋 Diagnósticos")
        
            diagnosticos_html = str(
            paciente["diagnosticos"]
            ).strip().replace("\n", "<br>")
        
            st.markdown(
                f"""
        <div style="
            border-left:5px solid #2E86C1;
            background-color:#f8f9fa;
            padding:5px 15px;
            border-radius:8px;
            font-size:15px;
            margin-bottom:15px;
            white-space:pre-wrap;
        ">{diagnosticos_html}
        </div>
        """,
            unsafe_allow_html=True
        )

        with col_ant:
            
            st.markdown("### 📄 Antecedentes")

            antecedentes_html = str(
                paciente.get("antecedentes", "")
            ).strip().replace("\n", "<br>")

            st.markdown(
                f"""
        <div style="
            border-left:5px solid #4CAF50;
            background-color:#f8f9fa;
            padding:5px 15px;
            border-radius:8px;
            font-size:15px;
            margin-bottom:15px;
            white-space:pre-wrap;
        ">
        {antecedentes_html if antecedentes_html else "<i>Sin antecedentes registrados</i>"}
        </div>
        """,
                unsafe_allow_html=True
            )
            
        if "editar_paciente_version" not in st.session_state:
            st.session_state.editar_paciente_version = 0

        version_editar_paciente = "\u200b" * st.session_state.editar_paciente_version

        with st.expander(
            f"✏️ Editar paciente{version_editar_paciente}",
            expanded=False
        ):

            nuevo_nombre = st.text_input(
                "Nombre paciente",
                value=paciente["nombre"],
                key=f"nombre_paciente_{paciente['id']}"
            )

            nuevo_id_paciente = st.text_input(
                "ID paciente",
                value=paciente["id_paciente"],
                key=f"id_paciente_{paciente['id']}"
            )

            servicios = ["UCI", "UTI", "UCO", "Medicina", "Cirugía"]
            servicio_actual = paciente["servicio"] if paciente["servicio"] in servicios else "UCI"

            nuevo_servicio = st.selectbox(
                "Servicio",
                servicios,
                index=servicios.index(servicio_actual),
                key=f"servicio_paciente_{paciente['id']}"
            )

            nueva_fecha_ingreso = st.date_input(
                "Fecha ingreso",
                value=pd.to_datetime(paciente["fecha_ingreso"]).date(),
                format="DD/MM/YYYY",
                key=f"fecha_ingreso_paciente_{paciente['id']}"
            )

            nuevos_diagnosticos = st.text_area(
                "Diagnósticos",
                value=paciente["diagnosticos"],
                height=160,
                key=f"diagnosticos_paciente_{paciente['id']}"
            )

            nuevos_antecedentes = st.text_area(
                "Antecedentes",
                value=paciente.get("antecedentes", ""),
                height=160,
                key=f"antecedentes_paciente_{paciente['id']}"
            )

            if st.button(
                "Guardar cambios del paciente",
                key=f"guardar_paciente_{paciente['id']}"
            ):

                if nuevo_nombre == "" or nuevo_id_paciente == "":
                    st.error("Nombre e ID no pueden quedar vacíos")

                else:
                    actualizar_paciente(
                        paciente["id"],
                        nuevo_nombre,
                        nuevo_id_paciente,
                        nuevo_servicio,
                        nueva_fecha_ingreso,
                        nuevos_diagnosticos,
                        nuevos_antecedentes
                    )
                    st.session_state.paciente_ficha_id = paciente["id"]
                    st.session_state.editar_paciente_version += 1

                    st.success("Paciente actualizado correctamente")
                    st.rerun()

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
        st.divider()
        st.write("### Terapia antimicrobiana")

        terapias_df = obtener_terapias_atm_paciente(paciente["id"])

        if len(terapias_df) > 0:

            terapias_mostrar = terapias_df.copy()
            
            terapias_mostrar["estado"] = terapias_mostrar.apply(
                calcular_estado_visual_atm,
                axis=1
            )
            def colorear_estado(estado):
                if estado == "Vigente":
                    return "🔵 Vigente"
                elif estado == "Cambio":
                    return "🟠 Cambio"
                elif estado == "Suspendida":
                    return "🔴 Suspendida"
                elif estado == "Término tratamiento":
                    return "⚫ Término tratamiento"
                return estado

            terapias_mostrar["estado"] = terapias_mostrar["estado"].apply(colorear_estado)
            
            terapias_mostrar["alerta"] = terapias_mostrar.apply(
                evaluar_alerta_atm,
                axis=1
            )

            terapias_mostrar["fecha_inicio"] = terapias_mostrar["fecha_inicio"].apply(formatear_fecha)
            terapias_mostrar["fecha_termino"] = terapias_mostrar["fecha_termino"].apply(formatear_fecha)

            terapias_mostrar = terapias_mostrar[
                [
                    "antimicrobiano",
                    "fecha_inicio",
                    "fecha_termino",
                    "estado",
                    "dias_tratamiento",
                    "alerta",
                    "observacion"
                ]
            ]

            terapias_mostrar = terapias_mostrar.rename(columns={
                "antimicrobiano": "Antimicrobiano",
                "fecha_inicio": "Inicio",
                "fecha_termino": "Término",
                "estado": "Estado",
                "dias_tratamiento": "Días",
                "alerta": "Alerta",
                "observacion": "Observación"
            })

            terapias_vigentes = terapias_mostrar[
                terapias_mostrar["Estado"].str.contains("Vigente", na=False)
            ]

            terapias_no_vigentes = terapias_mostrar[
                ~terapias_mostrar["Estado"].str.contains("Vigente", na=False)
            ]

            st.markdown("#### 🟢 Terapias vigentes")

            if len(terapias_vigentes) > 0:
                st.dataframe(
                    terapias_vigentes,
                    use_container_width=True
                )
            else:
                st.info("No existen terapias vigentes")

            if len(terapias_no_vigentes) > 0:
                with st.expander(
                    "📂 Ver terapias finalizadas / suspendidas / cambio",
                    expanded=False
                ):
                    st.dataframe(
                        terapias_no_vigentes,
                        use_container_width=True
                    )

        else:
            st.info("Este paciente no tiene terapias ATM registradas")
        st.divider()
        st.write("### Evoluciones registradas")

        evoluciones_df = obtener_evoluciones_paciente(paciente["id"])

        if len(evoluciones_df) == 0:
            st.info("Este paciente aún no tiene evoluciones registradas")

        else:
            for idx, evo in evoluciones_df.iterrows():

                with st.expander(
                    f"🗓️ {formatear_fecha(evo['fecha'])}",
                    expanded=False
                ):

                    st.subheader(f"📅 {formatear_fecha(evo['fecha'])}")

                    st.markdown("**Evolución clínica**")
                    st.markdown(
                        str(evo["evolucion_clinica"]),
                        unsafe_allow_html=False
                    )

                    st.divider()

                    st.markdown("**Resultados laboratorio**")
                    st.markdown(
                        str(evo["resultados_laboratorio"]).replace("\n", "<br>"),
                        unsafe_allow_html=True
                    )
                    

                    st.divider()

                    st.markdown("**Resultados microbiología**")
                    st.markdown(
                        str(evo["resultados_microbiologia"]).replace("\n", "<br>"),
                        unsafe_allow_html=True
                    )

                    st.divider()

                    st.markdown("**Terapia farmacológica**")
                    st.markdown(
                        str(evo["antimicrobianos_activos"]).replace("\n", "<br>"),
                        unsafe_allow_html=True
                    )

                    st.divider()

                    st.markdown("**Intervención farmacéutica**")
                    st.markdown(
                        str(evo["intervencion_farmaceutica"]).replace("\n", "<br>"),
                        unsafe_allow_html=True
                    )

                    if "editar_evolucion_version" not in st.session_state:
                        st.session_state.editar_evolucion_version = 0

                    version_editar_evolucion = "\u200b" * st.session_state.editar_evolucion_version

                    with st.expander(
                        f"✏️ Editar evolución{version_editar_evolucion}",
                        expanded=False
                    ):

                        nueva_fecha = st.date_input(
                            "Fecha",
                            value=pd.to_datetime(evo["fecha"]).date(),
                            key=f"fecha_evo_{evo['id']}"
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
                            "Terapia farmacológica",
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
                            st.session_state.editar_evolucion_version += 1
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


# --------------------------
# EVOLUCIÓN DIARIA
# --------------------------

elif menu == "Evolución diaria":

    st.markdown("### 📝 Evolución clínica diaria")
    # st.info(
    # "Puede usar formato Markdown: **negrita**, ### subtítulos, - listas."
    # )
    
    if "expandir_evolucion" not in st.session_state:
        st.session_state.expandir_evolucion = False

    if "evolucion_clinica_txt" not in st.session_state:
        st.session_state.evolucion_clinica_txt = ""

    if "resultados_laboratorio_txt" not in st.session_state:
        st.session_state.resultados_laboratorio_txt = ""

    if "resultados_microbiologia_txt" not in st.session_state:
        st.session_state.resultados_microbiologia_txt = ""

    if "antimicrobianos_activos_txt" not in st.session_state:
        st.session_state.antimicrobianos_activos_txt = ""

    if "intervencion_farmaceutica_txt" not in st.session_state:
        st.session_state.intervencion_farmaceutica_txt = ""

    if "evolucion_form_version" not in st.session_state:
        st.session_state.evolucion_form_version = 0

    pacientes_df = obtener_pacientes(st.session_state.usuario_logueado["id"])

    if len(pacientes_df) == 0:
        st.warning("Debe ingresar al menos un paciente antes de registrar evolución")

    else:
        pacientes_df["selector"] = (
            pacientes_df["nombre"] + " | ID: " + pacientes_df["id_paciente"]
        )

        opciones_pacientes = ["-- Seleccione paciente --"] + pacientes_df["selector"].tolist()

        seleccion = st.selectbox(
            "Paciente",
            opciones_pacientes,
            index=0
        )

        if seleccion == "-- Seleccione paciente --":
            st.info("Seleccione un paciente para registrar una evolución")
            st.stop()

        paciente = pacientes_df[pacientes_df["selector"] == seleccion].iloc[0]

        fecha_evolucion = st.date_input(
            "Fecha evolución",
            value=date.today(),
            format="DD/MM/YYYY"
        )
        version_invisible = "\u200b" * st.session_state.evolucion_form_version
        
        with st.expander(
            f"📝 Evolución clínica{version_invisible}",
            expanded=False
        ):
            evolucion_clinica = st.text_area(
                "Evolución clínica",
                height=250,
                key=f"evolucion_clinica_txt_{st.session_state.evolucion_form_version}"
            )

        with st.expander(
            f"🧪 Resultados laboratorio{version_invisible}",
            expanded=False
        ):
            resultados_laboratorio = st.text_area(
                "Resultados laboratorio",
                height=200,
                key=f"resultados_laboratorio_txt_{st.session_state.evolucion_form_version}"
            )

        with st.expander(
            f"🦠 Resultados microbiología{version_invisible}",
            expanded=False
        ):
            resultados_microbiologia = st.text_area(
                "Resultados microbiología",
                height=200,
                key=f"resultados_microbiologia_txt_{st.session_state.evolucion_form_version}"
            )

        with st.expander(
            f"💊 Terapia farmacológica{version_invisible}",
            expanded=False
        ):
            antimicrobianos_activos = st.text_area(
                "",
                height=180,
                key=f"antimicrobianos_activos_txt_{st.session_state.evolucion_form_version}"
            )

        with st.expander(
            f"💬 Intervención farmacéutica{version_invisible}",
            expanded=False
        ):
            intervencion_farmaceutica = st.text_area(
                "Intervención farmacéutica",
                height=200,
                key=f"intervencion_farmaceutica_txt_{st.session_state.evolucion_form_version}"
            )

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
            st.session_state.evolucion_form_version += 1
            st.rerun()

        st.divider()
        st.subheader("Evoluciones del paciente")

        evoluciones_df = obtener_evoluciones_paciente(paciente["id"])

        if len(evoluciones_df) > 0:
            
            evoluciones_mostrar = evoluciones_df.copy()

            evoluciones_mostrar["fecha"] = pd.to_datetime(
                evoluciones_mostrar["fecha"]
            ).dt.strftime("%d/%m/%Y")
            evoluciones_mostrar = evoluciones_mostrar.drop(
                columns=["id"],
                errors="ignore"
            )
            
            with st.expander("📋 Ver evoluciones registradas", expanded=False):
                st.dataframe(
                    evoluciones_mostrar,
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No hay evoluciones registradas para este paciente")
elif menu == "Búsqueda global":

    st.header("🔍 Búsqueda global")

    texto_busqueda = st.text_input(
        "Buscar por nombre, ID, diagnóstico, antimicrobiano, microbiología o evolución"
    )

    if texto_busqueda.strip():

        resultados_df = buscar_global(
            texto_busqueda,
            st.session_state.usuario_logueado["id"]
        )

        if len(resultados_df) > 0:

            resultados_mostrar = resultados_df.copy()
            resultados_mostrar["fecha_ingreso"] = resultados_mostrar["fecha_ingreso"].apply(formatear_fecha)

            resultados_mostrar = resultados_mostrar.rename(columns={
                
                "nombre": "Paciente",
                "id_paciente": "ID paciente",
                "servicio": "Servicio",
                "fecha_ingreso": "Ingreso",
                "diagnosticos": "Diagnósticos",
                "origen": "Origen coincidencia"
            })

            st.success(f"Se encontraron {len(resultados_mostrar)} paciente(s)")

            st.dataframe(
                resultados_mostrar[
                    ["Paciente", "ID paciente", "Servicio", "Ingreso", "Diagnósticos", "Origen coincidencia"]
                ],
                use_container_width=True
            )
            st.write("### Acceso rápido")

            pacientes_unicos = resultados_mostrar.drop_duplicates(
                subset=["ID paciente"]
            )

            opcion_paciente = st.selectbox(
                "Seleccione paciente para revisar",
                pacientes_unicos["Paciente"] + " | ID: " + pacientes_unicos["ID paciente"].astype(str)
            )

            paciente_seleccionado_busqueda = pacientes_unicos[
                (pacientes_unicos["Paciente"] + " | ID: " + pacientes_unicos["ID paciente"].astype(str))
                == opcion_paciente
            ].iloc[0]

            if st.button("📋 Abrir ficha clínica"):
                st.session_state.paciente_ficha_id = int(paciente_seleccionado_busqueda["id"])
                st.session_state.menu_actual = "Ficha clínica"
                st.rerun()

        else:
            st.warning("No se encontraron resultados")

    else:
        st.info("Ingrese un término de búsqueda")

        
elif menu == "Terapia ATM":

    st.markdown("### 💊 Terapia Antimicrobiana")
    
    if "atm_form_version" not in st.session_state:
        st.session_state.atm_form_version = 0

    pacientes_df = obtener_pacientes(st.session_state.usuario_logueado["id"])

    if len(pacientes_df) == 0:
        st.warning("No existen pacientes registrados")
        st.stop()

    opciones_pacientes = ["-- Seleccione paciente --"] + (
        pacientes_df["nombre"] + " | ID: " + pacientes_df["id_paciente"].astype(str)
    ).tolist()

    paciente_seleccionado = st.selectbox(
        "Seleccione paciente",
        opciones_pacientes,
        index=0
    )

    if paciente_seleccionado == "-- Seleccione paciente --":
        st.info("Seleccione un paciente para continuar")
        st.stop()

    paciente_idx = (
        pacientes_df["nombre"]
        + " | ID: "
        + pacientes_df["id_paciente"].astype(str)
    ) == paciente_seleccionado

    paciente = pacientes_df[paciente_idx].iloc[0]

    lista_antimicrobianos = [
        "-- Seleccione antimicrobiano --",
        "Aciclovir ev",
        "Aciclovir vo",
        "Amikacina",
        "Ampicilina",
        "Ampicilina/sulbactam",
        "Anfotericina B liposomal",
        "Anidulafungina",
        "Azitromicina ev",
        "Azitromicina vo",
        "Aztreonam",
        "Cefazolina",
        "Cefepime",
        "Cefotaxima ev",
        "Ceftazidima",
        "Ceftazidima/avibactam", 
        "Ceftriaxona",
        "Ciprofloxacino ev",  
        "Ciprofloxacino vo",
        "Clindamicina vo",
        "Clindamicina ev",
        "Cloxacilina ev",
        "Cloxacilina vo",
        "Colistin",
        "Cotrimoxazol ev",
        "Cotrimoxazol vo",
        "Daptomicina",
        "Ertapenem",
        "Fluconazol ev",
        "Fluconazol vo",
        "Fosfomicina ev",
        "Ganciclovir",
        "Imipenem",
        "Isavuconazol vo",
        "Isavuconazol ev",
        "Levofloxacino ev",
        "Levofloxacino vo",
        "Linezolid vo",
        "Linezolid ev",
        "Meropenem",
        "Metronidazol ev",
        "Metronidazol vo",
        "Penicilina G",
        "Piperacilina/tazobactam",
        "Tigeciclina",
        "Vancomicina",
        "Voriconazol ev",
        "Voriconazol vo",
        "Otro"
    ]

    antimicrobiano = st.selectbox(
        "Antimicrobiano",
        lista_antimicrobianos,
        index=0,
        key=f"antimicrobiano_atm_{st.session_state.atm_form_version}"
    )

    if antimicrobiano == "Otro":
        antimicrobiano = st.text_input(
            "Especifique antimicrobiano",
            key=f"otro_antimicrobiano_atm_{st.session_state.atm_form_version}"
        )


    fecha_inicio = st.date_input(
        "Fecha inicio",
        value=None,
        format="DD/MM/YYYY",
        key=f"fecha_inicio_atm_{st.session_state.atm_form_version}"
    )

    estado = st.selectbox(
        "Estado",
        [
            "-- Seleccione estado --",
            "Vigente",
            "Cambio",
            "Suspendida",
            "Término tratamiento"
        ],
        index=0,
        key=f"estado_atm_{st.session_state.atm_form_version}"
    )

    fecha_termino = None

    if estado not in ["Vigente", "-- Seleccione estado --"]:
        fecha_termino = st.date_input(
            "Fecha término",
            value=None,
            format="DD/MM/YYYY",
            key=f"fecha_termino_atm_{st.session_state.atm_form_version}"
        )

    observacion = st.text_area(
        "Observación",
        key=f"observacion_atm_{st.session_state.atm_form_version}"
    )

    excepcion_prolongada = st.checkbox(
        "Tratamiento prolongado justificado",
        key=f"excepcion_atm_{st.session_state.atm_form_version}"
    )

    motivo_excepcion = ""

    if excepcion_prolongada:
        motivo_excepcion = st.text_area(
            "Motivo de excepción",
            key=f"motivo_excepcion_atm_{st.session_state.atm_form_version}"
        )

    if st.button("Guardar terapia ATM"):
        if antimicrobiano == "-- Seleccione antimicrobiano --":
            st.warning("Seleccione un antimicrobiano")
            
        elif fecha_inicio is None:
            st.warning("Seleccione fecha de inicio")

        elif estado == "-- Seleccione estado --":
            st.warning("Seleccione un estado")

        else:

            guardar_terapia_atm(
                paciente["id"],
                antimicrobiano,
                fecha_inicio,
                fecha_termino,
                estado,
                observacion,
                excepcion_prolongada,
                motivo_excepcion
            )

            st.success("Terapia registrada correctamente")
            st.session_state.atm_form_version += 1
            st.rerun()
            st.divider()
    st.subheader("Terapias ATM registradas")

    terapias_df = obtener_terapias_atm_paciente(paciente["id"])
    terapias_editor_df = terapias_df.copy()

    if len(terapias_df) > 0:

        terapias_df["fecha_inicio"] = terapias_df["fecha_inicio"].apply(formatear_fecha)
        terapias_df["fecha_termino"] = terapias_df["fecha_termino"].apply(formatear_fecha)

        terapias_mostrar = terapias_df.copy()
        
        columnas_ocultar = ["id", "paciente_id", "excepcion_prolongada"]
        
        terapias_mostrar = terapias_mostrar.drop(
            columns=[col for col in columnas_ocultar if col in terapias_mostrar.columns]
        )

        with st.expander("💊 Ver terapias ATM registradas", expanded=False):
            st.dataframe(
                terapias_mostrar,
                use_container_width=True
            )

    st.divider()
    st.markdown("### ✏️ Editar fechas y estado de terapias ATM")

    for _, terapia in terapias_editor_df.iterrows():

        with st.expander(
            f"✏️ {terapia['antimicrobiano']} | Inicio: {formatear_fecha(terapia['fecha_inicio'])}",
            expanded=False
        ):

            nueva_fecha_inicio = st.date_input(
                "Fecha inicio",
                value=pd.to_datetime(terapia["fecha_inicio"], dayfirst=True).date() if terapia["fecha_inicio"] else None,
                format="DD/MM/YYYY",
                key=f"editar_fecha_inicio_atm_{terapia['id']}"
            )

            nueva_fecha_termino = st.date_input(
                "Fecha término",
                value=pd.to_datetime(terapia["fecha_termino"], dayfirst=True).date() if terapia["fecha_termino"] else None,
                format="DD/MM/YYYY",
                key=f"editar_fecha_termino_atm_{terapia['id']}"
            )

            estados_atm = [
                "Vigente",
                "Cambio",
                "Suspendida",
                "Término tratamiento"
            ]

            estado_actual = terapia["estado"] if terapia["estado"] in estados_atm else "Vigente"

            nuevo_estado = st.selectbox(
                "Estado",
                estados_atm,
                index=estados_atm.index(estado_actual),
                key=f"editar_estado_atm_{terapia['id']}"
            )

            if st.button(
                "Guardar cambios",
                key=f"guardar_edicion_atm_{terapia['id']}"
            ):
                actualizar_fechas_estado_terapia_atm(
                    terapia["id"],
                    nueva_fecha_inicio,
                    nueva_fecha_termino,
                    nuevo_estado
                )

                st.success("Terapia ATM actualizada correctamente")
                st.rerun()

else:
    st.info("Este paciente no tiene terapias ATM registradas")
