import pandas as pd
import plotly.express as px
import streamlit as st
import re

# Configuración básica
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")

# CSS sin errores de sintaxis
st.markdown("""
<style>
    h1, h2, h3 { color: #002e5d !important; }
    div.stButton > button:first-child { background-color: #002e5d !important; color: white !important; font-weight: bold !important; border-radius: 8px !important; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Cuadro de Mando: Auditoría de Inventario")

archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

# Definición de funciones FUERA de cualquier bloque lógico para evitar errores de sintaxis
def clasificar(row):
    if row['Dif'] == 0: return "Correcto"
    if row['Dif'] > 0: return "Found"
    return "Lost"

def extraer_raiz(sku):
    sku_str = str(sku).strip()
    partes = re.split(r'[-_/](?=[^-/_]*$)', sku_str)
    return partes[0].strip().upper() if len(partes) > 1 else sku_str.upper()

if archivo_carga:
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    sku_col = st.sidebar.text_input("Columna SKU", "Sku")
    col_expected = st.sidebar.selectbox("Columna Esperadas", df.columns)
    col_read_1 = st.sidebar.selectbox("Lecturas Paso 1", df.columns)
    col_read_2 = st.sidebar.selectbox("Lecturas Paso 2", df.columns)
    pos_col = st.sidebar.text_input("Columna Ubicación", "Posición")
    
    if st.sidebar.button("📊 Ejecutar Comparativa"):
        # Cálculos
        df['Paso1_Num'] = pd.to_numeric(df[col_read_1], errors='coerce').fillna(0)
        df['Paso2_Num'] = pd.to_numeric(df[col_read_2], errors='coerce').fillna(0)
        df['Total_Real'] = df.apply(lambda r: r['Paso2_Num'] if r['Paso2_Num'] > 0 else r['Paso1_Num'], axis=1)
        df['Dif'] = df['Total_Real'] - pd.to_numeric(df[col_expected], errors='coerce').fillna(0)
        
        # Aplicar funciones
        df['Categoria'] = df.apply(clasificar, axis=1)
        df['Raiz_Modelo'] = df[sku_col].apply(extraer_raiz)
        
        # Mostrar métricas
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Correcto", len(df[df['Categoria'] == "Correcto"]))
        c2.metric("Found", len(df[df['Categoria'] == "Found"]))
        c3.metric("Lost", len(df[df['Categoria'] == "Lost"]))
        c4.metric("Reubicado", "Pendiente")
        c5.metric("Cambio Talla", "Pendiente")
        
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Guardar Reporte", data=csv, file_name="auditoria_final.csv", mime="text/csv")
