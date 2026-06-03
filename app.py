import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración básica e imagen corporativa
st.set_page_config(page_title="Auditoría Logisfashion", page_icon="📊", layout="wide")
st.sidebar.image("https://www.logisfashion.com/wp-content/uploads/2023/04/logisfashion-logo.png", width=200)

st.title("📊 Control de Diferencias de Inventario")
st.markdown("Sube los reportes del sistema y del conteo físico para generar el análisis de descuadres.")

# Subida de ficheros
col1, col2 = st.columns(2)
with col1:
    file_sis = st.file_uploader("1. Cargar Stock en Sistema (Excel/CSV)", type=["xlsx", "csv"])
with col2:
    file_fis = st.file_uploader("2. Cargar Conteo Físico (Excel/CSV)", type=["xlsx", "csv"])

if file_sis and file_fis:
    df_sis = pd.read_excel(file_sis) if file_sis.name.endswith(".xlsx") else pd.read_csv(file_sis)
    df_fis = pd.read_excel(file_fis) if file_fis.name.endswith(".xlsx") else pd.read_csv(file_fis)

    # Mostrar columnas reales detectadas en las listas azules
    st.info(f"🔍 **Columnas en Sistema:** {', '.join(df_sis.columns.tolist())}")
    st.info(f"🔍 **Columnas en Físico:** {', '.join(df_fis.columns.tolist())}")

    st.sidebar.header("⚙️ Configuración de Columnas")
    sku_col = st.sidebar.text_input("Columna de Código SKU", df_sis.columns[0])
    unit_col = st.sidebar.text_input("Columna de Unidades Totales", df_sis.columns[1] if len(df_sis.columns) > 1 else "Unidades")
    pos_col = st.sidebar.text_input("Columna de Ubicación/Posición", "Posicion")

    if st.sidebar.button("🚀 Ejecutar Análisis Completo"):
        if sku_col not in df_sis.columns or sku_col not in df_fis.columns:
            st.error("❌ La columna SKU no coincide. Revisa los nombres de las listas azules.")
        elif unit_col not in df_sis.columns or unit_col not in df_fis.columns:
            st.error("❌ La columna de Unidades no coincide. Revisa los nombres de las listas azules.")
        else:
            # Forzar nombres uniformes para el cruce rápido
            df_sis_clean = df_sis[[sku_col, unit_col]].copy().rename(columns={sku_col: 'SKU', unit_col: 'Uds_Sistema'})
            df_fis_clean = df_fis[[sku_col, unit_col]].copy().rename(columns={sku_col: 'SKU', unit_col: 'Uds_Fisico'})

            # Agrupar por si hay repetidos
            df_sis_clean = df_sis_clean.groupby('SKU', as_index=False).sum()
            df_fis_clean = df_fis_clean.groupby('SKU', as_index=False).sum()

            # Cruzar datos
            df_total = pd.merge(df_sis_clean, df_fis_clean, on='SKU', how='outer').fillna(0)
            df_total['Diferencia'] = df_total['Uds_Fisico'] - df_total['Uds_Sistema']
            df_total['Dif_Absoluta'] = df_total['Diferencia'].abs()

            # Métricas
            st.write("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total SKU Auditados", len(df_total))
            m2.metric("Descuadre Neto (Uds)", int(df_total['Diferencia'].sum()))
            m3.metric("Impacto Total de Errores (Uds Absolutas)", int(df_total['Dif_Absoluta'].sum()))

            # Gráfico de barras de las mayores diferencias
            st.write("---")
            st.subheader("🔥 Top SKU con Mayores Descuadres")
            top_descuadres = df_total.sort_values(by='Dif_Absoluta', ascending=False).head(10)
            fig = px.bar(top_descuadres, x='SKU', y='Diferencia', color='Diferencia',
                         title="Mayores diferencias detectadas (Sobrantes vs Faltantes)",
                         color_continuous_scale=["#E53E3E", "#00818A"])
            st.plotly_chart(fig, use_container_width=True)

            # Tabla de resultados
            st.write("---")
            st.subheader("📋 Detalle General de Diferencias")
            st.dataframe(df_total, use_container_width=True)

            # Botón de descarga
            csv = df_total.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Descargar Informe de Diferencias (CSV)", data=csv, file_name="informe_diferencias.csv", mime="text/csv")
