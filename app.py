import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import openai

# Configuración de la página
st.set_page_config(
    page_title="Análisis Deportivo - Cypress",
    page_icon="⚽",
    layout="wide"
)

# Título principal
st.title("⚽ Análisis de Eventos Deportivos - Cypress")
st.markdown("---")

# Cargar datos
@st.cache_data
def cargar_datos():
    df = pd.read_excel("CypressPbP.xlsx", sheet_name="Input")
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip()
    return df

# Cargar el DataFrame
try:
    df = cargar_datos()
    st.success(f"✅ Datos cargados: {len(df)} registros")
except Exception as e:
    st.error(f"❌ Error al cargar datos: {e}")
    st.stop()

# Sidebar con información
st.sidebar.header("📊 Configuración de Análisis")
st.sidebar.markdown("---")

# CONTROLES DE FILTROS

# 1. VENUE - Botones de selección única
st.sidebar.subheader("🏟️ Sede")
venue_options = ["Todos", "Home", "Away"]
venue_selected = st.sidebar.radio(
    "Selecciona la sede:",
    options=venue_options,
    horizontal=True,
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

# 2. OPPONENT - Botones de selección (filtrados por Venue)
st.sidebar.subheader("🎯 Rival")

# Filtrar rivales según el Venue seleccionado
if venue_selected == "Todos":
    df_for_opponents = df
else:
    df_for_opponents = df[df["Venue"] == venue_selected]

opponents = sorted(df_for_opponents["Opponent"].unique().tolist())
opponent_options = ["Todos"] + opponents

# Usar selectbox para rivales (más práctico que muchos botones)
opponent_selected = st.sidebar.selectbox(
    "Selecciona el rival:",
    options=opponent_options,
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

# 3. VARIABLES - Checkboxes para selección múltiple
st.sidebar.subheader("📈 Variables a Analizar")
variables_disponibles = {
    "Scorer2": "⚽ Goles Anotados",
    "Goal Against": "🥅 Goles en Contra",
    "Yellow Card2": "🟨 Tarjetas Amarillas",
    "Red Card2": "🟥 Tarjetas Rojas",
    "Sub In2": "🔄 Sustituciones"
}

variables_seleccionadas = []
for var_key, var_label in variables_disponibles.items():
    if st.sidebar.checkbox(var_label, value=(var_key == "Scorer2"), key=var_key):
        variables_seleccionadas.append(var_key)

st.sidebar.markdown("---")

# Botón para limpiar filtros
if st.sidebar.button("🔄 Limpiar Filtros", use_container_width=True):
    st.rerun()

# APLICAR FILTROS
df_filtrado = df.copy()

# Filtro de Venue
if venue_selected != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Venue"] == venue_selected]

# Filtro de Opponent
if opponent_selected != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Opponent"] == opponent_selected]

# MOSTRAR INFORMACIÓN DE FILTROS APLICADOS
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📍 Sede", venue_selected)
with col2:
    st.metric("🎯 Rival", opponent_selected)
with col3:
    st.metric("📊 Registros", len(df_filtrado))

st.markdown("---")

# VALIDAR QUE HAYA VARIABLES SELECCIONADAS
if not variables_seleccionadas:
    st.warning("⚠️ Por favor selecciona al menos una variable para analizar")
    st.stop()

# VISUALIZACIÓN DE DATOS
st.subheader("📊 Análisis por Bin Time")

# Preparar datos para el gráfico
datos_grafico = []
for variable in variables_seleccionadas:
    # Agrupar por Bin Time y sumar eventos
    agrupado = df_filtrado.groupby("Bin Time")[variable].sum().reset_index()
    agrupado["Variable"] = variables_disponibles[variable]
    agrupado.rename(columns={variable: "Cantidad"}, inplace=True)
    datos_grafico.append(agrupado)

# Concatenar todos los datos
df_grafico = pd.concat(datos_grafico, ignore_index=True)

# Crear gráfico de barras agrupadas
fig = px.bar(
    df_grafico,
    x="Bin Time",
    y="Cantidad",
    color="Variable",
    barmode="group",
    title=f"Distribución de Eventos por Momento del Partido",
    labels={"Bin Time": "Momento del Partido", "Cantidad": "Cantidad de Eventos"},
    color_discrete_sequence=px.colors.qualitative.Set2,
    text="Cantidad"  # Mostrar valores en las barras
)

fig.update_layout(
    height=500,
    xaxis_title="Momento del Partido (minutos)",
    yaxis_title="Cantidad de Eventos",
    legend_title="Eventos",
    hovermode="x unified"
)

# Configurar el formato de los números en las barras
fig.update_traces(textposition='outside')

st.plotly_chart(fig, use_container_width=True)

# ANÁLISIS CON IA
st.markdown("---")
st.subheader("🤖 Análisis con Inteligencia Artificial")

# Verificar si hay API Key disponible
def get_openai_api_key():
    """Obtiene la API Key de OpenAI"""
    api_key = None
    
    # Intentar obtener de st.secrets (producción en Streamlit Cloud)
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
    except:
        pass
    
    # Si no está en secrets, intentar variable de entorno
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    
    return api_key

# Función para construir el prompt de análisis
def construir_prompt_analisis(df_filtrado, variables_seleccionadas, venue, opponent, tipo="rapido"):
    """Construye el prompt para el análisis de IA"""
    
    # Resumen de filtros aplicados
    filtros = f"Sede: {venue}, Rival: {opponent}"
    
    # Estadísticas por Bin Time
    stats_texto = ""
    for variable in variables_seleccionadas:
        agrupado = df_filtrado.groupby("Bin Time")[variable].sum().sort_values(ascending=False)
        stats_texto += f"\n{variables_disponibles[variable]}:\n{agrupado.to_string()}\n"
    
    if tipo == "rapido":
        prompt = f"""Eres un analista táctico de fútbol. Analiza estos datos de manera CONCISA (máximo 150 palabras):

Filtros aplicados: {filtros}
Total de registros: {len(df_filtrado)}

Estadísticas por momento del partido (Bin Time):
{stats_texto}

Proporciona un resumen ejecutivo destacando:
1. Los momentos más críticos del partido
2. Patrones principales observados
3. Una conclusión breve"""
    else:  # profundo
        prompt = f"""Eres un analista táctico de fútbol experto. Realiza un análisis PROFUNDO de estos datos:

Filtros aplicados: {filtros}
Total de registros: {len(df_filtrado)}

Estadísticas por momento del partido (Bin Time):
{stats_texto}

Proporciona un análisis detallado que incluya:
1. Análisis de patrones temporales (primeros minutos, mitad de tiempo, final)
2. Identificación de momentos críticos y vulnerabilidades
3. Comparación entre diferentes periodos del partido
4. 3-5 recomendaciones tácticas específicas y accionables
5. Conclusiones estratégicas

Sé específico con los datos y proporciona insights profundos."""
    
    return prompt

# Función para generar análisis
def generar_analisis(prompt, tipo="rapido"):
    """Genera el análisis usando OpenAI"""
    api_key = get_openai_api_key()
    
    if not api_key:
        st.error("⚠️ No se encontró la API Key de OpenAI. Configúrala en los secrets de Streamlit o como variable de entorno.")
        return None
    
    try:
        # Configurar la API key
        openai.api_key = api_key
        
        max_tokens = 300 if tipo == "rapido" else 800
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un analista táctico de fútbol experto en interpretar datos estadísticos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        st.error(f"❌ Error al generar análisis: {e}")
        return None

# Botones de análisis
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])

