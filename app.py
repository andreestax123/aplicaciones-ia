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
    st.error("⚠️ No se encontró la GEMINI_API_KEY. Configúrala en tu archivo .env o en Streamlit Secrets.")
    st.stop()

# Inicializar cliente de Gemini
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


# Intentar importar tus servicios existentes (con respaldo por si faltan carpetas al subir)
try:
    from service.clasificador_service import AgenteClasificador
    from service.estimador_service import EstimadorService
    from service.ia_service import IAService
    from service.ticket_service import TicketService

    SERVICIOS_CARGADOS = True
except ImportError:
    SERVICIOS_CARGADOS = False

# --- INTERFAZ LATERAL (EQUIVALENTE A mostrar_menu() EN main.py) ---
st.sidebar.title("🤖 Mesa de Ayuda IA")
st.sidebar.markdown("Proyecto - Ingeniería de IA (Ciclo II)")

rol = st.sidebar.selectbox(
    "Seleccione su Rol de Ingreso:",
    ["Usuario", "Trabajador", "Lider de Equipo", "SuperUsuario"],
)

st.sidebar.divider()
st.sidebar.info(f"Sesión activa como: **{rol}**")

# --- CUERPO PRINCIPAL ---
st.title("Sistema Inteligente de Mesa de Ayuda")

tab1, tab2, tab3 = st.tabs([
    "🎫 Gestión de Tickets",
    "💬 Agente de Soporte IA",
    "📊 Base de Datos (tickets.csv)",
])

# PESTAÑA 1: GESTIÓN SEGÚN EL ROL
with tab1:
    if rol == "Usuario":
        st.subheader("Crear Nuevo Ticket de Soporte")
        with st.form("form_ticket"):
            nombre = st.text_input("Ingrese su nombre:")
            descripcion = st.text_area("Describa su problema o requerimiento:")
            enviado = st.form_submit_button("Registrar Ticket")

            if enviado and nombre and descripcion:
                prompt_clasif = (
                    "Clasifica este ticket de soporte técnico en un Área "
                    "(Redes, Hardware, Software, Accesos) y una Prioridad "
                    "(Alta, Media, Baja). Responde en una línea breve.\n"
                    f"Ticket: {descripcion}"
                )
                try:
                    respuesta = generar_con_respaldo(prompt_clasif)
                    st.success(f"✅ Ticket registrado para **{nombre}**.")
                    st.info(f"**Análisis Automático del Agente:** {respuesta.text}")
                except Exception as e:
                    st.warning(
                        "El servicio de IA está experimentando alta demanda en este momento. "
                        f"Intenta de nuevo en unos segundos. ({e})"
                    )

    elif rol == "Trabajador":
        st.subheader("Panel de Resolución - Nivel 2")
        st.write("Aquí puedes revisar los tickets pendientes asignados a tu área.")
        if os.path.exists("tickets.csv"):
            df = pd.read_csv("tickets.csv")
            pendientes = df[df["estado"] != "Resuelto"] if "estado" in df.columns else df
            st.dataframe(pendientes, use_container_width=True)
        else:
            st.warning("No se encontró el archivo tickets.csv en la raíz del proyecto.")

    elif rol == "Lider de Equipo":
        st.subheader("Métricas y Supervisión de Equipo")
        if os.path.exists("tickets.csv"):
            df = pd.read_csv("tickets.csv")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Tickets", len(df))
            if "prioridad" in df.columns:
                col2.metric("Prioridad Alta", len(df[df["prioridad"] == "Alta"]))
            if "estado" in df.columns:
                col3.metric("Resueltos", len(df[df["estado"] == "Resuelto"]))
            if "area" in df.columns and not df.empty:
                st.bar_chart(df["area"].value_counts())
        else:
            st.warning("No se encontró el archivo tickets.csv en la raíz del proyecto.")

    elif rol == "SuperUsuario":
        st.subheader("Panel Administrativo VIP & Auditoría")
        st.warning("Acceso total habilitado (Estimador, Evaluación de Modelos y Clasificador).")
        if os.path.exists("tickets.csv"):
            df = pd.read_csv("tickets.csv")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No se encontró el archivo tickets.csv en la raíz del proyecto.")

# PESTAÑA 2: AGENTE DE SOPORTE INTERACTIVO (EQUIVALENTE A iniciar_soporte)
with tab2:
    canales = {
        "Usuario": "Agente de Soporte Asignado",
        "Trabajador": "Ingeniero de Soporte Nivel 2",
        "Lider de Equipo": "Analista Corporativo",
        "SuperUsuario": "Asistencia VIP en Vivo (Atención Inmediata)",
    }
    st.subheader(f"Canal activo: {canales[rol]}")

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    for msg in st.session_state.mensajes:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe tu consulta para el agente de soporte..."):
        st.session_state.mensajes.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            contexto_rol = (
                f"Eres el '{canales[rol]}' de una Mesa de Ayuda empresarial. "
                f"Estás atendiendo a un '{rol}'. Responde de manera técnica, amable y directa."
            )
            try:
                respuesta = generar_con_respaldo(
                    f"{contexto_rol}\n\nConsulta del usuario: {prompt}"
                )
                st.markdown(respuesta.text)
                st.session_state.mensajes.append({"role": "assistant", "content": respuesta.text})
            except Exception as e:
                st.warning(
                    "El agente está experimentando alta demanda en este momento. "
                    f"Envía tu consulta nuevamente en unos segundos. ({e})"
                )

# PESTAÑA 3: DATASET
with tab3:
    st.subheader("Registros actuales en tickets.csv")
    if os.path.exists("tickets.csv"):
        df_tickets = pd.read_csv("tickets.csv")
        st.dataframe(df_tickets, use_container_width=True)
    else:
        st.warning("No se encontró el archivo tickets.csv en la raíz del proyecto.")
