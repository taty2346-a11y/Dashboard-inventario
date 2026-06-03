import pandas as pd
import plotly.express as px
import streamlit as st
import re

# Configuración básica e imagen corporativa
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")
st.sidebar.image("https://www.logisfashion.com/wp-content/uploads/2023/04/logisfashion-logo.png", width=200)

st.title("📊 Cuadro de Mando: Comparativa de Unidades (Lógica de Recuento)")
st.markdown("Sube tu reporte de inventario. El sistema consolidará el Paso 1 y Paso 2 aplicando la regla de auditoría de Logisfashion.")

# Subida del único fichero
archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    # Lectura automática del archivo
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    # Mostrar columnas en la lista azul para guiar al usuario
    st.info(f"🔍 **Columnas detectadas en el archivo:** {', '.join(df.columns.tolist())}")
    
    st.sidebar.header("⚙️ Configuración de Columnas")
    
    # Intentar autodetectar la columna de SKU
    default_sku = "Sku" if "Sku" in df.columns else (df.columns[0] if len(df.columns) > 0 else "")
    sku_col = st.sidebar.text_input("Columna de Código SKU", default_sku)
    
    opciones_columnas = df.columns.tolist()
    
    # 1. Columna de Esperadas (Sistema)
    idx_expected = opciones_columnas.index("expectedUnits") if "expectedUnits" in opciones_columnas else 0
    col_expected = st.sidebar.selectbox("Columna de Unidades Esperadas (Sistema)", opciones_columnas, index=idx_expected)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Fases del Conteo Físico")
    
    # 2. Intento de detección automática de los pasos de lectura
    col_read_1_default = [c for c in opciones_columnas if "Read" in c]
    
    idx_r1 = opciones_columnas.index(col_read_1_default[0]) if len(col_read_1_default) > 0 else 0
    idx_r2 = opciones_columnas.index(col_read_1_default[1]) if len(col_read_1_default) > 1 else (1 if len(opciones_columnas) > 1 else 0)
    
    col_read_1 = st.sidebar.selectbox("Lecturas Paso 1 (Primer Conteo)", opciones_columnas, index=idx_r1)
    col_read_2 = st.sidebar.selectbox("Lecturas Paso 2 (Recuento por Descuadre)", opciones_columnas, index=idx_r2)
    
    st.sidebar.markdown("---")
    # Intentar autodetectar ubicación
    default_pos = "Posición" if "Posición" in opciones_columnas else ("Posicion" if "Posicion" in opciones_columnas else "Ubicacion")
    pos_col = st.sidebar.text_input("Columna de Ubicación (Opcional)", default_pos)
    
    if st.sidebar.button("📊 Ejecutar Comparativa"):
        if sku_col not in df.columns:
            st.error(f"❌ La columna SKU '{sku_col}' no se encuentra en el archivo.")
        elif col_expected not in df.columns:
            st.error(f"❌ La columna Esperadas '{col_expected}' no se encuentra.")
        else:
            # Limpieza y conversión a números
            df[col_expected] = pd.to_numeric(df[col_expected], errors='coerce').fillna(0)
            df['Paso1_Num'] = pd.to_numeric(df[col_read_1], errors='coerce').fillna(0)
            df['Paso2_Num'] = pd.to_numeric(df[col_read_2], errors='coerce').fillna(0)
            
            # APLICACIÓN DE LA REGLA LOGÍSTICA:
            # Si el Paso 2 se rellenó (es mayor que 0), se toma el Paso 2 como conteo final.
            # Si el Paso 2 está a 0 o vacío, significa que el Paso 1 era correcto.
            def calcular_total_leido(row):
                if row['Paso2_Num'] > 0:
                    return row['Paso2_Num']
                return row['Paso1_Num']
            
            df['Total_Real_Leido'] = df.apply(calcular_total_leido, axis=1)
            
            # Calcular las diferencias matemáticas reales basadas en el consolidado (Leído - Esperado)
            df['Diferencia_Uds'] = df['Total_Real_Leido'] - df[col_expected]
            df['Desviacion_Absoluta'] = df['Diferencia_Uds'].abs()
            
            # --- SECCIÓN 1: MÉTRICAS CLAVE ---
            st.write("---")
            st.subheader("📌 Resumen Ejecutivo de Descuadres")
            m1, m2, m3, m4 = st.columns(4)
            
            m1.metric("Total SKU Analizados", f"{len(df[sku_col].unique()):,}")
            m2.metric("Total Unidades Esperadas", f"{int(df[col_expected].sum()):,}")
            m3.metric("Total Unidades Consolidadas", f"{int(df['Total_Real_Leido'].sum()):,}")
            
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
                    st.info("💡 Agrega una ubicación válida para ver los descuadres por estantería.")
            
            # --- SECCIÓN 3: ALGORITMOS INTELIGENTES AVANZADOS ---
            st.write("---")
            st.subheader("🧠 Diagnósticos Automáticos de Operaciones (Detección de Patrones)")
            col_a, col_b = st.columns(2)
            
            tiene_pos = pos_col in df.columns
            
            with col_a:
                st.markdown("### 🔄 Mercancía Reubicada (Mismo artículo en huecos distintos)")
                if tiene_pos:
                    faltas = df[df['Diferencia_Uds'] < 0]
                    sobras = df[df['Diferencia_Uds'] > 0]
                    reubicaciones = []
                    
                    for _, f in faltas.iterrows():
                        match = sobras[(sobras[sku_col] == f[sku_col]) & (sobras['Diferencia_Uds'] == abs(f['Diferencia_Uds']))]
                        for _, s in match.iterrows():
                            reubicaciones.append({
                                "SKU": f[sku_col],
                                "Ubicación Origen (Falta)": f[pos_col],
                                "Ubicación Destino (Sobra)": s[pos_col],
                                "Cantidad Cruzada": int(abs(f['Diferencia_Uds']))
                            })
                    if reubicaciones:
                        st.dataframe(pd.DataFrame(reubicaciones).drop_duplicates(), use_container_width=True)
                    else:
                        st.info("No se encontraron patrones de prendas idénticas movidas de un hueco a otro.")
                else:
                    st.warning("⚠️ Se necesita una ubicación válida para calcular traspasos.")
                    
            with col_b:
                st.markdown("### 🏷️ Posibles Cruces de Talla o Variante (Tallas Complejas)")
                if tiene_pos:
                    cruces_talla = []
                    
                    # Identifica el modelo base eliminando el último guion/barra con número o letra (ej: -18, -22, -M)
                    def extraer_raiz_definitiva(sku):
                        sku_str = str(sku).strip()
                        partes = re.split(r'[-_/](?=[^-/_]*$)', sku_str)
                        if len(partes) > 1:
                            return partes[0]
                        return sku_str

                    df['Raiz_Modelo'] = df[sku_col].apply(extraer_raiz_definitiva)
                    
                    for (pos, raiz), g in df.groupby([pos_col, 'Raiz_Modelo']):
                        if len(g) > 1 and int(g['Diferencia_Uds'].sum()) == 0 and (g['Diferencia_Uds'] != 0).any():
                            detalles = ", ".join([f"{row[sku_col]}: {int(row['Diferencia_Uds'])}" for _, row in g.iterrows() if row['Diferencia_Uds'] != 0])
                            cruces_talla.append({
                                "Ubicación": pos,
                                "Modelo Base": raiz,
                                "Descuadre Interno de Variantes": detalles
                            })
                    if cruces_talla:
                        st.dataframe(pd.DataFrame(cruces_talla), use_container_width=True)
                    else:
                        st.info("No se detectaron errores de tallas cruzadas en el mismo hueco.")
                else:
                    st.warning("⚠️ Se necesita una columna de ubicación válida para calcular cruces de variantes.")
            
            # --- SECCIÓN 4: TABLA DE DATOS DETALLADA ---
            st.write("---")
            st.subheader("📋 Detalle de la Comparación Realizada")
            
            cols_prioritarias = [sku_col]
            if tiene_pos: cols_prioritarias.append(pos_col)
            cols_prioritarias += [col_expected, col_read_1, col_read_2, 'Total_Real_Leido', 'Diferencia_Uds']
            
            resto_columnas = [c for c in df.columns if c not in cols_prioritarias and c not in ['Desviacion_Absoluta', 'Raiz_Modelo', 'Paso1_Num', 'Paso2_Num']]
            df_final = df[cols_prioritarias + resto_columnas]
            
            st.dataframe(df_final, use_container_width=True)
            
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Guardar Reporte Comparativo (CSV)", data=csv, file_name="comparativa_consolidada.csv", mime="text/csv")
