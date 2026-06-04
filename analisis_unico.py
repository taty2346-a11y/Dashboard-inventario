import pandas as pd
import plotly.express as px
import streamlit as st
import re

# Configuración básica de la página
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")

# URL del nuevo logo corporativo facilitado por el usuario
URL_LOGO_CORPORATIVO = "https://cdn.brandfetch.io/idBNTSMPCj/w/400/h/400/theme/dark/icon.jpeg?c=1bxid64Mup7aczewSAYMX&t=1752693425078"
st.sidebar.image(URL_LOGO_CORPORATIVO, width=150)

# --- INYECCIÓN DE ESTILOS CORPORATIVOS LOGISFASHION Y MODO IMPRESIÓN ---
st.markdown("""
<style>
    /* ---- ESTILOS VISUALES PARA LA PANTALLA EN VIVO ---- */
    /* Color de los títulos principales */
    h1, h2, h3 {
        color: #002e5d !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Personalización del botón de ejecutar con el azul marino corporativo */
    div.stButton > button:first-child {
        background-color: #002e5d !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.5rem 2rem !important;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    div.stButton > button:first-child:hover {
        background-color: #00818a !important;
        color: white !important;
    }

    /* ---- REGLAS ESPECIALES PARA IMPRESIÓN A PDF COMPLETO (SIN CORTES) ---- */
    @media print {
        /* Romper el scroll interno de Streamlit para que imprima todas las páginas hacia abajo */
        html, body, .stApp, .main, .block-container, [data-testid="stAppViewContainer"] {
            overflow: visible !important;
            height: auto !important;
            position: static !important;
            background-color: white !important;
        }
        
        /* Ocultar la barra lateral izquierda por completo en el PDF */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        
        /* Ocultar elementos web innecesarios (menús superiores y decoraciones) */
        header, footer, [data-testid="stHeader"], [data-testid="stDecoration"] {
            display: none !important;
        }
        
        /* Forzar a las cajas a usar todo el ancho disponible del papel */
        .block-container {
            max-width: 100% !important;
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            margin: 0 !important;
        }
        
        /* Asegurar que el navegador respete los colores de las gráficas y las tarjetas KPIs */
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        
        /* Evitar que los bloques de gráficos se partan por la mitad a mitad de folio */
        .stPlotlyChart, div[data-testid="stMetric"], div[data-testid="stDataFrame"] {
            page-break-inside: avoid !important;
            margin-bottom: 20px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Cuadro de Mando: Comparativa de Unidades (Lógica de Recuento)")
st.markdown("Sube tu reporte de inventario. El sistema consolidará el Paso 1 y Paso 2 aplicando la regla de auditoría de Logisfashion.")

# Subida del único fichero
archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    # Lectura automática del archivo
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    st.info(f"🔍 **Columnas detectadas en el archivo:** {', '.join(df.columns.tolist())}")
    
    st.sidebar.header("⚙️ Configuración de Columnas")
    
    default_sku = "Sku" if "Sku" in df.columns else (df.columns[0] if len(df.columns) > 0 else "")
    sku_col = st.sidebar.text_input("Columna de Código SKU", default_sku)
    
    opciones_columnas = df.columns.tolist()
    
    idx_expected = opciones_columnas.index("expectedUnits") if "expectedUnits" in opciones_columnas else 0
    col_expected = st.sidebar.selectbox("Columna de Unidades Esperadas (Sistema)", opciones_columnas, index=idx_expected)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Fases del Conteo Físico")
    
    col_read_1_default = [c for c in opciones_columnas if "Read" in c]
    
    idx_r1 = opciones_columnas.index(col_read_1_default[0]) if len(col_read_1_default) > 0 else 0
    idx_r2 = opciones_columnas.index(col_read_1_default[1]) if len(col_read_1_default) > 1 else (1 if len(opciones_columnas) > 1 else 0)
    
    col_read_1 = st.sidebar.selectbox("Lecturas Paso 1 (Primer Conteo)", opciones_columnas, index=idx_r1)
    col_read_2 = st.sidebar.selectbox("Lecturas Paso 2 (Recuento por Descuadre)", opciones_columnas, index=idx_r2)
    
    st.sidebar.markdown("---")
    default_pos = "Posición" if "Posición" in opciones_columnas else ("Posicion" if "Posicion" in opciones_columnas else "Ubicacion")
    pos_col = st.sidebar.text_input("Columna de Ubicación (Opcional)", default_pos)
    
    if st.sidebar.button("📊 Ejecutar Comparativa"):
        if sku_col not in df.columns:
            st.error(f"❌ La columna SKU '{sku_col}' no se encuentra en el archivo.")
        elif col_expected not in df.columns:
            st.error(f"❌ La columna Esperadas '{col_expected}' no se encuentra.")
        else:
            # Limpieza básica de datos
            df[sku_col] = df[sku_col].astype(str).str.strip()
            tiene_pos = pos_col in df.columns
            if tiene_pos:
                df[pos_col] = df[pos_col].astype(str).str.strip().str.upper()
            
            df[col_expected] = pd.to_numeric(df[col_expected], errors='coerce').fillna(0)
            df['Paso1_Num'] = pd.to_numeric(df[col_read_1], errors='coerce').fillna(0)
            df['Paso2_Num'] = pd.to_numeric(df[col_read_2], errors='coerce').fillna(0)
            
            # REGLA LOGÍSTICA DE RECUENTO REPASADO
            def calcular_total_leido(row):
                if row['Paso2_Num'] > 0:
                    return row['Paso2_Num']
                return row['Paso1_Num']
            
            df['Total_Real_Leido'] = df.apply(calcular_total_leido, axis=1)
            df['Diferencia_Uds'] = df['Total_Real_Leido'] - df[col_expected]
            df['Desviacion_Absoluta'] = df['Diferencia_Uds'].abs()
            
            # --- ALGORITMOS DE CLASIFICACIÓN DE ERROR ---
            total_uds_reubicadas = 0
            total_uds_cruces_talla = 0
            
            if tiene_pos:
                faltas = df[df['Diferencia_Uds'] < 0].copy()
                sobras = df[df['Diferencia_Uds'] > 0].copy()
                skus_procesados = set()
                
                for _, f in faltas.iterrows():
                    sku = f[sku_col]
                    if sku not in skus_procesados:
                        f_sku_total = abs(faltas[faltas[sku_col] == sku]['Diferencia_Uds'].sum())
                        s_sku_total = sobras[sobras[sku_col] == sku]['Diferencia_Uds'].sum()
                        total_uds_reubicadas += min(f_sku_total, s_sku_total)
                        skus_procesados.add(sku)
                
                def extraer_raiz_definitiva(sku):
                    sku_str = str(sku).strip()
                    partes = re.split(r'[-_/](?=[^-/_]*$)', sku_str)
                    if len(partes) > 1:
                        return partes[0].strip().upper()
                    return sku_str.upper()

                df['Raiz_Modelo'] = df[sku_col].apply(extraer_raiz_definitiva)
                
                for (pos, raiz), g in df.groupby([pos_col, 'Raiz_Modelo']):
                    lineas_descuadre = g[g['Diferencia_Uds'] != 0]
                    if len(lineas_descuadre) > 1:
                        t_faltas = abs(lineas_descuadre[lineas_descuadre['Diferencia_Uds'] < 0]['Diferencia_Uds'].sum())
                        t_sobras = lineas_descuadre[lineas_descuadre['Diferencia_Uds'] > 0]['Diferencia_Uds'].sum()
                        if t_faltas > 0 and t_sobras > 0:
                            total_uds_cruces_talla += min(t_faltas, t_sobras)

            total_desviacion_absoluta = df['Desviacion_Absoluta'].sum()
            uds_descuadre_puro = max(0, total_desviacion_absoluta - (total_uds_reubicadas * 2) - (total_uds_cruces_talla * 2))
            
            if total_desviacion_absoluta > 0:
                pct_reubicados = ((total_uds_reubicadas * 2) / total_desviacion_absoluta) * 100
                pct_tallas = ((total_uds_cruces_talla * 2) / total_desviacion_absoluta) * 100
                pct_puro = (uds_descuadre_puro / total_desviacion_absoluta) * 100
            else:
                pct_reubicados, pct_tallas, pct_puro = 0.0, 0.0, 0.0

            # --- SECCIÓN 1: MÉTRICAS CLAVE ---
            st.write("---")
            st.subheader("📌 Resumen Ejecutivo de Descuadres")
            m1, m2, m3, m4 = st.columns(4)
            
            m1.metric("Total SKU Analizados", f"{len(df[sku_col].unique()):,}")
            m2.metric("Total Unidades Esperadas", f"{int(df[col_expected].sum()):,}")
            m3.metric("Total Unidades Consolidadas", f"{int(df['Total_Real_Leido'].sum()):,}")
            
            descuadre_neto = int(df['Diferencia_Uds'].sum())
            m4.metric("Diferencia Global Neto", f"{descuadre_neto:,}")
            
            st.markdown("#### 🎯 Distribución e Impacto de los Errores Encontrados")
            p1, p2, p3 = st.columns(3)
            p1.metric("🔄 Peso de Mercancía Reubicada", f"{pct_reubicados:.1f}%")
            p2.metric("🏷️ Peso de Cruces de Talla", f"{pct_tallas:.1f}%")
            p3.metric("🚨 Peso de Descuadre Real Neto", f"{pct_puro:.1f}%")
            
            # --- SECCIÓN 2: GRÁFICOS CON LOS COLORES AJUSTADOS ---
            st.write("---")
            st.subheader("🔥 Análisis de Variaciones Línea a Línea")
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown(f"### Top 10 SKU con Mayores Desfases")
                df_sku = df.groupby(sku_col)[['Diferencia_Uds', 'Desviacion_Absoluta']].sum().reset_index()
                top_descuadres = df_sku.sort_values(by='Desviacion_Absoluta', ascending=False).head(10)
                
                # Paleta corporativa: Faltantes en rojo suave, Sobrantes en turquesa Logisfashion
                fig_sku = px.bar(top_descuadres, x=sku_col, y='Diferencia_Uds', color='Diferencia_Uds',
                                 title="Sobrantes (Turquesa) vs Faltantes (Rojo) por Artículo",
                                 color_continuous_scale=["#E53E3E", "#00818A"])
                st.plotly_chart(fig_sku, use_container_width=True)
                
            with col_g2:
                if tiene_pos:
                    st.markdown("### Top 10 Ubicaciones más Críticas")
                    df_pos = df.groupby(pos_col)[['Diferencia_Uds', 'Desviacion_Absoluta']].sum().reset_index()
                    top_pos = df_pos.sort_values(by='Desviacion_Absoluta', ascending=False).head(10)
                    
                    fig_pos = px.bar(top_pos, x=pos_col, y='Diferencia_Uds', color='Diferencia_Uds',
                                     title="Descuadre Neto Acumulado en la Estantería",
                                     color_continuous_scale=["#E53E3E", "#00818A"])
                    st.plotly_chart(fig_pos, use_container_width=True)
                else:
                    st.info("💡 Agrega una ubicación válida para ver los descuadres por estantería.")
            
            # --- SECCIÓN 3: DIAGNÓSTICOS OPERATIVOS ---
            st.write("---")
            st.subheader("🧠 Diagnósticos Automáticos de Operaciones (Detección de Patrones)")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("### 🔄 Mercancía Reubicada (Mismo artículo en huecos distintos)")
                if tiene_pos:
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
                st.markdown("### 🏷️ Análisis de Cruces de Talla (Compensación Proporcional)")
                if tiene_pos:
                    cruces_talla = []
                    for (pos, raiz), g in df.groupby([pos_col, 'Raiz_Modelo']):
                        lineas_descuadre = g[g['Diferencia_Uds'] != 0]
                        if len(lineas_descuadre) > 1:
                            total_faltas = abs(lineas_descuadre[lineas_descuadre['Diferencia_Uds'] < 0]['Diferencia_Uds'].sum())
                            total_sobras = lineas_descuadre[lineas_descuadre['Diferencia_Uds'] > 0]['Diferencia_Uds'].sum()
                            
                            if total_faltas > 0 and total_sobras > 0:
                                unidades_compensadas = int(min(total_faltas, total_sobras))
                                resto_neto = int(total_sobras - total_faltas)
                                
                                if resto_neto > 0:
                                    balance_final = f"Sobra el resto (+{resto_neto} Uds)"
                                elif resto_neto < 0:
                                    balance_final = f"Falta el resto ({resto_neto} Uds)"
                                else:
                                    balance_final = "Compensación Perfecta (Neto 0)"
                                    
                                detalles = ", ".join([f"{row[sku_col]}: {int(row['Diferencia_Uds'])}" for _, row in lineas_descuadre.iterrows()])
                                
                                cruces_talla.append({
                                    "Ubicación": pos,
                                    "Modelo Base": raiz,
                                    "Uds Cruzadas": unidades_compensadas,
                                    "Balance Restante": balance_final,
                                    "Desglose Detallado": detalles
                                })
                                
                    if cruces_talla:
                        st.dataframe(pd.DataFrame(cruces_talla), use_container_width=True)
                    else:
                        st.info("No se detectaron errores de variantes o tallas mezcladas en los mismos huecos.")
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
            st.download_button(
            label="💾 Guardar Reporte Comparativo (Excel)",
            data=excel_data,
            file_name="comparativa_consolidada.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
