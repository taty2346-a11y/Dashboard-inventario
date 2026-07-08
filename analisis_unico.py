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

    # 🔥 DENOMINADOR CORRECTO: unidades auditadas reales
    total_unidades = df["Fisico"].sum()

    # --- IDENTIFICACIÓN DE REUBICADOS ---
    reubicados_skus = df.groupby("SKU")["Ubicacion"].nunique()
    reubicados_skus = reubicados_skus[reubicados_skus > 1].index
    mask_reubicados = df["SKU"].isin(reubicados_skus)

    # --- IDENTIFICACIÓN DE CRUCES ---
    df["Raiz"] = df["SKU"].apply(lambda x: x.split("-")[0])
    cruces_talla = df.groupby(["Ubicacion", "Raiz"])["SKU"].nunique()
    cruces_detectados = cruces_talla[cruces_talla > 1].index
    mask_cruces = df.set_index(["Ubicacion", "Raiz"]).index.isin(cruces_detectados)

    # --- CATEGORÍAS EXCLUSIVAS ---
    lost_real_units = int(df[(df["Diferencia"] < 0) & ~mask_reubicados & ~mask_cruces]["Fisico"].sum())
    found_real_units = int(df[(df["Diferencia"] > 0) & ~mask_reubicados & ~mask_cruces]["Fisico"].sum())
    reubicados_units = int(df[mask_reubicados]["Fisico"].sum())
    cruces_units = int(df[mask_cruces]["Fisico"].sum())
    ok_units = int(df[(df["Diferencia"] == 0) & ~mask_reubicados & ~mask_cruces]["Fisico"].sum())

    # --- PORCENTAJES EXCLUSIVOS ---
    pct_lost_real = round((lost_real_units / total_unidades) * 100, 2)
    pct_found_real = round((found_real_units / total_unidades) * 100, 2)
    pct_reubicados = round((reubicados_units / total_unidades) * 100, 2)
    pct_cruces_talla = round((cruces_units / total_unidades) * 100, 2)
    pct_ok_units = round((ok_units / total_unidades) * 100, 2)

    # --- PANEL PORCENTAJES ---
    st.write("---")
    st.subheader("📊 Porcentajes Globales del Inventario (categorías exclusivas)")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("LOST reales", f"{pct_lost_real}% | {lost_real_units} uds")
    c2.metric("FOUND reales", f"{pct_found_real}% | {found_real_units} uds")
    c3.metric("Reubicados", f"{pct_reubicados}% | {reubicados_units} uds")
    c4.metric("Cruces de tallas", f"{pct_cruces_talla}% | {cruces_units} uds")
    c5.metric("OK", f"{pct_ok_units}% | {ok_units} uds")

    # --- RESUMEN GENERAL ---
    st.write("---")
    st.subheader("📌 Resumen General")

    m1, m2, m3, m4, m5, m6 = st.columns(6)

    m1.metric("Total SKU", df["SKU"].nunique())
    m2.metric("Unidades Sistema", int(df["Sistema"].sum()))
    m3.metric("Unidades Físico", int(df["Fisico"].sum()))
    m4.metric("LOST reales", lost_real_units)
    m5.metric("FOUND reales", found_real_units)
    m6.metric("Diferencia neta real", found_real_units - lost_real_units)

    # --- GRÁFICO CIRCULAR EXCLUSIVO ---
    st.write("---")
    st.subheader("📊 Distribución de estados (categorías exclusivas)")

    pie_df = pd.DataFrame({
        "Categoria": ["LOST", "FOUND", "Reubicados", "Cruces", "OK"],
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
        title="Distribución de unidades por categoría exclusiva",
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # --- DIFERENCIAS REALES (SIN REUBICADOS NI CRUCES) ---
    st.write("---")
    st.subheader("📦 Diferencias por SKU (solo reales, exclusivas)")

    df_real = df[(df["Diferencia"] != 0) & ~mask_reubicados & ~mask_cruces]

    resumen_real = df_real.groupby("SKU").agg(
        Sistema_Total=("Sistema", "sum"),
        Fisico_Total=("Fisico", "sum"),
        Diferencia_Total=("Diferencia", "sum"),
        Diferencia_Absoluta=("Dif_Abs", "sum"),
        Ubicaciones=("Ubicacion", lambda x: ", ".join(sorted(x.unique())))
    ).reset_index()

    st.dataframe(resumen_real, use_container_width=True)

    # --- ZONAS CRÍTICAS ---
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

    # --- REPORTE COMPLETO ---
    st.write("---")
    st.subheader("📋 Reporte Completo")
    st.dataframe(df, use_container_width=True)

    # --- DESCARGA ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventario")
        resumen_real.to_excel(writer, index=False, sheet_name="Diferencias Reales Exclusivas")

    excel_data = output.getvalue()

    st.download_button(
        label="💾 Descargar Excel",
        data=excel_data,
        file_name="reporte_inventario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
