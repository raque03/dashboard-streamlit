import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------

st.set_page_config(page_title="Dashboard Comercial", layout="wide")

st.title("Dashboard Ejecutivo — Desempeño Comercial")

st.write(
"""
Análisis del desempeño comercial considerando ventas, metas, inventario y calidad de datos.
El análisis comercial utiliza ventas válidas y reporta inconsistencias detectadas en los datos.
"""
)

# ----------------------------------------------------
# CARGA AUTOMÁTICA DE DATOS
# ----------------------------------------------------

@st.cache_data
def cargar_datos():

    ventas = pd.read_excel("Ventas.xlsx")
    clientes = pd.read_excel("Clientes.xlsx")
    sucursales = pd.read_excel("Maestro_Sucursales.xlsx")
    metas = pd.read_excel("Metas.xlsx")
    inventario = pd.read_excel("Inventario.xlsx")

    return ventas, clientes, sucursales, metas, inventario


ventas, clientes, sucursales, metas, inventario = cargar_datos()

# ----------------------------------------------------
# LIMPIEZA
# ----------------------------------------------------

ventas["Clave_Sucursal"] = ventas["Clave_Sucursal"].str.upper().str.strip()

ventas["Fecha"] = pd.to_datetime(ventas["Fecha"])
clientes["Fecha_Alta"] = pd.to_datetime(clientes["Fecha_Alta"])

# ----------------------------------------------------
# UNIÓN DE DATOS
# ----------------------------------------------------

ventas_full = ventas.merge(
    clientes,
    on="ID_Cliente",
    how="left"
).merge(
    sucursales,
    on="Clave_Sucursal",
    how="left"
)

# ----------------------------------------------------
# FILTROS
# ----------------------------------------------------

st.sidebar.header("Filtros")

zona = st.sidebar.multiselect(
    "Zona",
    sorted(ventas_full["Zona"].unique()),
    default=sorted(ventas_full["Zona"].unique())
)

sucursal = st.sidebar.multiselect(
    "Sucursal",
    sorted(ventas_full["Nombre_Sucursal"].unique()),
    default=sorted(ventas_full["Nombre_Sucursal"].unique())
)

ventas_full = ventas_full[
    (ventas_full["Zona"].isin(zona)) &
    (ventas_full["Nombre_Sucursal"].isin(sucursal))
]

# ----------------------------------------------------
# ALERTAS DE CALIDAD DE DATOS
# ----------------------------------------------------

ventas_inactivas = ventas_full[
    ventas_full["Activa"] == "No"
]["Monto"].sum()

ventas_cliente_error = ventas_full[
    ventas_full["Fecha"] < ventas_full["Fecha_Alta"]
]["Monto"].sum()

alertas = pd.DataFrame({

    "Problema": [
        "Ventas registradas en sucursal inactiva",
        "Ventas antes del alta del cliente"
    ],

    "Impacto en ventas": [
        ventas_inactivas,
        ventas_cliente_error
    ]
})

# ----------------------------------------------------
# VENTAS PARA ANÁLISIS COMERCIAL
# EXCLUYE SUCURSAL INACTIVA
# ----------------------------------------------------

ventas_comerciales = ventas_full[
    ventas_full["Activa"] == "Sí"
]

# ----------------------------------------------------
# KPIs
# ----------------------------------------------------

ventas_sistema = ventas_full["Monto"].sum()
ventas_validas = ventas_comerciales["Monto"].sum()

c1, c2, c3 = st.columns(3)

c1.metric("Ventas registradas en sistema", f"${ventas_sistema:,.0f}")
c2.metric("Ventas utilizadas para análisis", f"${ventas_validas:,.0f}")
c3.metric("Ventas en sucursal inactiva", f"${ventas_inactivas:,.0f}")

st.divider()

# ----------------------------------------------------
# CRECIMIENTO DE VENTAS
# ----------------------------------------------------

st.subheader("Evolución de ventas")

# Opción para incluir devoluciones
mostrar_devoluciones = st.checkbox("Incluir devoluciones en el análisis", value=True)

if mostrar_devoluciones:
    ventas_filtradas = ventas_comerciales
else:
    ventas_filtradas = ventas_comerciales[ventas_comerciales["Monto"] > 0]

ventas_tiempo = ventas_filtradas.groupby("Fecha")["Monto"].sum().reset_index()

fig_line = px.line(
    ventas_tiempo,
    x="Fecha",
    y="Monto",
    markers=True
)

st.plotly_chart(fig_line, use_container_width=True)


# ----------------------------------------------------
# VENTAS POR ZONA
# ----------------------------------------------------

st.subheader("Ventas por zona")

ventas_zona = ventas_comerciales.groupby("Zona")["Monto"].sum().reset_index()

fig_zona = px.bar(
    ventas_zona,
    x="Zona",
    y="Monto",
    color="Zona",
    text="Monto"
)

fig_zona.update_traces(texttemplate="$%{text:,.0f}")

st.plotly_chart(fig_zona, use_container_width=True)

# ----------------------------------------------------
# VENTAS POR SUCURSAL
# ----------------------------------------------------

st.subheader("Ventas por sucursal")

ventas_sucursal = ventas_comerciales.groupby(
    ["Clave_Sucursal", "Nombre_Sucursal", "Zona"]
)["Monto"].sum().reset_index()

fig_suc = px.bar(
    ventas_sucursal,
    x="Nombre_Sucursal",
    y="Monto",
    color="Zona",
    text="Monto"
)

fig_suc.update_traces(texttemplate="$%{text:,.0f}")

st.plotly_chart(fig_suc, use_container_width=True)

# ----------------------------------------------------
# SUCURSAL LÍDER POR ZONA
# ----------------------------------------------------

st.subheader("Sucursal líder por zona")

