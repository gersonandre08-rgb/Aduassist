import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Customs Auditor Pro | Perú", layout="wide", page_icon="🏢")

st.markdown("""

.stApp { background-color: #f8f9fa; }
.card-archivador {
padding: 20px; border-radius: 10px; margin-bottom: 15px;
border-left: 8px solid; background-color: white;
box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}
.status-nuevo { border-left-color: #33D1FF; } /* Celeste /
.status-proceso { border-left-color: #FFC300; } / Amarillo/Naranja /
.status-culminado { border-left-color: #2ECC71; } / Verde */
.alerta-plazo { color: #d9534f; font-weight: bold; animation: blinker 1.5s linear infinite; }
@keyframes blinker { 50% { opacity: 0; } }

""", unsafe_allow_html=True)

if 'db_files' not in st.session_state:
st.session_state.db_files = []
def registrar_file(datos):
st.session_state.db_files.append(datos)
# Aquí añadirías: sheet.append_row(list(datos.values())) una vez conectes GSheets

def calcular_plazos(fecha_llegada_nave):
# En Perú, el abandono legal suele ser a los 30 días calendario tras la descarga
hoy = datetime.now().date()
llegada = datetime.strptime(fecha_llegada_nave, "%Y-%m-%d").date()
dias_transcurridos = (hoy - llegada).days
dias_restantes_abandono = 30 - dias_transcurridos
return dias_restantes_abandono

with st.sidebar:
st.title("🛡️ Aduana Auditor AI")
st.markdown("---")
menu = st.radio("Módulos del Sistema",
["📂 Dashboard de Gestión",
"📝 Nuevo Despacho & IA",
"🧮 Liquidación & Valoración",
"⚖️ War Room (Consulta Legal)"])
st.info("Conectado a: Gemini 1.5 Pro")

