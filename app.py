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
    sku_col = st.sidebar.text_input("Columna de Código SKU", "Sku")
    unit_col = st.sidebar.text_input("Columna de Unidades Totales", "Unidades totales")
    pos_col = st.sidebar.text_input("Columna de Ubicación/Posición", "Posición")

    if st.sidebar.button("🚀 Ejecutar Análisis Completo"):
        if sku_col not in df_sis.columns or sku_col not in df_fis.columns:
            st.error(f"❌ La columna SKU '{sku_col}' no coincide. Revisa las listas superiores.")
        elif unit_col not in df_sis.columns or unit_col not in df_fis.columns:
            st.error(f"❌ La columna de Unidades '{unit_col}' no coincide. Revisa las listas superiores.")
        else:
            # Detectar si la posición existe en ambos
            tiene_pos = pos_col in df_sis.columns and pos_col in df_fis.columns

            # Limpieza básica de datos manteniendo posición si existe
            cols_sis = [sku_col, unit_col, pos_col] if tiene_pos else [sku_col, unit_col]
            cols_fis = [sku_col, unit_col, pos_col] if tiene_pos else [sku_col, unit_col]

            df_s_c = df_sis[cols_sis].copy().rename(columns={sku_col: 'SKU', unit_col: 'Uds_Sistema'})
            df_f_c = df_fis[cols_fis].copy().rename(columns={sku_col: 'SKU', unit_col: 'Uds_Fisico'})

            if tiene_pos:
                df_s_c = df_s_c.rename(columns={pos_col: 'Ubicacion'})
                df_f_c = df_f_c.rename(columns={pos_col: 'Ubicacion'})
                # Agrupar por SKU y Ubicación
                df_s_c = df_s_c.groupby(['SKU', 'Ubicacion'], as_index=False).sum()
                df_f_c = df_f_c.groupby(['SKU', 'Ubicacion'], as_index=False).sum()
                df_total = pd.merge(df_s_c, df_f_c, on=['SKU', 'Ubicacion'], how='outer').fillna(0)
            else:
                df_s_c = df_s_c.groupby('SKU', as_index=False).sum()
                df_f_c = df_f_c.groupby('SKU', as_index=False).sum()
                df_total = pd.merge(df_s_c, df_f_c, on='SKU', how='outer').fillna(0)

            df_total['Diferencia'] = df_total['Uds_Fisico'] - df_total['Uds_Sistema']
            df_total['Dif_Absoluta'] = df_total['Diferencia'].abs()

            # MÁTRICAS CLAVE
            st.write("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Artículos Auditados", len(df_total['SKU'].unique()))
            m2.metric("Descuadre Neto Neto (Uds)", int(df_total['Diferencia'].sum()))
            m3.metric("Movimiento de Errores (Uds Absolutas)", int(df_total['Dif_Absoluta'].sum()))

            # GRÁFICO CORPORATIVO
            st.write("---")
            st.subheader("🔥 Top SKU con Mayores Descuadres")
            top_descuadres = df_total.groupby('SKU', as_index=False)['Dif_Absoluta'].sum().sort_values(by='Dif_Absoluta', ascending=False).head(10)
            top_plot = df_total[df_total['SKU'].isin(top_descuadres['SKU'])].groupby('SKU', as_index=False)['Diferencia'].sum()
            fig = px.bar(top_plot, x='SKU', y='Diferencia', color='Diferencia',
                         title="Mayores diferencias detectadas (Sobrantes vs Faltantes)",
                         color_continuous_scale=["#E53E3E", "#00818A"])
            st.plotly_chart(fig, use_container_width=True)

            # ALGORITMOS INTELIGENTES DE DETECCIÓN
            st.write("---")
            st.subheader("🧠 Diagnósticos Automáticos de Operaciones")
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("### 🔄 Mercancía Reubicada (Traspasos sin registrar)")
                if tiene_pos:
                    faltas = df_total[df_total['Diferencia'] < 0]
                    sobras = df_total[df_total['Diferencia'] > 0]
                    reubicaciones = []
                    for _, f in faltas.iterrows():
                        match = sobras[(sobras['SKU'] == f['SKU']) & (sobras['Diferencia'] == abs(f['Diferencia']))]
                        for _, s in match.iterrows():
                            reubicaciones.append({
                                "SKU": f['SKU'],
                                "Ubicación Origen (Falta)": f['Ubicacion'],
                                "Ubicación Destino (Sobra)": s['Ubicacion'],
                                "Cantidad Cruzada": abs(f['Diferencia'])
                            })
                    if reubicaciones:
                        st.dataframe(pd.DataFrame(reubicaciones), use_container_width=True)
                    else:
                        st.info("No se encontraron patrones de prendas idénticas movidas de un hueco a otro.")
                else:
                    st.warning("⚠️ Se necesita mapear la columna de ubicación para calcular traspasos.")

            with col_b:
                st.markdown("### 🏷️ Posibles Cruces de Talla o Variante")
                if tiene_pos:
                    cruces_talla = []
                    df_total['Raiz'] = df_total['SKU'].apply(lambda x: str(x).split('-')[0].split('_')[0])
                    for (pos, raiz), g in df_total.groupby(['Ubicacion', 'Raiz']):
                        if len(g) > 1 and g['Diferencia'].sum() == 0 and (g['Diferencia'] != 0).any():
                            detalles = ", ".join([f"{row['SKU']}: {int(row['Diferencia'])}" for _, row in g.iterrows() if row['Diferencia'] != 0])
                            cruces_talla.append({
                                "Ubicación": pos,
                                "Modelo Base": raiz,
                                "Descuadre Interno": detalles
                            })
                    if cruces_talla:
                        st.dataframe(pd.DataFrame(cruces_talla), use_container_width=True)
                    else:
                        st.info("No se detectaron errores de 'Sobra Talla S / Falta Talla M' en la misma ubicación.")
                else:
                    st.warning("⚠️ Se necesita mapear la columna de ubicación para calcular cruces de variantes.")

            # TABLA GENERAL

            st.write("---")
            st.subheader("📋 Detalle General de Diferencias")
            st.dataframe(df_total, use_container_width=True)

            csv = df_total.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Descargar Informe de Diferencias (CSV)", data=csv, file_name="informe_diferencias.csv", mime="text/csv")
