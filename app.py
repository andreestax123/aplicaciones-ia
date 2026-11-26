import os
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError

# 1. Configuración de la página
st.set_page_config(
    page_title="Mesa de Ayuda IA",
    page_icon="🤖",
    layout="wide",
)

# 2. Carga segura de la API Key (funciona tanto en VS Code local como en la nube)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.error("No se encontro GEMINI_API_KEY. Configurala en tu archivo .env o en Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)


def generar_con_respaldo(contenido):
    modelos = [
        "gemini-3.8-flash",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
    ]
    ultimo_error = None
    for modelo in modelos:
        for _ in range(2):
            try:
                return client.models.generate_content(
                    model=modelo,
                    contents=contenido,
                )
            except ServerError as e:
                ultimo_error = e
                time.sleep(1.5)
    raise ultimo_error


def cargar_tickets():
    if os.path.exists("tickets.csv"):
        return pd.read_csv("tickets.csv")
    return None


# --- INTERFAZ LATERAL ---
st.sidebar.title("Mesa de Ayuda IA")
st.sidebar.markdown("Proyecto - Ingenieria de IA (Ciclo II)")

rol = st.sidebar.selectbox(
    "Seleccione su Rol de Ingreso:",
    ["Usuario", "Trabajador", "Lider de Equipo", "SuperUsuario"],
)

PERMISOS_POR_ROL = {
    "Usuario": {
        "etiqueta": "Usuario Final",
        "puede_ver_bd": False,
        "puede_ver_metricas": False,
        "canal": "Agente de Soporte Asignado",
        "pestanas": ["Crear Ticket", "Agente de Soporte IA"],
    },
    "Trabajador": {
        "etiqueta": "Soporte Nivel 2",
        "puede_ver_bd": False,
        "puede_ver_metricas": False,
        "canal": "Ingeniero de Soporte Nivel 2",
        "pestanas": ["Cola de Resolucion", "Agente de Soporte IA"],
    },
    "Lider de Equipo": {
        "etiqueta": "Lider de Equipo",
        "puede_ver_bd": True,
        "puede_ver_metricas": True,
        "canal": "Analista Corporativo",
        "pestanas": ["Panel y Metricas", "Agente de Soporte IA", "Base de Datos"],
    },
    "SuperUsuario": {
        "etiqueta": "SuperUsuario (Acceso Total)",
        "puede_ver_bd": True,
        "puede_ver_metricas": True,
        "canal": "Asistencia VIP en Vivo (Atencion Inmediata)",
        "pestanas": ["Auditoria y Metricas", "Agente de Soporte IA", "Base de Datos"],
    },
}

config_rol = PERMISOS_POR_ROL[rol]

st.sidebar.divider()
st.sidebar.info(f"Perfil activo: **{config_rol['etiqueta']}**")
st.sidebar.caption(
    "Acceso a Base de Datos: "
    + ("Permitido" if config_rol["puede_ver_bd"] else "Restringido")
)

# --- CUERPO PRINCIPAL ---
st.title("Sistema Inteligente de Mesa de Ayuda")

pestanas = st.tabs(config_rol["pestanas"])

