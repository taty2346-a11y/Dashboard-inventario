import pandas as pd
import plotly.express as px
import streamlit as st
import re

# Configuración básica
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")

# --- ESTILOS CSS UNIFICADOS ---
st.markdown("""
<style>
    /* Fondo general limpio */
    .stApp { background-color: #ffffff !important; }
    
    /* Títulos y textos */
    h1, h2, h3 { color: #002e5d !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Tarjetas de métricas */
    div[data-testid="stMetric"] {
        background-color: #f9fbfb !important;
        border: 1px solid #00818a !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }
    
    /* Botón de ejecutar */
    div.stButton > button:first-child {
        background-color: #00818a !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.5rem 2rem !important;
    }
    
    div.stButton > button:first-child:hover {
        background-color: #00a4b0 !important;
    }
    
    /* Tablas */
    .stDataFrame { border: 1px solid #e0e0e0 !important; }

    /* Impresión a PDF */
    @media print {
        html, body, .stApp { background-color: white !important; }
        section[data-testid="stSidebar"], header, footer { display: none !important; }
        .block-container { max-width: 100% !important; margin: 0 !important; }
    }
</style>
""", unsafe_allow_html=True)

# Logo
URL_LOGO = "https://cdn.brandfetch.io/idBNTSMPCj/w/400/h/400/theme/dark/icon.jpeg?c=1bxid64Mup7aczewSAYMX&t=1752693425078"
st.sidebar.image(URL_LOGO, width=160)

st.title("📊 Cuadro de Mando: Comparativa de Unidades")
st.markdown("Sube tu reporte de inventario para aplicar la auditoría.")

# Subida del archivo
archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    st.sidebar.header("⚙️ Configuración")
    sku_col = st.sidebar.text_input("Columna SKU", "Sku")
    opciones = df.columns.tolist()
    
    col_expected = st.sidebar.selectbox("Columna Esperadas", opciones, index=0)
    col_read_1 = st.sidebar.selectbox("Lecturas Paso 1", opciones, index=0)
    col_read_2 = st.sidebar.selectbox("Lecturas Paso 2", opciones, index=1 if len(opciones)>1 else 0)
    pos_col = st.sidebar.text_input("Columna Ubicación", "Posición")
    
    if st.sidebar.button("📊 Ejecutar Comparativa"):
        # Cálculos
        df['Total_Real_Leido'] = df.apply(lambda row: row[col_read_2] if pd.to_numeric(row[col_read_2], errors='coerce') > 0 else row[col_read_1], axis=1)
        df['Diferencia_Uds'] = pd.to_numeric(df['Total_Real_Leido'], errors='coerce') - pd.to_numeric(df[col_expected], errors='coerce')
        df['Desviacion_Absoluta'] = df['Diferencia_Uds'].abs()
        
        # Resumen
        st.subheader("📌 Resumen Ejecutivo")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SKUs Analizados", f"{len(df[sku_col].unique()):,}")
        m2.metric("Unidades Esperadas", f"{int(df[col_expected].sum()):,}")
        m3.metric("Unidades Reales", f"{int(df['Total_Real_Leido'].sum()):,}")
        m4.metric("Diferencia Neto", f"{int(df['Diferencia_Uds'].sum()):,}")
        
        # Gráficos
        st.subheader("🔥 Análisis de Descuadres")
        fig = px.bar(df, x=sku_col, y='Diferencia_Uds', color='Diferencia_Uds', color_continuous_scale=["#E53E3E", "#00818A"])
        st.plotly_chart(fig, use_container_width=True)
        
        # Detalle
        st.subheader("📋 Detalle")
        st.dataframe(df, use_container_width=True)
        
        # Descarga
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Guardar Reporte", data=csv, file_name="reporte.csv", mime="text/csv")
