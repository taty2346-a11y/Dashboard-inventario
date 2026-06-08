import pandas as pd
import plotly.express as px
import streamlit as st
import re

# Configuración básica
st.set_page_config(page_title="Auditoría Logisfashion", layout="wide")

# CSS corregido (sin 'ipx')
st.markdown("""
<style>
    h1, h2, h3 { color: #002e5d !important; }
    div.stButton > button:first-child { background-color: #002e5d !important; color: white !important; font-weight: bold !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Cuadro de Mando: Auditoría Logisfashion")

archivo_carga = st.file_uploader("Cargar Archivo", type=["xlsx", "csv"])

if archivo_carga:
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    sku_col = st.sidebar.text_input("Columna SKU", "Sku")
    col_expected = st.sidebar.selectbox("Columna Esperadas", df.columns)
    col_read_1 = st.sidebar.selectbox("Lecturas Paso 1", df.columns)
    col_read_2 = st.sidebar.selectbox("Lecturas Paso 2", df.columns)
    pos_col = st.sidebar.text_input("Columna Ubicación", "Posición")
    
    if st.sidebar.button("📊 Ejecutar Comparativa"):
        # Cálculos de diferencias
        df['Paso1_Num'] = pd.to_numeric(df[col_read_1], errors='coerce').fillna(0)
        df['Paso2_Num'] = pd.to_numeric(df[col_read_2], errors='coerce').fillna(0)
        df['Total_Real'] = df.apply(lambda r: r['Paso2_Num'] if r['Paso2_Num'] > 0 else r['Paso1_Num'], axis=1)
        df['Dif'] = df['Total_Real'] - pd.to_numeric(df[col_expected], errors='coerce').fillna(0)
        
        # Lógica de Clasificación
        def definir_estado(row):
            if row['Dif'] == 0: return "Correcto"
            if row['Dif'] > 0: return "Found"
            return "Lost"

        df['Categoria'] = df.apply(definir_estado, axis=1)
        
        # --- Cálculo de Reubicado y Cambio de Talla ---
        # Aquí puedes insertar tu lógica de agrupación si deseas valores distintos a 0
        total_reubicados = 0 
        total_tallas = 0
        
        # Mostrar Métricas
        st.subheader("📌 Resumen Ejecutivo")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Correcto", len(df[df['Categoria'] == "Correcto"]))
        c2.metric("Found", len(df[df['Categoria'] == "Found"]))
        c3.metric("Lost", len(df[df['Categoria'] == "Lost"]))
        c4.metric("Reubicado", total_reubicados)
        c5.metric("Cambio Talla", total_tallas)
        
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Guardar Reporte", data=csv, file_name="auditoria_final.csv", mime="text/csv")
