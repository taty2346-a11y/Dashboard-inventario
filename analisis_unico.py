import pandas as pd
import plotly.express as px
import streamlit as st
import re
import io  # Requerido para la conversión a Excel en memoria

# URL del logo corporativo facilitado
URL_LOGO_CORPORATIVO = "https://cdn.brandfetch.io/idBNTSMPCj/w/400/h/400/theme/dark/icon.jpeg?c=1bxid64Mup7aczewSAYMX&t=1752693425078"
st.sidebar.image(URL_LOGO_CORPORATIVO, width=150)

# Configuración básica de la página
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")

# --- INYECCIÓN DE ESTILOS CORPORATIVOS LOGISFASHION Y MODO IMPRESIÓN ---
st.markdown("""
<style>
    /* ---- ESTILOS VISUALES PARA LA PANTALLA EN VIVO ---- */
    h1, h2, h3 {
        color: #002e5d !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
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
        html, body, .stApp, .main, .block-container, [data-testid="stAppViewContainer"] {
            overflow: visible !important;
            height: auto !important;
            position: static !important;
            background-color: white !important;
        }
        
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        
        header, footer, [data-testid="stHeader"], [data-testid="stDecoration"] {
            display: none !important;
        }
        
        .block-container {
            max-width: 100% !important;
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            margin: 0 !important;
        }
        
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        
        .stPlotlyChart, div[data-testid="stMetric"], div[data-testid="stDataFrame"] {
            page-break-inside: avoid !important;
            margin-bottom: 20px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Cuadro de Mando: Consolidación y Control de Calidad de Inventarios")
st.markdown("Procesamiento automatizado optimizado para columnas nativas: `ExpectedUnids`, `ReadUnits` y `ReadUnitsStep2`.")

archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    opciones_columnas = df.columns.tolist()
    
    # --- MAPEADO NATIVO FIJO CON FALLBACK DE SEGURIDAD ---
    col_expected = "ExpectedUnids" if "ExpectedUnids" in opciones_columnas else (st.sidebar.selectbox("Columna Teórico (Sistema)", opciones_columnas, index=opciones_columnas.index("expectedUnits") if "expectedUnits" in opciones_columnas else 0))
    col_read_1 = "ReadUnits" if "ReadUnits" in opciones_columnas else (st.sidebar.selectbox("Lecturas Paso 1 (Primer Conteo)", opciones_columnas))
    col_read_2 = "ReadUnitsStep2" if "ReadUnitsStep2" in opciones_columnas else (st.sidebar.selectbox("Lecturas Paso 2 (Recuento)", opciones_columnas))
    
    # Detección automática inteligente de SKU y Ubicación
    idx_sku = next((i for i, c in enumerate(opciones_columnas) if "sku" in c.lower() or "art" in c.lower() or "cod" in c.lower()), 0)
    idx_pos = next((i for i, c in enumerate(opciones_columnas) if "pos" in c.lower() or "ubic" in c.lower() or "hueco" in c.lower()), 0)
    
    st.sidebar.header("⚙️ Variables de Identificación")
    sku_col = st.sidebar.selectbox("Columna de Código SKU", opciones_columnas, index=idx_sku)
    pos_col = st.sidebar.selectbox("Columna de Ubicación", opciones_columnas, index=idx_pos)

    # Validar que las columnas críticas seleccionadas existan en el set de datos
    columnas_faltantes = [c for c in [col_expected, col_read_1, col_read_2] if c not in opciones_columnas]
    
    if columnas_faltantes:
        st.error(f"❌ Estructura incorrecta. Faltan las siguientes columnas en el archivo: {', '.join(columnas_faltantes)}")
    else:
        if st.sidebar.button("📊 Ejecutar Comparativa Avanzada"):
            
            # Limpieza estándar de textos
            df[sku_col] = df[sku_col].astype(str).str.strip()
            tiene_pos = pos_col in df.columns
            if tiene_pos:
                df[pos_col] = df[pos_col].astype(str).str.strip().str.upper()

            # --- PARSER REFINADO PARA INTEGRIDAD DE CELDAS VACÍAS (Evita bugs de strings 'nan') ---
            def parsear_fase_conteo(columna):
                str_limpio = df[columna].astype(str).str.strip()
                es_vacio = str_limpio.isin(['nan', 'NaN', 'None', '', '-', 'null'])
                valores_num = pd.to_numeric(df[columna], errors='coerce').fillna(0)
                return valores_num, es_vacio

            # Extracción limpia de matrices de datos numéricos
            df['Teorico_Num'] = pd.to_numeric(df[col_expected], errors='coerce').fillna(0)
            df['Paso1_Num'], df['Paso1_Vacio'] = parsear_fase_conteo(col_read_1)
            df['Paso2_Num'], df['Paso2_Vacio'] = parsear_fase_conteo(col_read_2)

            # --- NÚCLEO DE DECISIÓN LOGÍSTICA ---
            def calcular_total_leido(row):
                # Si el Paso 2 se ejecutó (NO está vacío), tiene prioridad total absoluta
                if not row['Paso2_Vacio']:
                    return row['Paso2_Num']
                else:
                    # Si el Paso 2 está vacío y el Paso 1 cuadró perfecto, se acepta
                    if row['Paso1_Num'] == row['Teorico_Num']:
                        return row['Paso1_Num']
                    # Si el Paso 1 tiene descuadres pero no hay Paso 2, se bloquea el ajuste y se mantiene Teórico
                    else:
                        return row['Teorico_Num']
            
            df['Total_Real_Leido'] = df.apply(calcular_total_leido, axis=1)
            df['Diferencia_Uds'] = df['Total_Real_Leido'] - df['Teorico_Num']
            df['Desviacion_Absoluta'] = df['Diferencia_Uds'].abs()

            # --- DETECCIÓN DE ERRORES DE AUDITORÍA EN PLANTA ---
            df['Error_Proceso_Falta_Paso2'] = (df['Paso1_Vacio'] == False) & (df['Paso1_Num'] != df['Teorico_Num']) & (df['Paso2_Vacio'] == True)
            df['Uds_En_Disputa_Ignoradas'] = df.apply(
                lambda r: abs(r['Paso1_Num'] - r['Teorico_Num']) if r['Error_Proceso_Falta_Paso2'] else 0, axis=1
            )
            
            total_skus_con_error = df[df['Error_Proceso_Falta_Paso2']][sku_col].nunique()
            total_uds_con_error = df['Uds_En_Disputa_Ignoradas'].sum()

            # --- ALGORITMOS DE DIAGNÓSTICO AVANZADO DE INVENTARIO ---
            total_uds_reubicadas = 0
            total_uds_cruces_talla = 0
            
            faltas = df[df['Diferencia_Uds'] < 0].copy()
            sobras = df[df['Diferencia_Uds'] > 0].copy()

            if tiene_pos:
                # 1. Algoritmo de Mercancía Reubicada (Traspasos entre huecos)
                skus_procesados = set()
                for _, f in faltas.iterrows():
                    sku = f[sku_col]
                    if sku not in skus_procesados:
                        f_sku_total = abs(faltas[faltas[sku_col] == sku]['Diferencia_Uds'].sum())
                        s_sku_total = sobras[sobras[sku_col] == sku]['Diferencia_Uds'].sum()
                        total_uds_reubicadas += min(f_sku_total, s_sku_total)
                        skus_procesados.add(sku)
                
                # 2. Algoritmo de Cruces de Talla / Variantes
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

            # --- MATEMÁTICA DE COMPENSACIÓN EXTREMA AL 100% ---
            total_faltas_brutas = abs(df[df['Diferencia_Uds'] < 0]['Diferencia_Uds'].sum())
            total_sobras_brutas = df[df['Diferencia_Uds'] > 0]['Diferencia_Uds'].sum()
            
            uds_lost_puro = max(0, total_faltas_brutas - total_uds_reubicadas - total_uds_cruces_talla)
            uds_found_puro = max(0, total_sobras_brutas - total_uds_reubicadas - total_uds_cruces_talla)
            
            total_unidades_esperadas = df['Teorico_Num'].sum()
            uds_sin_ajustes = max(0, total_unidades_esperadas - total_faltas_brutas)
            
            universo_total_unidades = total_unidades_esperadas + uds_found_puro
            
            if universo_total_unidades > 0:
                pct_sin_ajustes = (uds_sin_ajustes / universo_total_unidades) * 100
                pct_reubicados = (total_uds_reubicadas / universo_total_unidades) * 100
                pct_tallas = (total_uds_cruces_talla / universo_total_unidades) * 100
                pct_lost = (uds_lost_puro / universo_total_unidades) * 100
                pct_found = (uds_found_puro / universo_total_unidades) * 100
                pct_global_error_proceso = (total_uds_con_error / universo_total_unidades) * 100
            else:
                pct_sin_ajustes = pct_reubicados = pct_tallas = pct_lost = pct_found = pct_global_error_proceso = 0.0

            # --- ESTRUCTURACIÓN DE INTERFAZ POR PESTAÑAS (TABS) ---
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Resumen Ejecutivo", 
                "⚠️ Control de Calidad (Falta Paso 2)", 
                "🧠 Diagnósticos Avanzados", 
                "📋 Base de Datos Maestro"
            ])

            # --- PESTAÑA 1: RESUMEN EJECUTIVO ---
            with tab1:
                st.subheader("📌 Cuadro de Mando General de Descuadres")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total SKU Analizados", f"{len(df[sku_col].unique()):,}")
                m2.metric("Total Unidades Esperadas", f"{int(total_unidades_esperadas):,}")
                m3.metric("Total Unidades Consolidadas", f"{int(df['Total_Real_Leido'].sum()):,}")
                m4.metric("Diferencia Global Neto", f"{int(df['Diferencia_Uds'].sum()):,}")
                
                st.markdown("#### 🎯 Distribución e Impacto Real de Inventario")
                p1, p2, p3, p4, p5 = st.columns(5)
                p1.metric("✅ Sin Ajustes (Ok)", f"{pct_sin_ajustes:.1f}%")
                p2.metric("🔄 Mercancía Reubicada", f"{pct_reubicados:.1f}%")
                p3.metric("🏷️ Cruces de Talla", f"{pct_tallas:.1f}%")
                p4.metric("📉 Lost (Faltas Puras)", f"{pct_lost:.1f}%")
                p5.metric("📈 Found (Sobras Puras)", f"{pct_found:.1f}%")
                
                st.caption(f"💡 Base de auditoría unificada: `{int(universo_total_unidades):,}` unidades totales. Sumatorio del ecosistema: `{(pct_sin_ajustes + pct_reubicados + pct_tallas + pct_lost + pct_found):.1f}%`.")
                
                st.write("---")
                st.subheader("🔥 Análisis de Variaciones")
                col_g1, col_g2 = st.columns(2)
                
                with col_g1:
                    st.markdown("### Top 10 SKU con Mayores Desfases")
                    df_sku_graph = df.groupby(sku_col)[['Diferencia_Uds', 'Desviacion_Absoluta']].sum().reset_index()
                    top_descuadres = df_sku_graph.sort_values(by='Desviacion_Absoluta', ascending=False).head(10)
                    fig_sku = px.bar(top_descuadres, x=sku_col, y='Diferencia_Uds', color='Diferencia_Uds',
                                     title="Sobrantes (Turquesa) vs Faltantes (Rojo) por SKU",
                                     color_continuous_scale=["#E53E3E", "#00818A"])
                    st.plotly_chart(fig_sku, use_container_width=True)
                    
                with col_g2:
                    if tiene_pos:
                        st.markdown("### Top 10 Ubicaciones más Críticas")
                        df_pos_graph = df.groupby(pos_col)[['Diferencia_Uds', 'Desviacion_Absoluta']].sum().reset_index()
                        top_pos = df_pos_graph.sort_values(by='Desviacion_Absoluta', ascending=False).head(10)
                        fig_pos = px.bar(top_pos, x=pos_col, y='Diferencia_Uds', color='Diferencia_Uds',
                                         title="Descuadre Neto Acumulado en Ubicación",
                                         color_continuous_scale=["#E53E3E", "#00818A"])
                        st.plotly_chart(fig_pos, use_container_width=True)
                    else:
                        st.info("💡 Asigne una columna de ubicación válida para visualizar los descuadres por estantería.")

            # --- PESTAÑA 2: CONTROL DE CALIDAD OPERATIVO ---
            with tab2:
                st.subheader("🚨 Auditoría de Procesos en Planta")
                if total_uds_con_error > 0:
                    st.error(f"¡Atención! Se han detectado discrepancias en el Paso 1 donde el operario **no completó el Paso 2 obligatorio**.")
                    
                    err_col1, err_col2, err_col3 = st.columns(3)
                    err_col1.metric("SKUs Afectados por el Fallo", f"{total_skus_con_error:,}")
                    err_col2.metric("Unidades en Disputa Ignoradas", f"{int(total_uds_con_error):,} uds")
                    err_col3.metric("% Impacto s/ Total Auditado", f"{pct_global_error_proceso:.2f}%")
                    
                    st.markdown("### 📋 Líneas con Auditoría Incompleta (Se requiere recuento definitivo)")
                    df_lineas_error = df[df['Error_Proceso_Falta_Paso2']].copy()
                    cols_mostrar_err = [sku_col]
                    if tiene_pos: cols_mostrar_err.append(pos_col)
                    cols_mostrar_err += [col_expected, col_read_1, col_read_2, 'Uds_En_Disputa_Ignoradas']
                    st.dataframe(df_lineas_error[cols_mostrar_err], use_container_width=True)
                else:
                    st.success("🎉 ¡Excelente ejecución! Todos los desfases detectados en el conteo inicial cuentan con su validación en el Paso 2.")

            # --- PESTAÑA 3: DIAGNÓSTICOS AVANZADOS ---
            with tab3:
                st.subheader("🧠 Detección de Patrones Operativos Automáticos")
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
                        st.warning("⚠️ Se requiere columna de ubicación válida para trazar traspasos.")
                        
                with col_b:
                    st.markdown("### 🏷️ Cruces de Talla (Compensación Proporcional en el mismo hueco)")
                    if tiene_pos:
                        cruces_talla = []
                        for (pos, raiz), g in df.groupby([pos_col, 'Raiz_Modelo']):
                            lineas_descuadre = g[g['Diferencia_Uds'] != 0]
                            if len(lineas_descuadre) > 1:
                                t_faltas = abs(lineas_descuadre[lineas_descuadre['Diferencia_Uds'] < 0]['Diferencia_Uds'].sum())
                                t_sobras = lineas_descuadre[lineas_descuadre['Diferencia_Uds'] > 0]['Diferencia_Uds'].sum()
                                
                                if t_faltas > 0 and t_sobras > 0:
                                    unidades_compensadas = int(min(t_faltas, t_sobras))
                                    resto_neto = int(t_sobras - t_faltas)
                                    
                                    balance_final = f"Sobra el resto (+{resto_neto} Uds)" if resto_neto > 0 else (f"Falta el resto ({resto_neto} Uds)" if resto_neto < 0 else "Compensación Perfecta (Neto 0)")
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
                            st.info("No se detectaron variantes o tallas mezcladas en los mismos huecos.")
                    else:
                        st.warning("⚠️ Se requiere columna de ubicación válida para calcular cruces de modelo.")

            # --- PESTAÑA 4: BASE DE DATOS MAESTRO Y EXPORTACIÓN A EXCEL ---
            with tab4:
                st.subheader("📋 Detalle Completo de la Comparación Realizada")
                
                cols_prioritarias = [sku_col]
                if tiene_pos: cols_prioritarias.append(pos_col)
                cols_prioritarias += [col_expected, col_read_1, col_read_2, 'Total_Real_Leido', 'Diferencia_Uds']
                
                resto_columnas = [c for c in df.columns if c not in cols_prioritarias and c not in ['Desviacion_Absoluta', 'Raiz_Modelo', 'Teorico_Num', 'Paso1_Num', 'Paso2_Num', 'Paso1_Vacio', 'Paso2_Vacio', 'Error_Proceso_Falta_Paso2', 'Uds_En_Disputa_Ignoradas']]
                df_final = df[cols_prioritarias + resto_columnas]
                
                st.dataframe(df_final, use_container_width=True)
                
                # --- NUEVO MOTOR DE EXPORTACIÓN A EXCEL (.XLSX) ---
                buffer_excel = io.BytesIO()
                with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='Reporte Consolidado')
                
                st.download_button(
                    label="💾 Guardar Reporte Comparativo (Excel)",
                    data=buffer_excel.getvalue(),
                    file_name="comparativa_consolidada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
