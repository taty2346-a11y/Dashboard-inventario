import pandas as pd
import streamlit as st
st.set_page_config(page_title="Auditoría Logisfashion", page_icon="📊", layout="wide")
st.title("📊 Control de Diferencias de Inventario")
st.markdown("Sube ambos archivos para realizar la comparación.")
# Creamos dos columnas para los dos archivos
col1, col2 = st.columns(2)
with col1:
   archivo_sistema = st.file_uploader("1. Cargar Stock Cliente (Excel/CSV)", type=["xlsx", "csv"])
with col2:
   archivo_fisico = st.file_uploader("2. Cargar Conteo Logisfashion (Excel/CSV)", type=["xlsx", "csv"])
if archivo_sistema and archivo_fisico:
   # Cargar archivos
   df_sis = pd.read_excel(archivo_sistema) if archivo_sistema.name.endswith(".xlsx") else pd.read_csv(archivo_sistema)
   df_fis = pd.read_excel(archivo_fisico) if archivo_fisico.name.endswith(".xlsx") else pd.read_csv(archivo_fisico)
   st.sidebar.header("⚙️ Configuración de Columnas")
   # Selección de columnas para el sistema
   sku_sis = st.sidebar.selectbox("Columna SKU (Archivo 1)", df_sis.columns)
   cant_sis = st.sidebar.selectbox("Columna Unidades (Archivo 1)", df_sis.columns)
   # Selección de columnas para el físico
   sku_fis = st.sidebar.selectbox("Columna SKU (Archivo 2)", df_fis.columns)
   cant_fis = st.sidebar.selectbox("Columna Unidades (Archivo 2)", df_fis.columns)
   if st.sidebar.button("🚀 Ejecutar Comparativa"):
       # Realizar el merge (cruce) de los archivos por SKU
       df_merge = pd.merge(
           df_sis[[sku_sis, cant_sis]],
           df_fis[[sku_fis, cant_fis]],
           left_on=sku_sis,
           right_on=sku_fis,
           how='outer'
       ).fillna(0)
       # Calcular diferencia
       df_merge['Diferencia'] = df_merge[cant_fis] - df_merge[cant_sis]
       st.subheader("📋 Resultados de la Auditoría")
       st.dataframe(df_merge, use_container_width=True)
       # Botón de descarga
       csv = df_merge.to_csv(index=False).encode('utf-8')
       st.download_button("💾 Descargar Comparativa", data=csv, file_name="resultado_auditoria.csv", mime="text/csv")
