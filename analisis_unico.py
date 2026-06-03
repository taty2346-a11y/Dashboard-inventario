import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración básica e imagen corporativa
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")
st.sidebar.image("https://www.logisfashion.com/wp-content/uploads/2023/04/logisfashion-logo.png", width=200)

st.title("📊 Cuadro de Mando: Comparativa de Unidades (Mismo Fichero)")
st.markdown("Sube tu reporte de inventario para analizar las diferencias directamente entre las columnas de unidades.")

# Subida del único fichero
archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    # Lectura automática del archivo
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    # Mostrar columnas en la lista azul para guiar al usuario
    st.info(f"🔍 **Columnas detectadas en el archivo:** {', '.join(df.columns.tolist())}")
    
    st.sidebar.header("⚙️ Configuración de Columnas")
    
    # Intentar autodetectar la columna de SKU (buscando variantes comunes)
    default_sku = "Sku" if "Sku" in df.columns else (df.columns[0] if len(df.columns) > 0 else "")
    sku_col = st.sidebar.text_input("Columna de Código SKU", default_sku)
    
    # Selección inteligente y automática de tus columnas reales
    opciones_columnas = df.columns.tolist()
    
    idx_expected = opciones_columnas.index("expectedUnits") if "expectedUnits" in opciones_columnas else 0
    idx_read = opciones_columnas.index("ReadUnits") if "ReadUnits" in opciones_columnas else (1 if len(opciones_columnas) > 1 else 0)
    
    col_cant_1 = st.sidebar.selectbox("Columna de Unidades Esperadas (Sistema)", opciones_columnas, index=idx_expected)
    col_cant_2 = st.sidebar.selectbox("Columna de Unidades Leídas (Físico)", opciones_columnas, index=idx_read)
    
    # Intentar autodetectar ubicación
    default_pos = "Posición" if "Posición" in opciones_columnas else ("Posicion" if "Posicion" in opciones_columnas else "Ubicacion")
    pos_col = st.sidebar.text_input("Columna de Ubicación (Opcional)", default_pos)
    
    if st.sidebar.button("📊 Ejecutar Comparativa"):
        if sku_col not in df.columns:
            st.error(f"❌ La columna SKU '{sku_col}' no se encuentra en el archivo. Verifica las mayúsculas en la lista azul superior.")
        else:
            # Asegurar que ambas columnas sean tratadas como números limpios
            df[col_cant_1] = pd.to_numeric(df[col_cant_1], errors='coerce').fillna(0)
            df[col_cant_2] = pd.to_numeric(df[col_cant_2], errors='coerce').fillna(0)
            
            # Calcular las diferencias matemáticas reales (Leído - Esperado)
            df['Diferencia_Uds'] = df[col_cant_2] - df[col_cant_1]
            df['Desviacion_Absoluta'] = df['Diferencia_Uds'].abs()
            
            # --- SECCIÓN 1: MÉTRICAS CLAVE ---
            st.write("---")
            st.subheader("📌 Resumen Ejecutivo de Descuadres")
            m1, m2, m3, m4 = st.columns(4)
            
            m1.metric("Total SKU Analizados", f"{len(df[sku_col].unique()):,}")
            m2.metric(f"Total {col_cant_1}", f"{int(df[col_cant_1].sum()):,}")
            m3.metric(f"Total {col_cant_2}", f"{int(df[col_cant_2].sum()):,}")
            
            descuadre_neto = int(df['Diferencia_Uds'].sum())
            m4.metric("Diferencia Global Neto", f"{descuadre_neto:,}")
            
            # --- SECCIÓN 2: GRÁFICOS DE DESVIACIONES ---
            st.write("---")
            st.subheader("🔥 Análisis de Variaciones Línea a Línea")
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown(f"### Top 10 SKU con Mayores Desfases")
                df_sku = df.groupby(sku_col)[['Diferencia_Uds', 'Desviacion_Absoluta']].sum().reset_index()
                top_descuadres = df_sku.sort_values(by='Desviacion_Absoluta', ascending=False).head(10)
                
                fig_sku = px.bar(top_descuadres, x=sku_col, y='Diferencia_Uds', color='Diferencia_Uds',
                                 title="Sobrantes (Verde) vs Faltantes (Rojo) por Artículo",
                                 color_continuous_scale=["#E53E3E", "#00818A"])
                st.plotly_chart(fig_sku, use_container_width=True)
                
            with col_g2:
                if pos_col in df.columns:
                    st.markdown("### Top 10 Ubicaciones más Críticas")
                    df_pos = df.groupby(pos_col)[['Diferencia_Uds', 'Desviacion_Absoluta']].sum().reset_index()
                    top_pos = df_pos.sort_values(by='Desviacion_Absoluta', ascending=False).head(10)
                    
                    fig_pos = px.bar(top_pos, x=pos_col, y='Diferencia_Uds', color='Diferencia_Uds',
                                     title="Descuadre Neto Acumulado en la Estantería",
                                     color_continuous_scale=["#E53E3E", "#00818A"])
                    st.plotly_chart(fig_pos, use_container_width=True)
                else:
                    st.info("💡 Si la tabla contiene columnas de estantería o hueco, escribe su nombre exacto en la izquierda para ver el mapa de calor.")
            
            # --- SECCIÓN 3: TABLA DE DATOS ORDENADA Y COPIA EN CSV ---
            st.write("---")
            st.subheader("📋 Detalle de la Comparación Realizada")
            
            # Reorganizar el orden visual de la tabla para que sea hiperfácil de leer en la reunión
            cols_prioritarias = [sku_col]
            if pos_col in df.columns: cols_prioritarias.append(pos_col)
            cols_prioritarias += [col_cant_1, col_cant_2, 'Diferencia_Uds']
            
            resto_columnas = [c for c in df.columns if c not in cols_prioritarias and c != 'Desviacion_Absoluta']
            df_final = df[cols_prioritarias + resto_columnas]
            
            st.dataframe(df_final, use_container_width=True)
            
            # Botón de exportación inmediata
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Guardar Reporte Comparativo (CSV)", data=csv, file_name="comparativa_expected_vs_read.csv", mime="text/csv")
