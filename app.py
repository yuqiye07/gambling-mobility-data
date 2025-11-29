# app.py
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
# !pip install dash 
from dash import Dash, dcc, html, Input, Output

# ---------- LOAD DATA ----------
df_poi_raw_jan = pd.read_csv("df_poi_raw_jan.csv")
df_visits_cnty_geo = pd.read_csv("df_visits_cnty_geo.csv")

# Make sure placekey is string and consistent
df_poi_raw_jan["placekey"] = df_poi_raw_jan["placekey"].astype(str)
df_visits_cnty_geo["placekey"] = df_visits_cnty_geo["placekey"].astype(str)

# ---------- BASE FIGURE (POI MAP) ----------
base_fig = px.scatter_mapbox(
    df_poi_raw_jan,
    lat="latitude",
    lon="longitude",
    hover_name="location_name",
    hover_data={"raw_visit_counts": True, "placekey": True},
    zoom=3,
)

base_fig.update_layout(
    mapbox_style="open-street-map",
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
)

# encode placekey into customdata so we can retrieve it from clickData
base_fig.update_traces(
    marker=dict(size=6),
    customdata=df_poi_raw_jan["placekey"],
    name="Casinos"
)

# ---------- DASH APP ----------
app = Dash(__name__)
app.title = "Casino Visitor Origins"

app.layout = html.Div(
    style={"font-family": "Arial, sans-serif"},
    children=[
        html.H2("Casino Visitor Origins Map"),
        html.P(
            "Click a casino marker to show the home counties of its visitors. "
            "Marker size for counties reflects the number of visits."
        ),
        dcc.Graph(
            id="map",
            figure=base_fig,
            style={"height": "90vh"}
        ),
        html.Div(id="info", style={"marginTop": "10px", "fontSize": "14px"})
    ]
)

# ---------- CALLBACK ----------
@app.callback(
    Output("map", "figure"),
    Output("info", "children"),
    Input("map", "clickData"),
)
def update_map(clickData):
    # Always start from base figure so we don't accumulate traces
    fig = go.Figure(base_fig)

    if clickData is None:
        return fig, "Click a casino to see visitor origin counties."

    # Extract placekey from clicked point
    point = clickData["points"][0]
    placekey_clicked = point.get("customdata")

    # Filter visits for this POI
    tmp = df_visits_cnty_geo[df_visits_cnty_geo["placekey"] == placekey_clicked]

    if tmp.empty:
        return (
            fig,
            f"No county-level visitor data found for placekey {placekey_clicked}."
        )

    # Scale marker size by visits
    visits = tmp["visits"].astype(float)
    if visits.max() > 0:
        sizes = 6 + 18 * (visits / visits.max())  # between ~6 and 24
    else:
        sizes = 8

    fig.add_scattermapbox(
        lat=tmp["lat"],
        lon=tmp["lon"],
        mode="markers",
        marker=dict(
            size=sizes,
            opacity=0.7,
        ),
        name="Visitor counties",
        hovertext=(
            "County: " + tmp["NAME"].astype(str)
            + "<br>FIPS: " + tmp["county"].astype(str)
            + "<br>Visits: " + tmp["visits"].astype(str)
        ),
        hoverinfo="text",
    )

    info_text = (
        f"Selected casino placekey: {placekey_clicked}. "
        f"Distinct origin counties: {tmp['county'].nunique()}, "
        f"total visits in sample: {int(tmp['visits'].sum())}."
    )

    return fig, info_text


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
