import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
import pandas as pd
from datetime import datetime

# Configuración inicial
st.set_page_config(page_title="Aduassist Control", layout="wide")
st.title("⚓ Aduassist Control - Auxiliar de Despacho")

# 1. Conexión a Google Sheets (Base de Datos)
# Configura tus credenciales en .streamlit/secrets.toml para usar GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Configuración de IA (Gemini 2.5 Flash)
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- MENU LATERAL ---
menu = st.sidebar.selectbox("Módulo", ["Previo y Aforo Físico", "Consultas IA", "Historial de Despachos"])

# --- MODULO 1: PREVIOS Y AFOROS (La función más compleja) ---
if menu == "Previo y Aforo Físico":
    st.header("📋 Registro de Previo / Reconocimiento Físico")
    
    with st.form("form_previo"):
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Cliente")
            nro_dam = st.text_input("Nro de DAM")
            doc_transporte = st.text_input("Doc. de Transporte (BL/AWB)")
        with col2:
            nro_orden = st.text_input("Nro de Orden")
            fecha = st.date_input("Fecha de Operación", datetime.now())
            canal = st.selectbox("Canal de Control", ["Verde", "Naranja", "Rojo"])

        st.subheader("Detalle de Mercancía")
        # Simulación de ingreso de ítems (puedes expandir esto a una tabla dinámica)
        nombre_comercial = st.text_input("Nombre Comercial")
        marca = st.text_input("Marca / Modelo")
        estado = st.selectbox("Estado", ["Nuevo", "Usado"])
        origen = st.text_input("País de Origen")
        cantidad = st.number_input("Cantidad", min_value=0)
        
        submitted = st.form_submit_button("Guardar y Generar Reporte")
        
        if submitted:
            # Lógica para guardar en GSheets y permitir descarga
            st.success("Información registrada con éxito.")
            # Aquí generarías un CSV/PDF para descarga

# --- MODULO 2: CONSULTAS IA (Liquidación, Dumping, TLC) ---
elif menu == "Consultas IA":
    st.header("🤖 Asistente Técnico Aduanero")
    st.info("Consulta sobre Liquidación, Dumping, TLC, Ad Valorem, etc.")
    
    pregunta = st.text_area("Escribe tu consulta técnica:")
    if st.button("Consultar a Gemini 2.5 Flash"):
        if pregunta:
            # Llamada a la API de Gemini 2.5 Flash
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Actúa como un experto en aduanas peruanas. Responde de forma técnica y precisa: {pregunta}"
            )
            st.markdown(f"**Respuesta:** \n\n {response.text}")
        else:
            st.warning("Por favor ingresa una pregunta.")

# --- MODULO 3: HISTORIAL (Filtros) ---
elif menu == "Historial de Despachos":
    st.header("🗄️ Archivo de Despachos")
    # Lectura de datos desde Google Sheets
    # df = conn.read()
    # Filtros por cliente, fecha, almacén, etc.
    st.write("Filtros de búsqueda próximamente...")
