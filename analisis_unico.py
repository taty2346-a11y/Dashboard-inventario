import pandas as pd
import plotly.express as px
import streamlit as st
import io

st.set_page_config(page_title="Inventario", page_icon="📊", layout="wide")

st.title("📊 Control de Inventario con un Solo Reporte")
st.markdown("Sube un único archivo con columnas: FECHA, Ubicación, SKU, Sistema, Físico")

archivo = st.file_uploader("📥 Cargar Reporte Único (Excel/CSV)", type=["xlsx", "csv"])

if archivo:
    df = (
        pd.read_excel(archivo)
        if archivo.name.endswith(".xlsx")
        else pd.read_csv(archivo)
    )

    # Renombrar columnas
    df = df.rename(columns={
        "FECHA": "Fecha",
        "Ubicación": "Ubicacion",
        "SKU": "SKU",
        "Sistema": "Sistema",
        "Físico": "Fisico"
    })

    # Diferencias
    df["Diferencia"] = df["Fisico"] - df["Sistema"]
    df["Dif_Abs"] = df["Diferencia"].abs()

    total_unidades = df["Sistema"].sum()

    # Clasificación básica
    df["Estado"] = df["Diferencia"].apply(
        lambda x: "FOUND (Sobra)" if x > 0 else ("LOST (Falta)" if x < 0 else "OK")
    )

    # LOST / FOUND brutos
    lost_raw_units = int(df[df["Diferencia"] < 0]["Diferencia"].abs().sum())
    found_raw_units = int(df[df["Diferencia"] > 0]["Diferencia"].sum())

    # REUBICADOS (SKU con varias ubicaciones)
    reubicados = df.groupby("SKU")["Ubicacion"].nunique()
    reubicados_skus = reubicados[reubicados > 1].index

    # CRUCES DE TALLAS
    df["Raiz"] = df["SKU"].apply(lambda x: str(x).split("-")[0])
    cruces_talla = df.groupby(["Ubicacion", "Raiz"])["SKU"].nunique()
    cruces_detectados = cruces_talla[cruces_talla > 1]
    cruces_index = cruces_detectados.index

    # --- DIFERENCIAS REALES POR SKU ---
    sku_diff = df.groupby("SKU")["Diferencia"].sum()

    lost_real_units = int(sku_diff[sku_diff < 0].abs().sum())
    found_real_units = int(sku_diff[sku_diff > 0].sum())

    # Unidades informativas
    resto_units = int(df[(df["Diferencia"] == 0) & ~mask_reubicados & ~mask_cruces]["Fisico"].sum())
    cruces_units = int(df[df.set_index(["Ubicacion", "Raiz"]).index.isin(cruces_index)]["Dif_Abs"].sum())

    # SKU sin diferencia
    ok_items = df[df["Diferencia"] == 0]
    ok_units = int(ok_items["Sistema"].sum())
    ok_skus = ok_items["SKU"].nunique()

    # Porcentajes
    pct_lost_real = round((lost_real_units / total_unidades) * 100, 2)
    pct_found_real = round((found_real_units / total_unidades) * 100, 2)
    pct_reubicados = round((reubicados_units / total_unidades) * 100, 2)
    pct_cruces_talla = round((cruces_units / total_unidades) * 100, 2)
    pct_ok_units = round((ok_units / total_unidades) * 100, 2)

    diferencia_neta_real = found_real_units - lost_real_units
    diferencia_neta_bruta = found_raw_units - lost_raw_units

    # Salud inventario
    if diferencia_neta_real == 0:
        salud = "Excelente — Sin diferencias reales"
        color_salud = "🟢"
    elif abs(diferencia_neta_real) <= total_unidades * 0.01:
        salud = "Buena — Diferencias mínimas"
        color_salud = "🟡"
    else:
        salud = "Crítica — Diferencias significativas"
        color_salud = "🔴"

    # PANEL PORCENTAJES
    st.write("---")
    st.subheader("📊 Porcentajes Globales del Inventario (unidades reales)")

    # Denominador: unidades físicas auditadas
    total_unidades = df["Fisico"].sum()

    # Cálculo del resto
    resto_units = total_unidades - (lost_real_units + found_real_units + cruces_units)
    pct_resto = round((resto_units / total_unidades) * 100, 2)
    
    # Porcentajes sobre FÍSICO real
    pct_lost_real = round((lost_real_units / total_unidades) * 100, 2)
    pct_found_real = round((found_real_units / total_unidades) * 100, 2)
    pct_cruces_talla = round((cruces_units / total_unidades) * 100, 2)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LOST reales", f"{pct_lost_real}% | {lost_real_units} uds")
    c2.metric("FOUND reales", f"{pct_found_real}% | {found_real_units} uds")
    c3.metric("Cruces de tallas", f"{pct_cruces_talla}% | {cruces_units} uds")
    c4.metric("Resto", f"{pct_resto}% | {resto_units} uds")

    # RESUMEN GENERAL
    st.write("---")
    st.subheader("📌 Resumen General")

    m1, m2, m3, m4, m5 = st.columns(5)

    m1.metric("Total SKU", df["SKU"].nunique())
    m2.metric("Unidades Sistema", int(df["Sistema"].sum()))
    m3.metric("Unidades Físico", int(df["Fisico"].sum()))
    m4.metric("Diferencia neta bruta", f"{diferencia_neta_bruta} uds")
    m5.metric("Salud inventario", salud, color_salud)

    # GRÁFICO CIRCULAR
    st.write("---")
    st.subheader("📊 Distribución de estados del inventario")

    pie_df = pd.DataFrame({
        "Categoria": ["LOST reales", "FOUND reales", "Reubicados", "Cruces de talla", "OK"],
        "Unidades": [
            lost_real_units,
            found_real_units,
            reubicados_units,
            cruces_units,
            ok_units
        ]
    })

    fig_pie = px.pie(
        pie_df,
        names="Categoria",
        values="Unidades",
        title="Distribución de unidades por tipo de diferencia",
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # DIFERENCIAS BRUTAS
    st.write("---")
    st.subheader("📦 Diferencias por SKU (brutas)")

    resumen_bruto = df.groupby("SKU").agg(
        Sistema_Total=("Sistema", "sum"),
        Fisico_Total=("Fisico", "sum"),
        Diferencia_Total=("Diferencia", "sum"),
        Diferencia_Absoluta=("Dif_Abs", "sum"),
        Ubicaciones=("Ubicacion", lambda x: ", ".join(sorted(x.unique())))
    ).reset_index()

    st.dataframe(resumen_bruto, use_container_width=True)

    # DIFERENCIAS REALES
    st.write("---")
    st.subheader("📦 Diferencias por SKU (reales)")

    df_real = df[df["SKU"].isin(sku_diff[sku_diff != 0].index)]

    resumen_real = df_real.groupby("SKU").agg(
        Sistema_Total=("Sistema", "sum"),
        Fisico_Total=("Fisico", "sum"),
        Diferencia_Total=("Diferencia", "sum"),
        Diferencia_Absoluta=("Dif_Abs", "sum"),
        Ubicaciones=("Ubicacion", lambda x: ", ".join(sorted(x.unique())))
    ).reset_index()

    st.dataframe(resumen_real, use_container_width=True)

    # REUBICACIONES — SOLO SI COMPENSAN LOST/FOUND
    st.write("---")
    st.subheader("🔄 Reubicaciones Internas (solo si compensan)")

    reubicaciones = []
    restantes_reubicados = []

    for sku, grupo in df.groupby("SKU"):

        if grupo["Ubicacion"].nunique() > 1:

            grupo_dif = grupo[grupo["Diferencia"] != 0]
            if grupo_dif.empty:
                continue

            resto = grupo_dif["Diferencia"].sum()

            if resto == 0:
                reubicaciones.append({
                    "SKU": sku,
                    "Ubicaciones": ", ".join(sorted(grupo["Ubicacion"].unique())),
                    "Detalle diferencias": ", ".join(
                        f"{row['Ubicacion']} → Dif {row['Diferencia']}"
                        for _, row in grupo_dif.iterrows()
                    )
                })
            else:
                restantes_reubicados.append({
                    "SKU": f"{sku}-RESTO",
                    "Sistema_Total": 0,
                    "Fisico_Total": 0,
                    "Diferencia_Total": resto,
                    "Diferencia_Absoluta": abs(resto),
                    "Ubicaciones": ", ".join(sorted(grupo["Ubicacion"].unique()))
                })

    if reubicaciones:
        st.dataframe(pd.DataFrame(reubicaciones), use_container_width=True)
    else:
        st.info("No se detectaron reubicaciones que compensen LOST y FOUND.")

    # CRUCES DE TALLAS — SOLO SI COMPENSAN LOST/FOUND
    st.write("---")
    st.subheader("🏷️ Cruces de Variantes (solo si compensan)")

    cruces = []
    restantes_cruces = []

    for (ubic, raiz), grupo in df.groupby(["Ubicacion", "Raiz"]):

        if grupo["SKU"].nunique() > 1:

            grupo_dif = grupo[grupo["Diferencia"] != 0]
            if grupo_dif.empty:
                continue

            resto = grupo_dif["Diferencia"].sum()

            if resto == 0:
                detalle = ", ".join(
                    f"{row['SKU']} → Dif {row['Diferencia']}"
                    for _, row in grupo_dif.iterrows()
                )
                cruces.append({
                    "Ubicación": ubic,
                    "Artículo Base": raiz,
                    "Variantes con diferencia": detalle
                })
            else:
                restantes_cruces.append({
                    "SKU": f"{raiz}-RESTO",
                    "Sistema_Total": 0,
                    "Fisico_Total": 0,
                    "Diferencia_Total": resto,
                    "Diferencia_Absoluta": abs(resto),
                    "Ubicaciones": ubic
                })

    if cruces:
        st.dataframe(pd.DataFrame(cruces), use_container_width=True)
    else:
        st.info("No se detectaron cruces de talla que compensen LOST y FOUND.")

    # Añadir RESTOS a diferencias reales
    if restantes_reubicados or restantes_cruces:
        resumen_real = pd.concat([
            resumen_real,
            pd.DataFrame(restantes_reubicados),
            pd.DataFrame(restantes_cruces)
        ], ignore_index=True)

    # Mostrar diferencias reales actualizadas
    st.write("---")
    st.subheader("📦 Diferencias por SKU (incluye RESTO por modelo y reubicado)")
    st.dataframe(resumen_real, use_container_width=True)

    # ZONAS CRÍTICAS
    st.write("---")
    st.subheader("🔥 Zonas con Mayor Diferencia")

    zonas = df.groupby("Ubicacion")["Dif_Abs"].sum().reset_index()

    fig = px.bar(
        zonas,
        x="Ubicacion",
        y="Dif_Abs",
        title="Diferencias por Ubicación",
        color="Dif_Abs",
        color_continuous_scale="Reds"
    )
    st.plotly_chart(fig, use_container_width=True)

    # REPORTE COMPLETO
    st.write("---")
    st.subheader("📋 Reporte Completo")
    st.dataframe(df, use_container_width=True)

    # DESCARGA EN EXCEL
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventario")
        resumen_bruto.to_excel(writer, index=False, sheet_name="Diferencias Brutas")
        resumen_real.to_excel(writer, index=False, sheet_name="Diferencias Reales")
        pd.DataFrame(cruces).to_excel(writer, index=False, sheet_name="Cruces Compensados")
        pd.DataFrame(reubicaciones).to_excel(writer, index=False, sheet_name="Reubicados Compensados")

    excel_data = output.getvalue()

    st.download_button(
        label="💾 Descargar Excel",
        data=excel_data,
        file_name="reporte_inventario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
