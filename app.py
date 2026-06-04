import pandas as pd
import streamlit as st
st.set_page_config(page_title="Auditoría Logisfashion", page_icon="📊", layout="wide")
st.title("📊 Control de Diferencias de Inventario")
col1, col2 = st.columns(2)
with col1:
   archivo_sistema = st.file_uploader("1. Cargar Stock Cliente (Excel/CSV)", type=["xlsx", "csv"])
with col2:
   archivo_fisico = st.file_uploader("2. Cargar Conteo Logisfashion (Excel/CSV)", type=["xlsx", "csv"])
if archivo_sistema and archivo_fisico:
   # Cargar y limpiar nombres de columnas (eliminar espacios extra)
   df_sis = pd.read_excel(archivo_sistema) if archivo_sistema.name.endswith(".xlsx") else pd.read_csv(archivo_sistema)
   df_fis = pd.read_excel(archivo_fisico) if archivo_fisico.name.endswith(".xlsx") else pd.read_csv(archivo_fisico)
   df_sis.columns = df_sis.columns.str.strip()
   df_fis.columns = df_fis.columns.str.strip()
   st.sidebar.header("⚙️ Configuración")
   sku_sis = st.sidebar.selectbox("SKU (Archivo 1)", df_sis.columns)
   cant_sis = st.sidebar.selectbox("Unidades (Archivo 1)", df_sis.columns)
   sku_fis = st.sidebar.selectbox("SKU (Archivo 2)", df_fis.columns)
   cant_fis = st.sidebar.selectbox("Unidades (Archivo 2)", df_fis.columns)
   if st.sidebar.button("🚀 Ejecutar Comparativa"):
       # Realizar el cruce de datos
       try:
           df_merge = pd.merge(
               df_sis[[sku_sis, cant_sis]],
               df_fis[[sku_fis, cant_fis]],
               left_on=sku_sis,
               right_on=sku_fis,
               how='outer'
           ).fillna(0)
           # Convertir a numérico forzado para evitar el error de cálculo
           df_merge[cant_sis] = pd.to_numeric(df_merge[cant_sis], errors='coerce').fillna(0)
           df_merge[cant_fis] = pd.to_numeric(df_merge[cant_fis], errors='coerce').fillna(0)
           # Calcular diferencia
           df_merge['Diferencia'] = df_merge[cant_fis] - df_merge[cant_sis]
           st.subheader("📋 Resultados de la Auditoría")
           st.dataframe(df_merge, use_container_width=True)
           csv = df_merge.to_csv(index=False).encode('utf-8')
           st.download_button("💾 Descargar Comparativa", data=csv, file_name="resultado_auditoria.csv", mime="text/csv")
       except Exception as e:
           st.error(f"Error al procesar: {e}. Revisa que las columnas seleccionadas sean numéricas.")
