"""
Dashboard Comportamental - Versión para despliegue en Render
CSV alojado en Google Drive, actualizable con botón
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import os
import io
import requests

# ─────────────────────────────────────────────
# URL del CSV en Google Drive
# Reemplaza el ID por el de tu archivo
# ─────────────────────────────────────────────
GDRIVE_FILE_ID = "1A4uD_jZH3_BRf--SXDDwRetAPpOC61x5W_1foIlWuog"
# Google Sheets → exportar como CSV directo
GDRIVE_URL = f"https://docs.google.com/spreadsheets/d/{GDRIVE_FILE_ID}/export?format=csv"


# ─────────────────────────────────────────────
# 1. CARGA Y TRANSFORMACIÓN DE DATOS
# ─────────────────────────────────────────────

def cargar_datos(url: str = GDRIVE_URL) -> pd.DataFrame:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.content.decode("utf-8-sig")), sep=",")
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el CSV: {e}")
        return pd.DataFrame()

    # Limpiar espacios en columnas de texto
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    df.replace("nan", "N/A", inplace=True)

    # Normalizado: conteo de event_type dentro de cada momento x 3
    df["momento"]    = df["momento"].astype(str).str.strip()
    df["event_type"] = df["event_type"].astype(str).str.strip()
    conteo = df.groupby(["momento", "event_type"])["event_type"].transform("count")
    df["normalizado"] = conteo * 3

    # Fecha y hora desde timestamp
    ts = df["timestamp"].astype(str).str.strip()
    df["fecha"] = ts.str[:10]
    df["hora"]  = ts.str[11:19]
    df.loc[~df["fecha"].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False), "fecha"] = "desconocido"
    df.loc[~df["hora"].str.match(r"^\d{2}:\d{2}:\d{2}$",  na=False), "hora"]  = "desconocido"

    df["momento_num"] = pd.to_numeric(df["momento"], errors="coerce").fillna(0).astype(int)
    df["momento"]     = df["momento"].astype(str)
    df["eje_x"]       = "Momento " + df["momento"] + " | " + df["event_type"]

    return df


# ─────────────────────────────────────────────
# 2. OPCIONES PARA DROPDOWNS
# ─────────────────────────────────────────────

def opciones(df: pd.DataFrame, col: str):
    if df.empty or col not in df.columns:
        return []
    vals = sorted(df[col].dropna().unique().tolist(), key=str)
    return [{"label": str(v), "value": str(v)} for v in vals]


# ─────────────────────────────────────────────
# 3. APP DASH
# ─────────────────────────────────────────────

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], title="Dashboard Comportamental")
server = app.server  # necesario para Render/Gunicorn

cols_tabla = [
    "id", "event_type", "nombre_animal", "momento", "fase",
    "predio", "fecha", "hora", "normalizado",
    "humedad_max", "humedad_min", "temperatura_max", "temperatura_min"
]

app.layout = dbc.Container(fluid=True, children=[

    dbc.Row(dbc.Col(html.H2(
        "Dashboard Comportamental",
        className="text-center my-3",
        style={"color": "#00d4aa", "fontWeight": "bold"}
    ))),

    # Botón actualizar + mensaje de estado
    dbc.Row(dbc.Col([
        dbc.Button(
            "🔄 Actualizar datos",
            id="btn-actualizar",
            color="success",
            className="mb-3 me-3",
            n_clicks=0
        ),
        html.Span(id="msg-estado", style={"color": "#aaa", "fontSize": "13px"})
    ])),

    # Store para guardar los datos en memoria del navegador
    dcc.Store(id="store-datos"),

    # Filtros
    dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([html.Label("Animal",       style={"color": "#aaa"}),
                     dcc.Dropdown(id="f-animal",     multi=True, placeholder="Todos", clearable=True)], md=2),
            dbc.Col([html.Label("Momento",      style={"color": "#aaa"}),
                     dcc.Dropdown(id="f-momento",    multi=True, placeholder="Todos", clearable=True)], md=2),
            dbc.Col([html.Label("Fase",         style={"color": "#aaa"}),
                     dcc.Dropdown(id="f-fase",       multi=True, placeholder="Todos", clearable=True)], md=2),
            dbc.Col([html.Label("Predio",       style={"color": "#aaa"}),
                     dcc.Dropdown(id="f-predio",     multi=True, placeholder="Todos", clearable=True)], md=2),
            dbc.Col([html.Label("Fecha",        style={"color": "#aaa"}),
                     dcc.Dropdown(id="f-fecha",      multi=True, placeholder="Todas", clearable=True)], md=2),
            dbc.Col([html.Label("Hora",         style={"color": "#aaa"}),
                     dcc.Dropdown(id="f-hora",       multi=True, placeholder="Todas", clearable=True)], md=2),
            dbc.Col([html.Label("Tipo de evento", style={"color": "#aaa"}),
                     dcc.Dropdown(id="f-event_type", multi=True, placeholder="Todos", clearable=True)], md=2),
        ], className="g-2")
    ]), className="mb-3", style={"background": "#1e1e2e"}),

    # Gráfica
    dbc.Row(dbc.Col(dcc.Graph(id="histograma", style={"height": "480px"}))),

    # Tabla
    dbc.Row(dbc.Col([
        html.H5("Base comportamental", className="mt-4 mb-2", style={"color": "#00d4aa"}),
        dash_table.DataTable(
            id="tabla",
            columns=[{"name": c, "id": c} for c in cols_tabla],
            page_size=15,
            filter_action="native",
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": "#2d2d44", "color": "#00d4aa", "fontWeight": "bold"},
            style_cell={"backgroundColor": "#1a1a2e", "color": "#e0e0e0", "fontSize": "12px", "padding": "6px"},
            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#22223b"}]
        )
    ]))
])


# ─────────────────────────────────────────────
# CALLBACK 1: cargar datos al iniciar o al presionar "Actualizar"
# ─────────────────────────────────────────────
@app.callback(
    Output("store-datos",  "data"),
    Output("msg-estado",   "children"),
    Output("f-animal",     "options"),
    Output("f-momento",    "options"),
    Output("f-fase",       "options"),
    Output("f-predio",     "options"),
    Output("f-fecha",      "options"),
    Output("f-hora",       "options"),
    Output("f-event_type", "options"),
    Input("btn-actualizar", "n_clicks"),
)
def recargar_datos(n_clicks):
    df = cargar_datos()
    if df.empty:
        msg = "⚠️ No se pudieron cargar los datos. Verifica el enlace de Google Drive."
        opciones_vacias = [] * 7
        return None, msg, *([[]]*7)

    msg = f"✅ Datos actualizados — {len(df)} registros cargados"
    return (
        df.to_dict("records"),
        msg,
        opciones(df, "nombre_animal"),
        opciones(df, "momento"),
        opciones(df, "fase"),
        opciones(df, "predio"),
        opciones(df, "fecha"),
        opciones(df, "hora"),
        opciones(df, "event_type"),
    )


# ─────────────────────────────────────────────
# CALLBACK 2: filtrar y graficar
# ─────────────────────────────────────────────
@app.callback(
    Output("histograma", "figure"),
    Output("tabla",      "data"),
    Input("store-datos",   "data"),
    Input("f-animal",      "value"),
    Input("f-momento",     "value"),
    Input("f-fase",        "value"),
    Input("f-predio",      "value"),
    Input("f-fecha",       "value"),
    Input("f-hora",        "value"),
    Input("f-event_type",  "value"),
)
def actualizar(data, animal, momento, fase, predio, fecha, hora, event_type):
    if not data:
        fig = go.Figure()
        fig.update_layout(title="Presiona 'Actualizar datos' para cargar",
                          paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e", font_color="#aaa")
        return fig, []

    dff = pd.DataFrame(data)
    cols_presentes = [c for c in cols_tabla if c in dff.columns]

    if animal:      dff = dff[dff["nombre_animal"].isin(animal)]
    if momento:     dff = dff[dff["momento"].isin(momento)]
    if fase:        dff = dff[dff["fase"].isin(fase)]
    if predio:      dff = dff[dff["predio"].isin(predio)]
    if fecha:       dff = dff[dff["fecha"].isin(fecha)]
    if hora:        dff = dff[dff["hora"].isin(hora)]
    if event_type:  dff = dff[dff["event_type"].isin(event_type)]

    if dff.empty:
        fig = go.Figure()
        fig.update_layout(title="Sin datos para los filtros seleccionados",
                          paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e", font_color="#aaa")
        return fig, []

    dff = dff.copy()
    conteo = dff.groupby(["momento", "event_type"])["event_type"].transform("count")
    dff["normalizado"] = conteo * 3
    dff["momento_num"] = pd.to_numeric(dff["momento"], errors="coerce").fillna(0).astype(int)
    dff["eje_x"] = "Momento " + dff["momento"].astype(str) + " | " + dff["event_type"].astype(str)

    agrup = (
        dff.drop_duplicates(subset=["momento", "event_type"])
           [["eje_x", "event_type", "momento_num", "normalizado"]]
           .sort_values(["momento_num", "event_type"])
           .reset_index(drop=True)
    )

    fig = px.bar(
        agrup, x="eje_x", y="normalizado", color="event_type", text="normalizado",
        labels={"eje_x": "Momento | Tipo de Evento", "normalizado": "Normalizado"},
        title="Distribución Normalizada por Momento y Tipo de Evento",
        color_discrete_sequence=px.colors.qualitative.Bold,
        category_orders={"eje_x": agrup["eje_x"].tolist()},
    )
    fig.update_traces(textposition="outside", textfont_size=11,
                      marker_line_width=0.5, marker_line_color="white")
    fig.update_layout(
        paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e", font_color="#e0e0e0",
        xaxis_tickangle=-35, legend_title_text="event_type",
        margin=dict(t=60, b=120), bargap=0.25,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#333")

    return fig, dff[cols_presentes].to_dict("records")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
    # Local: http://127.0.0.1:8050
