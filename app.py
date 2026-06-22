import pandas as pd
import streamlit as st
import io  # Necesario para manejar la descarga en memoria de Excel

# Configuración de página
st.set_page_config(page_title="Auditoría Logisfashion", page_icon="📊", layout="wide")
st.title("📊 Control de Diferencias e Historial de Inventario")

# Carga de dos archivos
col1, col2 = st.columns(2)
with col1:
    archivo_sistema = st.file_uploader("1. Cargar Stock Cliente / Inventario Anterior (Excel/CSV)", type=["xlsx", "csv"])
with col2:
    archivo_fisico = st.file_uploader("2. Cargar Conteo Nuevo / Logisfashion (Excel/CSV)", type=["xlsx", "csv"])

if archivo_sistema and archivo_fisico:
    # Leer archivos
    df_sis = pd.read_excel(archivo_sistema) if archivo_sistema.name.endswith(".xlsx") else pd.read_csv(archivo_sistema)
    df_fis = pd.read_excel(archivo_fisico) if archivo_fisico.name.endswith(".xlsx") else pd.read_csv(archivo_fisico)
    
    # Limpieza básica de nombres de columnas
    df_sis.columns = df_sis.columns.str.strip()
    df_fis.columns = df_fis.columns.str.strip()
    
    st.sidebar.header("⚙️ Configuración")
    
    # Selección de columnas mapeadas
    sku_sis = st.sidebar.selectbox("SKU (Archivo 1)", df_sis.columns)
    cant_sis = st.sidebar.selectbox("Unidades (Archivo 1)", df_sis.columns)
    
    # Nueva opción: Selección de columna de estado anterior (LOST/FOUND)
    columnas_estado = ["(No evaluar estados)"] + list(df_sis.columns)
    estado_sis = st.sidebar.selectbox("Columna Estado Anterior - LOST/FOUND (Archivo 1)", columnas_estado)
    
    sku_fis = st.sidebar.selectbox("SKU (Archivo 2)", df_fis.columns)
    cant_fis = st.sidebar.selectbox("Unidades (Archivo 2)", df_fis.columns)
    
    if st.sidebar.button("🚀 Ejecutar Comparativa"):
        try:
            # Preparar datos base
            columnas_filtrar_sis = [sku_sis, cant_sis]
            if estado_sis != "(No evaluar estados)":
                columnas_filtrar_sis.append(estado_sis)
                
            df_sis_clean = df_sis[columnas_filtrar_sis].copy()
            df_fis_clean = df_fis[[sku_fis, cant_fis]].copy()
            
            # Convertir cantidades a numérico
            df_sis_clean[cant_sis] = pd.to_numeric(df_sis_clean[cant_sis], errors='coerce').fillna(0)
            df_fis_clean[cant_fis] = pd.to_numeric(df_fis_clean[cant_fis], errors='coerce').fillna(0)
            
            # Unir tablas (Outer join para no perder SKUs de ningún lado)
            df_merge = pd.merge(
                df_sis_clean,
                df_fis_clean,
                left_on=sku_sis,
                right_on=sku_fis,
                how='outer'
            ).fillna(0)
            
            # Si un SKU solo existía en el físico, el SKU del sistema queda
