import streamlit as st
import pandas as pd
from google import genai
from datetime import datetime, timedelta
import io

# --- 1. CONFIGURACIÓN DEL CLIENTE IA ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    ID_MODELO = 'gemini-2.5-flash'
except Exception as e:
    st.error("Error: No se encontró la API Key en Streamlit Secrets o el SDK no está instalado.")

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Customs Auditor Pro | Perú", layout="wide", page_icon="🏢")

# --- 3. ESTILO CSS PROFESIONAL ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .card-archivador {
        padding: 20px; border-radius: 10px; margin-bottom: 15px;
        border-left: 8px solid; background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .status-nuevo { border-left-color: #33D1FF; }
    .status-proceso { border-left-color: #FFC300; }
    .status-culminado { border-left-color: #2ECC71; }
    .alerta-plazo { color: #d9534f; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
    """, unsafe_allow_html=True)

# --- 4. INICIALIZACIÓN DE SESIÓN ---
if 'db_files' not in st.session_state:
    st.session_state.db_files = []

# --- 5. FUNCIONES DE APOYO ---
def registrar_file(datos):
    st.session_state.db_files.append(datos)

def calcular_plazos(fecha_llegada_nave):
    try:
        hoy = datetime.now().date()
        llegada = datetime.strptime(fecha_llegada_nave, "%Y-%m-%d").date()
        dias_transcurridos = (hoy - llegada).days
        dias_restantes_abandono = 30 - dias_transcurridos
        return dias_restantes_abandono
    except:
        return 30

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Aduana Auditor AI")
    st.markdown("---")
    menu = st.sidebar.radio("Módulos del Sistema", [
        "📂 Dashboard de Gestión", 
        "📝 Nuevo Despacho & IA", 
        "🧮 Liquidación & Valoración", 
        "⚖️ War Room (Consulta Legal)"
    ])
    st.info(f"Conectado a: {ID_MODELO}")

# --- 7. MÓDULO: DASHBOARD DE GESTIÓN ---
if menu == "📂 Dashboard de Gestión":
    st.header("Gestión de Files y Depósitos")
    
    # Filtros de búsqueda
    c_f1, c_f2, c_f3 = st.columns([2,1,1])
    with c_f1:
        search = st.text_input("Buscar por cliente o código...")
    with c_f2:
        dep_filter = st.selectbox("Filtrar Depósito", ["Todos", "Temporal", "Aduanero", "Simple"])
    with c_f3:
        sort_by = st.selectbox("Ordenar por", ["Fecha", "Plazo Crítico"])

    if not st.session_state.db_files:
        st.warning("No hay files registrados actualmente.")
    else:
        for f in st.session_state.db_files:
            # Lógica de búsqueda
            if search.lower() in f['cliente'].lower() or search.lower() in f['codigo'].lower():
                # Determinar color según avance
                estilo_clase = "status-nuevo"
                if 30 <= f['progreso'] < 100:
                    estilo_clase = "status-proceso"
                elif f['progreso'] == 100:
                    estilo_clase = "status-culminado"

                # Alerta de plazos
                dias_restantes = calcular_plazos(f['fecha_nave'])
                if dias_restantes < 5:
                    alerta_html = f'<span class="alerta-plazo">⚠️ ¡VENCE EN {dias_restantes} DÍAS!</span>'
                else:
                    alerta_html = f'{dias_restantes} días para abandono'

                st.markdown(f"""
                    <div class="card-archivador {estilo_clase}">
                        <div style="display: flex; justify-content: space-between;">
                            <span><b>ID: {f['codigo']}</b> | {f['cliente']}</span>
                            <span><b>{f['progreso']}% completado</b></span>
                        </div>
                        <p style="margin:10px 0;">📍 <b>Almacén:</b> {f['deposito']} | <b>Tipo:</b> {f['tipo_deposito']}</p>
                        <p style="margin:5px 0;">🚢 <b>Nave:</b> {f['fecha_nave']} | ⏳ <b>Plazo:</b> {alerta_html}</p>
                        <p style="margin:5px 0;">📦 <b>Estado Mercancía:</b> {'🔴 RESTRINGIDA' if f['es_restringida'] else '🟢 LIBRE'}</p>
                    </div>
                """, unsafe_allow_html=True)

                with st.expander(f"Ver observaciones y bitácora del file {f['codigo']}"):
                    st.write(f"**Observaciones:** {f['obs']}")
                    st.progress(f['progreso']/100)

# --- CONTINUACIÓN DEL CÓDIGO (INSERTAR DESPUÉS DE LA PARTE 1) ---

elif menu == "📝 Nuevo Despacho & IA":
    st.header("Registro de Nuevo File y Análisis de Riesgo")
    
    with st.form("registro_ia"):
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            cod_file = st.text_input("Código Interno del File", placeholder="EJ: ADU-2024-001")
            nom_cliente = st.text_input("Nombre del Importador/Exportador")
            fecha_nave = st.date_input("Fecha de llegada de la nave").strftime("%Y-%m-%d")
        
        with col_r2:
            dep_nom = st.text_input("Nombre del Depósito (Almacén)")
            tipo_almacen = st.selectbox("Tipo de Depósito", ["Depósito Temporal", "Depósito Aduanero", "Depósito Simple"])
            regimen_ad = st.selectbox("Régimen Aduanero", ["Importación para el Consumo (10)", "Admisión Temporal", "Exportación Definitiva (40)", "Depósito Aduanero (70)"])
        
        desc_comercial = st.text_area("Descripción detallada de la mercancía (Para análisis IA)")
        
        st.markdown("---")
        st.subheader("Configuración de Control")
        c_c1, c_c2 = st.columns(2)
        progreso_init = c_c1.slider("Porcentaje de avance inicial", 0, 100, 10)
        es_restringida = c_c2.checkbox("¿Marcada como mercancía restringida/prohibida?")
        observaciones_init = st.text_area("Observaciones iniciales de revisión")
        
        btn_generar = st.form_submit_button("🚀 Generar File y Analizar con IA")
        
        if btn_generar:
            if not desc_comercial.strip() or not cod_file.strip():
                st.error("⚠️ El código del file y la descripción son obligatorios.")
            else:
                with st.spinner("Gemini analizando partida, restricciones y sanciones posibles..."):
                    try:
                        # PROMPT TÉCNICO PARA GEMINI
                        prompt_analisis = f"""
                        Actúa como un Técnico Aduanero Revisor experto en Perú.
                        Analiza esta mercancía: '{desc_comercial}' bajo el régimen {regimen_ad}.
                        1. Sugiere la Partida Arancelaria con su sustento legal (Reglas de Interpretación).
                        2. Genera un Checklist documental específico para este caso.
                        3. Indica si es Carga Restringida o Prohibida y ante qué entidad (VUCE).
                        4. Cita posibles infracciones de la Tabla de Sanciones si hay errores en la declaración de este tipo de producto.
                        5. Menciona Tratados (TLC) aplicables si viene de China, EE.UU. o UE.
                        """
                        response = model.generate_content(prompt_analisis)
                        respuesta_ia = response.text
                        
                        nuevo_registro = {
                            "codigo": cod_file, "cliente": nom_cliente, "fecha_nave": fecha_nave,
                            "deposito": dep_nom, "tipo_deposito": tipo_almacen, "regimen": regimen_ad,
                            "progreso": progreso_init, "es_restringida": es_restringida,
                            "obs": observaciones_init, "analisis_ia": respuesta_ia,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                        
                        if "db_files" not in st.session_state:
                            st.session_state.db_files = []
                            
                        st.session_state.db_files.append(nuevo_registro)
                        st.success("✅ File registrado y analizado.")
                        st.markdown("### 🤖 Informe Técnico de la IA")
                        st.markdown(respuesta_ia)
                    except Exception as e:
                        st.error(f"Error al conectar con la IA: {e}")

elif menu == "🧮 Liquidación & Valoración":
    st.header("Calculadora de Tributos y Percepcion IGV")
    
    col_calc1, col_calc2 = st.columns(2)
    
    with col_calc1:
        st.subheader("Datos de Valoración")
        val_fob = st.number_input("Valor FOB (USD)", min_value=0.0, format="%.2f")
        val_flete = st.number_input("Flete (USD)", min_value=0.0, format="%.2f")
        val_seguro = st.number_input("Seguro (USD)", min_value=0.0, format="%.2f")
        
        st.markdown("---")
        st.subheader("Tasas de Impuestos")
        adv_tasa = st.selectbox("Ad-Valorem (%)", [0, 4, 6, 11])
        tasa_percepcion_data = [("Normal (3.5%)", 0.035), ("Primera Importación (10%)", 0.10), ("Bienes Usados (5%)", 0.05)]
        tasa_percepcion_label = st.radio("Tipo de Importación (Percepción)", [t[0] for t in tasa_percepcion_data], index=0)
        tasa_valor = next(t[1] for t in tasa_percepcion_data if t[0] == tasa_percepcion_label)
        
        gastos_log = st.number_input("Gastos Operativos/Logísticos (USD)", min_value=0.0)

    with col_calc2:
        st.subheader("Liquidación Proyectada")
        cif = val_fob + val_flete + val_seguro
        monto_adv = cif * (adv_tasa / 100)
        base_igv_ipm = cif + monto_adv
        monto_igv = base_igv_ipm * 0.16
        monto_ipm = base_igv_ipm * 0.02
        
        total_tributos_aduana = monto_adv + monto_igv + monto_ipm
        monto_percepcion = (cif + total_tributos_aduana) * tasa_valor
        
        total_gastos = total_tributos_aduana + monto_percepcion + gastos_log
        
        # Resultados visuales
        st.metric("TOTAL CIF", f"USD {cif:,.2f}")
        st.write(f"**Ad-Valorem ({adv_tasa}%):** USD {monto_adv:,.2f}")
        st.write(f"**IGV (16%) + IPM (2%):** USD {monto_igv + monto_ipm:,.2f}")
        st.markdown(f"### **Percepción ({tasa_percepcion_label}):** USD {monto_percepcion:,.2f}")
        st.error(f"## TOTAL A PAGAR: USD {total_gastos:,.2f}")
        
        if st.session_state.get("db_files"):
            file_para_vincular = st.selectbox("Seleccionar File para vincular", [f["codigo"] for f in st.session_state.db_files])
            if st.button("💾 Vincular cálculo al File"):
                for f in st.session_state.db_files:
                    if f["codigo"] == file_para_vincular:
                        f["obs"] += f"\n[Cálculo] Total Liquidado: USD {total_gastos:,.2f}"
                st.info(f"Cálculo guardado en la bitácora del file {file_para_vincular}.")
        else:
            st.warning("No hay files registrados para vincular el cálculo.")

elif menu == "⚖️ War Room (Consulta Legal)":
    st.header("Consultoría Técnica y Debate Crítico")
    st.markdown("""En este apartado puedes debatir con la IA sobre la **Ley General de Aduanas**, **Reglamento**, **Tabla de Sanciones** e **Incoterms**.""")

    tema_legal = st.selectbox("Marco Normativo Base:", ["Ley General de Aduanas (DL 1053)", "Reglamento de la LGA", "Tabla de Sanciones (D.S. 418-2019-EF)", "Procedimiento DESPA-PG.01", "Incoterms 2020", "Valoración (OMC)"])

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt_chat := st.chat_input("Ej: ¿Procede la rectificación de la DAM sin sanción si el canal es naranja?"):
        st.session_state.messages.append({"role": "user", "content": prompt_chat})
        with st.chat_message("user"):
            st.markdown(prompt_chat)

        with st.chat_message("assistant"):
            try:
                full_prompt = f"Analiza como un experto legal aduanero peruano el tema: {tema_legal}. Consulta: {prompt_chat}. Responde citando artículos."
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Operaciones de Datos")

if st.session_state.get("db_files"):
    df_export = pd.DataFrame(st.session_state.db_files)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Historial_Aduanero')
    
    st.sidebar.download_button(
        label="📥 Descargar Reporte Excel",
        data=output.getvalue(),
        file_name=f"Reporte_Aduanero_{datetime.now().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if st.sidebar.button("🗑️ Limpiar Sesión (Borrar todo)"):
        st.session_state.db_files = []
        st.session_state.messages = []
        st.rerun()

def añadir_observacion(indice, nueva_nota):
    timestamp = datetime.now().strftime("%d/%m %H:%M")
    st.session_state.db_files[indice]['obs'] += f"\n[{timestamp}] {nueva_nota}"
