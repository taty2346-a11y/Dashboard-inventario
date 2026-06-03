import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración básica e imagen corporativa
st.set_page_config(page_title="Análisis de Inventario Único", page_icon="📦", layout="wide")
st.sidebar.image("https://www.logisfashion.com/wp-content/uploads/2023/04/logisfashion-logo.png", width=200)

st.title("📦 Cuadro de Mando: Análisis de Stock (Fichero Único)")
st.markdown("Sube un único reporte de inventario (Sistema o Conteo) para analizar la distribución del stock y los artículos top.")

# Subida del único fichero
archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    # Lectura del archivo
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)

    # Mostrar columnas en la lista azul para guiar al usuario
    st.info(f"🔍 **Columnas detectadas en el archivo:** {', '.join(df.columns.tolist())}")

    st.sidebar.header("⚙️ Configuración de Columnas")
    sku_col = st.sidebar.text_input("Columna de Código SKU", "Sku")
    unit_col = st.sidebar.text_input("Columna de Unidades/Cantidad", "Unidades totales")
    pos_col = st.sidebar.text_input("Columna de Ubicación (Opcional)", "Posición")

    if st.sidebar.button("📊 Generar Reporte"):
        if sku_col not in df.columns:
            st.error(f"❌ La columna SKU '{sku_col}' no existe en el archivo.")
        elif unit_col not in df.columns:
            st.error(f"❌ La columna de Unidades '{unit_col}' no existe en el archivo.")
        else:
            # Asegurar que las unidades sean numéricas
            df[unit_col] = pd.to_numeric(df[unit_col], errors='coerce').fillna(0)

            # --- SECCIÓN 1: MÉTRICAS CLAVE ---
            st.write("---")
            st.subheader("📌 Resumen General del Stock")
            m1, m2, m3 = st.columns(3)

            total_skus = len(df[sku_col].unique())
            total_unidades = int(df[unit_col].sum())

            m1.metric("Variedad de SKU únicos", f"{total_skus:,}")
            m2.metric("Total Unidades en Stock", f"{total_unidades:,}")

            if pos_col in df.columns:
                total_pos = len(df[pos_col].unique())
                m3.metric("Ubicaciones Ocupadas", f"{total_pos:,}")
            else:
                m3.metric("Líneas de Registro", f"{len(df):,}")

            # --- SECCIÓN 2: GRÁFICOS INTERACTIVOS ---
            st.write("---")
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown("### 🔥 Top 10 SKU con Mayor Volumen de Stock")
                top_sku = df.groupby(sku_col)[unit_col].sum().reset_index()
                top_sku = top_sku.sort_values(by=unit_col, ascending=False).head(10)

                fig_sku = px.bar(top_sku, x=sku_col, y=unit_col, text_auto='.2s',
                                 labels={unit_col: 'Unidades', sku_col: 'Código SKU'},
                                 color_continuous_scale=["#00818A"], color=unit_col)
                st.plotly_chart(fig_sku, use_container_width=True)

            with col_g2:
                if pos_col in df.columns:
                    st.markdown("### 🗺️ Top 10 Ubicaciones más Saturadas")
                    top_pos = df.groupby(pos_col)[unit_col].sum().reset_index()
                    top_pos = top_pos.sort_values(by=unit_col, ascending=False).head(10)

                    fig_pos = px.bar(top_pos, x=pos_col, y=unit_col, text_auto='.2s',
                                     labels={unit_col: 'Unidades', pos_col: 'Ubicación'},
                                     color_continuous_scale=["#F4F7F6", "#00818A"], color=unit_col)
                    st.plotly_chart(fig_pos, use_container_width=True)
                else:
                    st.info("💡 Si configuras una columna de ubicación válida, aquí verás el mapa de calor de las estanterías.")

            # --- SECCIÓN 3: TABLA DE DATOS Y DESCARGA ---
            st.write("---")
            st.subheader("📋 Vista Detallada del Inventario")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Exportar Copia en Limpio (CSV)", data=csv, file_name="analisis_stock.csv", mime="text/csv")
