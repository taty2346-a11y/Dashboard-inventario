import pandas as pd
import plotly.express as px
import streamlit as st
# Configuración de página
st.set_page_config(page_title="Auditoría Logisfashion", page_icon="📊", layout="wide")
# Estilo corporativo
st.markdown("""
<style>
   .stApp { background-color: #f8f9fa; }
   h1 { color: #002e5d; }
   div.stButton > button { background-color: #00818a; color: white; font-weight: bold; }
</style>
""", unsafe_allow_html=True)
st.title("📊 Control de Diferencias de Inventario")
# Carga de archivo
archivo = st.file_uploader("Sube tu reporte de inventario (Excel o CSV)", type=["xlsx", "csv"])
if archivo:
   df = pd.read_excel(archivo) if archivo.name.endswith(".xlsx") else pd.read_csv(archivo)
   st.sidebar.header("⚙️ Mapeo de Columnas")
   # Intenta detectar columnas automáticamente
   cols = df.columns.tolist()
   # Selecciones con detección automática
   sku_col = st.sidebar.selectbox("Columna SKU", cols, index=cols.index("Sku") if "Sku" in cols else 0)
   esp_col = st.sidebar.selectbox("Unidades Esperadas", cols, index=cols.index("ExpectedUnits") if "ExpectedUnits" in cols else 0)
   fis_col = st.sidebar.selectbox("Unidades Físicas (Conteo)", cols, index=cols.index("ReadUnits") if "ReadUnits" in cols else 0)
   if st.button("🚀 Ejecutar Análisis"):
       # Limpieza
       df[esp_col] = pd.to_numeric(df[esp_col], errors='coerce').fillna(0)
       df[fis_col] = pd.to_numeric(df[fis_col], errors='coerce').fillna(0)
       # Cálculo de diferencias
       df['Diferencia'] = df[fis_col] - df[esp_col]
       # Dashboard
       col1, col2, col3 = st.columns(3)
       col1.metric("Esperadas", int(df[esp_col].sum()))
       col2.metric("Físicas", int(df[fis_col].sum()))
       col3.metric("Diferencia Total", int(df['Diferencia'].sum()))
       st.subheader("📋 Detalle de Descuadres")
       st.dataframe(df[[sku_col, esp_col, fis_col, 'Diferencia']], use_container_width=True)
       # Gráfico
       fig = px.bar(df[df['Diferencia'] != 0], x=sku_col, y='Diferencia',
                    title="SKUs con descuadre", color='Diferencia',
                    color_continuous_scale=["#E53E3E", "#00818A"])
       st.plotly_chart(fig, use_container_width=True)
       # Descarga
       csv = df.to_csv(index=False).encode('utf-8')
       st.download_button("💾 Descargar Resultados", data=csv, file_name="auditoria_final.csv", mime="text/csv")
