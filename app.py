import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title="Control de Inventario Inteligente", page_icon="📊", layout="wide"
)

# Insertar logotipo oficial de Logisfashion
st.sidebar.image("https://www.logisfashion.com/wp-content/uploads/2023/04/logisfashion-logo.png",
    width=200,
                )
    # Mostrar las columnas reales detectadas para ayudar al usuario
    st.info(f"🔍 **Columnas detectadas en Sistema:** {', '.join(df_sistema.columns.tolist())}"
    )
    st.info(f"🔍 **Columnas detectadas en Físico:** {', '.join(df_fisico.columns.tolist())}"
    )

    st.sidebar.header("⚙️ Configuración de Columnas")
    st.sidebar.markdown(
        "Escribe el nombre exacto de las columnas basándote en las listas azules de la pantalla:"
    )

    # Inputs para mapear las columnas dinámicamente
    sku_col = st.sidebar.text_input("Columna de Código SKU", "SKU")
    unidad_col = st.sidebar.text_input("Columna de Unidades Totales", "Unidades")
    pos_col = st.sidebar.text_input(
        "Columna de Ubicación/Posición (Opcional)", "Posicion"
    )

    if st.sidebar.button("🚀 Ejecutar Análisis Completo"):
        # Verificación de seguridad para evitar KeyErrors
        if sku_col not in df_sistema.columns or sku_col not in df_fisico.columns:
            st.error(
                f"❌ El nombre de columna SKU '{sku_col}' no se encuentra en alguno de los dos archivos. Revisa las listas azules."
            )
        elif (
            unidad_col not in df_sistema.columns
            or unidad_col not in df_fisico.columns
        ):
            st.error(
                f"❌ El nombre de columna de Unidades '{unidad_col}' no se encuentra en alguno de los dos archivos. Revisa las listas azules."
            )
        else:
            # Lógica inteligente de cruce dinámico
            usar_posicion = (
                pos_col
                and pos_col in df_sistema.columns
                and pos_col in df_fisico.columns
            )
            columnas_cruce = [sku_col, pos_col] if usar_posicion else [sku_col]

            # Hacer el cruce (Merge)
            df_completo = pd.merge(
                df_sistema,
                df_fisico,
                on=columnas_cruce,
                suffixes=("_Sistema", "_Fisico"),
            )

            # Determinar nombres de columnas de unidades calculadas
            u_sistema = (
                f"{unidad_col}_Sistema"
                if f"{unidad_col}_Sistema" in df_completo.columns
                else f"{unidad_col}_x"
            )
            u_fisico = (
                f"{unidad_col}_Fisico"
                if f"{unidad_col}_Fisico" in df_completo.columns
                else f"{unidad_col}_y"
            )

            # En caso de que las columnas tengan sufijos automáticos de pandas si no se cruzan por posición
            if u_sistema not in df_completo.columns:
                u_sistema = [
                    c for c in df_completo.columns if f"{unidad_col}" in c
                ][0]
                u_f_list = [
                    c for c in df_completo.columns if f"{unidad_col}" in c
                ]
                u_fisico = u_f_list[1] if len(u_f_list) > 1 else u_f_list[0]

            # Calcular diferencias numéricas
            df_completo["Diferencia"] = (
                df_completo[u_fisico] - df_completo[u_sistema]
            )
            df_completo["Dif_Absoluta"] = df_completo["Diferencia"].abs()

            # --- SECCIÓN 1: MÉTRICAS CLAVE ---
            st.write("---")
            st.subheader("📌 Resumen Ejecutivo de la Auditoría")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total SKU Auditados", len(df_completo[sku_col].unique()))
            m2.metric(
                "Descuadre Neto (Uds)", int(df_completo["Diferencia"].sum())
            )
            m3.metric(
                "Impacto Total de Errores (Uds Absolutas)",
                int(df_completo["Dif_Absoluta"].sum()),
            )

            # --- SECCIÓN 2: GRÁFICOS (ZONAS CALIENTES) ---
            st.write("---")
            st.subheader("🔥 Análisis de Zonas Críticas (Zonas Calientes)")

            if usar_posicion:
                posiciones = (
                    df_completo.groupby(pos_col)["Dif_Absoluta"]
                    .sum()
                    .reset_index()
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
                    color_discrete_sequence=["#00818A"],
                )
                st.plotly_chart(fig_pos, use_container_width=True)
            else:
                st.warning(
                    "⚠️ No se pudo generar el gráfico de posiciones porque la columna de ubicación no coincide o no existe en ambos archivos. El resto del análisis sigue disponible abajo."
                )

            # --- SECCIÓN 3: ALGORITMOS INTELIGENTES DE DETECCIÓN ---
            st.write("---")
            st.subheader("🧠 Diagnósticos Automáticos del Algoritmo")

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("### 🔄 Mercancía Reubicada (Traspasos sin registrar)")
                faltantes = df_completo[df_completo["Diferencia"] < 0]
                sobrantes = df_completo[df_completo["Diferencia"] > 0]

                reubicaciones = []
                if usar_posicion:
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
                    st.dataframe(
                        pd.DataFrame(reubicaciones), use_container_width=True
                    )
                else:
                    st.info(
                        "No se encontraron patrones claros de reubicación o falta mapear la columna de posición."
                    )

            with col_b:
                st.markdown("### 🏷️ Posibles Cruces de Talla o Variante")
                cruces_talla = []
                if usar_posicion:
                    df_completo["Raiz_Articulo"] = df_completo[sku_col].apply(
                        lambda x: str(x).split("-")[0]
                    )

                    for (pos, raiz), g in df_completo.groupby(
                        [pos_col, "Raiz_Articulo"]
                    ):
                        if (
                            len(g) > 1
                            and g["Diferencia"].sum() == 0
                            and (g["g_diff"] != 0).any()
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
                    st.dataframe(
                        pd.DataFrame(cruces_talla), use_container_width=True
                    )
                else:
                    st.info(
                        "No se detectaron cruces evidentes de variantes o falta mapear la columna de posición."
                    )

            # --- SECCIÓN 4: REPORTE COMPLETO Y DESCARGA ---
            st.write("---")
            st.subheader("📋 Tabla General de Resultados")
            st.dataframe(df_completo, use_container_width=True)

            csv = df_completo.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="💾 Descargar Informe de Diferencias (CSV)",
                data=csv,
                file_name="informe_auditoria_inventario.csv",
                mime="text/csv",
            )