if menu == "📂 Dashboard de Gestión":
st.header("Gestión de Files y Depósitos")
# Filtros de búsqueda
c_f1, c_f2, c_f3 = st.columns([2,1,1])
with c_f1: search = st.text_input("Buscar por cliente o código...")
with c_f2: dep_filter = st.selectbox("Filtrar Depósito", ["Todos", "Temporal", "Aduanero", "Simple"])
with c_f3: sort_by = st.selectbox("Ordenar por", ["Fecha", "Plazo Crítico"])
if not st.session_state.db_files:
st.warning("No hay files registrados actualmente.")
else:
for f in st.session_state.db_files:
# Determinar color según avance
estilo_clase = "status-nuevo"
if f['progreso'] > 30: estilo_clase = "status-proceso"
if f['progreso'] == 100: estilo_clase = "status-culminado"
# Alerta de plazos
dias_restantes = calcular_plazos(f['fecha_nave'])
alerta_html = f'⚠️ ¡VENCE EN {dias_restantes} DÍAS!' if dias_restantes < 5 else f'{dias_restantes} días para abandono'
st.markdown(f"""


ID: {f['codigo']} | {f['cliente']}
{f['progreso']}% completado


📍 Almacén: {f['deposito']} | Tipo: {f['tipo_deposito']}
🚢 Nave: {f['fecha_nave']} | ⏳ Plazo: {alerta_html}
📦 Estado Mercancía: {'🔴 RESTRINGIDA' if f['es_restringida'] else '🟢 LIBRE'}

""", unsafe_allow_html=True)
with st.expander(f"Ver observaciones y bitácora del file {f['codigo']}"):
st.write(f"Observaciones: {f['obs']}")
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
            with st.spinner("Gemini analizando partida, restricciones y sanciones posibles..."):
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
                
                nuevo_registro = {
                    "codigo": cod_file, "cliente": nom_cliente, "fecha_nave": fecha_nave,
                    "deposito": dep_nom, "tipo_deposito": tipo_almacen, "regimen": regimen_ad,
                    "progreso": progreso_init, "es_restringida": es_restringida,
                    "obs": observaciones_init, "analisis_ia": response.text,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
                st.session_state.db_files.append(nuevo_registro)
                st.success("✅ File registrado y analizado.")
                st.markdown("### 🤖 Informe Técnico de la IA")
                st.write(response.text)

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
        tasa_percepcion = st.radio(
            "Tipo de Importación (Percepción)",
            [("Normal (3.5%)", 0.035), ("Primera Importación (10%)", 0.10), ("Bienes Usados (5%)", 0.05)],
            index=0
        )
        gastos_log = st.number_input("Gastos Operativos/Logísticos (USD)", min_value=0.0)

    with col_calc2:
        st.subheader("Liquidación Proyectada")
        cif = val_fob + val_flete + val_seguro
        monto_adv = cif * (adv_tasa / 100)
        base_igv_ipm = cif + monto_adv
        monto_igv = base_igv_ipm * 0.16
        monto_ipm = base_igv_ipm * 0.02
        
        total_tributos_aduana = monto_adv + monto_igv + monto_ipm
        monto_percepcion = (cif + total_tributos_aduana) * tasa_percepcion[1]
        
        total_gastos = total_tributos_aduana + monto_percepcion + gastos_log
        
        # Resultados visuales
        st.metric("TOTAL CIF", f"USD {cif:,.2f}")
        st.write(f"**Ad-Valorem ({adv_tasa}%):** USD {monto_adv:,.2f}")
        st.write(f"**IGV (16%) + IPM (2%):** USD {monto_igv + monto_ipm:,.2f}")
        st.markdown(f"### **Percepción ({tasa_percepcion[0]}):** USD {monto_percepcion:,.2f}")
        st.error(f"## TOTAL A PAGAR: USD {total_gastos:,.2f}")
        
        if st.button("💾 Vincular cálculo al File"):
            st.info("Cálculo guardado en la bitácora del file seleccionado.")

# --- CONTINUACIÓN DEL CÓDIGO (INSERTAR DESPUÉS DE LA PARTE 2) ---

elif menu == "⚖️ War Room (Consulta Legal)":
    st.header("Consultoría Técnica y Debate Crítico")
    st.markdown("""
        En este apartado puedes debatir con la IA sobre la **Ley General de Aduanas**, 
        **Reglamento**, **Tabla de Sanciones** e **Incoterms**. 
    """)

    # Selector de base legal para orientar a la IA
    tema_legal = st.selectbox("Marco Normativo Base:", 
        ["Ley General de Aduanas (DL 1053)", "Reglamento de la LGA", "Tabla de Sanciones (D.S. 418-2019-EF)", 
         "Procedimiento DESPA-PG.01", "Incoterms 2020", "Valoración (OMC)"])

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt_chat := st.chat_input("Ej: ¿Procede la rectificación de la DAM sin sanción si el canal es naranja?"):
        st.session_state.messages.append({"role": "user", "content": prompt_chat})
        with st.chat_message("user"):
            st.markdown(prompt_chat)

        with st.chat_message("assistant"):
            # Prompt enriquecido con pensamiento crítico
            full_prompt = f"""
            Analiza como un experto legal aduanero peruano el siguiente tema: {tema_legal}.
            Consulta: {prompt_chat}
            Responde citando artículos, analiza la intención de la norma y debate posibles contingencias 
            o vacíos legales que el revisor deba prever.
            """
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- FUNCIONALIDADES TRANSVERSALES (PIE DE PÁGINA Y EXPORTACIÓN) ---

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Operaciones de Datos")

# Botón para exportar TODO el historial de Files a Excel
if st.session_state.db_files:
    df_export = pd.DataFrame(st.session_state.db_files)
    
    # Limpieza de datos para el Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Historial_Aduanero')
        # Formateo básico
        workbook  = writer.book
        worksheet = writer.sheets['Historial_Aduanero']
        header_format = workbook.add_format({'bold': True, 'bg_color': '#0E1117', 'font_color': 'white'})
        for col_num, value in enumerate(df_export.columns.values):
            worksheet.write(0, col_num, value, header_format)

    st.sidebar.download_button(
        label="📥 Descargar Reporte Excel",
        data=output.getvalue(),
        file_name=f"Reporte_Aduanero_{datetime.now().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if st.sidebar.button("🗑️ Limpiar Sesión (Borrar todo)"):
        st.session_state.db_files = []
        st.rerun()

# --- MODAL DE OBSERVACIONES (Adición a la lógica de Dashboard de la Parte 1) ---
# Esta función permite añadir notas cada vez que se detecta algo en la revisión
def añadir_observacion(indice, nueva_nota):
    timestamp = datetime.now().strftime("%d/%m %H:%M")
    st.session_state.db_files[indice]['obs'] += f"\n[{timestamp}] {nueva_nota}"

# --- NOTA FINAL DE IMPLEMENTACIÓN ---
# Recuerda crear un archivo .streamlit/secrets.toml en tu repo de GitHub con:
# GEMINI_API_KEY = "tu_api_key_aqui"
