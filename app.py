# app.py
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
# !pip install dash 
from dash import Dash, dcc, html, Input, Output

# ---------- LOAD DATA ----------
df_poi_raw_jan = pd.read_csv("df_poi_raw_jan.csv")
df_visits_cnty_geo = pd.read_csv("df_visits_cnty_geo.csv.gz", compression="gzip")

# Make sure placekey is string and consistent
df_poi_raw_jan["placekey"] = df_poi_raw_jan["placekey"].astype(str)
df_visits_cnty_geo["placekey"] = df_visits_cnty_geo["placekey"].astype(str)

# ---------- BASE FIGURE (POI MAP) ----------
base_fig = px.scatter_mapbox(
    df_poi_raw_jan,
    lat="latitude",
    lon="longitude",
    hover_name="location_name",  # this becomes %{hovertext}
    hover_data={},               # we'll control hover ourselves
    zoom=3,
)
base_fig.update_layout(
    mapbox_style="open-street-map",
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
)

# customdata: [placekey, raw_visit_counts] for each point
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
        "<b>%{hovertext}</b><br>"       # location_name
        "Visits: %{customdata[1]}<extra></extra>"
    ),
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
    # start from base fig every time (this resets previous click state)
    fig = go.Figure(base_fig)

    # no click yet → just show all casinos fully visible
    if clickData is None:
        return fig, "Click a casino to see visitor origin counties."

    point = clickData["points"][0]

    # customdata = [placekey, raw_visit_counts]
    placekey_clicked = str(point["customdata"][0])

    # ----- 2a. dim other POIs -----
    mask = df_poi_raw_jan["placekey"].astype(str) == placekey_clicked
    opacities = [1.0 if m else 0.3 for m in mask]

    # POI trace is the first trace in the figure
    fig.data[0].marker.opacity = opacities

    # ----- 2b. county markers for this POI -----
    tmp = df_visits_cnty_geo[df_visits_cnty_geo["placekey"].astype(str) == placekey_clicked]

    if tmp.empty:
        info_text = f"No county-level visitor data found for placekey {placekey_clicked}."
        return fig, info_text

    visits = tmp["visits"].astype(float)
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
        ),
        name="Visitor counties",
        hovertext=(
            "County: " + tmp["county_NAME"].astype(str)
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
