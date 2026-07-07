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
    reubicados_units = int(df[df["SKU"].isin(reubicados_skus)]["Dif_Abs"].sum())
    cruces_units = int(df[df.set_index(["Ubicacion", "Raiz"]).index.isin(cruces_index)]["Dif_Abs"].sum())

    # SKU sin diferencia
    ok_items = df[df["Diferencia"] == 0]
    ok_units = int(ok_items["Sistema"].sum())
    ok_skus = ok_items["SKU"].nunique()

    # Porcentajes iniciales
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

    # DIFERENCIAS BRUTAS
    resumen_bruto = df.groupby("SKU").agg(
        Sistema_Total=("Sistema", "sum"),
        Fisico_Total=("Fisico", "sum"),
        Diferencia_Total=("Diferencia", "sum"),
        Diferencia_Absoluta=("Dif_Abs", "sum"),
        Ubicaciones=("Ubicacion", lambda x: ", ".join(sorted(x.unique())))
    ).reset_index()

    # DIFERENCIAS REALES
    df_real = df[df["SKU"].isin(sku_diff[sku_diff != 0].index)]

    resumen_real = df_real.groupby("SKU").agg(
        Sistema_Total=("Sistema", "sum"),
        Fisico_Total=("Fisico", "sum"),
        Diferencia_Total=("Diferencia", "sum"),
        Diferencia_Absoluta=("Dif_Abs", "sum"),
        Ubicaciones=("Ubicacion", lambda x: ", ".join(sorted(x.unique())))
    ).reset_index()

    # --- CRUCES Y REUBICADOS (misma lógica) ---
    cruces_final = []
    reubicaciones_final = []
    restantes = []  # <-- RESTOS agrupados por modelo

    # 1️⃣ CRUCES DE TALLA
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
                cruces_final.append({
                    "Tipo": "Cruce de talla",
                    "Ubicación": ubic,
                    "Modelo": raiz,
                    "Tallas involucradas": detalle
                })
            else:
                restantes.append({
                    "Modelo": raiz,
                    "SKU": f"{raiz}-RESTO",
                    "Diferencia_Total": resto,
                    "Diferencia_Absoluta": abs(resto),
                    "Ubicaciones": ubic
                })

    # 2️⃣ REUBICADOS
    for sku, grupo in df.groupby("SKU"):

        if grupo["Ubicacion"].nunique() > 1:

            grupo_dif = grupo[grupo["Diferencia"] != 0]
            if grupo_dif.empty:
                continue

            resto = grupo_dif["Diferencia"].sum()
            raiz = sku.split("-")[0]

            if resto == 0:
                detalle = ", ".join(
                    f"{row['Ubicacion']} → Dif {row['Diferencia']}"
                    for _, row in grupo_dif.iterrows()
                )
                reubicaciones_final.append({
                    "Tipo": "Reubicado",
                    "SKU": sku,
                    "Modelo": raiz,
                    "Ubicaciones": ", ".join(sorted(grupo["Ubicacion"].unique())),
                    "Detalle diferencias": detalle
                })
            else:
                restantes.append({
                    "Modelo": raiz,
                    "SKU": f"{sku}-RESTO",
                    "Diferencia_Total": resto,
                    "Diferencia_Absoluta": abs(resto),
                    "Ubicaciones": ", ".join(sorted(grupo["Ubicacion"].unique()))
                })

    # Añadir RESTOS agrupados por modelo a diferencias reales
    if restantes:
        df_restantes = pd.DataFrame(restantes)
        resumen_real = pd.concat([resumen_real, df_restantes], ignore_index=True)

    # PANEL PORCENTAJES (sin sumar RESTOS)
    st.write("---")
    st.subheader("📊 Porcentajes Globales del Inventario (unidades reales)")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("LOST reales", f"{pct_lost_real}% | {lost_real_units} uds")
    c2.metric("FOUND reales", f"{pct_found_real}% | {found_real_units} uds")
    c3.metric("Reubicados", f"{pct_reubicados}% | {reubicados_units} uds")
    c4.metric("Cruces de tallas", f"{pct_cruces_talla}% | {cruces_units} uds")
    c5.metric("SKU sin diferencia", f"{pct_ok_units}% | {ok_units} uds", f"{ok_skus} SKU")

    # Mostrar cruces y reubicados compensados
    if cruces_final or reubicaciones_final:
        st.dataframe(pd.DataFrame(cruces_final + reubicaciones_final), use_container_width=True)
    else:
        st.info("No hay cruces ni reubicados que compensen LOST y FOUND.")

    # Mostrar diferencias reales actualizadas
    st.write("---")
    st.subheader("📦 Diferencias por SKU (incluye RESTO agrupado por modelo)")
    st.dataframe(resumen_real, use_container_width=True)

    # ZONAS CRÍTICAS
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
        pd.DataFrame(cruces_final).to_excel(writer, index=False, sheet_name="Cruces Compensados")
        pd.DataFrame(reubicaciones_final).to_excel(writer, index=False, sheet_name="Reubicados Compensados")
        pd.DataFrame(restantes).to_excel(writer, index=False, sheet_name="Restos por Modelo")

    excel_data = output.getvalue()

    st.download_button(
        label="💾 Descargar Excel",
        data=excel_data,
        file_name="reporte_inventario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
