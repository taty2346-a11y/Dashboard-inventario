import pandas as pd
import plotly.express as px
import streamlit as st
import re

# Configuración básica
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")

# --- ESTILOS: FONDO BLANCO, CABECERAS AZUL MARINO Y BOTÓN/DETALLES TURQUESA ---
st.markdown("""
<style>
    /* Fondo general limpio */
    .stApp { background-color: #ffffff !important; }
    
    /* Textos y títulos */
    h1, h2, h3 { color: #002e5d !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Tarjetas de métricas (borde turquesa suave) */
    div[data-testid="stMetric"] {
        background-color: #f9fbfb !important;
        border: 1px solid #00818a !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }
    
    /* Botón de ejecutar (El color que te gusta) */
    div.stButton > button:first-child {
        background-color: #00818a !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
    }
    
    /* Estilo de tablas y otros */
    .stDataFrame { border: 1px solid #e0e0e0 !important; }
</style>
""", unsafe_allow_html=True)

# Logo (Usando la URL remota para evitar errores de carga)
URL_LOGO_CORPORATIVO = "https://cdn.brandfetch.io/idBNTSMPCj/w/400/h/400/theme/dark/icon.jpeg?c=1bxid64Mup7aczewSAYMX&t=1752693425078"
st.sidebar.image(URL_LOGO_CORPORATIVO, width=160)

st.title("📊 Cuadro de Mando: Comparativa de Unidades")
st.markdown("Sube tu reporte de inventario para comenzar el análisis.")

# Lógica principal
archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    st.sidebar.header("⚙️ Configuración")
    sku_col = st.sidebar.text_input("Columna de Código SKU", "Sku")
    
    opciones = df.columns.tolist()
    col_expected = st.sidebar.selectbox("Columna Unidades Esperadas", opciones, index=0)
    col_read_1 = st.sidebar.selectbox("Lecturas Paso 1", opciones, index=0)
    col_read_2 = st.sidebar.selectbox("Lecturas Paso 2", opciones, index=1 if len(opciones)>1 else 0)
    
    if st.sidebar.button("📊 Ejecutar Comparativa"):
        # Cálculos
        df['Total_Real_Leido'] = df[col_read_2].apply(lambda x: x if x > 0 else df[col_read_1])
        df['Diferencia'] = df['Total_Real_Leido'] - df[col_expected]
        
        st.subheader("📌 Resumen Ejecutivo")
        m1, m2, m3 = st.columns(3)
        m1.metric("Unidades Esperadas", f"{int(df[col_expected].sum()):,}")
        m2.metric("Unidades Reales", f"{int(df['Total_Real_Leido'].sum()):,}")
        m3.metric("Diferencia Neto", f"{int(df['Diferencia'].sum()):,}")
        
        st.subheader("🔥 Gráfico de Descuadres")
        fig = px.bar(df, x=sku_col, y='Diferencia', color_discrete_sequence=['#00818a'])
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 Detalle")
        st.dataframe(df, use_container_width=True)