lider = ventas_sucursal.loc[
    ventas_sucursal.groupby("Zona")["Monto"].idxmax()
]

st.dataframe(
    lider[["Zona", "Nombre_Sucursal", "Monto"]]
)

# ----------------------------------------------------
# METAS
# ----------------------------------------------------

st.subheader("Ventas vs Meta")

ventas_meta = ventas_sucursal.merge(
    metas,
    on="Clave_Sucursal",
    how="left"
)

ventas_meta["Cumplimiento"] = (
    ventas_meta["Monto"] /
    ventas_meta["Meta_Mensual_Ventas"]
)

ventas_meta["Brecha"] = (
    ventas_meta["Meta_Mensual_Ventas"] -
    ventas_meta["Monto"]
)

col1, col2 = st.columns([3,2])

with col1:

    fig_meta = px.bar(
        ventas_meta,
        x="Nombre_Sucursal",
        y="Cumplimiento",
        color="Zona",
        text=ventas_meta["Cumplimiento"].round(2)
    )

    fig_meta.update_traces(
        texttemplate="%{text:.0%}",
        textposition="outside"
    )

    fig_meta.update_yaxes(
        tickformat=".0%",
        title="Cumplimiento de meta"
    )

    st.plotly_chart(fig_meta, use_container_width=True)

with col2:

    st.write("Resumen por sucursal")

    st.dataframe(
        ventas_meta[
            [
                "Nombre_Sucursal",
                "Monto",
                "Meta_Mensual_Ventas",
                "Brecha"
            ]
        ].style.format({
            "Monto":"${:,.0f}",
            "Meta_Mensual_Ventas":"${:,.0f}",
            "Brecha":"${:,.0f}"
        })
    )

# ------------------------------------------------
# NUEVOS CLIENTES VS META
# ------------------------------------------------

st.subheader("Nuevos clientes vs meta")

# asegurar formato de fecha correcto
clientes["Fecha_Alta"] = pd.to_datetime(clientes["Fecha_Alta"])

# detectar el mes de análisis desde ventas
mes_ventas = ventas["Fecha"].dt.to_period("M").iloc[0]

# filtrar clientes dados de alta en ese mes
clientes_mes = clientes[
    clientes["Fecha_Alta"].dt.to_period("M") == mes_ventas
]

# contar clientes nuevos por sucursal
clientes_nuevos = (
    clientes_mes
    .groupby("Sucursal_Asignada")["ID_Cliente"]
    .count()
    .reset_index()
)

clientes_nuevos.columns = [
    "Clave_Sucursal",
    "Clientes_Nuevos"
]

# unir con metas
clientes_meta = metas.merge(
    clientes_nuevos,
    on="Clave_Sucursal",
    how="left"
)

# rellenar sucursales sin clientes
clientes_meta["Clientes_Nuevos"] = clientes_meta["Clientes_Nuevos"].fillna(0)

# calcular cumplimiento
clientes_meta["Cumplimiento_%"] = (
    clientes_meta["Clientes_Nuevos"] /
    clientes_meta["Meta_Nuevos_Clientes"]
) * 100

# unir con tabla de sucursales
clientes_meta = clientes_meta.merge(
    sucursales[["Clave_Sucursal","Nombre_Sucursal","Zona"]],
    on="Clave_Sucursal",
    how="left"
)

# ------------------------------------------------
# GRAFICA
# ------------------------------------------------

fig_clientes = px.bar(
    clientes_meta,
    x="Nombre_Sucursal",
    y="Cumplimiento_%",
    color="Zona",
    text=clientes_meta["Cumplimiento_%"].round(1),
    title="Cumplimiento de meta de nuevos clientes"
)

fig_clientes.update_traces(
    texttemplate="%{text:.1f}%",
    textposition="outside"
)

fig_clientes.update_yaxes(
    title="Cumplimiento (%)"
)

st.plotly_chart(fig_clientes, use_container_width=True)

# ------------------------------------------------
# TABLA RESUMEN
# ------------------------------------------------

st.dataframe(
    clientes_meta[
        [
            "Nombre_Sucursal",
            "Clientes_Nuevos",
            "Meta_Nuevos_Clientes",
            "Cumplimiento_%"
        ]
    ]
)

# ------------------------------------------------
# ALERTA
# ------------------------------------------------

if clientes_meta["Cumplimiento_%"].mean() < 100:

    st.warning(
        "Las sucursales están muy por debajo de la meta de captación de nuevos clientes."
    )

# ----------------------------------------------------
# INVENTARIO
# ----------------------------------------------------

st.subheader("Inventario por sucursal")

inventario_full = inventario.merge(
    sucursales,
    on="Clave_Sucursal"
)

st.dataframe(inventario_full)

stock_critico = inventario_full[
    inventario_full["Stock_Disponible"] < 50
]

if len(stock_critico) > 0:

    st.warning("Riesgo de desabasto detectado")

    st.dataframe(stock_critico)

# ----------------------------------------------------
# ALERTAS DE DATOS
# ----------------------------------------------------

st.subheader("Alertas de integridad de datos")

st.dataframe(
    alertas.style.format({"Impacto en ventas": "${:,.0f}"})
)

# ----------------------------------------------------
# CONCLUSIONES
# ----------------------------------------------------

st.divider()

st.subheader("Conclusiones del análisis")

st.write(
"""
Se detectaron inconsistencias en los datos del sistema, incluyendo ventas registradas en una sucursal inactiva y ventas anteriores al registro del cliente.
Para el análisis comercial se utilizaron únicamente las ventas de sucursales activas.

El análisis muestra que ciertas sucursales concentran el mayor volumen de ventas, aunque ninguna alcanza las metas establecidas.
También se detecta riesgo operativo debido a inventario bajo en algunas sucursales.
"""
)