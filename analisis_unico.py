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

    # CRUCES DE TALLAS (mismo modelo)
    df["Raiz"] = df["SKU"].apply(lambda x: str(x).split("-")[0])

    # --- DIFERENCIAS REALES POR SKU ---
    sku_diff = df.groupby("SKU")["Diferencia"].sum()

    lost_real_units = int(sku_diff[sku_diff < 0].abs().sum())
    found_real_units = int(sku_diff[sku_diff > 0].sum())

    # SKU sin diferencia
    ok_items = df[df["Diferencia"] == 0]
    ok_units = int(ok_items["Sistema"].sum())
    ok_skus = ok_items["SKU"].nunique()

    # Porcentajes
    pct_lost_real = round((lost_real_units / total_unidades) * 100, 2)
    pct_found_real = round((found_real_units / total_unidades) * 100, 2)
    pct_ok_units = round((ok_units / total_unidades) * 100, 2)

    diferencia_neta_real = found_real_units - lost_real_units

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

    c1, c2, c3 = st.columns(3)
    c1.metric("LOST reales", f"{pct_lost_real}% | {lost_real_units} uds")
    c2.metric("FOUND reales", f"{pct_found_real}% | {found_real_units} uds")
    c3.metric("SKU sin diferencia", f"{pct_ok_units}% | {ok_units} uds", f"{ok_skus} SKU")

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

    # --- CRUCES DE TALLAS (solo SKU con diferencias y compensación lógica) ---
    st.write("---")
    st.subheader("🏷️ Cruces de Variantes (solo si hay diferencias reales)")

    cruces_final = []

    for (ubic, raiz), grupo in df.groupby(["Ubicacion", "Raiz"]):

        # Solo si hay más de una talla del mismo modelo
        if grupo["SKU"].nunique() > 1:

            # Filtrar solo tallas con diferencias
            grupo_dif = grupo[grupo["Diferencia"] != 0]

            # Si NO hay tallas con diferencia → NO es cruce
            if grupo_dif.empty:
                continue

            # Diferencia neta del modelo (compensación)
            resto = grupo_dif["Diferencia"].sum()

            # Si el modelo se compensa completamente → NO es cruce
            if resto == 0:
                continue

            # Si NO se compensa → mostrar SOLO tallas con diferencia
            tallas_detalle = []

            for _, row in grupo_dif.iterrows():

                dif = row["Diferencia"]

                if dif < 0:
                    estado = f"LOST {abs(dif)}"
                elif dif > 0:
                    estado = f"FOUND {dif}"
                else:
                    estado = "OK (no reubicado)"

                tallas_detalle.append(
                    f"{row['SKU']} → Dif: {dif}, {estado}"
                )

            cruces_final.append({
                "Ubicación": ubic,
                "Modelo": raiz,
                "Tallas involucradas": "; ".join(tallas_detalle)
            })

    df_cruces_final = pd.DataFrame(cruces_final)

    if not df_cruces_final.empty:
        st.dataframe(df_cruces_final, use_container_width=True)
    else:
        st.info("No se detectaron cruces de talla con diferencias reales.")

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
        df_cruces_final.to_excel(writer, index=False, sheet_name="Cruces Detallados")

    excel_data = output.getvalue()

    st.download_button(
        label="💾 Descargar Excel",
        data=excel_data,
        file_name="reporte_inventario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
