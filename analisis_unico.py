import pandas as pd
import plotly.express as px
import streamlit as st
import re

# Configuración básica
st.set_page_config(page_title="Comparativa Logisfashion", page_icon="📊", layout="wide")

# --- ESTILOS CORPORATIVOS ---
st.markdown("""
<style>
    h1, h2, h3 { color: #002e5d !important; font-family: 'Segoe UI', sans-serif; }
    div.stButton > button:first-child { background-color: #002e5d !important; color: white !important; font-weight: bold !important; border-radius: 8px !important; border: none !important; padding: 0.5rem 2rem !important; }
    div.stButton > button:first-child:hover { background-color: #00818a !important; color: white !important; }
    @media print {
        section[data-testid="stSidebar"], header, footer { display: none !important; }
        .block-container { max-width: 100% !important; padding-top: 0 !important; }
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.image("https://cdn.brandfetch.io/idBNTSMPCj/w/400/h/400/theme/dark/icon.jpeg?c=1bxid64Mup7aczewSAYMX&t=1752693425078", width=150)
st.title("📊 Cuadro de Mando: Auditoría Logisfashion")

archivo_carga = st.file_uploader("Cargar Archivo de Inventario (Excel/CSV)", type=["xlsx", "csv"])

if archivo_carga:
    df = pd.read_excel(archivo_carga) if archivo_carga.name.endswith(".xlsx") else pd.read_csv(archivo_carga)
    
    st.sidebar.header("⚙️ Configuración")
    sku_col = st.sidebar.text_input("Columna SKU", "Sku")
    col_expected = st.sidebar.selectbox("Columna Esperadas", df.columns)
    col_read_1 = st.sidebar.selectbox("Lecturas Paso 1", df.columns)
    col_read_2 = st.sidebar.selectbox("Lecturas Paso 2", df.columns)
    pos_col = st.sidebar.text_input("Columna Ubicación", "Posición")
    
    if st.sidebar.button("📊 Ejecutar Comparativa"):
        # Limpieza
        df[sku_col] = df[sku_col].astype(str).str.strip()
        df['Paso1_Num'] = pd.to_numeric(df[col_read_1], errors='coerce').fillna(0)
        df['Paso2_Num'] = pd.to_numeric(df[col_read_2], errors='coerce').fillna(0)
        
        # Lógica de consolidación
        df['Total_Real_Leido'] = df.apply(lambda r: r['Paso2_Num'] if r['Paso2_Num'] > 0 else r['Paso1_Num'], axis=1)
        df['Diferencia_Uds'] = df['Total_Real_Leido'] - pd.to_numeric(df[col_expected], errors='coerce').fillna(0)
        df['Desviacion_Absoluta'] = df['Diferencia_Uds'].abs()
        
        # Funciones corregidas
        def extraer_raiz(sku):
            partes = re.split(r'[-_/](?=[^-/_]*$)', str(sku))
            return partes[0].strip().upper()

        df['Raiz_Modelo'] = df[sku_col].apply(extraer_raiz)
        
        # --- RESUMEN Y KPIs ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SKUs", f"{len(df[sku_col].unique()):,}")
        m2.metric("Esperadas", f"{int(df[col_expected].sum()):,}")
        m3.metric("Reales", f"{int(df['Total_Real_Leido'].sum()):,}")
        m4.metric("Diferencia", f"{int(df['Diferencia_Uds'].sum()):,}")
        
        # Gráficos
        st.subheader("🔥 Análisis de Variaciones")
        fig = px.bar(df.head(20), x=sku_col, y='Diferencia_Uds', color='Diferencia_Uds', color_continuous_scale=["#E53E3E", "#00818A"])
        st.plotly_chart(fig, use_container_width=True)
        
        # Detalle
        st.dataframe(df, use_container_width=True)
        
        # Descarga
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Guardar Reporte", data=csv, file_name="auditoria_final.csv", mime="text/csv")