with col_btn1:
    btn_rapido = st.button("🚀 Análisis Rápido", use_container_width=True)

with col_btn2:
    btn_profundo = st.button("🔍 Análisis Profundo", use_container_width=True)

# Generar análisis según el botón presionado
if btn_rapido:
    with st.spinner("Generando análisis rápido..."):
        prompt = construir_prompt_analisis(df_filtrado, variables_seleccionadas, venue_selected, opponent_selected, tipo="rapido")
        analisis = generar_analisis(prompt, tipo="rapido")
        
        if analisis:
            st.info(analisis)

if btn_profundo:
    with st.spinner("Generando análisis profundo..."):
        prompt = construir_prompt_analisis(df_filtrado, variables_seleccionadas, venue_selected, opponent_selected, tipo="profundo")
        analisis = generar_analisis(prompt, tipo="profundo")
        
        if analisis:
            st.success(analisis)

# TABLA DE DATOS DETALLADOS
st.markdown("---")
st.subheader("📋 Datos Detallados")

# Mostrar solo columnas relevantes
columnas_mostrar = ["Opponent", "Venue", "Bin Time", "Game Time"] + variables_seleccionadas
df_mostrar = df_filtrado[columnas_mostrar]

st.dataframe(df_mostrar, use_container_width=True, height=400)

# DESCARGAR DATOS
st.download_button(
    label="📥 Descargar datos filtrados (CSV)",
    data=df_mostrar.to_csv(index=False).encode("utf-8"),
    file_name="datos_filtrados.csv",
    mime="text/csv"
)