# PESTAÑA 1: OPERACION SEGUN EL ROL
with pestanas[0]:
    if rol == "Usuario":
        st.subheader("Crear Nuevo Ticket de Soporte")
        st.caption("Solo puedes registrar tu ticket y consultar el analisis inicial de tu caso.")
        with st.form("form_ticket"):
            nombre = st.text_input("Ingrese su nombre:")
            descripcion = st.text_area("Describa su problema o requerimiento:")
            enviado = st.form_submit_button("Registrar Ticket")

            if enviado and nombre.strip() and descripcion.strip():
                prompt_clasif = (
                    "Clasifica este ticket de soporte tecnico en un Area "
                    "(Redes, Hardware, Software, Accesos) y una Prioridad "
                    "(Alta, Media, Baja). Responde en una linea breve.\n"
                    f"Ticket: {descripcion}"
                )
                try:
                    respuesta = generar_con_respaldo(prompt_clasif)
                    st.success(f"Ticket registrado para **{nombre.strip()}**.")
                    st.info(f"Clasificacion preliminar: {respuesta.text}")
                except Exception as e:
                    st.warning(
                        "El servicio de IA esta temporalmente ocupado. "
                        f"Intenta de nuevo en unos segundos. ({e})"
                    )
            elif enviado:
                st.error("Completa tu nombre y la descripcion del problema.")

    elif rol == "Trabajador":
        st.subheader("Cola de Resolucion - Nivel 2")
        st.caption("Vista operativa restringida a tickets pendientes o en atencion.")
        df = cargar_tickets()
        if df is not None:
            if "estado" in df.columns:
                pendientes = df[df["estado"] != "Resuelto"]
                st.metric("Tickets por atender", len(pendientes))
                st.dataframe(pendientes, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.warning("No se encontro tickets.csv en el repositorio.")

    elif rol == "Lider de Equipo":
        st.subheader("Metricas y Supervision de Equipo")
        df = cargar_tickets()
        if df is not None:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Tickets", len(df))
            if "prioridad" in df.columns:
                col2.metric("Prioridad Alta", len(df[df["prioridad"] == "Alta"]))
            if "estado" in df.columns:
                col3.metric("Resueltos", len(df[df["estado"] == "Resuelto"]))
            if "area" in df.columns and not df.empty:
                st.bar_chart(df["area"].value_counts())
        else:
            st.warning("No se encontro tickets.csv en el repositorio.")

    elif rol == "SuperUsuario":
        st.subheader("Panel Administrativo VIP y Auditoria")
        st.success("Nivel de acceso maximo habilitado para supervision global.")
        df = cargar_tickets()
        if df is not None:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Registros", len(df))
            if "prioridad" in df.columns:
                col2.metric("Alta Prioridad", len(df[df["prioridad"] == "Alta"]))
            if "estado" in df.columns:
                col3.metric("Resueltos", len(df[df["estado"] == "Resuelto"]))
                col4.metric("Pendientes", len(df[df["estado"] != "Resuelto"]))
            if "area" in df.columns and not df.empty:
                st.bar_chart(df["area"].value_counts())
        else:
            st.warning("No se encontro tickets.csv en el repositorio.")

# PESTAÑA 2: AGENTE DE SOPORTE SEGUN EL ROL
with pestanas[1]:
    canal_actual = config_rol["canal"]
    st.subheader(f"Canal activo: {canal_actual}")

    clave_historial = f"mensajes_{rol}"
    if clave_historial not in st.session_state:
        st.session_state[clave_historial] = []

    for msg in st.session_state[clave_historial]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(f"Escribe tu consulta para {canal_actual}..."):
        st.session_state[clave_historial].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            restriccion_prompt = (
                "No reveles datos internos de toda la base de datos ni registros de otros usuarios."
                if rol == "Usuario"
                else "Responde con enfoque operativo o ejecutivo segun tu rol."
            )
            contexto_rol = (
                f"Eres el '{canal_actual}' de una Mesa de Ayuda empresarial. "
                f"Estas atendiendo a un '{rol}'. {restriccion_prompt} "
                "Responde de manera tecnica, amable y directa."
            )
            try:
                respuesta = generar_con_respaldo(
                    f"{contexto_rol}\n\nConsulta: {prompt}"
                )
                st.markdown(respuesta.text)
                st.session_state[clave_historial].append(
                    {"role": "assistant", "content": respuesta.text}
                )
            except Exception as e:
                st.warning(
                    "El agente esta experimentando alta demanda en este momento. "
                    f"Envia tu consulta nuevamente en unos segundos. ({e})"
                )

# PESTAÑA 3: BASE DE DATOS (SOLO LIDER DE EQUIPO Y SUPERUSUARIO)
if len(pestanas) > 2:
    with pestanas[2]:
        if not config_rol["puede_ver_bd"]:
            st.error("Acceso denegado: tu rol no tiene permiso para ver la base de datos.")
            st.stop()

        st.subheader("Base de Datos de Tickets (tickets.csv)")
        df_tickets = cargar_tickets()
        if df_tickets is not None:
            if rol == "Lider de Equipo" and "area" in df_tickets.columns:
                areas_disp = ["Todas"] + sorted(df_tickets["area"].dropna().unique().tolist())
                area_sel = st.selectbox("Filtrar por area:", areas_disp)
                if area_sel != "Todas":
                    df_tickets = df_tickets[df_tickets["area"] == area_sel]
            st.dataframe(df_tickets, use_container_width=True)
        else:
            st.warning("No se encontro el archivo tickets.csv en la raiz del proyecto.")
