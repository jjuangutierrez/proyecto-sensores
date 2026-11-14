import os
import requests
import pandas as pd
from dash import Dash, html, dcc, Input, Output
import plotly.express as px

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000/sensors/")

app = Dash(__name__)
app.title = "Monitoreo de Caldera Industrial"

app.layout = html.Div(style={"fontFamily": "Segoe UI, sans-serif", "padding": "25px", "backgroundColor": "#f8f9fa"}, children=[
    
    html.Div([
        html.H1("Panel de Monitoreo - Caldera Industrial", style={"color": "#1a365d", "marginBottom": "5px"}),
        html.P("Telemetría en tiempo real de variables mecatrónicas (Temperatura, Presión y Velocidad)", style={"color": "#4a5568"})
    ], style={"marginBottom": "20px"}),

    dcc.Interval(id="intervalo-actualizacion", interval=2000, n_intervals=0),

    html.Div(style={
        "display": "flex", "gap": "20px", "backgroundColor": "#ffffff", 
        "padding": "15px", "borderRadius": "8px", "boxShadow": "0 2px 4px rgba(0,0,0,0.05)", "marginBottom": "20px"
    }, children=[
        
        html.Div([
            html.Label("Tipo de Sensor:", style={"fontWeight": "bold", "color": "#2d3748"}),
            dcc.Dropdown(
                id="filtro-tipo",
                options=[
                    {"label": "Todos los tipos", "value": "TODOS"},
                    {"label": "Temperatura (°C)", "value": "temperatura"},
                    {"label": "Presión (kPa)", "value": "presión"},
                    {"label": "Velocidad (m/s)", "value": "velocidad"}
                ],
                value="TODOS",
                clearable=False
            )
        ], style={"flex": "1"}),

        html.Div([
            html.Label("ID del Sensor:", style={"fontWeight": "bold", "color": "#2d3748"}),
            dcc.Dropdown(
                id="filtro-sensor-id",
                placeholder="Todos los IDs",
                clearable=True
            )
        ], style={"flex": "1"}),

        html.Div([
            html.Label("Rango Temporal (Puntos de muestreo):", style={"fontWeight": "bold", "color": "#2d3748"}),
            dcc.RangeSlider(
                id="filtro-tiempo-slider",
                min=0,
                max=5,
                step=1,
                value=[0, 5],
                tooltip={"placement": "bottom", "always_visible": False}
            )
        ], style={"flex": "2"})
    ]),

    html.Div(id="tarjetas-metricas", style={"display": "flex", "gap": "20px", "marginBottom": "25px"}),

    html.Div([
        dcc.Graph(id="grafico-historico-sensores")
    ], style={"backgroundColor": "#ffffff", "padding": "15px", "borderRadius": "8px", "boxShadow": "0 2px 4px rgba(0,0,0,0.05)"})
])


@app.callback(
    [
        Output("filtro-sensor-id", "options"),
        Output("filtro-tiempo-slider", "max"),
        Output("tarjetas-metricas", "children"),
        Output("grafico-historico-sensores", "figure")
    ],
    [
        Input("intervalo-actualizacion", "n_intervals"),
        Input("filtro-tipo", "value"),
        Input("filtro-sensor-id", "value"),
        Input("filtro-tiempo-slider", "value")
    ]
)
def actualizar_panel(n_ticks, tipo_seleccionado, sensor_id_seleccionado, rango_indices):
    try:
        respuesta = requests.get(API_URL, timeout=1.5)
        datos = respuesta.json() if respuesta.status_code == 200 else []
    except requests.exceptions.RequestException:
        datos = []

    if not datos:
        fig_vacia = px.line(title="Sin conexión con la API o sin datos registrados.")
        mensaje_espera = html.Div("Esperando respuesta de la API...", style={"color": "#718096"})
        return [], 0, mensaje_espera, fig_vacia

    df = pd.DataFrame(datos)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)

    opciones_id = [{"label": f"Sensor #{s_id}", "value": s_id} for s_id in sorted(df["sensor_id"].unique())]

    df_filtrado = df.copy()
    if tipo_seleccionado and tipo_seleccionado != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["type"] == tipo_seleccionado]

    if sensor_id_seleccionado is not None:
        df_filtrado = df_filtrado[df_filtrado["sensor_id"] == sensor_id_seleccionado]

    total_registros = len(df_filtrado)
    slider_max = max(total_registros - 1, 1)

    if rango_indices and total_registros > 0:
        inicio = min(rango_indices[0], total_registros - 1)
        fin = min(rango_indices[1], total_registros - 1)
        df_filtrado = df_filtrado.iloc[inicio:fin + 1]

    if not df_filtrado.empty:
        promedio = round(df_filtrado["value"].mean(), 2)
        minimo = round(df_filtrado["value"].min(), 2)
        maximo = round(df_filtrado["value"].max(), 2)

        estilo_tarjeta = {
            "flex": "1", "padding": "15px", "borderRadius": "8px", 
            "color": "#ffffff", "textAlign": "center", "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
        }

        tarjetas = [
            html.Div([
                html.Span("PROMEDIO", style={"fontSize": "12px", "letterSpacing": "1px"}),
                html.H2(f"{promedio}", style={"margin": "5px 0"})
            ], style={**estilo_tarjeta, "backgroundColor": "#2b6cb0"}),

            html.Div([
                html.Span("VALOR MÍNIMO", style={"fontSize": "12px", "letterSpacing": "1px"}),
                html.H2(f"{minimo}", style={"margin": "5px 0"})
            ], style={**estilo_tarjeta, "backgroundColor": "#c53030"}),

            html.Div([
                html.Span("VALOR MÁXIMO", style={"fontSize": "12px", "letterSpacing": "1px"}),
                html.H2(f"{maximo}", style={"margin": "5px 0"})
            ], style={**estilo_tarjeta, "backgroundColor": "#2f855a"})
        ]

        figura = px.line(
            df_filtrado,
            x="timestamp",
            y="value",
            color="type",
            markers=True,
            title="Evolución Temporal de las Mediciones",
            labels={"value": "Medición (Valor)", "timestamp": "Fecha / Hora", "type": "Variable"}
        )
        figura.update_layout(template="plotly_white", hovermode="x unified")

    else:
        tarjetas = [html.Div("No existen mediciones que coincidan con los filtros seleccionados.", style={"color": "#718096"})]
        figura = px.line(title="Sin datos para los filtros actuales.")

    return opciones_id, slider_max, tarjetas, figura


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)