import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title="Control de Inventario Inteligente", page_icon="📊", layout="wide"
)
st.sidebar.image("https://website-assets-fs.freshworks.com/attachments/cjyh5btzx00954kfz5wibfo9s-logisfashion-logo.one-half.png", width=200)

st.title("📊 Cuadro de Mando: Control de Diferencias de Inventario")
st.markdown(
    "Sube los reportes del sistema y del conteo físico para generar el análisis de diferencias y detectar patrones automáticamente."
)

# Diseño de la interfaz en dos columnas para la carga de datos
col_f1, col_f2 = st.columns(2)

with col_f1:
    archivo_sistema = st.file_uploader(
        "1. Cargar Stock en Sistema (Excel/CSV)", type=["xlsx", "csv"]
    )
with col_f2:
    archivo_fisico = st.file_uploader(
        "2. Cargar Conteo Físico (Excel/CSV)", type=["xlsx", "csv"]
    )

if archivo_sistema and archivo_fisico:
    # Lectura de ficheros automática
    df_sistema = (
        pd.read_excel(archivo_sistema)
        if archivo_sistema.name.endswith(".xlsx")
        else pd.read_csv(archivo_sistema)
    )
    df_fisico = (
        pd.read_excel(archivo_fisico)
        if archivo_fisico.name.endswith(".xlsx")
        else pd.read_csv(archivo_fisico)
    )

    st.sidebar.header("⚙️ Configuración de Columnas")
    st.sidebar.markdown(
        "Escribe el nombre exacto de las columnas en tus archivos si no coinciden con los valores por defecto:"
    )

    # Inputs para mapear las columnas dinámicamente
    sku_col = st.sidebar.text_input("Columna de Código SKU", "SKU")
    unidad_col = st.sidebar.text_input("Columna de Unidades Totales", "Unidades")
    pos_col = st.sidebar.text_input(
        "Columna de Ubicación/Posición", "Posicion"
    )  # Nueva clave para el análisis espacial

    if st.sidebar.button("🚀 Ejecutar Análisis Completo"):
        # 1. Cruce de datos por SKU y Posición (para asegurar consistencia espacial)
        # Si tus archivos no tienen posición, el cruce se haría solo por SKU (eliminando pos_col)
        columnas_cruce = (
            [sku_col, pos_col] if pos_col in df_sistema.columns else [sku_col]
        )

        df_completo = pd.merge(
            df_sistema,
            df_fisico,
            on=columnas_cruce,
            suffixes=("_Sistema", "_Fisico"),
        )

        # Determinar nombres de columnas post-cruce
        u_sistema = f"{unidad_col}_Sistema"
        u_fisico = f"{unidad_col}_Fisico"

        # Calcular diferencias numéricas
        df_completo["Diferencia"] = df_completo[u_fisico] - df_completo[u_sistema]
        df_completo["Dif_Absoluta"] = df_completo["Diferencia"].abs()

        # --- SECCIÓN 1: MÉTRICAS CLAVE ---
        st.write("---")
        st.subheader("📌 Resumen Ejecutivo de la Auditoría")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total SKU Auditados", len(df_completo[sku_col].unique()))
        m2.metric("Descuadre Neto (Uds)", int(df_completo["Diferencia"].sum()))
        m3.metric(
            "Impacto Total de Errores (Uds Absolutas)",
            int(df_completo["Dif_Absoluta"].sum()),
        )

        # --- SECCIÓN 2: GRÁFICOS (ZONAS CALIENTES) ---
        st.write("---")
        st.subheader("🔥 Análisis de Zonas Críticas (Zonas Calientes)")

        if pos_col in df_completo.columns:
            # Agrupar errores por posición física
            posiciones = (
                df_completo.groupby(pos_col)["Dif_Absoluta"].sum().reset_index()
            )
            posiciones = posiciones.sort_values(
                by="Dif_Absoluta", ascending=False
            ).head(10)

            fig_pos = px.bar(
                posiciones,
                x=pos_col,
                y="Dif_Absoluta",
                title="Top 10 Ubicaciones con Mayor Descuadre Acumulado",
                labels={"Dif_Absoluta": "Unidades Afectadas"},
                color_discrete_sequence=["#E53E3E"],
            )
            st.plotly_chart(fig_pos, use_container_width=True)
        else:
            st.info(
                "Nota: Para ver el gráfico de Zonas Calientes, introduce una columna de Ubicación/Posición."
            )

        # --- SECCIÓN 3: ALGORITMOS INTELIGENTES DE DETECCIÓN ---
        st.write("---")
        st.subheader("🧠 Diagnósticos Automáticos del Algoritmo")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### 🔄 Mercancía Reubicada (Traspasos sin registrar)")
            st.caption(
                "Detecta SKUs que faltan exactamente en una posición pero sobran en otra."
            )
            faltantes = df_completo[df_completo["Diferencia"] < 0]
            sobrantes = df_completo[df_completo["Diferencia"] > 0]

            reubicaciones = []
            if pos_col in df_completo.columns:
                for _, f in faltantes.iterrows():
                    match = sobrantes[
                        (sobrantes[sku_col] == f[sku_col])
                        & (sobrantes["Diferencia"] == abs(f["Diferencia"]))
                    ]
                    for _, s in match.iterrows():
                        reubicaciones.append(
                            {
                                "SKU": f[sku_col],
                                "Origen (Falta)": f[pos_col],
                                "Destino (Sobra)": s[pos_col],
                                "Cantidad": abs(f["Diferencia"]),
                            }
                        )

            if reubicaciones:
                st.dataframe(pd.DataFrame(reubicaciones), use_container_width=True)
            else:
                st.info("No se encontraron patrones claros de reubicación.")

        with col_b:
            st.markdown("### 🏷️ Posibles Cruces de Talla o Variante")
            st.caption(
                "Detecta cuando en una misma posición sobra una talla y falta otra del mismo artículo."
            )

            cruces_talla = []
            if pos_col in df_completo.columns:
                # Extraer los primeros caracteres antes de un guion como base del producto
                df_completo["Raiz_Articulo"] = df_completo[sku_col].apply(
                    lambda x: str(x).split("-")[0]
                )

                for (pos, raiz), g in df_completo.groupby(
                    [pos_col, "Raiz_Articulo"]
                ):
                    if (
                        len(g) > 1
                        and g["Diferencia"].sum() == 0
                        and (g["Diferencia"] != 0).any()
                    ):
                        detalles = ", ".join(
                            [
                                f"{row[sku_col]}: {int(row['Diferencia'])}"
                                for _, row in g.iterrows()
                                if row["Diferencia"] != 0
                            ]
                        )
                        cruces_talla.append(
                            {
                                "Ubicación": pos,
                                "Artículo Base": raiz,
                                "Descuadre Cruzado": detalles,
                            }
                        )

            if cruces_talla:
                st.dataframe(pd.DataFrame(cruces_talla), use_container_width=True)
            else:
                st.info(
                    "No se detectaron cruces evidentes de variantes en la misma ubicación."
                )

        # --- SECCIÓN 4: REPORTE COMPLETO Y DESCARGA ---
        st.write("---")
        st.subheader("📋 Tabla General de Resultados")
        st.dataframe(df_completo, use_container_width=True)

        # Preparar descarga del informe de diferencias corregido
        csv = df_completo.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="💾 Descargar Informe de Diferencias (CSV)",
            data=csv,
            file_name="informe_auditoria_inventario.csv",
            mime="text/csv",
        )
