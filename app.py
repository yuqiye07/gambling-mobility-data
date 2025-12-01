# app.py
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from dash import Dash, dcc, html, Input, Output

# ---------- LOAD DATA ----------
df_poi_raw_jan = pd.read_csv("df_poi_raw_jan.csv")
df_visits_cnty_geo = pd.read_csv("df_visits_cnty_geo.csv.gz", compression="gzip")

# Make sure placekey is string and consistent
df_poi_raw_jan["placekey"] = df_poi_raw_jan["placekey"].astype(str)
df_visits_cnty_geo["placekey"] = df_visits_cnty_geo["placekey"].astype(str)

# ---------- PRE-GROUP VISITS BY PLACEKEY (performance) ----------
df_visits_small = df_visits_cnty_geo[[
    "placekey", "county", "NAME", "lat", "lon", "visits"
]].copy()

df_visits_small["placekey"] = df_visits_small["placekey"].astype(str)
df_visits_small["visits"] = df_visits_small["visits"].astype(float)

visits_by_placekey = {
    pk: grp.reset_index(drop=True)
    for pk, grp in df_visits_small.groupby("placekey")
}

# ---------- BASE FIGURE (POI MAP) ----------
base_fig = px.scatter_mapbox(
    df_poi_raw_jan,
    lat="latitude",
    lon="longitude",
    hover_name="location_name",  # becomes %{hovertext}
    hover_data={},               # we control hover ourselves
    zoom=3,
)
base_fig.update_layout(
    mapbox_style="open-street-map",
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
)

# customdata: [placekey, raw_visit_counts]
poi_customdata = np.stack(
    [
        df_poi_raw_jan["placekey"].astype(str),
        df_poi_raw_jan["raw_visit_counts"].astype(int),
    ],
    axis=-1,
)

base_fig.update_traces(
    marker=dict(size=6, opacity=1.0),
    customdata=poi_customdata,
    name="Casinos",
    hovertemplate=(
        "<b>%{hovertext}</b><br>"
        "Visitors: %{customdata[1]}<extra></extra>"
    ),
)

# ---------- DASH APP ----------
app = Dash(__name__)
app.title = "Casino Visitor Origins"

app.layout = html.Div(
    style={"font-family": "Arial, sans-serif"},
    children=[
        html.H2("Casino Visitor Origins Map (data from January 2019)"),
        html.P([
            "The blue markers represent gambling locations, inclusing casinos, casino hotels, and other gambling venues. ",
            html.Br(),
            "Click a casino marker to show the home counties of its visitors (in red markers). ",
            html.Br(),
            "Marker size for counties reflects the number of visitors."
    ]),
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
    # start from base fig every time (this resets previous click state)
    fig = go.Figure(base_fig)

    if clickData is None:
        return fig, "Click a casino to see visitor origin counties."

    point = clickData["points"][0]
    cd = point.get("customdata")

    # customdata = [placekey, raw_visit_counts] or scalar
    if isinstance(cd, (list, tuple)) and len(cd) > 0:
        placekey_clicked = str(cd[0])
        raw_visits = cd[1] if len(cd) > 1 else None
    else:
        placekey_clicked = str(cd)
        raw_visits = None

    # ----- dim other POIs -----
    mask = df_poi_raw_jan["placekey"].astype(str) == placekey_clicked
    opacities = [1.0 if m else 0.3 for m in mask]
    fig.data[0].marker.opacity = opacities

    # ----- county markers for this POI (fast dict lookup) -----
    tmp = visits_by_placekey.get(placekey_clicked)
    if tmp is None or tmp.empty:
        info_text = (
            f"Clicked placekey: {placekey_clicked} "
            f"(raw_visit_counts={raw_visits}). "
            "No county-level visitor data found for this POI."
        )
        return fig, info_text

    visits = tmp["visits"]
    if visits.max() > 0:
        sizes = 6 + 18 * (visits / visits.max())
    else:
        sizes = 8

    fig.add_scattermapbox(
    lat=tmp["lat"],
    lon=tmp["lon"],
    mode="markers",
    marker=dict(
        size=sizes,
        opacity=0.7,
        color="red",       # <--- add this
    ),
    name="Visitor counties",
    hovertext=(
        "County: " + tmp["NAME"].astype(str)
        + "<br>FIPS: " + tmp["county"].astype(str)
        + "<br>Visitors: " + tmp["visits"].astype(int).astype(str)
    ),
    hoverinfo="text",
)


    info_text = (
        f"Clicked placekey: {placekey_clicked} "
        f"(raw_visit_counts={raw_visits}). "
        f"Matched county rows: {len(tmp)}. "
        f"Distinct origin counties: {tmp['county'].nunique()}, "
        f"total visitors in sample: {int(tmp['visits'].sum())}."
    )

    return fig, info_text


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
