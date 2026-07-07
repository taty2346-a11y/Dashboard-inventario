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

    # REUBICADOS
    reubicados = df.groupby("SKU")["Ubicacion"].nunique()
    reubicados_skus = reubicados[reubicados > 1].index

    # CRUCES DE TALLAS
    df["Raiz"] = df["SKU"].apply(lambda x: str(x).split("-")[0])
    cruces_talla = df.groupby(["Ubicacion", "Raiz"])["SKU"].nunique()
    cruces_detectados = cruces_talla[cruces_talla > 1]
    cruces_index = cruces_detectados.index  # (Ubicacion, Raiz)

    # Filas que son movimiento (reubicado o cruce de talla)
    mov_mask = (
        df["SKU"].isin(reubicados_skus)
        | df.set_index(["Ubicacion", "Raiz"]).index.isin(cruces_index)
    )

    # --- NUEVA LÓGICA DE LOST / FOUND REALES ---
    # Diferencia neta por SKU (incluye reubicados y cruces)
    sku_diff = df.groupby("SKU")["Diferencia"].sum()

    # LOST real = suma de diferencias negativas netas
    lost_real_units = int(sku_diff[sku_diff < 0].abs().sum())

    # FOUND real = suma de diferencias positivas netas
    found_real_units = int(sku_diff[sku_diff > 0].sum())

    # Unidades en reubicados y cruces (solo informativas)
    reubicados_units = int(df[df["SKU"].isin(reubicados_skus)]["Dif_Abs"].sum())
    cruces_units = int(
        df[df.set_index(["Ubicacion", "Raiz"]).index.isin(cruces_index)]["Dif_Abs"].sum()
    )

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

    # Diferencias netas
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

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("LOST reales", f"{pct_lost_real}% | {lost_real_units} uds")
    c2.metric("FOUND reales", f"{pct_found_real}% | {found_real_units} uds")
    c3.metric("Reubicados", f"{pct_reubicados}% | {reubicados_units} uds")
    c4.metric("Cruces de tallas", f"{pct_cruces_talla}% | {cruces_units} uds")
    c5.metric("SKU sin diferencia", f"{pct_ok_units}% | {ok_units} uds", f"{ok_skus} SKU")

    # RESUMEN GENERAL
    st.write("---")
    st.subheader("📌 Resumen General")

    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)

    m1.metric("Total SKU", df["SKU"].nunique())
    m2.metric("Unidades Sistema", int(df["Sistema"].sum()))
    m3.metric("Unidades Físico", int(df["Fisico"].sum()))
    m4.metric("LOST bruto", f"{lost_raw_units} uds")
    m5.metric("FOUND bruto", f"{found_raw_units} uds")
    m6.metric("Diferencia neta bruta", f"{diferencia_neta_bruta} uds")
    m7.metric("Salud inventario", salud, color_salud)

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

    # DIFERENCIAS POR SKU (BRUTAS)
    st.write("---")
    st.subheader("📦 Diferencias por SKU (brutas, contando reubicados y cambios de talla)")

    resumen_bruto = df.groupby("SKU").agg(
        Sistema_Total=("Sistema", "sum"),
        Fisico_Total=("Fisico", "sum"),
        Diferencia_Total=("Diferencia", "sum"),
        Diferencia_Absoluta=("Dif_Abs", "sum"),
        Ubicaciones=("Ubicacion", lambda x: ", ".join(sorted(x.unique())))
    ).reset_index()

    st.dataframe(resumen_bruto, use_container_width=True)

    # DIFERENCIAS POR SKU (REALES)
    st.write("---")
    st.subheader("📦 Diferencias por SKU (reales, sin movimientos compensados)")

    df_real = df[df["SKU"].isin(sku_diff[sku_diff != 0].index)]

    resumen_real = df_real.groupby("SKU").agg(
        Sistema_Total=("Sistema", "sum"),
        Fisico_Total=("Fisico", "sum"),
        Diferencia_Total=("Diferencia", "sum"),
        Diferencia_Absoluta=("Dif_Abs", "sum"),
        Ubicaciones=("Ubicacion", lambda x: ", ".join(sorted(x.unique())))
    ).reset_index()

    st.dataframe(resumen_real, use_container_width=True)

    # REUBICACIONES
    st.write("---")
    st.subheader("🔄 Reubicaciones Internas")

    reubicaciones = []
    for sku, grupo in df.groupby("SKU"):
        if grupo["Ubicacion"].nunique() > 1:
            reubicaciones.append({
                "SKU": sku,
                "Ubicaciones": ", ".join(sorted(grupo["Ubicacion"].unique())),
                "Total Sistema": grupo["Sistema"].sum(),
                "Total Físico": grupo["Fisico"].sum()
            })

    if reubicaciones:
        st.dataframe(pd.DataFrame(reubicaciones), use_container_width=True)
    else:
        st.info("No se detectaron reubicaciones internas.")

    # CRUCES DE TALLAS
    st.write("---")
    st.subheader("🏷️ Cruces de Variantes")

    cruces = []
    for (ubic, raiz), grupo in df.groupby(["Ubicacion", "Raiz"]):
        if grupo["SKU"].nunique() > 1:
            detalle = ", ".join(
                f"{row['SKU']} ({row['Fisico']})"
                for _, row in grupo.iterrows()
            )
            cruces.append({
                "Ubicación": ubic,
                "Artículo Base": raiz,
                "Variantes": detalle
            })

    if cruces:
        st.dataframe(pd.DataFrame(cruces), use_container_width=True)
    else:
        st.info("No se detectaron variantes mezcladas.")

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
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventario")
        resumen_bruto.to_excel(writer, index=False, sheet_name="Diferencias Brutas")
        resumen_real.to_excel(writer, index=False, sheet_name="Diferencias Reales")

    excel_data = output.getvalue()

    st.download_button(
        label="💾 Descargar Excel",
        data=excel_data,
        file_name="reporte_inventario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
