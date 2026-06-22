import pandas as pd
import streamlit as st
import io

# Configuración de página
st.set_page_config(page_title="Auditoría Logisfashion", page_icon="📊", layout="wide")
st.title("📊 Control de Diferencias e Historial de Inventario")

# Carga de dos archivos
col1, col2 = st.columns(2)
with col1:
    archivo_sistema = st.file_uploader("1. Cargar Stock Cliente / Inventario Anterior (Excel/CSV)", type=["xlsx", "csv"])
with col2:
    archivo_fisico = st.file_uploader("2. Cargar Conteo Nuevo / Logisfashion (Excel/CSV)", type=["xlsx", "csv"])

if archivo_sistema and archivo_fisico:
    # Leer archivos
    df_sis = pd.read_excel(archivo_sistema) if archivo_sistema.name.endswith(".xlsx") else pd.read_csv(archivo_sistema)
    df_fis = pd.read_excel(archivo_fisico) if archivo_fisico.name.endswith(".xlsx") else pd.read_csv(archivo_fisico)
    
    # Limpieza básica de nombres de columnas
    df_sis.columns = df_sis.columns.str.strip()
    df_fis.columns = df_fis.columns.str.strip()
    
    st.sidebar.header("⚙️ Configuración")
    
    # Selección de columnas mapeadas
    sku_sis = st.sidebar.selectbox("SKU (Archivo 1)", df_sis.columns)
    cant_sis = st.sidebar.selectbox("Unidades (Archivo 1)", df_sis.columns)
    
    # Selección de columna de estado anterior
    columnas_estado = ["(No evaluar estados)"] + list(df_sis.columns)
    estado_sis = st.sidebar.selectbox("Columna Estado Anterior - LOST/FOUND (Archivo 1)", columnas_estado)
    
    sku_fis = st.sidebar.selectbox("SKU (Archivo 2)", df_fis.columns)
    cant_fis = st.sidebar.selectbox("Unidades (Archivo 2)", df_fis.columns)
    
    if st.sidebar.button("🚀 Ejecutar Comparativa"):
        try:
            # Preparar datos base
            columnas_filtrar_sis = [sku_sis, cant_sis]
            if estado_sis != "(No evaluar estados)":
                columnas_filtrar_sis.append(estado_sis)
                
            df_sis_clean = df_sis[columnas_filtrar_sis].copy()
            df_fis_clean = df_fis[[sku_fis, cant_fis]].copy()
            
            # Convertir cantidades a numérico
            df_sis_clean[cant_sis] = pd.to_numeric(df_sis_clean[cant_sis], errors='coerce').fillna(0)
            df_fis_clean[cant_fis] = pd.to_numeric(df_fis_clean[cant_fis], errors='coerce').fillna(0)
            
            # Unir tablas (Outer join)
            df_merge = pd.merge(
                df_sis_clean,
                df_fis_clean,
                left_on=sku_sis,
                right_on=sku_fis,
                how='outer'
            ).fillna(0)
            
            # Consolidar SKU final de forma segura
            df_merge['SKU_Final'] = df_merge[sku_sis].astype(str).replace('0', '')
            df_merge.loc[df_merge['SKU_Final'] == '', 'SKU_Final'] = df_merge[sku_fis]
            
            # Calcular diferencia
            df_merge['Diferencia'] = df_merge[cant_fis] - df_merge[cant_sis]
            
            # Lógica de Control de Errores Corregidos (LOST / FOUND)
            if estado_sis != "(No evaluar estados)":
                def analizar_correccion(row):
                    estado_previo = str(row[estado_sis]).upper().strip()
                    dif_actual = row['Diferencia']
                    
                    if "LOST" in estado_previo:
                        return "🟢 Corregido (Era LOST, ahora cuadrado)" if dif_actual == 0 else "🔴 Error Persiste (Sigue con descuadre)"
                    elif "FOUND" in estado_previo:
                        return "🟢 Corregido (Era FOUND, ahora cuadrado)" if dif_actual == 0 else "🔴 Error Persiste (Sigue con descuadre)"
                    return "⚪ Sin Incidencia Previa"
                
                df_merge['Auditoría Estados'] = df_merge.apply(analizar_correccion, axis=1)
            
            # Reorganizar columnas
            columnas_finales = ['SKU_Final', cant_sis, cant_fis, 'Diferencia']
            if estado_sis != "(No evaluar estados)":
                columnas_finales.insert(1, estado_sis)
                columnas_finales.append('Auditoría Estados')
                
            df_resultado = df_merge[columnas_finales].copy()
            
            # Mostrar resultados en la app
            st.subheader("📋 Resultados de la Auditoría")
            st.dataframe(df_resultado, use_container_width=True)
            
            # Conversión y Descarga en formato EXCEL (.xlsx)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_resultado.to_excel(writer, index=False, sheet_name='Diferencias_Inventario')
            buffer.seek(0)
            
            st.download_button(
                label="📥 Descargar Comparativa en Excel (.xlsx)",
                data=buffer,
                file_name="resultado_auditoria_inventario.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"Error técnico: {e}. Asegúrate de que las columnas de cantidades contengan datos numéricos.")
