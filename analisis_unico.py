import pandas as pd
import plotly.express as px
import streamlit as st
import re

# Configuración básica de la página
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")

# --- INYECCIÓN DE ESTILOS CORPORATIVOS LOGISFASHION, FONDO Y MODO IMPRESIÓN ---
st.markdown("""
<style>
    /* ---- CONFIGURACIÓN DEL FONDO CORPORATIVO (PANTALLA) ---- */
    .stApp {
        background: linear-gradient(135deg, #001a35 0%, #002e5d 100%) !important;
    }
    
    /* Forzar que los textos principales sean blancos para que contrasten con el fondo oscuro */
    h1, h2, h3, p, span, label, .stMarkdown {
        color: #ffffff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Hacer que las tarjetas de métricas y componentes tengan un fondo sutil semitransparente */
    div[data-testid="stMetric"], div.stAlert, .stDataFrame, .stTable {
        background-color: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
    
    /* Personalización del botón de ejecutar (Azul turquesa de acento) */
    div.stButton > button:first-child {
        background-color: #00818a !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.5rem 2rem !important;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.2);
    }
    
    div.stButton > button:first-child:hover {
        background-color: #00a4b0 !important;
    }

    /* ---- REGLAS ESPECIALES PARA IMPRESIÓN A PDF COMPLETO (SIN CORTES) ---- */
    @media print {
        html, body, .stApp, .main, .block-container, [data-testid="stAppViewContainer"] {
            overflow: visible !important;
            height: auto !important;
            position: static !important;
            background: white !important; /* En el PDF el fondo vuelve a ser blanco para ahorrar tinta */
        }
        
        h1, h2, h3, p, span, label, .stMarkdown {
            color: #002e5d !important; /* En el PDF el texto vuelve a ser azul oscuro profesional */
        }
        
        section[data-testid="stSidebar"], header, footer, [data-testid="stHeader"], [data-testid="stDecoration"] {
            display: none !important;
        }
        
        .block-container {
            max-width: 100% !important;
            padding: 0 !important;
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

# Llama a la imagen "logo.png" que acabas de subir a GitHub para colocarla en la cabecera lateral
st.sidebar.image("logo.png", width=160)

st.title("📊 Cuadro de Mando: Comparativa de Unidades (Lógica de Recuento)")
st.markdown("Sube tu reporte de inventario. El sistema consolidará el Paso 1 y Paso 2 aplicando la regla de auditoría de Logisfashion.")

# Subida del único fichero
archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    st.info(f"🔍 **Columnas detectadas en el archivo:** {', '.join(df.columns.tolist())}")
    
    st.sidebar.header("⚙️ Configuración de Columnas")
    
    default_sku = "Sku" if "Sku" in df.columns else (df.columns[0] if len(df.columns) > 0 else "")
    sku_col = st.sidebar.text_input("Columna de Código SKU", default_sku)
    
    opciones_columnas = df.columns.tolist()
    
    idx_expected = opciones_columnas.index("ExpectedUnits") if "ExpectedUnits" in opciones_columnas else (opciones_columnas.index("expectedUnits") if "expectedUnits" in opciones_columnas else 0)
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
            df[sku_col] = df[sku_col].astype(str).str.strip()
            tiene_pos = pos_col in df.columns
            if tiene_pos:
                df[pos_col] = df[pos_col].astype(str).str.strip().str.upper()
            
            df[col_expected] = pd.to_numeric(df[col_expected], errors='coerce').fillna(0)
            df['Paso1_Num'] = pd.to_numeric(df[col_read_1], errors='coerce').fillna(0)
            df['Paso2_Num'] = pd.to_numeric(df[col_read_2], errors='coerce').fillna(0)
            
            def calcular_total_leido(row):
                if row['Paso2_Num'] > 0:
                    return row['Paso2_Num']
                return row['Paso1_Num']
            
            df['Total_Real_Leido'] = df.apply(calcular_total_leido, axis=1)
            df['Diferencia_Uds'] = df['Total_Real_Leido'] - df[col_expected]
            df['Desviacion_Absoluta'] = df['Diferencia_Uds'].abs()
            
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
            
            st.write("---")
            st.subheader("🔥 Análisis de Variaciones Línea a Línea")
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown(f"### Top 10 SKU con Mayores Desfases")
                df_sku = df.groupby(sku_col)[['Diferencia_Uds', 'Desviacion_Absoluta']].sum().reset_index()
                top_descuadres = df_sku.sort_values(by='Desviacion_Absoluta', ascending=False).head(10)
                
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
            
            st.write("---")
            st.subheader("📋 Detalle de la Comparación Realizada")
            cols_prioritarias = [sku_col]
            if tiene_pos: cols_prioritarias.append(pos_col)
            cols_prioritarias += [col_expected, col_read_1, col_read_2, 'Total_Real_Leido', 'Diferencia_Uds']
            resto_columnas = [c for c in df.columns if c not in cols_prioritarias and c not in ['Desviacion_Absoluta', 'Raiz_Modelo', 'Paso1_Num', 'Paso2_Num']]
            df_final = df[cols_prioritarias + resto_columnas]
            st.dataframe(df_final, use_container_width=True)
